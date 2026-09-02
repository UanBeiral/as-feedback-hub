"""Revalidação de sessão a cada requisição — PAR-08 § "Acesso revogado imediatamente".

O access token vale 15 minutos. Sem a consulta de `assert_session_active`, um usuário
removido continuaria trabalhando durante essa janela, e o cenário é `@critico` — ou
seja, bloqueador de cutover. Estes testes prendem o comportamento nos dois sentidos:
sessão viva passa, qualquer um dos três estados fora de `active` derruba.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.di import client_ip
from app.core.errors import AuthenticationError
from app.core.tenancy import assert_session_active

ATIVA = {"user_status": "active", "tenant_status": "active", "profile_status": "active"}


class _Resultado:
    def __init__(self, linha: dict[str, str] | None) -> None:
        self._linha = linha

    def mappings(self) -> _Resultado:
        return self

    def first(self) -> dict[str, str] | None:
        return self._linha


class _SessaoFake:
    def __init__(self, linha: dict[str, str] | None) -> None:
        self._linha = linha
        self.consultas = 0

    async def execute(self, *_args: object, **_kwargs: object) -> _Resultado:
        self.consultas += 1
        return _Resultado(self._linha)


async def _checar(linha: dict[str, str] | None) -> _SessaoFake:
    sessao = _SessaoFake(linha)
    await assert_session_active(sessao, tenant_id=uuid4(), user_id=uuid4())  # type: ignore[arg-type]
    return sessao


async def test_sessao_ativa_passa() -> None:
    sessao = await _checar(dict(ATIVA))
    assert sessao.consultas == 1


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("user_status", "deleted"),
        ("user_status", "inactive"),
        ("profile_status", "deleted"),
        ("profile_status", "inactive"),
        ("tenant_status", "inactive"),
    ],
)
async def test_qualquer_estado_fora_de_ativo_derruba(campo: str, valor: str) -> None:
    with pytest.raises(AuthenticationError):
        await _checar({**ATIVA, campo: valor})


async def test_linha_ausente_falha_fechada() -> None:
    """Usuário apagado de verdade, ou perfil que nunca existiu: nega, não passa."""
    with pytest.raises(AuthenticationError):
        await _checar(None)


async def test_perfil_inexistente_nao_vira_none_silencioso() -> None:
    # O LEFT JOIN devolve NULL quando não há perfil; `None != "active"` nega.
    with pytest.raises(AuthenticationError):
        await _checar({**ATIVA, "profile_status": None})  # type: ignore[dict-item]


class _RequestFake:
    def __init__(self, headers: dict[str, str], peer: str | None = "203.0.113.9") -> None:
        self.headers = headers
        self.client = type("_C", (), {"host": peer})() if peer else None


def test_client_ip_ignora_x_forwarded_for_falsificavel() -> None:
    """O Nginx usa `$proxy_add_x_forwarded_for`, que anexa ao que o cliente mandou.

    Quem lê o primeiro elemento do XFF está lendo texto escrito pelo cliente. Hoje isso
    só sujaria `refresh_tokens.ip_address`; vira bypass no dia em que algo for chaveado
    por IP.
    """
    request = _RequestFake(
        {"x-forwarded-for": "10.0.0.1, 198.51.100.7", "x-real-ip": "198.51.100.7"}
    )
    assert client_ip(request) == "198.51.100.7"  # type: ignore[arg-type]


def test_client_ip_cai_para_o_peer_sem_proxy() -> None:
    assert client_ip(_RequestFake({})) == "203.0.113.9"  # type: ignore[arg-type]


def test_client_ip_sem_peer_nao_explode() -> None:
    assert client_ip(_RequestFake({}, peer=None)) == "unknown"  # type: ignore[arg-type]
