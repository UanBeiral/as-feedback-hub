"""Read models do contexto `reporting`.

Todas as agregações do sistema moram aqui, e todas escopadas por tenant como qualquer
repositório (o teste de isolamento do CI varre este arquivo também). No legado esses
cálculos rodavam **no browser**: cada tela baixava as linhas e somava do seu jeito, o
que produzia números diferentes para a mesma pergunta e obrigava a carregar a base
inteira para mostrar uma porcentagem.

Os limites de linha de BR-MIGRAR-029 (preview 50, tabela 100) são aplicados na query,
não na renderização: o ponto do limite é não trafegar o que ninguém vai olhar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, select

from app.contexts.client_eval.models import ClientEvaluation
from app.contexts.feedback.models import (
    FeedbackAnswer,
    FeedbackCycle,
    FeedbackRequest,
    FreeFeedback,
)
from app.contexts.identity.models import Department, Profile
from app.core.tenancy import TenantScopedRepository

LIMITE_PREVIEW = 50
LIMITE_TABELA = 100

# Mesmos conjuntos do `CycleProgressService`: o denominador do relatório precisa ser o
# mesmo do dashboard, senão voltamos ao problema que a migração veio resolver.
STATUS_NO_DENOMINADOR = ("pending", "draft", "submitted", "expired")


@dataclass(frozen=True, slots=True)
class LinhaDe360:
    profile_id: UUID
    nome: str
    departamento: str | None
    recebidos: int
    respondidos: int
    media_nota: float | None

    @property
    def percentual(self) -> float:
        return round(self.respondidos * 100 / self.recebidos, 1) if self.recebidos else 0.0


@dataclass(frozen=True, slots=True)
class LinhaDeCliente:
    profile_id: UUID
    nome: str
    avaliacoes: int
    respondidas: int
    media_geral: float | None
    negativas: int


@dataclass(frozen=True, slots=True)
class LinhaDeEngajamento:
    profile_id: UUID
    nome: str
    solicitados: int
    enviados: int

    @property
    def percentual(self) -> float:
        # `solicitados == 0` não chega aqui: quem não teve request sai do denominador
        # antes (BR-MIGRAR-028). O guard existe só para o caso degenerado.
        return round(self.enviados * 100 / self.solicitados, 1) if self.solicitados else 0.0


class Report360Query(TenantScopedRepository[FeedbackRequest]):
    """Feedback 360 por pessoa avaliada, dentro de um ciclo."""

    model = FeedbackRequest

    def _base(self, cycle_id: UUID | None, department_id: UUID | None) -> Select:
        media = func.avg(FeedbackAnswer.answer_score)
        stmt = (
            select(
                Profile.id,
                Profile.full_name,
                Department.name,
                func.count(func.distinct(FeedbackRequest.id)),
                func.count(
                    func.distinct(
                        case((FeedbackRequest.status == "submitted", FeedbackRequest.id))
                    )
                ),
                media,
            )
            .select_from(FeedbackRequest)
            .join(Profile, Profile.id == FeedbackRequest.receiver_id)
            .join(Department, Department.id == Profile.department_id, isouter=True)
            # LEFT JOIN nas respostas: um request pendente não tem nota, e sumir com a
            # linha faria o avaliado parecer inexistente em vez de sem resposta.
            .join(
                FeedbackAnswer,
                and_(
                    FeedbackAnswer.request_id == FeedbackRequest.id,
                    FeedbackAnswer.answer_score.is_not(None),
                ),
                isouter=True,
            )
            .where(
                FeedbackRequest.tenant_id == self.tenant_id,
                FeedbackRequest.status.in_(STATUS_NO_DENOMINADOR),
            )
            .group_by(Profile.id, Profile.full_name, Department.name)
            .order_by(Profile.full_name)
        )
        if cycle_id is not None:
            stmt = stmt.where(FeedbackRequest.cycle_id == cycle_id)
        if department_id is not None:
            stmt = stmt.where(Profile.department_id == department_id)
        return stmt

    async def linhas(
        self,
        *,
        cycle_id: UUID | None = None,
        department_id: UUID | None = None,
        limite: int = LIMITE_TABELA,
    ) -> list[LinhaDe360]:
        resultado = await self._session.execute(self._base(cycle_id, department_id).limit(limite))
        return [
            LinhaDe360(
                profile_id=pid,
                nome=nome,
                departamento=depto,
                recebidos=recebidos,
                respondidos=respondidos,
                media_nota=round(float(media), 2) if media is not None else None,
            )
            for pid, nome, depto, recebidos, respondidos, media in resultado.all()
        ]


class ClientReportQuery(TenantScopedRepository[ClientEvaluation]):
    """Avaliações de cliente agregadas por pessoa avaliada."""

    model = ClientEvaluation

    async def linhas(
        self,
        *,
        target_user_id: UUID | None = None,
        desde: date | None = None,
        ate: date | None = None,
        apenas_negativas: bool = False,
        limite: int = LIMITE_TABELA,
    ) -> list[LinhaDeCliente]:
        respondidas = func.count(
            case((ClientEvaluation.status == "submitted", ClientEvaluation.id))
        )
        negativas = func.count(case((ClientEvaluation.has_negative.is_(True), ClientEvaluation.id)))
        stmt = (
            select(
                Profile.id,
                Profile.full_name,
                func.count(ClientEvaluation.id),
                respondidas,
                func.avg(ClientEvaluation.overall_rating),
                negativas,
            )
            .select_from(ClientEvaluation)
            .join(Profile, Profile.id == ClientEvaluation.target_user_id)
            .where(ClientEvaluation.tenant_id == self.tenant_id)
            .group_by(Profile.id, Profile.full_name)
            .order_by(Profile.full_name)
            .limit(limite)
        )
        if target_user_id is not None:
            stmt = stmt.where(ClientEvaluation.target_user_id == target_user_id)
        if desde is not None:
            stmt = stmt.where(func.date(ClientEvaluation.created_at) >= desde)
        if ate is not None:
            stmt = stmt.where(func.date(ClientEvaluation.created_at) <= ate)
        if apenas_negativas:
            stmt = stmt.where(ClientEvaluation.has_negative.is_(True))

        resultado = await self._session.execute(stmt)
        return [
            LinhaDeCliente(
                profile_id=pid,
                nome=nome,
                avaliacoes=total,
                respondidas=resp,
                media_geral=round(float(media), 2) if media is not None else None,
                negativas=neg,
            )
            for pid, nome, total, resp, media, neg in resultado.all()
        ]


class EngagementQuery(TenantScopedRepository[FeedbackRequest]):
    """Engajamento por pessoa (BR-MIGRAR-028).

    Duas regras que o legado errava e que aqui são a query inteira:

    1. **Só ciclos fechados entram.** Um ciclo aberto ainda está sendo respondido;
       incluí-lo mede o calendário, não o engajamento das pessoas.
    2. **Quem não teve request sai do denominador.** Alguém que entrou ontem, ou que
       ninguém foi designado a avaliar, apareceria com 0% e puxaria a média para baixo
       por um trabalho que nunca lhe foi pedido. O `INNER JOIN` faz essa exclusão por
       construção — não há linha para quem não tem request.
    """

    model = FeedbackRequest

    async def linhas(self, *, limite: int = LIMITE_TABELA) -> list[LinhaDeEngajamento]:
        enviados = func.count(
            case((FeedbackRequest.status == "submitted", FeedbackRequest.id))
        )
        stmt = (
            select(Profile.id, Profile.full_name, func.count(FeedbackRequest.id), enviados)
            .select_from(FeedbackRequest)
            .join(Profile, Profile.id == FeedbackRequest.giver_id)
            .join(FeedbackCycle, FeedbackCycle.id == FeedbackRequest.cycle_id)
            .where(
                FeedbackRequest.tenant_id == self.tenant_id,
                FeedbackCycle.status.in_(("closed", "published", "archived")),
                FeedbackRequest.status.in_(STATUS_NO_DENOMINADOR),
            )
            .group_by(Profile.id, Profile.full_name)
            .order_by(Profile.full_name)
            .limit(limite)
        )
        resultado = await self._session.execute(stmt)
        return [
            LinhaDeEngajamento(
                profile_id=pid, nome=nome, solicitados=solicitados, enviados=enviados_
            )
            for pid, nome, solicitados, enviados_ in resultado.all()
        ]


@dataclass(frozen=True, slots=True)
class ItemDeHistorico:
    """Uma linha do histórico, seja de que tipo for.

    Um formato só para os três tipos (livre, cliente, 360) porque a tela os mostra em
    seções com a mesma estrutura. Guardar três formatos diferentes só empurraria a
    normalização para o front.
    """

    tipo: str
    quando: datetime | None
    sobre_id: UUID
    sobre_nome: str
    titulo: str
    detalhe: str | None
    lido_em: datetime | None


class TeamHistoryQuery(TenantScopedRepository[FeedbackRequest]):
    """Histórico dos três tipos de feedback, restrito ao escopo de equipe.

    O escopo chega pronto do `TeamScopeService` — esta query nunca o amplia. É o
    cenário "parâmetro não amplia escopo" de PAR-05 do lado da leitura: lista de ids
    vazia devolve vazio, e não "todo mundo".
    """

    model = FeedbackRequest

    async def livre(
        self, visiveis: set[UUID], *, limite: int = LIMITE_TABELA
    ) -> list[ItemDeHistorico]:
        if not visiveis:
            return []
        stmt = (
            select(
                FreeFeedback.created_at,
                Profile.id,
                Profile.full_name,
                FreeFeedback.is_anonymous,
                FreeFeedback.positives,
                FreeFeedback.improvements,
                FreeFeedback.message,
                FreeFeedback.read_at,
            )
            .select_from(FreeFeedback)
            .join(Profile, Profile.id == FreeFeedback.receiver_id)
            .where(
                FreeFeedback.tenant_id == self.tenant_id,
                FreeFeedback.receiver_id.in_(visiveis),
            )
            .order_by(FreeFeedback.created_at.desc())
            .limit(limite)
        )
        linhas = (await self._session.execute(stmt)).all()
        return [
            ItemDeHistorico(
                tipo="livre",
                quando=quando,
                sobre_id=pid,
                sobre_nome=nome,
                titulo="Feedback livre" + (" (anônimo)" if anonimo else ""),
                detalhe=_juntar(positivos, melhorias, mensagem),
                lido_em=lido,
            )
            for quando, pid, nome, anonimo, positivos, melhorias, mensagem, lido in linhas
        ]

    async def clientes(
        self, visiveis: set[UUID], *, limite: int = LIMITE_TABELA
    ) -> list[ItemDeHistorico]:
        if not visiveis:
            return []
        stmt = (
            select(
                ClientEvaluation.submitted_at,
                Profile.id,
                Profile.full_name,
                ClientEvaluation.client_name,
                ClientEvaluation.overall_rating,
                ClientEvaluation.has_negative,
            )
            .select_from(ClientEvaluation)
            .join(Profile, Profile.id == ClientEvaluation.target_user_id)
            .where(
                ClientEvaluation.tenant_id == self.tenant_id,
                ClientEvaluation.target_user_id.in_(visiveis),
                ClientEvaluation.status == "submitted",
            )
            .order_by(ClientEvaluation.submitted_at.desc())
            .limit(limite)
        )
        linhas = (await self._session.execute(stmt)).all()
        return [
            ItemDeHistorico(
                tipo="cliente",
                quando=quando,
                sobre_id=pid,
                sobre_nome=nome,
                titulo=f"Avaliação de {cliente or 'cliente'}",
                detalhe=_juntar(
                    f"Nota {nota}" if nota is not None else None,
                    "sinalizada para atenção" if negativa else None,
                ),
                lido_em=None,
            )
            for quando, pid, nome, cliente, nota, negativa in linhas
        ]

    async def ciclos(
        self, visiveis: set[UUID], *, limite: int = LIMITE_TABELA
    ) -> list[ItemDeHistorico]:
        if not visiveis:
            return []
        stmt = (
            select(
                FeedbackRequest.submitted_at,
                Profile.id,
                Profile.full_name,
                FeedbackCycle.name,
                FeedbackRequest.read_at,
            )
            .select_from(FeedbackRequest)
            .join(Profile, Profile.id == FeedbackRequest.receiver_id)
            .join(FeedbackCycle, FeedbackCycle.id == FeedbackRequest.cycle_id)
            .where(
                FeedbackRequest.tenant_id == self.tenant_id,
                FeedbackRequest.receiver_id.in_(visiveis),
                FeedbackRequest.status == "submitted",
            )
            .order_by(FeedbackRequest.submitted_at.desc())
            .limit(limite)
        )
        linhas = (await self._session.execute(stmt)).all()
        return [
            ItemDeHistorico(
                tipo="ciclo",
                quando=quando,
                sobre_id=pid,
                sobre_nome=nome,
                titulo=f"Feedback 360 — {ciclo}",
                # Sem o autor, de propósito: quem avaliou não aparece no histórico.
                detalhe=None,
                lido_em=lido,
            )
            for quando, pid, nome, ciclo, lido in linhas
        ]


def _juntar(*partes: str | None) -> str | None:
    """Junta o que existe, devolve `None` quando não sobra nada."""
    texto = " · ".join(parte.strip() for parte in partes if parte and parte.strip())
    return texto or None


class ExecutiveDataQuery(TenantScopedRepository[FeedbackRequest]):
    """Dados brutos do relatório executivo de uma pessoa em um ciclo."""

    model = FeedbackRequest

    async def respostas_da_pessoa(
        self, *, cycle_id: UUID, profile_id: UUID, giver_id: UUID | None = None
    ) -> list[tuple[str, str | None, int | None]]:
        """Devolve (pergunta, texto, nota) do que a pessoa recebeu no ciclo.

        Sem identificar quem escreveu: o relatório executivo é sobre o avaliado, e
        carregar o autor de cada frase transformaria o documento numa lista de quem
        falou o quê.
        """
        from app.contexts.feedback.models import FeedbackFormQuestion

        stmt = (
            select(
                FeedbackFormQuestion.question_text,
                FeedbackAnswer.answer_text,
                FeedbackAnswer.answer_score,
            )
            .select_from(FeedbackAnswer)
            .join(FeedbackRequest, FeedbackRequest.id == FeedbackAnswer.request_id)
            .join(
                FeedbackFormQuestion,
                FeedbackFormQuestion.id == FeedbackAnswer.question_id,
            )
            .where(
                FeedbackAnswer.tenant_id == self.tenant_id,
                FeedbackRequest.cycle_id == cycle_id,
                FeedbackRequest.receiver_id == profile_id,
                FeedbackRequest.status == "submitted",
            )
            .order_by(FeedbackFormQuestion.sort_order)
        )
        if giver_id is not None:
            stmt = stmt.where(FeedbackRequest.giver_id == giver_id)

        return [tuple(linha) for linha in (await self._session.execute(stmt)).all()]
