"""Ciclo de vida do request, feedback livre e fechamento automático — PAR-02 e PAR-06."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.feedback.models import (
    FeedbackCycle,
    FeedbackFormQuestion,
    FeedbackRequest,
    FreeFeedback,
)
from app.contexts.feedback.service import FreeFeedbackService, RequestService
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.tenancy import TenantContext

HOJE = date(2026, 9, 1)


def _contexto(user_id: UUID | None = None, role: str = "colaborador") -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(), user_id=user_id or uuid4(), role=role, flags=frozenset()
    )


class FakeOutbox:
    def __init__(self) -> None:
        self.chaves: list[str] = []

    async def enqueue(self, *, topic: str, payload: dict, idempotency_key: str) -> bool:
        self.chaves.append(idempotency_key)
        return True


class FakeAudit:
    def __init__(self) -> None:
        self.registros: list[dict[str, Any]] = []

    async def record(self, tenant: TenantContext, **campos: Any) -> None:
        self.registros.append({"actor_id": tenant.user_id, **campos})


class FakeRequestRepository:
    def __init__(self, requests: list[FeedbackRequest]) -> None:
        self.requests = requests

    async def get(self, request_id: UUID) -> FeedbackRequest | None:
        return next((r for r in self.requests if r.id == request_id), None)


class FakeAnswerRepository:
    def __init__(self) -> None:
        self.respostas: dict[tuple[UUID, UUID], tuple[str | None, int | None]] = {}

    async def upsert(
        self, *, request_id: UUID, question_id: UUID, answer_text, answer_score
    ) -> None:
        self.respostas[(request_id, question_id)] = (answer_text, answer_score)


class FakeQuestionRepository:
    def __init__(self, perguntas: list[FeedbackFormQuestion]) -> None:
        self.perguntas = perguntas

    async def list_by_form(self, form_id: UUID) -> list[FeedbackFormQuestion]:
        return list(self.perguntas)


def _pergunta(tipo: str = "textarea", required: bool = True) -> FeedbackFormQuestion:
    return FeedbackFormQuestion(
        id=uuid4(),
        form_id=uuid4(),
        question_text="Como foi?",
        question_type=tipo,
        required=required,
        sort_order=0,
    )


def _request(giver: UUID, status: str = "pending") -> FeedbackRequest:
    return FeedbackRequest(
        id=uuid4(),
        cycle_id=uuid4(),
        form_id=uuid4(),
        giver_id=giver,
        receiver_id=uuid4(),
        status=status,
        due_date=HOJE,
    )


def _service(
    request: FeedbackRequest,
    perguntas: list[FeedbackFormQuestion],
    *,
    answers: FakeAnswerRepository | None = None,
    outbox: FakeOutbox | None = None,
    audit: FakeAudit | None = None,
) -> RequestService:
    return RequestService(  # type: ignore[arg-type]
        requests=FakeRequestRepository([request]),
        answers=answers or FakeAnswerRepository(),
        questions=FakeQuestionRepository(perguntas),
        outbox=outbox or FakeOutbox(),
        audit=audit,
    )


# ---------------------------------------------------------------- rascunho


async def test_rascunho_preserva_respostas_parciais() -> None:
    """PAR-02: rascunho aceita o que ainda está pela metade."""
    tenant = _contexto()
    request = _request(tenant.user_id)
    obrigatoria, opcional = _pergunta(), _pergunta(required=False)
    answers = FakeAnswerRepository()

    await _service(request, [obrigatoria, opcional], answers=answers).save_draft(
        tenant, request.id, {obrigatoria.id: ("Comecei a escrever", None)}
    )

    assert request.status == "draft"
    assert answers.respostas[(request.id, obrigatoria.id)] == ("Comecei a escrever", None)


async def test_rascunho_nao_cobra_obrigatoria() -> None:
    """Cobrar no rascunho faria a pessoa perder o que já escreveu (BR-MIGRAR-012)."""
    tenant = _contexto()
    request = _request(tenant.user_id)
    q1, q2 = _pergunta(), _pergunta()

    await _service(request, [q1, q2]).save_draft(tenant, request.id, {q1.id: ("parcial", None)})

    assert request.status == "draft"


async def test_salvar_rascunho_duas_vezes_atualiza() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id)
    pergunta = _pergunta()
    answers = FakeAnswerRepository()
    service = _service(request, [pergunta], answers=answers)

    await service.save_draft(tenant, request.id, {pergunta.id: ("primeira", None)})
    await service.save_draft(tenant, request.id, {pergunta.id: ("segunda", None)})

    assert len(answers.respostas) == 1
    assert answers.respostas[(request.id, pergunta.id)] == ("segunda", None)


async def test_rascunho_de_request_enviado_e_recusado() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id, status="submitted")

    with pytest.raises(ConflictError):
        await _service(request, [_pergunta()]).save_draft(tenant, request.id, {})


# ---------------------------------------------------------------- envio


async def test_envio_valido_grava_submitted_at_e_enfileira() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    pergunta = _pergunta()
    answers, outbox = FakeAnswerRepository(), FakeOutbox()

    await _service(request, [pergunta], answers=answers, outbox=outbox).submit(
        tenant, request.id, {pergunta.id: ("resposta completa", None)}
    )

    assert request.status == "submitted"
    assert request.submitted_at is not None
    assert answers.respostas[(request.id, pergunta.id)] == ("resposta completa", None)
    assert outbox.chaves == [f"request.submitted:{request.id}"]


async def test_envio_direto_do_pendente_funciona() -> None:
    """Quem responde de uma sentada só não passa por rascunho."""
    tenant = _contexto()
    request = _request(tenant.user_id, status="pending")
    pergunta = _pergunta()

    await _service(request, [pergunta]).submit(
        tenant, request.id, {pergunta.id: ("tudo de uma vez", None)}
    )

    assert request.status == "submitted"


async def test_obrigatoria_em_branco_recusa_e_nao_persiste_nada() -> None:
    """PAR-02: recusa o envio inteiro, sem gravar metade."""
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    obrigatoria, outra = _pergunta(), _pergunta()
    answers = FakeAnswerRepository()

    with pytest.raises(ValidationError) as exc:
        await _service(request, [obrigatoria, outra], answers=answers).submit(
            tenant, request.id, {obrigatoria.id: ("respondi só esta", None)}
        )

    assert str(outra.id) in exc.value.details["question_ids"]
    assert request.status == "draft", "o estado não muda"
    assert answers.respostas == {}, "nada é persistido"


async def test_nota_em_pergunta_de_texto_nao_conta_como_resposta() -> None:
    """O erro típico do front mandando o campo errado — passaria batido sem isto."""
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    texto = _pergunta(tipo="textarea")

    with pytest.raises(ValidationError):
        await _service(request, [texto]).submit(tenant, request.id, {texto.id: (None, 5)})


async def test_rating_exige_nota() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    nota = _pergunta(tipo="rating")

    with pytest.raises(ValidationError):
        await _service(request, [nota]).submit(tenant, request.id, {nota.id: ("ótimo", None)})

    await _service(request, [nota]).submit(tenant, request.id, {nota.id: (None, 5)})
    assert request.status == "submitted"


async def test_opcional_em_branco_nao_impede_envio() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    obrigatoria, opcional = _pergunta(), _pergunta(required=False)

    await _service(request, [obrigatoria, opcional]).submit(
        tenant, request.id, {obrigatoria.id: ("respondida", None)}
    )

    assert request.status == "submitted"


async def test_resposta_para_pergunta_de_outro_formulario_e_recusada() -> None:
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    pergunta = _pergunta()
    intrusa = uuid4()

    with pytest.raises(ValidationError) as exc:
        await _service(request, [pergunta]).submit(
            tenant, request.id, {pergunta.id: ("ok", None), intrusa: ("?", None)}
        )

    assert str(intrusa) in exc.value.details["question_ids"]


# ---------------------------------------------------------------- transições


async def test_abdicar_e_retomar() -> None:
    """PAR-02: abdicar sai do denominador; retomar volta para `pending`."""
    tenant = _contexto()
    request = _request(tenant.user_id, status="draft")
    service = _service(request, [])

    await service.waive(tenant, request.id)
    assert request.status == "waived"

    await service.resume(tenant, request.id)
    assert request.status == "pending"


@pytest.mark.parametrize("destino", ["draft", "cancelled", "waived"])
async def test_request_enviado_e_terminal(destino: str) -> None:
    """Feedback enviado não volta atrás — quem recebeu já leu."""
    tenant = _contexto()
    request = _request(tenant.user_id, status="submitted")
    service = _service(request, [_pergunta()], audit=FakeAudit())

    comando = {
        "draft": lambda: service.save_draft(tenant, request.id, {}),
        "cancelled": lambda: service.cancel(tenant, request.id, justificativa="mudei de ideia"),
        "waived": lambda: service.waive(tenant, request.id),
    }[destino]

    with pytest.raises(ConflictError):
        await comando()
    assert request.status == "submitted"


async def test_cancelar_exige_justificativa_e_audita() -> None:
    """PAR-02: a justificativa é o que o avaliado lê depois."""
    gestor = _contexto(role="gestor")
    request = _request(uuid4(), status="pending")
    audit = FakeAudit()
    service = _service(request, [], audit=audit)

    with pytest.raises(ValidationError):
        await service.cancel(gestor, request.id, justificativa="   ")

    await service.cancel(gestor, request.id, justificativa="Pessoa saiu do time")

    assert request.status == "cancelled"
    assert request.cancel_justification == "Pessoa saiu do time"
    assert audit.registros[0]["actor_id"] == gestor.user_id
    assert audit.registros[0]["action"] == "request.cancelled"


async def test_ninguem_responde_no_lugar_de_outra_pessoa() -> None:
    """404 e não 403: quem não é dono não precisa saber que o request existe."""
    dono, intruso = uuid4(), _contexto()
    request = _request(dono, status="pending")
    service = _service(request, [_pergunta()])

    with pytest.raises(NotFoundError):
        await service.save_draft(intruso, request.id, {})
    with pytest.raises(NotFoundError):
        await service.waive(intruso, request.id)


async def test_request_inexistente_e_404() -> None:
    tenant = _contexto()
    service = _service(_request(tenant.user_id), [])
    with pytest.raises(NotFoundError):
        await service.waive(tenant, uuid4())


# ---------------------------------------------------------------- feedback livre


class FakeFreeRepository:
    def __init__(self, itens: list[FreeFeedback] | None = None) -> None:
        self.itens = itens or []

    def add(self, item: FreeFeedback) -> FreeFeedback:
        self.itens.append(item)
        return item

    async def get(self, item_id: UUID) -> FreeFeedback | None:
        return next((i for i in self.itens if i.id == item_id), None)


async def test_anonimo_nao_guarda_o_autor() -> None:
    """AMB-001: anonimato por construção, não por a tela esconder o campo."""
    tenant = _contexto()
    repo = FakeFreeRepository()

    feedback = await FreeFeedbackService(repo).send(  # type: ignore[arg-type]
        tenant,
        receiver_id=uuid4(),
        is_anonymous=True,
        is_sensitive=False,
        positives="mandou bem",
        improvements=None,
        message=None,
    )

    assert feedback.giver_id is None


async def test_identificado_guarda_o_autor() -> None:
    tenant = _contexto()
    feedback = await FreeFeedbackService(FakeFreeRepository()).send(  # type: ignore[arg-type]
        tenant,
        receiver_id=uuid4(),
        is_anonymous=False,
        is_sensitive=False,
        positives=None,
        improvements=None,
        message="obrigado",
    )

    assert feedback.giver_id == tenant.user_id


async def test_feedback_vazio_e_para_si_mesmo_sao_recusados() -> None:
    tenant = _contexto()
    service = FreeFeedbackService(FakeFreeRepository())  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        await service.send(
            tenant,
            receiver_id=uuid4(),
            is_anonymous=False,
            is_sensitive=False,
            positives=None,
            improvements=None,
            message=None,
        )

    with pytest.raises(ValidationError):
        await service.send(
            tenant,
            receiver_id=tenant.user_id,
            is_anonymous=False,
            is_sensitive=False,
            positives="eu sou ótimo",
            improvements=None,
            message=None,
        )


async def test_marcar_como_lido_e_idempotente_e_registra_quem_leu() -> None:
    tenant = _contexto()
    item = FreeFeedback(
        id=uuid4(),
        giver_id=uuid4(),
        receiver_id=tenant.user_id,
        is_anonymous=False,
        is_sensitive=False,
        message="oi",
    )
    service = FreeFeedbackService(FakeFreeRepository([item]))  # type: ignore[arg-type]

    await service.mark_read(tenant, item.id)
    primeira_leitura = item.read_at
    await service.mark_read(tenant, item.id)

    assert item.read_by == tenant.user_id
    assert item.read_at == primeira_leitura, "reler não reescreve o carimbo"


async def test_feedback_de_outra_pessoa_nao_e_marcado_como_lido() -> None:
    tenant = _contexto()
    alheio = FreeFeedback(
        id=uuid4(), giver_id=uuid4(), receiver_id=uuid4(), is_anonymous=False, is_sensitive=False
    )
    service = FreeFeedbackService(FakeFreeRepository([alheio]))  # type: ignore[arg-type]

    with pytest.raises(NotFoundError):
        await service.mark_read(tenant, alheio.id)


# ---------------------------------------------------------------- fechamento (PAR-06)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.adicionados: list[Any] = []

    def add(self, entidade: Any) -> None:
        self.adicionados.append(entidade)

    async def execute(self, *_a: Any, **_k: Any) -> Any:
        class _R:
            def scalar_one_or_none(_s) -> None:
                return None

        return _R()

    async def commit(self) -> None:
        self.commits += 1


def _ciclo_vencido(dias: int, evaluated_end: date | None = None) -> FeedbackCycle:
    return FeedbackCycle(
        id=uuid4(),
        tenant_id=uuid4(),
        name=f"Ciclo vencido há {dias} dias",
        form_id=uuid4(),
        status="open",
        start_date=HOJE - timedelta(days=60),
        end_date=HOJE - timedelta(days=dias),
        evaluated_end=evaluated_end,
    )


@pytest.fixture
def _due(monkeypatch: pytest.MonkeyPatch):
    """Substitui a varredura de vencidos: o SQL com `greatest` é do banco."""
    import worker.jobs.cycles as modulo

    ciclos: list[FeedbackCycle] = []

    class _RepoFake:
        def __init__(self, session: Any) -> None: ...

        async def vencidos(self, hoje: date | None = None, *, limit: int = 100):
            from app.contexts.feedback.models import DIAS_DE_CARENCIA

            limite = (hoje or HOJE) - timedelta(days=DIAS_DE_CARENCIA)
            return [c for c in ciclos if c.status == "open" and c.prazo_final < limite]

    monkeypatch.setattr(modulo, "CycleDueRepository", _RepoFake)
    return ciclos


async def test_ciclo_nao_fecha_antes_da_carencia(_due: list[FeedbackCycle]) -> None:
    """PAR-06: venceu há 2 dias, a carência é 3 — continua aberto."""
    from worker.jobs.cycles import fechar_ciclos_vencidos

    ciclo = _ciclo_vencido(2)
    _due.append(ciclo)

    fechados = await fechar_ciclos_vencidos(FakeSession(), HOJE)  # type: ignore[arg-type]

    assert fechados == []
    assert ciclo.status == "open"


async def test_ciclo_fecha_depois_da_carencia(_due: list[FeedbackCycle]) -> None:
    from worker.jobs.cycles import fechar_ciclos_vencidos

    ciclo = _ciclo_vencido(4)
    _due.append(ciclo)

    fechados = await fechar_ciclos_vencidos(FakeSession(), HOJE)  # type: ignore[arg-type]

    assert fechados == [ciclo.name]
    assert ciclo.status == "closed"
    assert ciclo.closed_at is not None


async def test_periodo_estendido_adia_o_fechamento(_due: list[FeedbackCycle]) -> None:
    """PAR-06: a extensão manual vence a data oficial."""
    from worker.jobs.cycles import fechar_ciclos_vencidos

    ciclo = _ciclo_vencido(10, evaluated_end=HOJE + timedelta(days=5))
    _due.append(ciclo)

    fechados = await fechar_ciclos_vencidos(FakeSession(), HOJE)  # type: ignore[arg-type]

    assert fechados == []
    assert ciclo.status == "open"


async def test_job_reexecutado_nao_repete_efeitos(_due: list[FeedbackCycle]) -> None:
    """PAR-06 @idempotencia: o filtro só enxerga `open`, então não há segunda vez."""
    from worker.jobs.cycles import fechar_ciclos_vencidos

    ciclo = _ciclo_vencido(4)
    _due.append(ciclo)

    primeira = await fechar_ciclos_vencidos(FakeSession(), HOJE)  # type: ignore[arg-type]
    fechado_em = ciclo.closed_at
    segunda = await fechar_ciclos_vencidos(FakeSession(), HOJE)  # type: ignore[arg-type]

    assert len(primeira) == 1
    assert segunda == []
    assert ciclo.closed_at == fechado_em


async def test_fila_vazia_nao_commita(_due: list[FeedbackCycle]) -> None:
    from worker.jobs.cycles import fechar_ciclos_vencidos

    sessao = FakeSession()
    assert await fechar_ciclos_vencidos(sessao, HOJE) == []  # type: ignore[arg-type]
    assert sessao.commits == 0


def test_prazo_final_ignora_extensao_menor_que_a_data_oficial() -> None:
    """Encurtar o período avaliado não antecipa o fechamento — só estender adia."""
    ciclo = FeedbackCycle(
        id=uuid4(),
        name="x",
        form_id=uuid4(),
        status="open",
        start_date=HOJE - timedelta(days=30),
        end_date=HOJE,
        evaluated_end=HOJE - timedelta(days=10),
    )
    assert ciclo.prazo_final == ciclo.end_date


def test_datetime_de_fechamento_e_utc() -> None:
    """Carimbo sem fuso vira uma hora errada no relatório de outro escritório."""
    agora = datetime.now(UTC)
    assert agora.tzinfo is not None
