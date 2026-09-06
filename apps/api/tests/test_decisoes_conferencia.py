"""As três decisões do cliente de 06/09/2026 (#19, #35/#36 e #59 da conferência).

Cada uma tem uma propriedade que só um teste segura: a classificação de sensibilidade não
pode reescrever o passado, a remoção de equipe não pode virar "gestor pode tudo", e a
descrição do departamento não pode sumir num update.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.contexts.engagement.service import ACOES_SENSIVEIS
from app.contexts.identity.admin_service import DepartmentService, TeamMembershipService
from app.contexts.identity.models import Department, Profile
from app.core.errors import NotFoundError, ValidationError
from app.core.tenancy import TenantContext

TENANT = uuid4()


def _contexto(user_id: UUID) -> TenantContext:
    return TenantContext(tenant_id=TENANT, user_id=user_id, role="gestor", flags=frozenset())


def _perfil(**campos) -> Profile:
    pid = campos.pop("id", uuid4())
    base = {
        "id": pid,
        "user_id": pid,
        "tenant_id": TENANT,
        "full_name": "Alguém",
        "role": "colaborador",
        "status": "active",
        "is_coordinator": False,
    }
    return Profile(**{**base, **campos})


class FakeProfiles:
    def __init__(self, perfis: list[Profile]) -> None:
        self.perfis = perfis

    async def get(self, profile_id: UUID) -> Profile | None:
        return next((p for p in self.perfis if p.id == profile_id), None)


class FakeCoordinators:
    def __init__(self, vinculos: list[tuple[UUID, UUID]] | None = None) -> None:
        self.vinculos = vinculos or []
        self.removidos: list[tuple[UUID, UUID]] = []

    async def get_vinculo(self, coordinator_id: UUID, member_id: UUID):
        par = (coordinator_id, member_id)
        return par if par in self.vinculos else None

    async def remove(self, vinculo) -> None:
        self.vinculos.remove(vinculo)
        self.removidos.append(vinculo)


class FakeAudit:
    def __init__(self) -> None:
        self.registros: list[dict] = []

    async def record(self, tenant, **campos) -> None:
        self.registros.append(campos)


# ---------------------------------------------------------------- sensibilidade


def test_catalogo_de_sensiveis_e_o_que_muda_poder_ou_apaga_trabalho() -> None:
    """A régua está escrita no módulo; o teste impede que ela derive sem querer.

    O ponto do cartão "ações sensíveis" é apontar o que pede olho. Se cadastrar usuário
    ou trocar a própria senha entrassem, o número inflaria e o alerta perderia o sentido
    — o mesmo motivo pelo qual o Diagnóstico deixa desequilíbrio de carga de fora.
    """
    assert {
        "profile.role_changed",
        "profile.flags_changed",
        "profile.soft_deleted",
        "user.password_reset",
        "request.cancelled",
    } == ACOES_SENSIVEIS
    assert "user.registered" not in ACOES_SENSIVEIS
    assert "user.password_changed" not in ACOES_SENSIVEIS


def test_migration_e_codigo_classificam_a_mesma_coisa() -> None:
    """A migration duplica o catálogo de propósito — e a cópia tem que bater.

    Uma migration não importa código de aplicação, que muda embaixo dela. O preço da
    duplicação é este teste; sem ele, o backfill classificaria o passado com uma régua e
    o presente com outra.
    """
    caminho = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0006_descricao_e_sensibilidade.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0006", caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    assert set(modulo.ACOES_SENSIVEIS) == set(ACOES_SENSIVEIS)


# ---------------------------------------------------------------- remoção de equipe


async def test_gestor_direto_remove_e_a_pessoa_continua_no_escritorio() -> None:
    gestora = _perfil(role="gestor")
    membro = _perfil(manager_id=gestora.id)
    audit = FakeAudit()
    servico = TeamMembershipService(
        FakeProfiles([gestora, membro]),  # type: ignore[arg-type]
        FakeCoordinators(),  # type: ignore[arg-type]
        audit,  # type: ignore[arg-type]
    )

    await servico.remove_from_my_team(_contexto(gestora.id), membro.id)

    assert membro.manager_id is None
    assert membro.status == "active", "sair da equipe não é sair do escritório"
    assert audit.registros[0]["action"] == "team.member_removed"
    assert audit.registros[0]["details"]["vinculo"] == "manager"


async def test_coordenador_remove_o_vinculo_de_coordenacao() -> None:
    coord = _perfil(is_coordinator=True)
    membro = _perfil()
    vinculos = FakeCoordinators([(coord.id, membro.id)])
    servico = TeamMembershipService(
        FakeProfiles([coord, membro]),  # type: ignore[arg-type]
        vinculos,  # type: ignore[arg-type]
        FakeAudit(),  # type: ignore[arg-type]
    )

    await servico.remove_from_my_team(_contexto(coord.id), membro.id)

    assert vinculos.removidos == [(coord.id, membro.id)]


async def test_quem_so_enxerga_nao_remove() -> None:
    """Ver alguém não dá direito de remover.

    Um coordenador enxerga os liderados do próprio gestor (o escopo é união) e não tem
    nada a decidir sobre eles. 404 e não 403: o erro não confirma que o vínculo existe.
    """
    outra_gestora = _perfil(role="gestor")
    membro = _perfil(manager_id=outra_gestora.id)
    intrometido = _perfil(is_coordinator=True)
    servico = TeamMembershipService(
        FakeProfiles([outra_gestora, membro, intrometido]),  # type: ignore[arg-type]
        FakeCoordinators(),  # type: ignore[arg-type]
        FakeAudit(),  # type: ignore[arg-type]
    )

    with pytest.raises(NotFoundError):
        await servico.remove_from_my_team(_contexto(intrometido.id), membro.id)

    assert membro.manager_id == outra_gestora.id


async def test_lideranca_direta_sai_antes_da_coordenacao() -> None:
    """Quem é liderado **e** coordenado perde o vínculo mais forte.

    Se sobrasse a coordenação, a pessoa continuaria na equipe depois de "sair dela".
    """
    chefe = _perfil(role="gestor", is_coordinator=True)
    membro = _perfil(manager_id=chefe.id)
    vinculos = FakeCoordinators([(chefe.id, membro.id)])
    servico = TeamMembershipService(
        FakeProfiles([chefe, membro]),  # type: ignore[arg-type]
        vinculos,  # type: ignore[arg-type]
        FakeAudit(),  # type: ignore[arg-type]
    )

    await servico.remove_from_my_team(_contexto(chefe.id), membro.id)

    assert membro.manager_id is None


async def test_ninguem_se_remove_da_propria_equipe() -> None:
    gestora = _perfil(role="gestor")
    servico = TeamMembershipService(
        FakeProfiles([gestora]),  # type: ignore[arg-type]
        FakeCoordinators(),  # type: ignore[arg-type]
        FakeAudit(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValidationError):
        await servico.remove_from_my_team(_contexto(gestora.id), gestora.id)


# ---------------------------------------------------------------- departamento


class FakeDepartments:
    def __init__(self, itens: list[Department]) -> None:
        self.itens = itens

    async def get(self, department_id: UUID) -> Department | None:
        return next((d for d in self.itens if d.id == department_id), None)

    async def get_por_nome(self, nome: str) -> Department | None:
        return next((d for d in self.itens if d.name == nome), None)

    def add(self, departamento: Department) -> Department:
        self.itens.append(departamento)
        return departamento


async def test_departamento_guarda_a_descricao() -> None:
    servico = DepartmentService(FakeDepartments([]))  # type: ignore[arg-type]

    criado = await servico.create(name="Tributário", description="Contencioso fiscal")

    assert criado.description == "Contencioso fiscal"


async def test_update_sem_descricao_apaga_a_anterior() -> None:
    """PUT é o recurso inteiro: campo ausente significa "vazio", não "mantenha".

    Tratar como "mantenha" faria a única forma de apagar uma descrição ser um `UPDATE`
    direto no banco.
    """
    depto = Department(id=uuid4(), tenant_id=TENANT, name="Cível", description="antiga")
    servico = DepartmentService(FakeDepartments([depto]))  # type: ignore[arg-type]

    await servico.update(depto.id, name="Cível", description=None)

    assert depto.description is None
