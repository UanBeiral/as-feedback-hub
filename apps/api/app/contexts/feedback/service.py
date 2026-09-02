"""Casos de uso do contexto `feedback`.

É aqui que mora a decisão central do `paradigm_decision.md`: no legado, abrir um ciclo
era uma sequência de chamadas soltas disparadas por um componente de tela — o React
lia permissões, montava pares e inseria requests um a um, e qualquer falha no meio
deixava o ciclo metade aberto. Aqui `CycleService.open` é **um comando**, com as
invariantes juntas, numa transação: ou o ciclo abre com todos os requests e o evento
de notificação, ou nada aconteceu.

O outro fio condutor é BR-MIGRAR-009: existe **um** cálculo de progresso no sistema
(`CycleProgressService`). O legado tinha três — gestor, coordenador e dashboard — e
eles discordavam entre si.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from app.contexts.engagement.service import AuditService, OutboxService
from app.contexts.feedback.models import (
    CycleNote,
    FeedbackCycle,
    FeedbackForm,
    FeedbackFormQuestion,
    FeedbackPermission,
    FeedbackRequest,
    FreeFeedback,
)
from app.contexts.feedback.repository import (
    STATUS_CONCLUIDO,
    STATUS_NO_DENOMINADOR,
    AnswerRepository,
    CycleNoteRepository,
    CycleRepository,
    FormRepository,
    FreeFeedbackRepository,
    PermissionRepository,
    QuestionRepository,
    RequestRepository,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.tenancy import TenantContext

# Máquina do ciclo (BR-MIGRAR-004). `draft → archived` existe para o ciclo que foi
# criado por engano e nunca abriu.
TRANSICOES_CICLO: dict[str, frozenset[str]] = {
    "draft": frozenset({"open", "archived"}),
    "open": frozenset({"closed"}),
    "closed": frozenset({"published"}),
    "published": frozenset({"archived"}),
    "archived": frozenset(),
}

# Máquina do request (BR-MIGRAR-003). `submitted` é terminal: feedback enviado não
# volta para rascunho nem é cancelado — quem recebeu já leu.
TRANSICOES_REQUEST: dict[str, frozenset[str]] = {
    "pending": frozenset({"draft", "waived", "cancelled", "expired"}),
    "draft": frozenset({"submitted", "waived", "cancelled", "expired"}),
    "waived": frozenset({"pending"}),
    "submitted": frozenset(),
    "cancelled": frozenset(),
    "expired": frozenset(),
}


def _exige_transicao(atual: str, destino: str, mapa: dict[str, frozenset[str]], o_que: str) -> None:
    permitidas = mapa.get(atual, frozenset())
    if destino not in permitidas:
        raise ConflictError(
            f"Transição de {o_que} não permitida",
            details={"de": atual, "para": destino, "permitidas": sorted(permitidas)},
        )


class FormService:
    def __init__(self, forms: FormRepository, questions: QuestionRepository) -> None:
        self._forms = forms
        self._questions = questions

    async def create(self, *, name: str, description: str | None) -> FeedbackForm:
        return self._forms.add(FeedbackForm(name=name, description=description))

    async def add_question(
        self,
        form_id: UUID,
        *,
        question_text: str,
        question_type: str,
        required: bool,
        help_text: str | None,
        sort_order: int | None = None,
    ) -> FeedbackFormQuestion:
        form = await self._forms.get(form_id)
        if form is None:
            raise NotFoundError("Formulário não encontrado")
        if form.archived_at is not None:
            raise ConflictError("Formulário arquivado não recebe perguntas novas")

        if sort_order is None:
            existentes = await self._questions.list_by_form(form_id)
            sort_order = max((q.sort_order for q in existentes), default=-1) + 1

        return self._questions.add(
            FeedbackFormQuestion(
                form_id=form_id,
                question_text=question_text,
                question_type=question_type,
                required=required,
                help_text=help_text,
                sort_order=sort_order,
            )
        )

    async def reorder(self, form_id: UUID, ordem: list[UUID]) -> None:
        perguntas = {q.id: q for q in await self._questions.list_by_form(form_id)}
        desconhecidas = [str(qid) for qid in ordem if qid not in perguntas]
        if desconhecidas:
            raise ValidationError(
                "Ordem inclui perguntas de outro formulário", details={"ids": desconhecidas}
            )
        if len(ordem) != len(perguntas):
            raise ValidationError(
                "A ordem precisa listar todas as perguntas do formulário",
                details={"esperado": len(perguntas), "recebido": len(ordem)},
            )
        for posicao, question_id in enumerate(ordem):
            perguntas[question_id].sort_order = posicao

    async def archive(self, form_id: UUID) -> FeedbackForm:
        """Formulário preso a ciclo vivo não some (invariante do aggregate FeedbackForm)."""
        form = await self._forms.get(form_id)
        if form is None:
            raise NotFoundError("Formulário não encontrado")
        if await self._forms.usado_por_ciclo_vivo(form_id):
            raise ConflictError(
                "Formulário em uso por ciclo em rascunho ou aberto",
                details={"form_id": str(form_id)},
            )
        form.archived_at = datetime.now(UTC)
        return form


class PermissionService:
    """Matriz de quem avalia quem (BR-MIGRAR-002)."""

    def __init__(self, permissions: PermissionRepository) -> None:
        self._permissions = permissions

    async def save(
        self,
        *,
        reviewer_id: UUID,
        reviewee_id: UUID,
        permission_type: str,
        cycle_id: UUID | None,
        active: bool = True,
    ) -> FeedbackPermission:
        """Salva a regra e, se for `peer_to_peer`, garante a recíproca.

        No legado a relação reversa era criada por um `useEffect` na tela de permissões:
        quem salvasse pela API, ou por outra tela, ficava com metade da relação — e o
        par aparecia avaliando sem ser avaliado. Aqui a recíproca entra na mesma
        transação, e "criar (ou preservar)" é literal: se a reversa já existe, ela é
        deixada como está, inclusive se estiver desativada de propósito.
        """
        regra = await self._salvar_uma(
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            permission_type=permission_type,
            cycle_id=cycle_id,
            active=active,
        )

        if permission_type == "peer_to_peer":
            reversa = await self._permissions.get_regra(
                reviewer_id=reviewee_id,
                reviewee_id=reviewer_id,
                permission_type=permission_type,
                cycle_id=cycle_id,
            )
            if reversa is None:
                await self._salvar_uma(
                    reviewer_id=reviewee_id,
                    reviewee_id=reviewer_id,
                    permission_type=permission_type,
                    cycle_id=cycle_id,
                    active=active,
                )

        return regra

    async def _salvar_uma(
        self,
        *,
        reviewer_id: UUID,
        reviewee_id: UUID,
        permission_type: str,
        cycle_id: UUID | None,
        active: bool,
    ) -> FeedbackPermission:
        if reviewer_id == reviewee_id and permission_type != "self":
            raise ValidationError(
                "Auto-avaliação só existe com o tipo `self`",
                details={"permission_type": permission_type},
            )

        existente = await self._permissions.get_regra(
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            permission_type=permission_type,
            cycle_id=cycle_id,
        )
        if existente is not None:
            existente.active = active
            return existente

        return self._permissions.add(
            FeedbackPermission(
                reviewer_id=reviewer_id,
                reviewee_id=reviewee_id,
                permission_type=permission_type,
                cycle_id=cycle_id,
                active=active,
            )
        )


@dataclass(frozen=True, slots=True)
class ResultadoDaAbertura:
    cycle: FeedbackCycle
    requests_criados: int
    pares_elegiveis: int


class CycleService:
    """Ciclo de feedback: um comando por transição, invariantes juntas."""

    def __init__(
        self,
        cycles: CycleRepository,
        permissions: PermissionRepository,
        requests: RequestRepository,
        outbox: OutboxService,
        perfis_ativos: set[UUID],
    ) -> None:
        self._cycles = cycles
        self._permissions = permissions
        self._requests = requests
        self._outbox = outbox
        self._perfis_ativos = perfis_ativos

    async def create(
        self,
        *,
        name: str,
        form_id: UUID,
        start_date: date,
        end_date: date,
        frequency: str | None,
        evaluated_start: date | None = None,
        evaluated_end: date | None = None,
    ) -> FeedbackCycle:
        if end_date < start_date:
            raise ValidationError("A data final não pode ser anterior à inicial")
        if evaluated_start and evaluated_end and evaluated_end < evaluated_start:
            raise ValidationError("Período avaliado inconsistente")

        return self._cycles.add(
            FeedbackCycle(
                name=name,
                form_id=form_id,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                evaluated_start=evaluated_start,
                evaluated_end=evaluated_end,
                status="draft",
            )
        )

    async def open(self, cycle_id: UUID) -> ResultadoDaAbertura:
        """Abre o ciclo e gera os requests (BR-MIGRAR-001/010/011).

        Tudo em uma transação: estado, requests e o evento de notificação. Se a geração
        falhar, o ciclo não fica "aberto e vazio" — o estado em que o legado às vezes
        parava, e que obrigava alguém a conferir na mão quem tinha recebido pedido.
        """
        cycle = await self._exige_ciclo(cycle_id)
        _exige_transicao(cycle.status, "open", TRANSICOES_CICLO, "ciclo")

        if cycle.frequency and await self._cycles.existe_aberto_na_frequencia(
            cycle.frequency, exceto=cycle.id
        ):
            raise ConflictError(
                "Já existe um ciclo aberto nesta frequência",
                details={"frequency": cycle.frequency},
            )

        pares = await self._pares_elegiveis(cycle)
        criados = await self._requests.gerar_em_lote(
            cycle_id=cycle.id,
            form_id=cycle.form_id,
            pares=sorted(pares),
            due_date=cycle.end_date,
        )

        cycle.status = "open"
        await self._outbox.enqueue(
            topic="cycle.opened",
            payload={"cycle_id": str(cycle.id), "requests": criados},
            idempotency_key=f"cycle.opened:{cycle.id}",
        )
        return ResultadoDaAbertura(
            cycle=cycle, requests_criados=criados, pares_elegiveis=len(pares)
        )

    async def _pares_elegiveis(self, cycle: FeedbackCycle) -> set[tuple[UUID, UUID]]:
        """Pares (avaliador, avaliado) a partir das permissões ativas.

        Só gente ativa entra, dos dois lados: gerar pedido para quem saiu da empresa
        enche a fila de pendência que ninguém vai responder, e ainda estraga o
        denominador do progresso.
        """
        permissoes = await self._permissions.list_ativas_para_ciclo(cycle.id)
        return {
            (p.reviewer_id, p.reviewee_id)
            for p in permissoes
            if p.reviewer_id in self._perfis_ativos and p.reviewee_id in self._perfis_ativos
        }

    async def regenerate_requests(self, cycle_id: UUID) -> ResultadoDaAbertura:
        """Reexecuta a geração num ciclo já aberto — idempotente por construção.

        Serve para quando uma permissão nova entra com o ciclo em andamento. Não
        duplica nada (BR-MIGRAR-010) e não republica o evento de abertura, porque o
        ciclo não abriu de novo.
        """
        cycle = await self._exige_ciclo(cycle_id)
        if cycle.status != "open":
            raise ConflictError(
                "Só um ciclo aberto regenera requests", details={"status": cycle.status}
            )

        pares = await self._pares_elegiveis(cycle)
        criados = await self._requests.gerar_em_lote(
            cycle_id=cycle.id,
            form_id=cycle.form_id,
            pares=sorted(pares),
            due_date=cycle.end_date,
        )
        return ResultadoDaAbertura(
            cycle=cycle, requests_criados=criados, pares_elegiveis=len(pares)
        )

    async def close(self, cycle_id: UUID, *, automatico: bool = False) -> FeedbackCycle:
        cycle = await self._exige_ciclo(cycle_id)
        _exige_transicao(cycle.status, "closed", TRANSICOES_CICLO, "ciclo")

        cycle.status = "closed"
        cycle.closed_at = datetime.now(UTC)
        await self._outbox.enqueue(
            topic="cycle.closed",
            payload={"cycle_id": str(cycle.id), "automatico": automatico},
            idempotency_key=f"cycle.closed:{cycle.id}",
        )
        return cycle

    async def publish(self, cycle_id: UUID) -> FeedbackCycle:
        cycle = await self._exige_ciclo(cycle_id)
        _exige_transicao(cycle.status, "published", TRANSICOES_CICLO, "ciclo")

        cycle.status = "published"
        cycle.published_at = datetime.now(UTC)
        await self._outbox.enqueue(
            topic="cycle.published",
            payload={"cycle_id": str(cycle.id)},
            idempotency_key=f"cycle.published:{cycle.id}",
        )
        return cycle

    async def archive(self, cycle_id: UUID) -> FeedbackCycle:
        cycle = await self._exige_ciclo(cycle_id)
        _exige_transicao(cycle.status, "archived", TRANSICOES_CICLO, "ciclo")
        cycle.status = "archived"
        return cycle

    async def extend_evaluated_period(
        self, cycle_id: UUID, *, evaluated_end: date
    ) -> FeedbackCycle:
        """Estende a janela de resposta sem mexer nas datas oficiais (BR-MIGRAR-006).

        Adia o fechamento automático como efeito — é o que PAR-06 espera.
        """
        cycle = await self._exige_ciclo(cycle_id)
        if cycle.status not in ("draft", "open"):
            raise ConflictError(
                "Só ciclo em rascunho ou aberto estende período",
                details={"status": cycle.status},
            )
        if evaluated_end < cycle.start_date:
            raise ValidationError("O período avaliado não pode terminar antes do início do ciclo")

        cycle.evaluated_end = evaluated_end
        return cycle

    async def _exige_ciclo(self, cycle_id: UUID) -> FeedbackCycle:
        cycle = await self._cycles.get(cycle_id)
        if cycle is None:
            raise NotFoundError("Ciclo não encontrado")
        return cycle


class RequestService:
    """Ciclo de vida do request — só por comando, nunca por update livre."""

    def __init__(
        self,
        requests: RequestRepository,
        answers: AnswerRepository,
        questions: QuestionRepository,
        outbox: OutboxService,
        audit: AuditService | None = None,
    ) -> None:
        self._requests = requests
        self._answers = answers
        self._questions = questions
        self._outbox = outbox
        self._audit = audit

    async def save_draft(
        self,
        tenant: TenantContext,
        request_id: UUID,
        respostas: dict[UUID, tuple[str | None, int | None]],
    ) -> FeedbackRequest:
        """Salva respostas parciais (BR-MIGRAR-012).

        Validação branda de propósito: rascunho aceita pergunta obrigatória em branco,
        aceita metade do formulário. O rigor é no envio — cobrar tudo no rascunho faria
        as pessoas perderem o que já escreveram, que é justamente o que a regra quer
        evitar.
        """
        request = await self._exige_do_avaliador(tenant, request_id)
        if request.status == "pending":
            _exige_transicao(request.status, "draft", TRANSICOES_REQUEST, "request")
            request.status = "draft"
        elif request.status != "draft":
            raise ConflictError(
                "Só request pendente ou em rascunho aceita rascunho",
                details={"status": request.status},
            )

        perguntas = {q.id: q for q in await self._questions.list_by_form(request.form_id)}
        await self._gravar_respostas(request, respostas, perguntas, estrito=False)
        return request

    async def submit(
        self,
        tenant: TenantContext,
        request_id: UUID,
        respostas: dict[UUID, tuple[str | None, int | None]],
    ) -> FeedbackRequest:
        """Envia o feedback (BR-MIGRAR-008).

        Validação estrita: pergunta obrigatória sem resposta recusa o envio inteiro, e
        nada é persistido — é o cenário "envio com respostas inválidas é recusado" de
        PAR-02. Por isso as respostas só são gravadas depois de a validação passar.
        """
        request = await self._exige_do_avaliador(tenant, request_id)
        if request.status == "pending":
            # Enviar direto, sem passar por rascunho, é o caminho comum de quem
            # responde de uma sentada só.
            request.status = "draft"
        _exige_transicao(request.status, "submitted", TRANSICOES_REQUEST, "request")

        perguntas = {q.id: q for q in await self._questions.list_by_form(request.form_id)}
        await self._gravar_respostas(request, respostas, perguntas, estrito=True)

        request.status = "submitted"
        request.submitted_at = datetime.now(UTC)
        await self._outbox.enqueue(
            topic="request.submitted",
            payload={
                "request_id": str(request.id),
                "user_id": str(request.receiver_id),
                "cycle_id": str(request.cycle_id),
            },
            idempotency_key=f"request.submitted:{request.id}",
        )
        return request

    async def _gravar_respostas(
        self,
        request: FeedbackRequest,
        respostas: dict[UUID, tuple[str | None, int | None]],
        perguntas: dict[UUID, FeedbackFormQuestion],
        *,
        estrito: bool,
    ) -> None:
        desconhecidas = [str(qid) for qid in respostas if qid not in perguntas]
        if desconhecidas:
            raise ValidationError(
                "Resposta para pergunta que não é deste formulário",
                details={"question_ids": desconhecidas},
            )

        if estrito:
            faltando = [
                str(q.id)
                for q in perguntas.values()
                if q.required and not _respondida(q, respostas.get(q.id))
            ]
            if faltando:
                raise ValidationError(
                    "Respostas obrigatórias em branco", details={"question_ids": faltando}
                )
            invalidas = [
                str(qid)
                for qid, valor in respostas.items()
                if _preenchida(valor) and not _respondida(perguntas[qid], valor)
            ]
            if invalidas:
                raise ValidationError(
                    "Resposta incompatível com o tipo da pergunta",
                    details={"question_ids": invalidas},
                )

        for question_id, (texto, nota) in respostas.items():
            if not _preenchida((texto, nota)):
                continue
            await self._answers.upsert(
                request_id=request.id,
                question_id=question_id,
                answer_text=texto,
                answer_score=nota,
            )

    async def mark_read(self, tenant: TenantContext, request_id: UUID) -> None:
        """Registra que o avaliado leu o feedback recebido.

        Idempotente: reler não reescreve o carimbo, porque o UPDATE só encontra linha
        com `read_at` nulo. Quem não é o destinatário recebe 404 — não precisa saber
        que o feedback existe.
        """
        if await self._requests.marcar_lido(request_id, tenant.user_id):
            return

        request = await self._requests.get(request_id)
        if request is None or request.receiver_id != tenant.user_id:
            raise NotFoundError("Feedback não encontrado")

    async def waive(self, tenant: TenantContext, request_id: UUID) -> FeedbackRequest:
        """Abdicar: sai do denominador do progresso (BR-MIGRAR-009)."""
        request = await self._exige_do_avaliador(tenant, request_id)
        _exige_transicao(request.status, "waived", TRANSICOES_REQUEST, "request")
        request.status = "waived"
        return request

    async def resume(self, tenant: TenantContext, request_id: UUID) -> FeedbackRequest:
        """Retomar volta para `pending` — não para o rascunho.

        As respostas gravadas continuam lá; o que se perde é só a marcação de "comecei".
        """
        request = await self._exige_do_avaliador(tenant, request_id)
        _exige_transicao(request.status, "pending", TRANSICOES_REQUEST, "request")
        request.status = "pending"
        return request

    async def cancel(
        self, tenant: TenantContext, request_id: UUID, *, justificativa: str
    ) -> FeedbackRequest:
        """Cancelamento é da gestão, exige justificativa e audita (PAR-02).

        A justificativa não é formalidade: é o que o avaliado lê depois para entender
        por que o pedido sumiu da lista dele. Vazio não passa, nem no banco (CHECK).
        """
        if not justificativa.strip():
            raise ValidationError("Cancelamento exige justificativa")

        request = await self._requests.get(request_id)
        if request is None:
            raise NotFoundError("Request não encontrado")
        _exige_transicao(request.status, "cancelled", TRANSICOES_REQUEST, "request")

        request.status = "cancelled"
        request.cancel_justification = justificativa.strip()

        if self._audit is not None:
            await self._audit.record(
                tenant,
                action="request.cancelled",
                table_name="feedback_requests",
                record_id=request.id,
                details={"justificativa": justificativa.strip()},
                notificar=[request.giver_id],
            )
        return request

    async def _exige_do_avaliador(
        self, tenant: TenantContext, request_id: UUID
    ) -> FeedbackRequest:
        """Request é do avaliador. Ninguém responde no lugar de outra pessoa."""
        request = await self._requests.get(request_id)
        if request is None:
            raise NotFoundError("Request não encontrado")
        if request.giver_id != tenant.user_id:
            # 404 e não 403: quem não é o dono não precisa saber que o request existe.
            raise NotFoundError("Request não encontrado")
        return request


@dataclass(frozen=True, slots=True)
class ProgressoDoCiclo:
    total: int
    concluidos: int
    pendentes: int
    atrasados: int
    excluidos: int

    @property
    def percentual(self) -> float:
        """Ciclo sem nada a fazer é 100% feito, não 0% — e não divide por zero."""
        if self.total == 0:
            return 100.0
        return round(self.concluidos * 100 / self.total, 1)


class CycleProgressService:
    """O único cálculo de progresso do sistema (BR-MIGRAR-009).

    O legado tinha três implementações — dashboard do gestor, do coordenador e do admin
    — e elas discordavam, porque cada tela decidia por conta própria o que fazia parte
    do denominador. Aqui `cancelled` e `waived` saem do total (o trabalho deixou de ser
    esperado) e `submitted` conta como concluído. Quem quiser outro número, muda aqui e
    muda para todo mundo, que é o ponto.
    """

    def __init__(self, requests: RequestRepository) -> None:
        self._requests = requests

    async def calcular(self, cycle_id: UUID, hoje: date | None = None) -> ProgressoDoCiclo:
        contagem = await self._requests.contagem_por_status(cycle_id)
        total = sum(contagem.get(s, 0) for s in STATUS_NO_DENOMINADOR)
        concluidos = sum(contagem.get(s, 0) for s in STATUS_CONCLUIDO)
        excluidos = contagem.get("cancelled", 0) + contagem.get("waived", 0)
        atrasados = await self._requests.ids_atrasados(cycle_id, hoje)

        return ProgressoDoCiclo(
            total=total,
            concluidos=concluidos,
            pendentes=total - concluidos,
            atrasados=len(atrasados),
            excluidos=excluidos,
        )


class FreeFeedbackService:
    def __init__(self, free: FreeFeedbackRepository) -> None:
        self._free = free

    async def send(
        self,
        tenant: TenantContext,
        *,
        receiver_id: UUID,
        is_anonymous: bool,
        is_sensitive: bool,
        positives: str | None,
        improvements: str | None,
        message: str | None,
    ) -> FreeFeedback:
        """Anônimo não guarda o autor — em lugar nenhum (AMB-001).

        Não é "esconde na tela": `giver_id` fica nulo no banco, e o CHECK impede que
        alguém preencha os dois. Anonimato que depende de a interface não mostrar
        acaba sendo quebrado pelo primeiro relatório novo.
        """
        if not any((positives, improvements, message)):
            raise ValidationError("Feedback vazio")
        if receiver_id == tenant.user_id:
            raise ValidationError("Não é possível enviar feedback para si mesmo")

        return self._free.add(
            FreeFeedback(
                giver_id=None if is_anonymous else tenant.user_id,
                receiver_id=receiver_id,
                is_anonymous=is_anonymous,
                is_sensitive=is_sensitive,
                positives=positives,
                improvements=improvements,
                message=message,
            )
        )

    async def mark_read(self, tenant: TenantContext, feedback_id: UUID) -> FreeFeedback:
        feedback = await self._free.get(feedback_id)
        if feedback is None:
            raise NotFoundError("Feedback não encontrado")
        if feedback.receiver_id != tenant.user_id and not tenant.has_role("admin", "rh"):
            raise NotFoundError("Feedback não encontrado")

        if feedback.read_at is None:
            feedback.read_at = datetime.now(UTC)
            feedback.read_by = tenant.user_id
        return feedback


class CycleNoteService:
    def __init__(self, notes: CycleNoteRepository) -> None:
        self._notes = notes

    async def write(
        self,
        tenant: TenantContext,
        *,
        cycle_id: UUID,
        about_user_id: UUID,
        content: str,
        is_audio_transcription: bool = False,
    ) -> CycleNote:
        if not content.strip():
            raise ValidationError("Anotação vazia")
        return self._notes.add(
            CycleNote(
                cycle_id=cycle_id,
                author_id=tenant.user_id,
                about_user_id=about_user_id,
                content=content.strip(),
                is_audio_transcription=is_audio_transcription,
            )
        )

    async def delete(self, tenant: TenantContext, note_id: UUID) -> None:
        """Anotação é do autor. Nem a gestão apaga a de outra pessoa."""
        nota = await self._notes.get(note_id)
        if nota is None or nota.author_id != tenant.user_id:
            raise NotFoundError("Anotação não encontrada")
        await self._notes.remove(nota)


def _preenchida(valor: tuple[str | None, int | None] | None) -> bool:
    if valor is None:
        return False
    texto, nota = valor
    return bool((texto or "").strip()) or nota is not None


def _respondida(
    pergunta: FeedbackFormQuestion, valor: tuple[str | None, int | None] | None
) -> bool:
    """Resposta válida é a que casa com o tipo da pergunta.

    Nota em pergunta de texto (e vice-versa) não conta como respondida: é o erro que
    aparece quando o front manda o campo errado, e passar batido geraria feedback com
    a metade útil vazia.
    """
    if valor is None:
        return False
    texto, nota = valor
    if pergunta.question_type == "rating":
        return nota is not None
    return bool((texto or "").strip())
