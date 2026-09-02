"""Resolução de escopo de equipe (`TeamScopeService`) — BR-MIGRAR-017 / PAR-05.

A regra é união, não substituição: quem coordena e também gerencia enxerga os dois
conjuntos. O legado errava exatamente aqui, e o cenário "escopo do coordenador é a
união deduplicada" de PAR-05 existe por causa desse erro.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.contexts.identity.service import TeamScopeService
from app.core.errors import AuthorizationError
from app.core.tenancy import TenantContext


class _PerfilFake:
    def __init__(self, id: UUID, *, is_coordinator: bool = False, status: str = "active") -> None:
        self.id = id
        self.is_coordinator = is_coordinator
        self.status = status


class FakeProfileRepository:
    def __init__(self, perfil: _PerfilFake | None, ativos: set[UUID], reports: set[UUID]) -> None:
        self._perfil = perfil
        self._ativos = ativos
        self._reports = reports

    async def get_by_user(self, user_id: UUID) -> _PerfilFake | None:
        return self._perfil

    async def list_active_ids(self) -> set[UUID]:
        return set(self._ativos)

    async def list_direct_report_ids(self, manager_id: UUID) -> set[UUID]:
        return set(self._reports)


class FakeCoordinatorMemberRepository:
    def __init__(self, membros: set[UUID]) -> None:
        self._membros = membros

    async def list_member_ids(self, coordinator_id: UUID) -> set[UUID]:
        return set(self._membros)


def _contexto(role: str) -> TenantContext:
    return TenantContext(tenant_id=uuid4(), user_id=uuid4(), role=role, flags=frozenset())


def _service(
    perfil: _PerfilFake | None,
    *,
    ativos: set[UUID] | None = None,
    reports: set[UUID] | None = None,
    coordenados: set[UUID] | None = None,
) -> TeamScopeService:
    return TeamScopeService(  # type: ignore[arg-type]
        profiles=FakeProfileRepository(perfil, ativos or set(), reports or set()),
        coordinator_members=FakeCoordinatorMemberRepository(coordenados or set()),
    )


async def test_admin_e_rh_enxergam_todos_os_ativos() -> None:
    ativos = {uuid4(), uuid4(), uuid4()}
    for papel in ("admin", "rh"):
        visiveis = await _service(None, ativos=ativos).resolve_visible_profile_ids(_contexto(papel))
        assert visiveis == ativos


async def test_gestor_ve_a_si_e_aos_subordinados_diretos() -> None:
    eu = _PerfilFake(uuid4())
    subordinados = {uuid4(), uuid4()}

    visiveis = await _service(eu, reports=subordinados).resolve_visible_profile_ids(
        _contexto("gestor")
    )

    assert visiveis == {eu.id, *subordinados}


async def test_coordenador_ve_a_uniao_deduplicada() -> None:
    """PAR-05: cada perfil aparece uma vez só, e ninguém de fora das duas fontes entra."""
    eu = _PerfilFake(uuid4(), is_coordinator=True)
    sobreposto = uuid4()
    subordinados = {uuid4(), sobreposto}
    coordenados = {sobreposto, uuid4()}

    visiveis = await _service(
        eu, reports=subordinados, coordenados=coordenados
    ).resolve_visible_profile_ids(_contexto("gestor"))

    assert visiveis == {eu.id, *subordinados, *coordenados}
    # A união não pode virar substituição: as duas fontes continuam inteiras.
    assert subordinados <= visiveis and coordenados <= visiveis


async def test_coordenacao_nao_e_consultada_para_quem_nao_coordena() -> None:
    eu = _PerfilFake(uuid4(), is_coordinator=False)
    coordenados = {uuid4()}

    visiveis = await _service(eu, coordenados=coordenados).resolve_visible_profile_ids(
        _contexto("colaborador")
    )

    assert visiveis == {eu.id}


async def test_perfil_removido_nao_enxerga_ninguem() -> None:
    eu = _PerfilFake(uuid4(), status="deleted")
    visiveis = await _service(eu, reports={uuid4()}).resolve_visible_profile_ids(
        _contexto("gestor")
    )
    assert visiveis == set()


async def test_identificador_de_fora_do_escopo_e_negado() -> None:
    """PAR-05: parâmetro de URL filtra dentro do escopo, nunca amplia."""
    eu = _PerfilFake(uuid4())
    service = _service(eu, reports={uuid4()})

    await service.assert_can_view(_contexto("gestor"), eu.id)  # dentro: passa

    with pytest.raises(AuthorizationError):
        await service.assert_can_view(_contexto("gestor"), uuid4())
