"""Abertura de ciclo, permissões e progresso — PAR-01 e PAR-04.

Estes são os cenários que o legado errava por construção: a abertura era orquestrada
por um componente de tela, e o progresso era calculado três vezes, de três jeitos.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.feedback.models import FeedbackCycle, FeedbackPermission
from app.contexts.feedback.service import (
    CycleProgressService,
    CycleService,
    FormService,
    PermissionService,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.tenancy import TenantContext

HOJE = date(2026, 9, 1)


def _contexto(role: str = "admin") -> TenantContext:
    return TenantContext(tenant_id=uuid4(), user_id=uuid4(), role=role, flags=frozenset())


class FakeOutbox:
    def __init__(self) -> None:
        self.mensagens: list[tuple[str, str]] = []

    async def enqueue(self, *, topic: str, payload: dict, idempotency_key: str) -> bool:
        if (topic, idempotency_key) in self.mensagens:
            return False
        self.mensagens.append((topic, idempotency_key))
        return True

    @property
    def topicos(self) -> list[str]:
        return [t for t, _ in self.mensagens]


class FakeCycleRepository:
    def __init__(self, ciclos: list[FeedbackCycle] | None = None) -> None:
        self.ciclos = ciclos or []

    async def get(self, cycle_id: UUID) -> FeedbackCycle | None:
        return next((c for c in self.ciclos if c.id == cycle_id), None)

    def add(self, ciclo: FeedbackCycle) -> FeedbackCycle:
        ciclo.id = ciclo.id or uuid4()
        self.ciclos.append(ciclo)
        return ciclo

    async def existe_aberto_na_frequencia(
        self, frequency: str, *, exceto: UUID | None = None
    ) -> bool:
        return any(
            c.frequency == frequency and c.status == "open" and c.id != exceto for c in self.ciclos
        )


class FakePermissionRepository:
    def __init__(self, regras: list[FeedbackPermission] | None = None) -> None:
        self.regras = regras or []

    async def list_ativas_para_ciclo(self, cycle_id: UUID) -> list[FeedbackPermission]:
        return [
            r for r in self.regras if r.active and (r.cycle_id is None or r.cycle_id == cycle_id)
        ]

    async def get_regra(
        self, *, reviewer_id: UUID, reviewee_id: UUID, permission_type: str, cycle_id: UUID | None
    ) -> FeedbackPermission | None:
        return next(
            (
                r
                for r in self.regras
                if r.reviewer_id == reviewer_id
                and r.reviewee_id == reviewee_id
                and r.permission_type == permission_type
                and r.cycle_id == cycle_id
            ),
            None,
        )

    def add(self, regra: FeedbackPermission) -> FeedbackPermission:
        self.regras.append(regra)
        return regra


class FakeRequestRepository:
    """Reproduz a chave natural (cycle, giver, receiver, form) do banco."""

    def __init__(self) -> None:
        self.criados: set[tuple[UUID, UUID, UUID, UUID]] = set()
        self.contagem: dict[str, int] = {}
        self.atrasados: set[UUID] = set()

    async def gerar_em_lote(
        self, *, cycle_id: UUID, form_id: UUID, pares: list[tuple[UUID, UUID]], due_date
    ) -> int:
        novos = 0
        for giver, receiver in pares:
            chave = (cycle_id, giver, receiver, form_id)
            if chave not in self.criados:
                self.criados.add(chave)
                novos += 1
        return novos

    async def contagem_por_status(self, cycle_id: UUID) -> dict[str, int]:
        return dict(self.contagem)

    async def ids_atrasados(self, cycle_id: UUID, hoje: date | None = None) -> set[UUID]:
        return set(self.atrasados)


def _ciclo(**campos: Any) -> FeedbackCycle:
    base = {
        "id": uuid4(),
        "name": "Ciclo de setembro",
        "form_id": uuid4(),
        "status": "draft",
        "start_date": HOJE,
        "end_date": HOJE + timedelta(days=30),
        "frequency": None,
        "evaluated_start": None,
        "evaluated_end": None,
    }
    return FeedbackCycle(**{**base, **campos})


def _permissao(reviewer: UUID, reviewee: UUID, **campos: Any) -> FeedbackPermission:
    base = {
        "id": uuid4(),
        "reviewer_id": reviewer,
        "reviewee_id": reviewee,
        "permission_type": "peer",
        "cycle_id": None,
        "active": True,
    }
    return FeedbackPermission(**{**base, **campos})


def _service(
    ciclos: FakeCycleRepository,
    permissoes: FakePermissionRepository,
    requests: FakeRequestRepository,
    outbox: FakeOutbox,
    ativos: set[UUID],
) -> CycleService:
    return CycleService(  # type: ignore[arg-type]
        cycles=ciclos,
        permissions=permissoes,
        requests=requests,
        outbox=outbox,
        perfis_ativos=ativos,
    )


# ---------------------------------------------------------------- abertura


async def test_abrir_gera_um_request_por_par_elegivel() -> None:
    ana, bruno = uuid4(), uuid4()
    ciclo = _ciclo()
    ciclos = FakeCycleRepository([ciclo])
    permissoes = FakePermissionRepository([_permissao(ana, bruno), _permissao(bruno, ana)])
    requests = FakeRequestRepository()
    outbox = FakeOutbox()

    resultado = await _service(ciclos, permissoes, requests, outbox, {ana, bruno}).open(ciclo.id)

    assert resultado.cycle.status == "open"
    assert resultado.requests_criados == 2
    assert outbox.topicos == ["cycle.opened"]


async def test_usuario_inativo_nao_recebe_request() -> None:
    """BR-MIGRAR-001: só perfil ativo entra na geração.

    Pedido para quem saiu da empresa enche a lista de pendência que ninguém responde,
    e ainda estraga o denominador do progresso.
    """
    ana, desligado = uuid4(), uuid4()
    ciclo = _ciclo()
    permissoes = FakePermissionRepository(
        [_permissao(ana, desligado), _permissao(desligado, ana)]
    )
    requests = FakeRequestRepository()

    resultado = await _service(
        FakeCycleRepository([ciclo]), permissoes, requests, FakeOutbox(), {ana}
    ).open(ciclo.id)

    assert resultado.requests_criados == 0
    assert resultado.pares_elegiveis == 0


async def test_permissao_inativa_nao_gera_request() -> None:
    ana, bruno = uuid4(), uuid4()
    ciclo = _ciclo()
    permissoes = FakePermissionRepository([_permissao(ana, bruno, active=False)])

    service = _service(
        FakeCycleRepository([ciclo]),
        permissoes,
        FakeRequestRepository(),
        FakeOutbox(),
        {ana, bruno},
    )
    resultado = await service.open(ciclo.id)

    assert resultado.requests_criados == 0


async def test_regerar_nao_duplica(  ) -> None:
    """PAR-01 @idempotencia: rodar a geração de novo não cria nada repetido."""
    ana, bruno = uuid4(), uuid4()
    ciclo = _ciclo()
    ciclos = FakeCycleRepository([ciclo])
    permissoes = FakePermissionRepository([_permissao(ana, bruno)])
    requests = FakeRequestRepository()
    outbox = FakeOutbox()
    service = _service(ciclos, permissoes, requests, outbox, {ana, bruno})

    await service.open(ciclo.id)
    segunda = await service.regenerate_requests(ciclo.id)

    assert segunda.requests_criados == 0
    assert len(requests.criados) == 1
    assert outbox.topicos == ["cycle.opened"], "regerar não republica a abertura"


async def test_permissao_nova_no_meio_do_ciclo_gera_so_o_que_falta() -> None:
    ana, bruno, carla = uuid4(), uuid4(), uuid4()
    ciclo = _ciclo()
    permissoes = FakePermissionRepository([_permissao(ana, bruno)])
    requests = FakeRequestRepository()
    service = _service(
        FakeCycleRepository([ciclo]), permissoes, requests, FakeOutbox(), {ana, bruno, carla}
    )

    await service.open(ciclo.id)
    permissoes.regras.append(_permissao(ana, carla))
    resultado = await service.regenerate_requests(ciclo.id)

    assert resultado.requests_criados == 1
    assert len(requests.criados) == 2


async def test_limite_de_concorrencia_por_frequencia() -> None:
    """BR-MIGRAR-011: janela ocupada recusa, com o alerta do legado."""
    aberto = _ciclo(status="open", frequency="mensal")
    novo = _ciclo(frequency="mensal")
    ciclos = FakeCycleRepository([aberto, novo])

    with pytest.raises(ConflictError) as exc:
        await _service(
            ciclos, FakePermissionRepository(), FakeRequestRepository(), FakeOutbox(), set()
        ).open(novo.id)

    assert exc.value.details["frequency"] == "mensal"
    assert novo.status == "draft", "o ciclo recusado não pode ficar meio aberto"


async def test_ciclo_sem_frequencia_nao_disputa_janela() -> None:
    aberto = _ciclo(status="open", frequency="mensal")
    avulso = _ciclo(frequency=None)
    ciclos = FakeCycleRepository([aberto, avulso])

    resultado = await _service(
        ciclos, FakePermissionRepository(), FakeRequestRepository(), FakeOutbox(), set()
    ).open(avulso.id)

    assert resultado.cycle.status == "open"


@pytest.mark.parametrize(
    "de,para",
    [
        ("draft", "closed"),
        ("draft", "published"),
        ("open", "published"),
        ("closed", "archived"),
        ("archived", "open"),
    ],
)
async def test_transicoes_de_ciclo_nao_previstas_sao_recusadas(de: str, para: str) -> None:
    ciclo = _ciclo(status=de)
    service = _service(
        FakeCycleRepository([ciclo]),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    comando = {
        "open": service.open,
        "closed": service.close,
        "published": service.publish,
        "archived": service.archive,
    }[para]

    with pytest.raises(ConflictError):
        await comando(ciclo.id)
    assert ciclo.status == de


async def test_fluxo_completo_do_ciclo() -> None:
    ciclo = _ciclo()
    outbox = FakeOutbox()
    service = _service(
        FakeCycleRepository([ciclo]),
        FakePermissionRepository(),
        FakeRequestRepository(),
        outbox,
        set(),
    )

    await service.open(ciclo.id)
    await service.close(ciclo.id)
    assert ciclo.closed_at is not None
    await service.publish(ciclo.id)
    assert ciclo.published_at is not None
    await service.archive(ciclo.id)

    assert ciclo.status == "archived"
    assert outbox.topicos == ["cycle.opened", "cycle.closed", "cycle.published"]


async def test_ciclo_criado_por_engano_arquiva_direto() -> None:
    ciclo = _ciclo()
    service = _service(
        FakeCycleRepository([ciclo]),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    assert (await service.archive(ciclo.id)).status == "archived"


async def test_estender_periodo_avaliado() -> None:
    """BR-MIGRAR-006: a extensão manual não mexe nas datas oficiais."""
    ciclo = _ciclo(status="open")
    service = _service(
        FakeCycleRepository([ciclo]),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    novo_fim = ciclo.end_date + timedelta(days=10)

    await service.extend_evaluated_period(ciclo.id, evaluated_end=novo_fim)

    assert ciclo.evaluated_end == novo_fim
    assert ciclo.end_date != novo_fim
    assert ciclo.prazo_final == novo_fim, "é o prazo que o fechamento automático observa"


async def test_ciclo_fechado_nao_estende() -> None:
    ciclo = _ciclo(status="closed")
    service = _service(
        FakeCycleRepository([ciclo]),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    with pytest.raises(ConflictError):
        await service.extend_evaluated_period(ciclo.id, evaluated_end=HOJE + timedelta(days=60))


async def test_data_final_antes_da_inicial_e_recusada() -> None:
    service = _service(
        FakeCycleRepository(),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    with pytest.raises(ValidationError):
        await service.create(
            name="x",
            form_id=uuid4(),
            start_date=HOJE,
            end_date=HOJE - timedelta(days=1),
            frequency=None,
        )


async def test_abrir_ciclo_inexistente_e_404() -> None:
    service = _service(
        FakeCycleRepository(),
        FakePermissionRepository(),
        FakeRequestRepository(),
        FakeOutbox(),
        set(),
    )
    with pytest.raises(NotFoundError):
        await service.open(uuid4())


# ---------------------------------------------------------------- permissões


async def test_peer_to_peer_cria_a_reciproca() -> None:
    """BR-MIGRAR-002 / PAR-01: no legado isso vivia num useEffect da tela."""
    ana, bruno = uuid4(), uuid4()
    repo = FakePermissionRepository()

    await PermissionService(repo).save(  # type: ignore[arg-type]
        reviewer_id=ana, reviewee_id=bruno, permission_type="peer_to_peer", cycle_id=None
    )

    pares = {(r.reviewer_id, r.reviewee_id) for r in repo.regras}
    assert pares == {(ana, bruno), (bruno, ana)}


async def test_peer_to_peer_preserva_reciproca_existente() -> None:
    """"Criar (ou preservar)" é literal: reversa desativada de propósito continua assim."""
    ana, bruno = uuid4(), uuid4()
    reversa = _permissao(bruno, ana, permission_type="peer_to_peer", active=False)
    repo = FakePermissionRepository([reversa])

    await PermissionService(repo).save(  # type: ignore[arg-type]
        reviewer_id=ana, reviewee_id=bruno, permission_type="peer_to_peer", cycle_id=None
    )

    assert reversa.active is False
    assert len(repo.regras) == 2


async def test_tipo_comum_nao_cria_reciproca() -> None:
    ana, bruno = uuid4(), uuid4()
    repo = FakePermissionRepository()

    await PermissionService(repo).save(  # type: ignore[arg-type]
        reviewer_id=ana, reviewee_id=bruno, permission_type="manager", cycle_id=None
    )

    assert len(repo.regras) == 1


async def test_auto_avaliacao_so_com_tipo_self() -> None:
    ana = uuid4()
    repo = FakePermissionRepository()
    service = PermissionService(repo)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        await service.save(
            reviewer_id=ana, reviewee_id=ana, permission_type="peer", cycle_id=None
        )

    await service.save(reviewer_id=ana, reviewee_id=ana, permission_type="self", cycle_id=None)
    assert len(repo.regras) == 1


async def test_salvar_regra_existente_atualiza_em_vez_de_duplicar() -> None:
    ana, bruno = uuid4(), uuid4()
    regra = _permissao(ana, bruno, active=False)
    repo = FakePermissionRepository([regra])

    await PermissionService(repo).save(  # type: ignore[arg-type]
        reviewer_id=ana, reviewee_id=bruno, permission_type="peer", cycle_id=None, active=True
    )

    assert len(repo.regras) == 1
    assert regra.active is True


# ---------------------------------------------------------------- progresso


async def test_progresso_exclui_cancelados_e_abdicados() -> None:
    """PAR-04, com os números exatos do cenário: 2 submitted de 4 no denominador."""
    requests = FakeRequestRepository()
    requests.contagem = {
        "submitted": 2,
        "pending": 1,
        "draft": 1,
        "cancelled": 1,
        "waived": 1,
    }

    progresso = await CycleProgressService(requests).calcular(uuid4())  # type: ignore[arg-type]

    assert progresso.total == 4
    assert progresso.concluidos == 2
    assert progresso.pendentes == 2
    assert progresso.excluidos == 2
    assert progresso.percentual == 50.0


async def test_expirado_continua_no_denominador() -> None:
    """Expirar não é abdicar: o trabalho era esperado e não foi feito."""
    requests = FakeRequestRepository()
    requests.contagem = {"submitted": 1, "expired": 1}

    progresso = await CycleProgressService(requests).calcular(uuid4())  # type: ignore[arg-type]

    assert progresso.total == 2
    assert progresso.percentual == 50.0


async def test_ciclo_sem_requests_e_cem_por_cento() -> None:
    """Não divide por zero, e 0% seria mentira — não há nada pendente."""
    progresso = await CycleProgressService(FakeRequestRepository()).calcular(uuid4())  # type: ignore[arg-type]

    assert progresso.total == 0
    assert progresso.percentual == 100.0


async def test_atraso_vem_do_mesmo_servico_que_o_progresso() -> None:
    """BR-MIGRAR-007: no legado cada tela calculava atraso do seu jeito."""
    requests = FakeRequestRepository()
    requests.contagem = {"pending": 3, "submitted": 1}
    requests.atrasados = {uuid4(), uuid4()}

    progresso = await CycleProgressService(requests).calcular(uuid4())  # type: ignore[arg-type]

    assert progresso.atrasados == 2
    assert progresso.total == 4


# ---------------------------------------------------------------- formulários


class FakeFormRepository:
    def __init__(self, forms: list[Any] | None = None, em_uso: bool = False) -> None:
        self.forms = forms or []
        self.em_uso = em_uso

    async def get(self, form_id: UUID) -> Any:
        return next((f for f in self.forms if f.id == form_id), None)

    def add(self, form: Any) -> Any:
        self.forms.append(form)
        return form

    async def usado_por_ciclo_vivo(self, form_id: UUID) -> bool:
        return self.em_uso


class FakeQuestionRepository:
    def __init__(self, perguntas: list[Any] | None = None) -> None:
        self.perguntas = perguntas or []

    async def list_by_form(self, form_id: UUID) -> list[Any]:
        return [q for q in self.perguntas if q.form_id == form_id]

    def add(self, pergunta: Any) -> Any:
        self.perguntas.append(pergunta)
        return pergunta


async def test_formulario_em_uso_por_ciclo_vivo_nao_arquiva() -> None:
    from app.contexts.feedback.models import FeedbackForm

    form = FeedbackForm(id=uuid4(), name="360", description=None, archived_at=None)
    service = FormService(  # type: ignore[arg-type]
        FakeFormRepository([form], em_uso=True), FakeQuestionRepository()
    )

    with pytest.raises(ConflictError):
        await service.archive(form.id)
    assert form.archived_at is None


async def test_formulario_sem_ciclo_vivo_arquiva() -> None:
    from app.contexts.feedback.models import FeedbackForm

    form = FeedbackForm(id=uuid4(), name="360", description=None, archived_at=None)
    service = FormService(  # type: ignore[arg-type]
        FakeFormRepository([form], em_uso=False), FakeQuestionRepository()
    )

    assert (await service.archive(form.id)).archived_at is not None


async def test_perguntas_recebem_ordem_sequencial() -> None:
    from app.contexts.feedback.models import FeedbackForm

    form = FeedbackForm(id=uuid4(), name="360", description=None, archived_at=None)
    perguntas = FakeQuestionRepository()
    service = FormService(FakeFormRepository([form]), perguntas)  # type: ignore[arg-type]

    for texto in ("Primeira", "Segunda", "Terceira"):
        await service.add_question(
            form.id,
            question_text=texto,
            question_type="textarea",
            required=True,
            help_text=None,
        )

    assert [q.sort_order for q in perguntas.perguntas] == [0, 1, 2]


async def test_reordenar_exige_a_lista_completa() -> None:
    from app.contexts.feedback.models import FeedbackForm, FeedbackFormQuestion

    form = FeedbackForm(id=uuid4(), name="360", description=None, archived_at=None)
    q1 = FeedbackFormQuestion(
        id=uuid4(), form_id=form.id, question_text="a", question_type="textarea", sort_order=0
    )
    q2 = FeedbackFormQuestion(
        id=uuid4(), form_id=form.id, question_text="b", question_type="textarea", sort_order=1
    )
    service = FormService(  # type: ignore[arg-type]
        FakeFormRepository([form]), FakeQuestionRepository([q1, q2])
    )

    with pytest.raises(ValidationError):
        await service.reorder(form.id, [q1.id])
    with pytest.raises(ValidationError):
        await service.reorder(form.id, [q1.id, uuid4()])

    await service.reorder(form.id, [q2.id, q1.id])
    assert (q2.sort_order, q1.sort_order) == (0, 1)
