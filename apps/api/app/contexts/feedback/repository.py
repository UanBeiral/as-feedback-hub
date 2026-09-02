"""Repositórios do contexto `feedback`.

Todos herdam `TenantScopedRepository` — inclusive os de leitura pesada, como o de
progresso. É tentador escrever a agregação como SQL solto "porque é só um SELECT";
seria o primeiro furo no isolamento, e o teste do CI existe para impedir.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.contexts.feedback.models import (
    DIAS_DE_CARENCIA,
    CycleNote,
    FeedbackAnswer,
    FeedbackCycle,
    FeedbackForm,
    FeedbackFormQuestion,
    FeedbackPermission,
    FeedbackRequest,
    FreeFeedback,
)
from app.core.tenancy import TenantScopedRepository

# Estados que contam no denominador do progresso (BR-MIGRAR-009): `cancelled` e
# `waived` ficam de fora porque o trabalho deixou de ser esperado — mantê-los puniria
# o time por decisões da gestão.
STATUS_NO_DENOMINADOR = ("pending", "draft", "submitted", "expired")
STATUS_CONCLUIDO = ("submitted",)
# Só o que ainda espera resposta pode estar atrasado.
STATUS_EM_ABERTO = ("pending", "draft")


class FormRepository(TenantScopedRepository[FeedbackForm]):
    model = FeedbackForm

    async def list_active(self) -> list[FeedbackForm]:
        stmt = (
            self._scoped()
            .where(FeedbackForm.archived_at.is_(None))
            .order_by(FeedbackForm.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def usado_por_ciclo_vivo(self, form_id: UUID) -> bool:
        """Formulário preso a ciclo que ainda anda não pode ser arquivado.

        "Vivo" aqui é `draft` ou `open`: um ciclo fechado já colheu o que precisava, e
        travar o formulário para sempre por causa dele seria manter lixo na tela de
        administração.
        """
        stmt = (
            select(func.count())
            .select_from(FeedbackCycle)
            .where(
                FeedbackCycle.tenant_id == self.tenant_id,
                FeedbackCycle.form_id == form_id,
                FeedbackCycle.status.in_(("draft", "open")),
            )
        )
        return bool((await self._session.execute(stmt)).scalar_one())


class QuestionRepository(TenantScopedRepository[FeedbackFormQuestion]):
    model = FeedbackFormQuestion

    async def list_by_form(self, form_id: UUID) -> list[FeedbackFormQuestion]:
        stmt = (
            self._scoped()
            .where(FeedbackFormQuestion.form_id == form_id)
            .order_by(FeedbackFormQuestion.sort_order, FeedbackFormQuestion.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class PermissionRepository(TenantScopedRepository[FeedbackPermission]):
    model = FeedbackPermission

    async def get_regra(
        self, *, reviewer_id: UUID, reviewee_id: UUID, permission_type: str, cycle_id: UUID | None
    ) -> FeedbackPermission | None:
        stmt = self._scoped().where(
            FeedbackPermission.reviewer_id == reviewer_id,
            FeedbackPermission.reviewee_id == reviewee_id,
            FeedbackPermission.permission_type == permission_type,
            FeedbackPermission.cycle_id.is_(None)
            if cycle_id is None
            else FeedbackPermission.cycle_id == cycle_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_ativas_para_ciclo(self, cycle_id: UUID) -> list[FeedbackPermission]:
        """Permissões que valem para este ciclo: as dele e as permanentes."""
        stmt = self._scoped().where(
            FeedbackPermission.active.is_(True),
            or_(
                FeedbackPermission.cycle_id == cycle_id,
                FeedbackPermission.cycle_id.is_(None),
            ),
        )
        return list((await self._session.execute(stmt)).scalars().all())


class CycleRepository(TenantScopedRepository[FeedbackCycle]):
    model = FeedbackCycle

    async def list_by_status(self, *status: str) -> list[FeedbackCycle]:
        stmt = self._scoped().order_by(FeedbackCycle.start_date.desc())
        if status:
            stmt = stmt.where(FeedbackCycle.status.in_(status))
        return list((await self._session.execute(stmt)).scalars().all())

    async def existe_aberto_na_frequencia(
        self, frequency: str, *, exceto: UUID | None = None
    ) -> bool:
        """Limite de concorrência por frequência (BR-MIGRAR-011).

        Sem frequência declarada não há janela para ocupar — ciclos avulsos convivem.
        """
        stmt = (
            select(func.count())
            .select_from(FeedbackCycle)
            .where(
                FeedbackCycle.tenant_id == self.tenant_id,
                FeedbackCycle.frequency == frequency,
                FeedbackCycle.status == "open",
            )
        )
        if exceto is not None:
            stmt = stmt.where(FeedbackCycle.id != exceto)
        return bool((await self._session.execute(stmt)).scalar_one())


class CycleDueRepository:
    """Lado do scheduler: ciclos vencidos, de todos os tenants.

    Terceira exceção legítima ao isolamento por herança, pelo mesmo motivo do
    `OutboxDispatchRepository`: o job de fechamento não roda dentro de uma sessão de
    usuário. Cada ciclo devolvido carrega o próprio `tenant_id`, e é ele que o
    fechamento usa.
    """

    def __init__(self, session: object) -> None:
        self._session = session

    async def vencidos(self, hoje: date | None = None, *, limit: int = 100) -> list[FeedbackCycle]:
        """Ciclos `open` cujo prazo venceu há mais que a carência (BR-MIGRAR-005).

        A comparação usa `evaluated_end` quando ele estende o prazo — a extensão manual
        adia o fechamento, e é para isso que ela existe.
        """
        hoje = hoje or datetime.now(UTC).date()
        limite = hoje - timedelta(days=DIAS_DE_CARENCIA)
        stmt = (
            select(FeedbackCycle)
            .where(
                FeedbackCycle.status == "open",
                func.greatest(
                    FeedbackCycle.end_date,
                    func.coalesce(FeedbackCycle.evaluated_end, FeedbackCycle.end_date),
                )
                < limite,
            )
            .order_by(FeedbackCycle.end_date)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())  # type: ignore[attr-defined]


class RequestRepository(TenantScopedRepository[FeedbackRequest]):
    model = FeedbackRequest

    async def gerar_em_lote(
        self,
        *,
        cycle_id: UUID,
        form_id: UUID,
        pares: list[tuple[UUID, UUID]],
        due_date: date | None,
    ) -> int:
        """Cria os requests do ciclo, pulando o que já existe (BR-MIGRAR-001/010).

        `ON CONFLICT DO NOTHING` sobre a chave natural é o que faz a geração ser
        idempotente de verdade: reabrir não duplica, e a garantia é do banco, não da
        checagem prévia que alguém pode esquecer de escrever no próximo contexto.
        Devolve quantos foram efetivamente criados.
        """
        if not pares:
            return 0

        stmt = (
            pg_insert(FeedbackRequest)
            .values(
                [
                    {
                        "tenant_id": self.tenant_id,
                        "cycle_id": cycle_id,
                        "form_id": form_id,
                        "giver_id": giver,
                        "receiver_id": receiver,
                        "status": "pending",
                        "due_date": due_date,
                    }
                    for giver, receiver in pares
                ]
            )
            .on_conflict_do_nothing(constraint="uq_feedback_requests_par")
            .returning(FeedbackRequest.id)
        )
        return len((await self._session.execute(stmt)).scalars().all())

    async def list_do_ciclo(self, cycle_id: UUID) -> list[FeedbackRequest]:
        stmt = self._scoped().where(FeedbackRequest.cycle_id == cycle_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def ids_de_avaliadores_do_ciclo(self, cycle_id: UUID) -> list[UUID]:
        """Quem tem pedido neste ciclo — os destinatários do aviso de abertura.

        Só quem ainda deve resposta: avisar de um ciclo novo quem já teve o pedido
        cancelado ou abdicado é notificação que a pessoa não sabe o que fazer com.
        """
        stmt = (
            self._scoped()
            .where(
                FeedbackRequest.cycle_id == cycle_id,
                FeedbackRequest.status.in_(STATUS_EM_ABERTO),
            )
            .with_only_columns(FeedbackRequest.giver_id)
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def ids_de_participantes_do_ciclo(self, cycle_id: UUID) -> list[UUID]:
        """Todo mundo que participou — avaliadores e avaliados.

        Usado na publicação: o resultado interessa aos dois lados, e quem só recebeu
        feedback não aparece na lista de avaliadores.
        """
        avaliadores = self._scoped().where(
            FeedbackRequest.cycle_id == cycle_id
        ).with_only_columns(FeedbackRequest.giver_id)
        avaliados = self._scoped().where(
            FeedbackRequest.cycle_id == cycle_id
        ).with_only_columns(FeedbackRequest.receiver_id)

        ids = set((await self._session.execute(avaliadores)).scalars().all())
        ids |= set((await self._session.execute(avaliados)).scalars().all())
        return sorted(ids)

    async def marcar_lido(self, request_id: UUID, leitor_id: UUID) -> int:
        """Registra que o avaliado leu o feedback recebido (BR-MIGRAR-023 no request).

        O filtro por `receiver_id` está no próprio UPDATE: ninguém marca como lido o
        feedback de outra pessoa, e o escopo é do banco, não da memória de quem escreve
        o service.
        """
        from sqlalchemy import update

        resultado = await self._session.execute(
            update(FeedbackRequest)
            .where(
                FeedbackRequest.tenant_id == self.tenant_id,
                FeedbackRequest.id == request_id,
                FeedbackRequest.receiver_id == leitor_id,
                FeedbackRequest.status == "submitted",
                FeedbackRequest.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC), read_by=leitor_id)
        )
        return int(resultado.rowcount or 0)

    async def list_recebidos(self, receiver_id: UUID, *, limit: int = 100) -> list[FeedbackRequest]:
        """Feedbacks que a pessoa recebeu e já foram enviados."""
        stmt = (
            self._scoped()
            .where(
                FeedbackRequest.receiver_id == receiver_id,
                FeedbackRequest.status == "submitted",
            )
            .order_by(FeedbackRequest.submitted_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_para_avaliador(
        self, giver_id: UUID, *, status: tuple[str, ...] = STATUS_EM_ABERTO
    ) -> list[FeedbackRequest]:
        stmt = (
            self._scoped()
            .where(FeedbackRequest.giver_id == giver_id, FeedbackRequest.status.in_(status))
            .order_by(FeedbackRequest.due_date.nulls_last(), FeedbackRequest.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def contagem_por_status(self, cycle_id: UUID) -> dict[str, int]:
        stmt = (
            select(FeedbackRequest.status, func.count())
            .where(
                FeedbackRequest.tenant_id == self.tenant_id,
                FeedbackRequest.cycle_id == cycle_id,
            )
            .group_by(FeedbackRequest.status)
        )
        return {status: total for status, total in (await self._session.execute(stmt)).all()}

    def _atrasados_clause(self, hoje: date):
        """Atraso é derivação, não coluna (BR-MIGRAR-007).

        No legado o "atrasado" era calculado na tela — e cada tela calculava do seu
        jeito, que é como o mesmo request aparecia atrasado no dashboard e em dia no
        relatório. Aqui a expressão vive num lugar só e alimenta os dois.
        """
        return and_(
            FeedbackRequest.status.in_(STATUS_EM_ABERTO),
            FeedbackRequest.due_date.is_not(None),
            FeedbackRequest.due_date < hoje,
        )

    async def ids_atrasados(self, cycle_id: UUID, hoje: date | None = None) -> set[UUID]:
        hoje = hoje or datetime.now(UTC).date()
        stmt = (
            self._scoped()
            .where(FeedbackRequest.cycle_id == cycle_id, self._atrasados_clause(hoje))
            .with_only_columns(FeedbackRequest.id)
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def expirar_vencidos(self, hoje: date | None = None) -> int:
        """Marca como `expired` o que passou do prazo + carência (BR-MIGRAR-003/007).

        Diferente de "atrasado", que é derivação: aqui o request morre de fato, porque
        a janela de tolerância acabou.
        """
        hoje = hoje or datetime.now(UTC).date()
        limite = hoje - timedelta(days=DIAS_DE_CARENCIA)
        alvos = (
            self._scoped()
            .where(
                FeedbackRequest.status.in_(STATUS_EM_ABERTO),
                FeedbackRequest.due_date.is_not(None),
                FeedbackRequest.due_date < limite,
            )
            .with_only_columns(FeedbackRequest.id)
        )
        ids = list((await self._session.execute(alvos)).scalars().all())
        for request_id in ids:
            request = await self.get(request_id)
            if request is not None:
                request.status = "expired"
        return len(ids)


class AnswerRepository(TenantScopedRepository[FeedbackAnswer]):
    model = FeedbackAnswer

    async def list_do_request(self, request_id: UUID) -> list[FeedbackAnswer]:
        stmt = self._scoped().where(FeedbackAnswer.request_id == request_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def upsert(
        self,
        *,
        request_id: UUID,
        question_id: UUID,
        answer_text: str | None,
        answer_score: int | None,
    ) -> None:
        """Salvar rascunho duas vezes atualiza, não acumula (BR-MIGRAR-012)."""
        stmt = (
            pg_insert(FeedbackAnswer)
            .values(
                tenant_id=self.tenant_id,
                request_id=request_id,
                question_id=question_id,
                answer_text=answer_text,
                answer_score=answer_score,
            )
            .on_conflict_do_update(
                constraint="uq_feedback_answers_pergunta",
                set_={
                    "answer_text": answer_text,
                    "answer_score": answer_score,
                    "updated_at": datetime.now(UTC),
                },
            )
        )
        await self._session.execute(stmt)


class FreeFeedbackRepository(TenantScopedRepository[FreeFeedback]):
    model = FreeFeedback

    def _visiveis_para(self, profile_id: UUID, *, gestao: bool) -> Select[tuple[FreeFeedback]]:
        """O sensível não chega ao destinatário — só à gestão (invariante do aggregate)."""
        stmt = self._scoped().where(FreeFeedback.receiver_id == profile_id)
        if not gestao:
            stmt = stmt.where(FreeFeedback.is_sensitive.is_(False))
        return stmt

    async def list_recebidos(
        self, profile_id: UUID, *, gestao: bool = False
    ) -> list[FreeFeedback]:
        stmt = self._visiveis_para(profile_id, gestao=gestao).order_by(
            FreeFeedback.created_at.desc()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_sensiveis(self) -> list[FreeFeedback]:
        stmt = (
            self._scoped()
            .where(FreeFeedback.is_sensitive.is_(True))
            .order_by(FreeFeedback.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())


class CycleNoteRepository(TenantScopedRepository[CycleNote]):
    model = CycleNote

    async def list_do_autor(self, author_id: UUID, cycle_id: UUID | None = None) -> list[CycleNote]:
        stmt = self._scoped().where(CycleNote.author_id == author_id)
        if cycle_id is not None:
            stmt = stmt.where(CycleNote.cycle_id == cycle_id)
        stmt = stmt.order_by(CycleNote.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())
