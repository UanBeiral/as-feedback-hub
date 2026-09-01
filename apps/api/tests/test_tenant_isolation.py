"""Guard de isolamento multi-tenant (AD-10 / R-09).

Estes testes não exercitam comportamento: eles vigiam uma decisão estrutural. Como
descartamos o RLS, nada no banco impede uma query de atravessar tenants — a única
defesa é que todo modelo de domínio tenha `tenant_id` e todo repositório parta de
`_scoped()`. Um teste que roda no CI transforma essa disciplina em falha de build,
que é o único jeito de ela sobreviver a pressa e a gente nova no time.

Quando um contexto novo entrar, importe seus models e repositórios em
`_import_all_contexts()`, senão eles ficam de fora da vigilância sem ninguém notar.
"""

from __future__ import annotations

import importlib
from uuid import uuid4

import pytest

from app.core.db import Base
from app.core.tenancy import TenantContext, TenantScopedRepository

# Única tabela legitimamente sem `tenant_id`: ela é o próprio tenant.
TABELAS_SEM_TENANT = {"tenants"}

CONTEXTOS = ["identity"]


def _import_all_contexts() -> None:
    for ctx in CONTEXTOS:
        importlib.import_module(f"app.contexts.{ctx}.models")
        importlib.import_module(f"app.contexts.{ctx}.repository")


def _all_scoped_repositories() -> list[type[TenantScopedRepository]]:
    _import_all_contexts()
    encontrados: list[type[TenantScopedRepository]] = []
    pendentes = list(TenantScopedRepository.__subclasses__())
    while pendentes:
        cls = pendentes.pop()
        encontrados.append(cls)
        pendentes.extend(cls.__subclasses__())
    return encontrados


def test_toda_tabela_de_dominio_tem_tenant_id() -> None:
    _import_all_contexts()
    sem_tenant = [
        nome
        for nome, tabela in Base.metadata.tables.items()
        if nome not in TABELAS_SEM_TENANT and "tenant_id" not in tabela.columns
    ]
    assert not sem_tenant, (
        f"Tabelas de domínio sem `tenant_id`: {sem_tenant}. "
        "Ou a tabela ganha tenant_id, ou entra em TABELAS_SEM_TENANT com justificativa."
    )


def test_tenant_id_nunca_e_nulavel() -> None:
    _import_all_contexts()
    nulaveis = [
        nome
        for nome, tabela in Base.metadata.tables.items()
        if "tenant_id" in tabela.columns and tabela.columns["tenant_id"].nullable
    ]
    assert not nulaveis, f"`tenant_id` nulável permite linha órfã: {nulaveis}"


def test_existe_pelo_menos_um_repositorio_vigiado() -> None:
    # Protege contra o cenário silencioso: alguém renomeia a base, a descoberta
    # devolve lista vazia, e os testes abaixo passam sem verificar nada.
    assert _all_scoped_repositories(), "Nenhum TenantScopedRepository encontrado"


@pytest.mark.parametrize("repo_cls", _all_scoped_repositories(), ids=lambda c: c.__name__)
def test_scoped_filtra_por_tenant(repo_cls: type[TenantScopedRepository]) -> None:
    tenant = TenantContext(
        tenant_id=uuid4(), user_id=uuid4(), role="colaborador", flags=frozenset()
    )
    repo = repo_cls(session=None, tenant=tenant)  # type: ignore[arg-type]
    sql = str(repo._scoped())
    assert "tenant_id" in sql, f"{repo_cls.__name__}._scoped() não filtra por tenant: {sql}"


def test_add_carimba_o_tenant_do_contexto() -> None:
    """Quem chama `add` não escolhe o tenant — senão o isolamento vira convenção."""
    from app.contexts.identity.models import Profile

    tenant_correto = uuid4()
    tenant = TenantContext(
        tenant_id=tenant_correto, user_id=uuid4(), role="admin", flags=frozenset()
    )

    class _SessionFake:
        def __init__(self) -> None:
            self.adicionados: list[object] = []

        def add(self, entity: object) -> None:
            self.adicionados.append(entity)

    from app.contexts.identity.repository import ProfileRepository

    session = _SessionFake()
    repo = ProfileRepository(session=session, tenant=tenant)  # type: ignore[arg-type]

    profile = Profile(
        tenant_id=uuid4(),  # tenant errado de propósito
        user_id=uuid4(),
        full_name="Alguém",
        role="colaborador",
    )
    repo.add(profile)

    assert profile.tenant_id == tenant_correto
    assert session.adicionados == [profile]
