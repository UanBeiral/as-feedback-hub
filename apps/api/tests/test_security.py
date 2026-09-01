"""Testes de credencial e token.

O teste central aqui é `test_aceita_hash_no_formato_do_supabase`: ele é a versão
automatizada da apuração de AMB-013. Se ele quebrar, a migração de credenciais deixou
de funcionar e a decisão AD-03 precisa ser revista antes do cutover, não durante.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import bcrypt
import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    PasswordHasher,
    PasswordTooLongError,
    TokenService,
    hash_refresh_token,
)

SEGREDO = "chave-de-teste-com-mais-de-32-caracteres-ok"


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(rounds=12)


@pytest.fixture
def tokens() -> TokenService:
    return TokenService(
        Settings(jwt_secret=SEGREDO, database_url="postgresql+asyncpg://x/y")  # type: ignore[call-arg]
    )


def test_hash_e_verify_ida_e_volta(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("senha-correta")
    assert hasher.verify("senha-correta", hashed)
    assert not hasher.verify("senha-errada", hashed)


def test_aceita_hash_no_formato_do_supabase(hasher: PasswordHasher) -> None:
    """GoTrue grava bcrypt com prefixo `$2a$` e custo 10.

    Reproduzimos exatamente esse formato para provar que a auth nova valida a senha de
    quem já tem conta, sem redefinição em massa (R-07).
    """
    legado = bcrypt.hashpw(b"senha-do-usuario", bcrypt.gensalt(10, prefix=b"2a"))
    hash_legado = legado.decode()

    assert hash_legado.startswith("$2a$10$")
    assert hasher.verify("senha-do-usuario", hash_legado)
    assert not hasher.verify("outra-senha", hash_legado)


def test_hash_legado_pede_rehash_e_o_novo_nao(hasher: PasswordHasher) -> None:
    hash_legado = bcrypt.hashpw(b"x", bcrypt.gensalt(10, prefix=b"2a")).decode()
    assert hasher.needs_rehash(hash_legado), "custo 10 < 12 deveria pedir regravação"
    assert not hasher.needs_rehash(hasher.hash("x"))


def test_hash_corrompido_falha_como_senha_errada(hasher: PasswordHasher) -> None:
    # Nunca deve levantar exceção: um registro estragado no banco não pode virar 500,
    # nem revelar que aquele e-mail existe.
    assert not hasher.verify("qualquer", "isto-nao-e-um-hash")
    assert not hasher.verify("qualquer", "")


def test_senha_acima_do_limite_do_bcrypt_e_rejeitada(hasher: PasswordHasher) -> None:
    # bcrypt ignora além de 72 bytes; truncar em silêncio faria duas senhas distintas
    # abrirem a mesma conta.
    with pytest.raises(PasswordTooLongError):
        hasher.hash("a" * 73)


def test_access_token_carrega_papel_e_flags(tokens: TokenService) -> None:
    user_id, tenant_id = uuid4(), uuid4()
    token, expira = tokens.create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role="gestor",
        flags=frozenset({"can_generate_reports"}),
    )

    claims = tokens.decode_access_token(token)
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id
    assert claims.role == "gestor"
    assert claims.flags == frozenset({"can_generate_reports"})
    assert expira > datetime.now(UTC)


def test_token_assinado_com_outro_segredo_e_recusado(tokens: TokenService) -> None:
    outro = TokenService(
        Settings(  # type: ignore[call-arg]
            jwt_secret="outro-segredo-com-mais-de-32-caracteres!!", database_url="postgresql+asyncpg://x/y"
        )
    )
    token, _ = outro.create_access_token(
        user_id=uuid4(), tenant_id=uuid4(), role="admin", flags=frozenset()
    )
    with pytest.raises(InvalidTokenError):
        tokens.decode_access_token(token)


def test_refresh_token_nao_e_guardado_em_claro(tokens: TokenService) -> None:
    refresh = tokens.create_refresh_token()
    assert refresh.digest != refresh.plain
    assert len(refresh.digest) == 64
    assert hash_refresh_token(refresh.plain) == refresh.digest
