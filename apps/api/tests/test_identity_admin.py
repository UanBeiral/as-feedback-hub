"""Comandos administrativos de `identity` — BR-MIGRAR-013/015/016/017/018, AMB-004.

Fecha as lacunas que o gate R-06 deixou anotadas: ciclo de vida das pessoas, vínculos
de equipe, pedidos de inclusão e o papel ativo.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.identity.admin_service import (
    CoordinatorService,
    ProfileService,
    TeamRequestService,
)
from app.contexts.identity.models import CAPABILITY_FLAGS, Profile, TeamRequest, User
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import PasswordHasher, pode_assumir
from app.core.tenancy import TenantContext

SEGREDO = "chave-de-teste-com-mais-de-32-caracteres-ok"


def _contexto(user_id: UUID | None = None, role: str = "admin") -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(), user_id=user_id or uuid4(), role=role, flags=frozenset()
    )


def _user(tenant_id: UUID, status: str = "active") -> User:
    return User(
        id=uuid4(),
        tenant_id=tenant_id,
        email="pessoa@exemplo.com",
        password_hash="hash",
        status=status,
    )


def _perfil(user: User, *, role: str = "colaborador", status: str = "active") -> Profile:
    return Profile.for_user(user, full_name="Pessoa", role=role, status=status)


class FakeProfileRepository:
    def __init__(self, perfis: list[Profile] | None = None, admins: int = 2) -> None:
        self.perfis = perfis or []
        self.admins = admins

    async def get(self, profile_id: UUID) -> Profile | None:
        return next((p for p in self.perfis if p.id == profile_id), None)

    def add(self, perfil: Profile) -> Profile:
        self.perfis.append(perfil)
        return perfil

    async def contar_admins_ativos(self) -> int:
        return self.admins


class FakeUserRepository:
    def __init__(self) -> None:
        self.usuarios: list[User] = []

    def add_user(self, user: User) -> User:
        self.usuarios.append(user)
        return user


class FakeAuthRepository:
    def __init__(self, usuarios: list[User] | None = None) -> None:
        self.usuarios = usuarios or []
        self.revogacoes: list[UUID] = []

    async def get_user_by_email(self, tenant_id: UUID, email: str) -> User | None:
        return next((u for u in self.usuarios if u.email == email), None)

    async def get_user(self, tenant_id: UUID, user_id: UUID) -> User | None:
        return next((u for u in self.usuarios if u.id == user_id), None)

    async def revoke_all_for_user(self, tenant_id: UUID, user_id: UUID) -> None:
        self.revogacoes.append(user_id)


class FakeProfileDepartments:
    def __init__(self) -> None:
        self.substituicoes: list[tuple[UUID, list[UUID]]] = []

    async def substituir(self, profile_id: UUID, department_ids: list[UUID]) -> None:
        self.substituicoes.append((profile_id, department_ids))


class FakeAudit:
    def __init__(self) -> None:
        self.acoes: list[dict[str, Any]] = []

    async def record(self, tenant: TenantContext, **campos: Any) -> None:
        self.acoes.append({"actor_id": tenant.user_id, **campos})

    @property
    def nomes(self) -> list[str]:
        return [a["action"] for a in self.acoes]


def _service(
    perfis: FakeProfileRepository,
    auth: FakeAuthRepository,
    audit: FakeAudit | None = None,
    departamentos: FakeProfileDepartments | None = None,
) -> ProfileService:
    return ProfileService(  # type: ignore[arg-type]
        profiles=perfis,
        users=FakeUserRepository(),
        auth=auth,
        hasher=PasswordHasher(rounds=10),
        departments=departamentos or FakeProfileDepartments(),
        audit=audit,
    )


# ---------------------------------------------------------------- registro


async def test_registrar_cria_usuario_e_perfil_com_o_mesmo_id() -> None:
    tenant = _contexto()
    perfis, auth = FakeProfileRepository([]), FakeAuthRepository()
    audit = FakeAudit()

    perfil = await _service(perfis, auth, audit).register(
        tenant, email="nova@exemplo.com", senha="senha-forte-123", full_name="Nova", role="gestor"
    )

    assert perfil.id == perfil.user_id, "invariante do banco: profiles.id = users.id"
    assert perfil.role == "gestor"
    assert audit.nomes == ["user.registered"]


async def test_email_duplicado_e_recusado() -> None:
    tenant = _contexto()
    existente = _user(tenant.tenant_id)
    service = _service(FakeProfileRepository(), FakeAuthRepository([existente]))

    with pytest.raises(ConflictError):
        await service.register(
            tenant,
            email="pessoa@exemplo.com",
            senha="senha-forte-123",
            full_name="Outra",
            role="colaborador",
        )


async def test_papel_invalido_e_recusado() -> None:
    tenant = _contexto()
    service = _service(FakeProfileRepository(), FakeAuthRepository())

    with pytest.raises(ValidationError):
        await service.register(
            tenant, email="x@e.com", senha="senha-forte-123", full_name="X", role="chefe"
        )


# ---------------------------------------------------------------- capacidades


async def test_set_flags_muda_so_o_que_veio() -> None:
    """PATCH que omite uma flag não pode desligá-la por acidente."""
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id))
    perfil.can_view_team_history = True
    perfil.can_generate_reports = False
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository(), FakeAudit())

    await service.set_flags(tenant, perfil.id, flags={"can_generate_reports": True})

    assert perfil.can_generate_reports is True
    assert perfil.can_view_team_history is True, "a flag omitida ficou como estava"


async def test_flag_desconhecida_e_erro_e_nao_silencio() -> None:
    """Flag com nome errado "aplicada" é o jeito mais rápido de achar que concedeu
    um acesso que não concedeu."""
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id))
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository())

    with pytest.raises(ValidationError) as exc:
        await service.set_flags(tenant, perfil.id, flags={"can_do_everything": True})

    assert exc.value.details["catalogo"] == list(CAPABILITY_FLAGS)


async def test_mudanca_de_papel_e_auditada() -> None:
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id), role="colaborador")
    audit = FakeAudit()
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository(), audit)

    await service.change_role(tenant, perfil.id, role="gestor")

    assert perfil.role == "gestor"
    assert audit.acoes[0]["details"] == {"de": "colaborador", "para": "gestor"}


async def test_mudanca_para_o_mesmo_papel_nao_audita() -> None:
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id), role="gestor")
    audit = FakeAudit()
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository(), audit)

    await service.change_role(tenant, perfil.id, role="gestor")

    assert audit.acoes == [], "trilha de auditoria não é log de requisição"


async def test_coordenacao_e_atributo_nao_papel() -> None:
    """BR-MIGRAR-015: foi aqui que o legado se enrolou."""
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id), role="colaborador")
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository())

    await service.set_coordinator(tenant, perfil.id, is_coordinator=True)

    assert perfil.is_coordinator is True
    assert perfil.role == "colaborador", "coordenar não muda o papel"


# ---------------------------------------------------------------- hierarquia


async def test_hierarquia_recusa_ciclo() -> None:
    """A→B→A faria a resolução de equipe girar para sempre."""
    tenant = _contexto()
    a = _perfil(_user(tenant.tenant_id))
    b = _perfil(_user(tenant.tenant_id))
    b.manager_id = a.id
    service = _service(FakeProfileRepository([a, b]), FakeAuthRepository())

    with pytest.raises(ValidationError):
        await service.assign_manager(tenant, a.id, manager_id=b.id)
    assert a.manager_id is None


async def test_ninguem_gerencia_a_si_mesmo() -> None:
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id))
    service = _service(FakeProfileRepository([perfil]), FakeAuthRepository())

    with pytest.raises(ValidationError):
        await service.assign_manager(tenant, perfil.id, manager_id=perfil.id)


async def test_vinculo_valido_e_aceito() -> None:
    tenant = _contexto()
    chefe = _perfil(_user(tenant.tenant_id), role="gestor")
    pessoa = _perfil(_user(tenant.tenant_id))
    service = _service(FakeProfileRepository([chefe, pessoa]), FakeAuthRepository())

    await service.assign_manager(tenant, pessoa.id, manager_id=chefe.id)

    assert pessoa.manager_id == chefe.id


async def test_departamentos_adicionais_sao_substituidos() -> None:
    tenant = _contexto()
    perfil = _perfil(_user(tenant.tenant_id))
    departamentos = FakeProfileDepartments()
    service = _service(
        FakeProfileRepository([perfil]), FakeAuthRepository(), departamentos=departamentos
    )

    ids = [uuid4(), uuid4()]
    await service.set_departments(tenant, perfil.id, department_ids=ids)

    assert departamentos.substituicoes == [(perfil.id, ids)]


# ---------------------------------------------------------------- soft-delete


async def test_soft_delete_preserva_e_revoga() -> None:
    """BR-MIGRAR-018 / PAR-08: as duas metades da regra, com mecanismos diferentes."""
    tenant = _contexto()
    usuario = _user(tenant.tenant_id)
    perfil = _perfil(usuario)
    auth = FakeAuthRepository([usuario])
    audit = FakeAudit()

    await _service(FakeProfileRepository([perfil]), auth, audit).soft_delete(tenant, perfil.id)

    assert perfil.status == "deleted", "nada é apagado: a FK continua válida"
    assert usuario.status == "deleted"
    assert auth.revogacoes == [perfil.user_id], "sessões caem agora, não quando o token expirar"
    assert audit.nomes == ["profile.soft_deleted"]


async def test_nao_se_remove_sozinho() -> None:
    tenant = _contexto()
    usuario = _user(tenant.tenant_id)
    perfil = _perfil(usuario)
    perfil.id = tenant.user_id

    with pytest.raises(ValidationError):
        await _service(FakeProfileRepository([perfil]), FakeAuthRepository([usuario])).soft_delete(
            tenant, tenant.user_id
        )


async def test_ultimo_admin_nao_e_removido() -> None:
    """Remover o último admin tranca todo mundo para fora do sistema."""
    tenant = _contexto()
    usuario = _user(tenant.tenant_id)
    perfil = _perfil(usuario, role="admin")

    with pytest.raises(ConflictError):
        await _service(
            FakeProfileRepository([perfil], admins=1), FakeAuthRepository([usuario])
        ).soft_delete(tenant, perfil.id)
    assert perfil.status == "active"


async def test_remover_duas_vezes_e_inofensivo() -> None:
    tenant = _contexto()
    usuario = _user(tenant.tenant_id)
    perfil = _perfil(usuario, status="deleted")
    auth = FakeAuthRepository([usuario])

    await _service(FakeProfileRepository([perfil]), auth).soft_delete(tenant, perfil.id)

    assert auth.revogacoes == [], "já estava removido: nada a revogar de novo"


async def test_redefinir_senha_derruba_sessoes() -> None:
    """Se a conta estava comprometida, o token do invasor continuaria valendo."""
    tenant = _contexto()
    usuario = _user(tenant.tenant_id)
    perfil = _perfil(usuario)
    auth = FakeAuthRepository([usuario])
    hash_antigo = usuario.password_hash

    await _service(FakeProfileRepository([perfil]), auth, FakeAudit()).reset_password(
        tenant, perfil.id, nova_senha="outra-senha-forte"
    )

    assert usuario.password_hash != hash_antigo
    assert auth.revogacoes == [perfil.user_id]


# ---------------------------------------------------------------- coordenação


class FakeCoordinatorRepository:
    def __init__(self) -> None:
        self.vinculos: list[Any] = []
        self.removidos: list[Any] = []

    async def get_vinculo(self, coordinator_id: UUID, member_id: UUID) -> Any:
        return next(
            (
                v
                for v in self.vinculos
                if v.coordinator_id == coordinator_id and v.member_id == member_id
            ),
            None,
        )

    def add(self, vinculo: Any) -> Any:
        vinculo.id = vinculo.id or uuid4()
        self.vinculos.append(vinculo)
        return vinculo

    async def remove(self, vinculo: Any) -> None:
        self.vinculos.remove(vinculo)
        self.removidos.append(vinculo)


async def test_vinculo_exige_coordenador_marcado() -> None:
    """Vínculo com quem não coordena não amplia escopo nenhum — só engana a tela."""
    tenant = _contexto()
    naoccoordenador = _perfil(_user(tenant.tenant_id))
    membro = _perfil(_user(tenant.tenant_id))
    service = CoordinatorService(  # type: ignore[arg-type]
        FakeCoordinatorRepository(), FakeProfileRepository([naoccoordenador, membro])
    )

    with pytest.raises(ConflictError):
        await service.add_member(
            tenant, coordinator_id=naoccoordenador.id, member_id=membro.id
        )


async def test_vinculo_repetido_devolve_o_existente() -> None:
    tenant = _contexto()
    coordenador = _perfil(_user(tenant.tenant_id))
    coordenador.is_coordinator = True
    membro = _perfil(_user(tenant.tenant_id))
    repo = FakeCoordinatorRepository()
    service = CoordinatorService(  # type: ignore[arg-type]
        repo, FakeProfileRepository([coordenador, membro])
    )

    primeiro = await service.add_member(
        tenant, coordinator_id=coordenador.id, member_id=membro.id
    )
    segundo = await service.add_member(
        tenant, coordinator_id=coordenador.id, member_id=membro.id
    )

    assert primeiro is segundo
    assert len(repo.vinculos) == 1


async def test_remover_membro_audita_e_notifica() -> None:
    """BR-MIGRAR-026: ação sensível registra `actor_id` e tenta notificar envolvidos."""
    tenant = _contexto()
    coordenador = _perfil(_user(tenant.tenant_id))
    coordenador.is_coordinator = True
    membro = _perfil(_user(tenant.tenant_id))
    repo = FakeCoordinatorRepository()
    audit = FakeAudit()
    service = CoordinatorService(  # type: ignore[arg-type]
        repo, FakeProfileRepository([coordenador, membro]), audit
    )
    await service.add_member(tenant, coordinator_id=coordenador.id, member_id=membro.id)

    await service.remove_member(tenant, coordinator_id=coordenador.id, member_id=membro.id)

    assert repo.vinculos == []
    assert audit.acoes[0]["action"] == "team.member_removed"
    assert audit.acoes[0]["actor_id"] == tenant.user_id
    assert set(audit.acoes[0]["notificar"]) == {membro.id, coordenador.id}


# ---------------------------------------------------------------- team requests


class FakeTeamRequestRepository:
    def __init__(self, pedidos: list[TeamRequest] | None = None) -> None:
        self.pedidos = pedidos or []

    async def get(self, request_id: UUID) -> TeamRequest | None:
        return next((p for p in self.pedidos if p.id == request_id), None)

    async def get_pendente(self, requester_id: UUID, member_id: UUID) -> TeamRequest | None:
        return next(
            (
                p
                for p in self.pedidos
                if p.requester_id == requester_id
                and p.requested_member_id == member_id
                and p.status == "pending"
            ),
            None,
        )

    def add(self, pedido: TeamRequest) -> TeamRequest:
        pedido.id = pedido.id or uuid4()
        pedido.status = pedido.status or "pending"
        self.pedidos.append(pedido)
        return pedido


def _pedido(status: str = "pending") -> TeamRequest:
    return TeamRequest(
        id=uuid4(),
        requester_id=uuid4(),
        requested_member_id=uuid4(),
        status=status,
    )


async def test_aprovar_move_a_pessoa_para_a_equipe() -> None:
    tenant = _contexto(role="gestor")
    pedido = _pedido()
    membro = _perfil(_user(tenant.tenant_id))
    membro.id = pedido.requested_member_id
    audit = FakeAudit()
    service = TeamRequestService(  # type: ignore[arg-type]
        FakeTeamRequestRepository([pedido]), FakeProfileRepository([membro]), audit
    )

    await service.approve(tenant, pedido.id)

    assert pedido.status == "approved"
    assert pedido.approved_by == tenant.user_id
    assert pedido.resolved_at is not None
    assert membro.manager_id == pedido.requester_id, "aprovar é o que efetiva o vínculo"
    assert audit.nomes == ["team.request_approved"]


async def test_rejeitar_guarda_o_motivo() -> None:
    tenant = _contexto(role="gestor")
    pedido = _pedido()
    service = TeamRequestService(  # type: ignore[arg-type]
        FakeTeamRequestRepository([pedido]), FakeProfileRepository(), FakeAudit()
    )

    await service.reject(tenant, pedido.id, motivo="equipe cheia")

    assert pedido.status == "rejected"
    assert pedido.rejection_reason == "equipe cheia"


@pytest.mark.parametrize("estado", ["approved", "rejected"])
async def test_pedido_resolvido_e_terminal(estado: str) -> None:
    """AMB-004: só aprovação e rejeição foram confirmadas no legado."""
    tenant = _contexto(role="gestor")
    pedido = _pedido(estado)
    service = TeamRequestService(  # type: ignore[arg-type]
        FakeTeamRequestRepository([pedido]), FakeProfileRepository(), FakeAudit()
    )

    with pytest.raises(ConflictError):
        await service.approve(tenant, pedido.id)
    assert pedido.status == estado


async def test_pedido_repetido_devolve_o_pendente() -> None:
    tenant = _contexto(role="gestor")
    alvo = _perfil(_user(tenant.tenant_id))
    repo = FakeTeamRequestRepository()
    service = TeamRequestService(  # type: ignore[arg-type]
        repo, FakeProfileRepository([alvo]), FakeAudit()
    )

    primeiro = await service.create(tenant, requested_member_id=alvo.id)
    segundo = await service.create(tenant, requested_member_id=alvo.id)

    assert primeiro is segundo
    assert len(repo.pedidos) == 1


async def test_pedir_a_si_mesmo_e_recusado() -> None:
    tenant = _contexto(role="gestor")
    service = TeamRequestService(  # type: ignore[arg-type]
        FakeTeamRequestRepository(), FakeProfileRepository(), FakeAudit()
    )

    with pytest.raises(ValidationError):
        await service.create(tenant, requested_member_id=tenant.user_id)


async def test_pedido_inexistente_e_404() -> None:
    tenant = _contexto(role="gestor")
    service = TeamRequestService(  # type: ignore[arg-type]
        FakeTeamRequestRepository(), FakeProfileRepository(), FakeAudit()
    )
    with pytest.raises(NotFoundError):
        await service.approve(tenant, uuid4())


# ---------------------------------------------------------------- papel ativo


@pytest.mark.parametrize(
    "persistido,ativo,permitido",
    [
        ("admin", "gestor", True),
        ("admin", "colaborador", True),
        ("admin", "admin", True),
        ("rh", "admin", False),
        ("gestor", "admin", False),
        ("gestor", "rh", False),
        ("colaborador", "gestor", False),
        ("gestor", "colaborador", True),
        ("admin", "inventado", False),
    ],
)
def test_troca_de_contexto_so_desce(persistido: str, ativo: str, permitido: bool) -> None:
    """BR-MIGRAR-016 / PAR-05: a troca restringe a visão, nunca concede poder."""
    assert pode_assumir(persistido, ativo) is permitido


def test_autorizacao_olha_o_papel_persistido() -> None:
    """Se olhasse o ativo, bastaria pedir para "ser admin" e a troca viraria escalada."""
    contexto = TenantContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        role="admin",
        flags=frozenset(),
        active_role="colaborador",
    )

    assert contexto.has_role("admin") is True, "autorização: papel persistido"
    assert contexto.enxerga_como("colaborador") is True, "visão: papel ativo"
    assert contexto.enxerga_como("admin") is False


def test_sem_papel_ativo_vale_o_persistido() -> None:
    contexto = TenantContext(
        tenant_id=uuid4(), user_id=uuid4(), role="gestor", flags=frozenset()
    )
    assert contexto.contexto_ativo == "gestor"
    assert contexto.enxerga_como("gestor") is True
