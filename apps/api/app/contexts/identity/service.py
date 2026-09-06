"""Casos de uso do aggregate UserAccount.

Aqui moram as invariantes de sessão (BR-MIGRAR-016/018): quem pode entrar, o que o
token carrega, e o que acontece quando um refresh token aparece duas vezes. O router
não decide nada disso — ele traduz HTTP para chamada de método e de volta.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.contexts.identity.models import (
    PasswordResetToken,
    Profile,
    RefreshToken,
    User,
)
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

# Curto de propósito: o link chega por e-mail, e e-mail é caixa que fica aberta em
# máquina compartilhada. Uma hora cobre "pedi, fui almoçar e voltei"; um dia cobriria
# também quem passar pela mesa amanhã.
TTL_DO_RESET = timedelta(hours=1)


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

    async def solicitar_reset(
        self,
        *,
        email: str,
        tenant_slug: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[UUID, UUID, str] | None:
        """Cria o token de redefinição. `None` quando não há a quem mandar.

        Quem chama **não** deve transformar o `None` em erro visível: a resposta da rota
        é a mesma com e sem conta, senão a tela vira um verificador de quem trabalha no
        escritório. É a mesma decisão do `_CREDENCIAIS_INVALIDAS`.

        Conta inativa também recebe `None`: quem foi desligado não volta por um link de
        senha (BR-MIGRAR-016/018).
        """
        tenant = await self._repo.get_tenant_by_slug(tenant_slug or self._default_tenant_slug)
        if tenant is None:
            return None

        user = await self._repo.get_user_by_email(tenant.id, email)
        if user is None or not user.can_sign_in:
            return None

        plain = secrets.token_urlsafe(48)
        self._repo.add_reset_token(
            PasswordResetToken(
                tenant_id=tenant.id,
                user_id=user.id,
                token_digest=hash_refresh_token(plain),
                expires_at=datetime.now(UTC) + TTL_DO_RESET,
                requested_ip=ip_address,
            )
        )
        return tenant.id, user.id, plain

    async def confirmar_reset(self, *, token: str, nova_senha: str) -> None:
        """Gasta o token e troca a senha.

        Todas as sessões daquela pessoa caem junto. Quem redefine senha ou esqueceu a
        anterior ou desconfia que alguém a tem — nos dois casos, deixar de pé a sessão
        que já estava aberta noutro lugar é deixar de pé exatamente o que o reset veio
        fechar.
        """
        linha = await self._repo.reivindicar_reset_token(hash_refresh_token(token))
        if linha is None:
            raise AuthenticationError("Link inválido ou expirado")

        user = await self._repo.get_user(linha.tenant_id, linha.user_id)
        if user is None or not user.can_sign_in:
            raise AuthenticationError("Link inválido ou expirado")

        user.password_hash = self._hasher.hash(nova_senha)
        await self._repo.revoke_all_for_user(linha.tenant_id, linha.user_id)

    async def refresh_session(
        self, *, refresh_token: str, user_agent: str | None = None, ip_address: str | None = None
    ) -> TokenPair:
        digest = hash_refresh_token(refresh_token)
        stored = await self._repo.get_refresh_token(digest)
        if stored is None:
            raise AuthenticationError("Sessão inválida")

        now = datetime.now(UTC)
        if stored.revoked_at is not None or stored.expires_at <= now:
            raise AuthenticationError("Sessão expirada")

        # Rotaciona antes de qualquer outra coisa, e num passo só: é a reivindicação
        # atômica que decide quem fica com o token. Ler `used_at` e gravar depois
        # deixava duas renovações simultâneas do mesmo token passarem juntas — e a
        # segunda a chegar derrubava a sessão de quem apenas recarregou a página.
        if not await self._repo.reivindicar_refresh_token(digest):
            # O token é de uso único. Uma segunda apresentação significa que alguém
            # tem uma cópia: não dá para saber se é o dono ou o ladrão, então as duas
            # sessões caem e o login é refeito.
            # Commita em transação própria: o `raise` logo abaixo faz a requisição
            # dar rollback, e sem isso a revogação não sobreviveria.
            await self._repo.revoke_all_for_user(stored.tenant_id, stored.user_id)
            raise AuthenticationError("Sessão encerrada por segurança. Entre novamente.")

        user = await self._repo.get_user(stored.tenant_id, stored.user_id)
        if user is None or not user.can_sign_in:
            raise AuthenticationError("Conta inativa. Procure o administrador.")

        profile = await self._repo.get_profile_by_user(stored.tenant_id, user.id)
        if profile is None or profile.status != "active":
            raise AuthenticationError("Conta inativa. Procure o administrador.")

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
        return _to_current_user(user, profile, active_role=tenant.active_role)

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


def _to_current_user(user: User, profile: Profile, *, active_role: str = "") -> CurrentUser:
    return CurrentUser(
        user_id=user.id,
        profile_id=profile.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=profile.full_name,
        role=profile.role,
        active_role=active_role or profile.role,
        job_title=profile.job_title,
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
        # `enxerga_como`, e não `has_role`: aqui é **visão**, e o papel ativo manda
        # (BR-MIGRAR-016 / PAR-05). Um admin que trocou o contexto para gestor passa a
        # ver a equipe dele, que é o ponto de trocar. Como a troca só desce na
        # hierarquia, isso restringe — nunca amplia. Autorização continua olhando o
        # papel persistido, em `require_role`.
        if tenant.enxerga_como("admin", "rh"):
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
