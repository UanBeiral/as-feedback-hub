"""Casos de uso de sessão (`AuthService`).

Cobre a parte de PAR-08 que é decidida no service: quem consegue entrar, quem é
recusado, e o que acontece quando um refresh token aparece pela segunda vez. Os
repositórios são dublês em memória — o que está sob teste é a regra, não o SQL.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.contexts.identity.models import Profile, RefreshToken, Tenant, User
from app.contexts.identity.repository import AuthRepository
from app.contexts.identity.service import AuthService
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.core.security import PasswordHasher, TokenService, hash_refresh_token

SEGREDO = "chave-de-teste-com-mais-de-32-caracteres-ok"
SENHA = "senha-correta"


class FakeAuthRepository:
    """Dublê do `AuthRepository` com a mesma superfície usada pelo service."""

    def __init__(self, tenant: Tenant, user: User | None, profile: Profile | None) -> None:
        self._tenant = tenant
        self._user = user
        self._profile = profile
        self.refresh_tokens: list[RefreshToken] = []
        self.revogacoes: list[tuple[UUID, UUID]] = []
        self.last_login_tocado = False

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        return self._tenant if slug == self._tenant.slug else None

    async def get_user_by_email(self, tenant_id: UUID, email: str) -> User | None:
        if self._user is None or self._user.tenant_id != tenant_id:
            return None
        return self._user if self._user.email == email else None

    async def get_user(self, tenant_id: UUID, user_id: UUID) -> User | None:
        if self._user is None or self._user.tenant_id != tenant_id:
            return None
        return self._user if self._user.id == user_id else None

    async def get_profile_by_user(self, tenant_id: UUID, user_id: UUID) -> Profile | None:
        return self._profile

    async def get_refresh_token(self, digest: str) -> RefreshToken | None:
        return next((t for t in self.refresh_tokens if t.token_digest == digest), None)

    def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.refresh_tokens.append(token)
        return token

    async def revoke_all_for_user(self, tenant_id: UUID, user_id: UUID) -> None:
        self.revogacoes.append((tenant_id, user_id))
        for t in self.refresh_tokens:
            t.revoked_at = datetime.now(UTC)

    async def touch_last_login(self, user: User) -> None:
        self.last_login_tocado = True


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(rounds=10)  # custo baixo: são muitos hashes por suíte


@pytest.fixture
def tokens() -> TokenService:
    return TokenService(
        Settings(jwt_secret=SEGREDO, database_url="postgresql+asyncpg://x/y")  # type: ignore[call-arg]
    )


def _cenario(
    hasher: PasswordHasher,
    *,
    user_status: str = "active",
    profile_status: str = "active",
    senha_hash: str | None = None,
) -> FakeAuthRepository:
    tenant = Tenant(id=uuid4(), slug="as", name="A&S", status="active")
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="pessoa@exemplo.com",
        password_hash=senha_hash or hasher.hash(SENHA),
        status=user_status,
    )
    profile = Profile.for_user(
        user, full_name="Pessoa", role="colaborador", status=profile_status
    )
    return FakeAuthRepository(tenant, user, profile)


def _service(
    repo: FakeAuthRepository, hasher: PasswordHasher, tokens: TokenService
) -> AuthService:
    return AuthService(  # type: ignore[arg-type]
        repository=repo, hasher=hasher, tokens=tokens, default_tenant_slug="as"
    )


async def test_login_valido_emite_par_e_guarda_refresh(hasher, tokens) -> None:
    repo = _cenario(hasher)
    par = await _service(repo, hasher, tokens).authenticate(
        email="pessoa@exemplo.com", password=SENHA
    )

    assert par.access_token and par.refresh_token
    assert repo.last_login_tocado
    # O que vai para o banco é o digest; o segredo em claro só existe na resposta.
    assert len(repo.refresh_tokens) == 1
    assert repo.refresh_tokens[0].token_digest == hash_refresh_token(par.refresh_token)


async def test_senha_errada_e_email_inexistente_dao_a_mesma_resposta(hasher, tokens) -> None:
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)

    with pytest.raises(AuthenticationError) as senha_errada:
        await service.authenticate(email="pessoa@exemplo.com", password="outra")
    with pytest.raises(AuthenticationError) as sem_conta:
        await service.authenticate(email="ninguem@exemplo.com", password=SENHA)

    assert senha_errada.value.message == sem_conta.value.message


@pytest.mark.parametrize("status", ["inactive", "deleted"])
async def test_usuario_desligado_nao_entra(hasher, tokens, status: str) -> None:
    """PAR-08: usuário inativo ou removido não recebe sessão nova."""
    repo = _cenario(hasher, user_status=status)
    with pytest.raises(AuthenticationError):
        await _service(repo, hasher, tokens).authenticate(
            email="pessoa@exemplo.com", password=SENHA
        )
    assert repo.refresh_tokens == []


async def test_perfil_removido_bloqueia_mesmo_com_usuario_ativo(hasher, tokens) -> None:
    repo = _cenario(hasher, profile_status="deleted")
    with pytest.raises(AuthenticationError):
        await _service(repo, hasher, tokens).authenticate(
            email="pessoa@exemplo.com", password=SENHA
        )


async def test_hash_do_supabase_e_regravado_no_primeiro_login(tokens) -> None:
    """R-07 / AMB-013: o único momento em que temos a senha em claro."""
    import bcrypt

    hasher = PasswordHasher(rounds=12)
    legado = bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt(10, prefix=b"2a")).decode()
    repo = _cenario(hasher, senha_hash=legado)

    await _service(repo, hasher, tokens).authenticate(email="pessoa@exemplo.com", password=SENHA)

    assert repo._user is not None
    assert repo._user.password_hash != legado
    assert not hasher.needs_rehash(repo._user.password_hash)


async def test_refresh_rotaciona_e_marca_o_anterior_como_usado(hasher, tokens) -> None:
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)
    primeiro = await service.authenticate(email="pessoa@exemplo.com", password=SENHA)

    segundo = await service.refresh_session(refresh_token=primeiro.refresh_token)

    assert segundo.refresh_token != primeiro.refresh_token
    assert repo.refresh_tokens[0].used_at is not None
    assert len(repo.refresh_tokens) == 2


async def test_reuso_de_refresh_derruba_todas_as_sessoes(hasher, tokens) -> None:
    """A regra que o rollback do request silenciava (ver `autonomous_session`).

    Um refresh token é de uso único. Segunda apresentação significa que existe uma
    cópia por aí — e como não dá para saber quem é o dono, as duas sessões caem.
    """
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)
    par = await service.authenticate(email="pessoa@exemplo.com", password=SENHA)
    await service.refresh_session(refresh_token=par.refresh_token)

    with pytest.raises(AuthenticationError):
        await service.refresh_session(refresh_token=par.refresh_token)

    assert len(repo.revogacoes) == 1, "reúso tem que revogar as sessões do usuário"
    assert all(t.revoked_at is not None for t in repo.refresh_tokens)


async def test_refresh_de_usuario_removido_e_negado(hasher, tokens) -> None:
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)
    par = await service.authenticate(email="pessoa@exemplo.com", password=SENHA)

    assert repo._user is not None
    repo._user.status = "deleted"

    with pytest.raises(AuthenticationError):
        await service.refresh_session(refresh_token=par.refresh_token)


async def test_refresh_expirado_e_negado(hasher, tokens) -> None:
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)
    par = await service.authenticate(email="pessoa@exemplo.com", password=SENHA)
    repo.refresh_tokens[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)

    with pytest.raises(AuthenticationError):
        await service.refresh_session(refresh_token=par.refresh_token)


async def test_logout_e_idempotente(hasher, tokens) -> None:
    repo = _cenario(hasher)
    service = _service(repo, hasher, tokens)
    par = await service.authenticate(email="pessoa@exemplo.com", password=SENHA)

    await service.logout(refresh_token=par.refresh_token)
    await service.logout(refresh_token=par.refresh_token)
    await service.logout(refresh_token="token-que-nunca-existiu")

    assert repo.refresh_tokens[0].revoked_at is not None


async def test_revogacao_roda_em_transacao_propria(monkeypatch) -> None:
    """Guarda estrutural do B1.

    Se a revogação voltar a usar a sessão da requisição, o rollback que acompanha o
    `AuthenticationError` a desfaz e o detector de reúso vira enfeite. O teste vigia o
    mecanismo, porque o sintoma (token roubado que continua válido) não aparece em
    nenhum teste de caminho feliz.
    """
    import app.contexts.identity.repository as repo_mod

    class _SessaoAutonoma:
        def __init__(self, registro: list[str]) -> None:
            self._registro = registro

        async def execute(self, *_args: object, **_kwargs: object) -> object:
            self._registro.append("execute")
            return object()

    class _CtxAutonomo:
        def __init__(self, registro: list[str]) -> None:
            self._registro = registro

        async def __aenter__(self) -> _SessaoAutonoma:
            self._registro.append("abriu")
            return _SessaoAutonoma(self._registro)

        async def __aexit__(self, *_exc: object) -> bool:
            self._registro.append("commitou")
            return False

    registro: list[str] = []
    monkeypatch.setattr(repo_mod, "autonomous_session", lambda: _CtxAutonomo(registro))

    class _SessaoDoRequest:
        async def execute(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("revogação usou a sessão da requisição")

    await AuthRepository(_SessaoDoRequest()).revoke_all_for_user(uuid4(), uuid4())  # type: ignore[arg-type]

    assert registro == ["abriu", "execute", "commitou"]
