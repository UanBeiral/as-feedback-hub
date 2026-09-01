"""Repositórios do contexto `identity`.

`AuthRepository` é a única exceção legítima ao `TenantScopedRepository`, e por um motivo
de ordem: no login o tenant ainda não foi resolvido — resolvê-lo *é* o trabalho. Por
isso todo método aqui recebe `tenant_id` explicitamente e nenhum aceita consulta
cross-tenant implícita. Fora do login, use `ProfileRepository`, que herda o escopo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.models import (
    CoordinatorMember,
    Profile,
    RefreshToken,
    Tenant,
    User,
)
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
        """Usado no logout total e na detecção de reúso de refresh token."""
        await self._session.execute(
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

    async def list_direct_report_ids(self, manager_id: UUID) -> set[UUID]:
        stmt = (
            self._scoped()
            .where(Profile.manager_id == manager_id, Profile.status == "active")
            .with_only_columns(Profile.id)
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())


class CoordinatorMemberRepository(TenantScopedRepository[CoordinatorMember]):
    model = CoordinatorMember

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
