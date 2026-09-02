"""Repositórios do contexto `identity`.

`AuthRepository` é a única exceção legítima ao `TenantScopedRepository`, e por um motivo
de ordem: no login o tenant ainda não foi resolvido — resolvê-lo *é* o trabalho. Por
isso todo método aqui recebe `tenant_id` explicitamente e nenhum aceita consulta
cross-tenant implícita. Fora do login, use `ProfileRepository`, que herda o escopo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.models import (
    CoordinatorMember,
    Department,
    Profile,
    ProfileDepartment,
    RefreshToken,
    TeamRequest,
    Tenant,
    User,
)
from app.core.db import autonomous_session
from app.core.tenancy import TenantScopedRepository


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.status == "active")
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, tenant_id: UUID, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user(self, tenant_id: UUID, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.tenant_id == tenant_id, User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_profile_by_user(self, tenant_id: UUID, user_id: UUID) -> Profile | None:
        result = await self._session.execute(
            select(Profile).where(Profile.tenant_id == tenant_id, Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_refresh_token(self, digest: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_digest == digest)
        )
        return result.scalar_one_or_none()

    def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self._session.add(token)
        return token

    async def revoke_all_for_user(self, tenant_id: UUID, user_id: UUID) -> None:
        """Derruba todas as sessões do usuário, em transação própria.

        A sessão é autônoma porque o principal chamador — a detecção de reúso de
        refresh token — revoga **e em seguida levanta** `AuthenticationError`. Na
        transação da requisição, o rollback do `get_session` desfaria a revogação e o
        token roubado continuaria valendo: o detector viraria enfeite. Aqui a revogação
        commita sozinha e sobrevive ao erro.

        Revogar é sempre o lado seguro de errar, então persistir mesmo com a requisição
        falhando é a direção certa (ver `core/db.autonomous_session`).
        """
        async with autonomous_session() as session:
            await session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.tenant_id == tenant_id,
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(UTC))
            )

    async def touch_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)


class ProfileRepository(TenantScopedRepository[Profile]):
    model = Profile

    async def get_by_user(self, user_id: UUID) -> Profile | None:
        result = await self._session.execute(self._scoped().where(Profile.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 500, offset: int = 0) -> list[Profile]:
        stmt = (
            self._scoped()
            .where(Profile.status == "active")
            .order_by(Profile.full_name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_ids(self, profile_ids: set[UUID]) -> list[Profile]:
        """Perfis ativos de um conjunto já resolvido pelo `TeamScopeService`.

        O filtro é do banco de propósito: buscar uma página de perfis e peneirar em
        Python omite silenciosamente quem cair fora do LIMIT — um bug que só aparece
        quando a empresa cresce, e aparece como "sumiu gente da minha equipe".
        """
        if not profile_ids:
            return []
        stmt = (
            self._scoped()
            .where(Profile.id.in_(profile_ids), Profile.status == "active")
            .order_by(Profile.full_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_direct_reports(self, manager_id: UUID) -> list[Profile]:
        stmt = self._scoped().where(
            Profile.manager_id == manager_id, Profile.status == "active"
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_ids(self) -> set[UUID]:
        result = await self._session.execute(
            self._scoped().where(Profile.status == "active").with_only_columns(Profile.id)
        )
        return set(result.scalars().all())

    async def list_ids_por_papel(self, *papeis: str) -> list[UUID]:
        """Perfis ativos de determinados papéis — quem a gestão precisa avisar."""
        stmt = (
            self._scoped()
            .where(Profile.role.in_(papeis), Profile.status == "active")
            .with_only_columns(Profile.id)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def contar_admins_ativos(self) -> int:
        """Usado antes de remover alguém: o tenant não pode ficar sem administrador."""
        stmt = (
            select(func.count())
            .select_from(Profile)
            .where(
                Profile.tenant_id == self.tenant_id,
                Profile.role == "admin",
                Profile.status == "active",
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_direct_report_ids(self, manager_id: UUID) -> set[UUID]:
        stmt = (
            self._scoped()
            .where(Profile.manager_id == manager_id, Profile.status == "active")
            .with_only_columns(Profile.id)
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())


class UserRepository(TenantScopedRepository[User]):
    """Escrita de credencial. A leitura de login continua no `AuthRepository`, que é
    quem trabalha antes de o tenant existir no contexto."""

    model = User

    def add_user(self, user: User) -> User:
        return self.add(user)


class DepartmentRepository(TenantScopedRepository[Department]):
    model = Department

    async def list_all_ordenado(self) -> list[Department]:
        stmt = self._scoped().order_by(Department.name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_por_nome(self, name: str) -> Department | None:
        stmt = self._scoped().where(Department.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class ProfileDepartmentRepository(TenantScopedRepository[ProfileDepartment]):
    model = ProfileDepartment

    async def list_ids_do_perfil(self, profile_id: UUID) -> set[UUID]:
        stmt = (
            self._scoped()
            .where(ProfileDepartment.profile_id == profile_id)
            .with_only_columns(ProfileDepartment.department_id)
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def substituir(self, profile_id: UUID, department_ids: list[UUID]) -> None:
        """Troca o conjunto inteiro de departamentos adicionais.

        Apagar e reinserir, em vez de calcular a diferença: a lista é pequena, a
        operação é atômica dentro da transação, e o resultado é exatamente o que veio
        na requisição — sem sobra de vínculo antigo que ninguém percebe.
        """
        await self._session.execute(
            delete(ProfileDepartment).where(
                ProfileDepartment.tenant_id == self.tenant_id,
                ProfileDepartment.profile_id == profile_id,
            )
        )
        for department_id in dict.fromkeys(department_ids):
            self.add(
                ProfileDepartment(profile_id=profile_id, department_id=department_id)
            )


class TeamRequestRepository(TenantScopedRepository[TeamRequest]):
    model = TeamRequest

    async def get_pendente(
        self, requester_id: UUID, requested_member_id: UUID
    ) -> TeamRequest | None:
        stmt = self._scoped().where(
            TeamRequest.requester_id == requester_id,
            TeamRequest.requested_member_id == requested_member_id,
            TeamRequest.status == "pending",
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def list_pendentes_para(self, manager_id: UUID) -> list[TeamRequest]:
        """Pedidos que este gestor precisa decidir."""
        stmt = (
            self._scoped()
            .where(TeamRequest.status == "pending", TeamRequest.requester_id == manager_id)
            .order_by(TeamRequest.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class CoordinatorMemberRepository(TenantScopedRepository[CoordinatorMember]):
    model = CoordinatorMember

    async def get_vinculo(
        self, coordinator_id: UUID, member_id: UUID
    ) -> CoordinatorMember | None:
        stmt = self._scoped().where(
            CoordinatorMember.coordinator_id == coordinator_id,
            CoordinatorMember.member_id == member_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_member_ids(self, coordinator_id: UUID) -> set[UUID]:
        """Membros sob coordenação, restrito aos perfis ativos do mesmo tenant.

        O join com `Profile` não é decoração: sem ele, um vínculo antigo apontando para
        alguém já desligado continuaria ampliando o escopo do coordenador.
        """
        stmt = (
            select(CoordinatorMember.member_id)
            .join(Profile, Profile.id == CoordinatorMember.member_id)
            .where(
                CoordinatorMember.tenant_id == self.tenant_id,
                CoordinatorMember.coordinator_id == coordinator_id,
                Profile.tenant_id == self.tenant_id,
                Profile.status == "active",
            )
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())
