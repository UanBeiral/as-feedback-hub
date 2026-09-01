"""Casos de uso do aggregate UserAccount.

Aqui moram as invariantes de sessão (BR-MIGRAR-016/018): quem pode entrar, o que o
token carrega, e o que acontece quando um refresh token aparece duas vezes. O router
não decide nada disso — ele traduz HTTP para chamada de método e de volta.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.contexts.identity.models import Profile, RefreshToken, User
from app.contexts.identity.repository import (
    AuthRepository,
    CoordinatorMemberRepository,
    ProfileRepository,
)
from app.contexts.identity.schemas import CapabilityFlags, CurrentUser, TokenPair
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import PasswordHasher, TokenService, hash_refresh_token
from app.core.tenancy import TenantContext

# Mensagem única para qualquer falha de login. Distinguir "e-mail não existe" de
# "senha errada" entrega meio segredo a quem está tentando adivinhar.
_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos"


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        default_tenant_slug: str,
    ) -> None:
        self._repo = repository
        self._hasher = hasher
        self._tokens = tokens
        self._default_tenant_slug = default_tenant_slug

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
        tenant_slug: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        tenant = await self._repo.get_tenant_by_slug(tenant_slug or self._default_tenant_slug)
        if tenant is None:
            self._hasher.dummy_verify()
            raise AuthenticationError(_CREDENCIAIS_INVALIDAS)

        user = await self._repo.get_user_by_email(tenant.id, email)
        if user is None:
            self._hasher.dummy_verify()
            raise AuthenticationError(_CREDENCIAIS_INVALIDAS)

        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError(_CREDENCIAIS_INVALIDAS)

        # Senha correta, mas conta desligada: BR-MIGRAR-016/018.
        if not user.can_sign_in:
            raise AuthenticationError("Conta inativa. Procure o administrador.")

        profile = await self._repo.get_profile_by_user(tenant.id, user.id)
        if profile is None or profile.status != "active":
            raise AuthenticationError("Conta inativa. Procure o administrador.")

        # Migração de credencial (R-07 / AMB-013): o hash veio do Supabase com custo
        # menor que o nosso, e este é o único momento em que temos a senha em claro
        # para regravá-lo. Silencioso de propósito — o usuário não precisa saber.
        if self._hasher.needs_rehash(user.password_hash):
            user.password_hash = self._hasher.hash(password)

        await self._repo.touch_last_login(user)
        return self._issue_pair(user, profile, user_agent=user_agent, ip_address=ip_address)

    async def refresh_session(
        self, *, refresh_token: str, user_agent: str | None = None, ip_address: str | None = None
    ) -> TokenPair:
        stored = await self._repo.get_refresh_token(hash_refresh_token(refresh_token))
        if stored is None:
            raise AuthenticationError("Sessão inválida")

        if stored.used_at is not None:
            # O token é de uso único. Uma segunda apresentação significa que alguém
            # tem uma cópia: não dá para saber se é o dono ou o ladrão, então as duas
            # sessões caem e o login é refeito.
            await self._repo.revoke_all_for_user(stored.tenant_id, stored.user_id)
            raise AuthenticationError("Sessão encerrada por segurança. Entre novamente.")

        now = datetime.now(UTC)
        if stored.revoked_at is not None or stored.expires_at <= now:
            raise AuthenticationError("Sessão expirada")

        user = await self._repo.get_user(stored.tenant_id, stored.user_id)
        if user is None or not user.can_sign_in:
            raise AuthenticationError("Conta inativa. Procure o administrador.")

        profile = await self._repo.get_profile_by_user(stored.tenant_id, user.id)
        if profile is None or profile.status != "active":
            raise AuthenticationError("Conta inativa. Procure o administrador.")

        stored.used_at = now
        return self._issue_pair(user, profile, user_agent=user_agent, ip_address=ip_address)

    async def logout(self, *, refresh_token: str) -> None:
        """Idempotente: token desconhecido não é erro, a sessão já não vale."""
        stored = await self._repo.get_refresh_token(hash_refresh_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)

    async def logout_all(self, tenant: TenantContext) -> None:
        await self._repo.revoke_all_for_user(tenant.tenant_id, tenant.user_id)

    async def describe_current_user(self, tenant: TenantContext) -> CurrentUser:
        user = await self._repo.get_user(tenant.tenant_id, tenant.user_id)
        profile = await self._repo.get_profile_by_user(tenant.tenant_id, tenant.user_id)
        if user is None or profile is None:
            raise AuthenticationError("Sessão inválida")
        return _to_current_user(user, profile)

    def _issue_pair(
        self,
        user: User,
        profile: Profile,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        access, expires_at = self._tokens.create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=profile.role,
            flags=profile.flags,
        )
        refresh = self._tokens.create_refresh_token()
        row = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_digest=refresh.digest,
            expires_at=refresh.expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._repo.add_refresh_token(row)
        return TokenPair(access_token=access, refresh_token=refresh.plain, expires_at=expires_at)


def _to_current_user(user: User, profile: Profile) -> CurrentUser:
    return CurrentUser(
        user_id=user.id,
        profile_id=profile.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=profile.full_name,
        role=profile.role,
        is_coordinator=profile.is_coordinator,
        department_id=profile.department_id,
        manager_id=profile.manager_id,
        flags=CapabilityFlags(
            can_request_client_feedback=profile.can_request_client_feedback,
            can_view_feedback_answers=profile.can_view_feedback_answers,
            can_view_team_history=profile.can_view_team_history,
            can_generate_reports=profile.can_generate_reports,
            can_view_manager_dashboard=profile.can_view_manager_dashboard,
        ),
    )


class TeamScopeService:
    """Resolução de escopo de equipe (BR-MIGRAR-017).

    A regra é **união, não substituição**: quem coordena e também gerencia enxerga os
    dois conjuntos. O legado errava aqui — tratava coordenação como se substituísse a
    gerência, e coordenador que também era gestor perdia a própria equipe de vista.

    O contrato desta classe é: o escopo sai daqui e de nenhum outro lugar. Parâmetro de
    requisição pode *filtrar* dentro do que este método devolveu, jamais ampliar
    (R-04 / R-09).
    """

    def __init__(
        self,
        profiles: ProfileRepository,
        coordinator_members: CoordinatorMemberRepository,
    ) -> None:
        self._profiles = profiles
        self._coordinator_members = coordinator_members

    async def resolve_visible_profile_ids(self, tenant: TenantContext) -> set[UUID]:
        if tenant.has_role("admin", "rh"):
            return await self._profiles.list_active_ids()

        profile = await self._profiles.get_by_user(tenant.user_id)
        if profile is None or profile.status != "active":
            return set()

        visible = {profile.id}
        visible |= await self._profiles.list_direct_report_ids(profile.id)
        if profile.is_coordinator:
            visible |= await self._coordinator_members.list_member_ids(profile.id)
        return visible

    async def assert_can_view(self, tenant: TenantContext, target_profile_id: UUID) -> None:
        """Guard de escopo — o último elo da cadeia de AD-02, o que os outros três
        (tenant, papel, flag) não conseguem checar sozinhos."""
        if target_profile_id not in await self.resolve_visible_profile_ids(tenant):
            raise AuthorizationError(
                "Perfil fora do seu escopo de equipe",
                details={"profile_id": str(target_profile_id)},
            )
