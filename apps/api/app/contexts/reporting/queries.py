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

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.orm import aliased

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
class LinhaDeFeedbackLivre:
    """Feedback livre agregado por pessoa — a aba "Livres" do legado.

    Recebidos e enviados na mesma linha porque a pergunta que o relatório responde é
    sobre reciprocidade: quem recebe muito e não escreve nada é um caso; quem escreve
    muito e não recebe é outro, e nenhum dos dois aparece se as duas colunas viverem
    em relatórios separados.
    """

    profile_id: UUID
    nome: str
    recebidos: int
    enviados: int
    anonimos: int
    sensiveis: int


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


class FreeFeedbackReportQuery(TenantScopedRepository[FreeFeedback]):
    """Feedback livre por pessoa: o que recebeu e o que enviou."""

    model = FreeFeedback

    async def linhas(self, *, limite: int = LIMITE_TABELA) -> list[LinhaDeFeedbackLivre]:
        # Duas agregações com chaves diferentes (recebedor e autor) não cabem num
        # `GROUP BY` só: são feitas separadas e casadas por id em Python, que é barato
        # porque cada uma devolve uma linha por pessoa, não por feedback.
        recebidos = (
            select(
                FreeFeedback.receiver_id.label("pid"),
                func.count().label("total"),
                func.count(case((FreeFeedback.is_anonymous.is_(True), 1))).label("anon"),
                func.count(case((FreeFeedback.is_sensitive.is_(True), 1))).label("sens"),
            )
            .where(FreeFeedback.tenant_id == self.tenant_id)
            .group_by(FreeFeedback.receiver_id)
        )
        enviados = (
            select(FreeFeedback.giver_id.label("pid"), func.count().label("total"))
            .where(
                FreeFeedback.tenant_id == self.tenant_id,
                # Anônimo não tem autor no banco (AMB-001), então não conta para
                # ninguém — contá-lo em algum lugar seria reinventar o autor.
                FreeFeedback.giver_id.is_not(None),
            )
            .group_by(FreeFeedback.giver_id)
        )

        por_recebido = {
            linha.pid: linha for linha in (await self._session.execute(recebidos)).all()
        }
        por_enviado = {
            linha.pid: linha.total for linha in (await self._session.execute(enviados)).all()
        }

        ids = set(por_recebido) | set(por_enviado)
        if not ids:
            return []

        perfis = (
            await self._session.execute(
                select(Profile.id, Profile.full_name)
                .where(Profile.tenant_id == self.tenant_id, Profile.id.in_(ids))
                .order_by(Profile.full_name)
                .limit(limite)
            )
        ).all()

        return [
            LinhaDeFeedbackLivre(
                profile_id=pid,
                nome=nome,
                recebidos=por_recebido[pid].total if pid in por_recebido else 0,
                enviados=por_enviado.get(pid, 0),
                anonimos=por_recebido[pid].anon if pid in por_recebido else 0,
                sensiveis=por_recebido[pid].sens if pid in por_recebido else 0,
            )
            for pid, nome in perfis
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
class ParteDoHistorico:
    """Um campo rotulado de um item do histórico."""

    rotulo: str
    texto: str


@dataclass(frozen=True, slots=True)
class ItemDeHistorico:
    """Uma linha do histórico, seja de que tipo for.

    Um formato só para os três tipos (livre, cliente, 360) porque a tela os mostra em
    seções com a mesma estrutura. Guardar três formatos diferentes só empurraria a
    normalização para o front.
    """

    tipo: str
    # Id do registro de origem (feedback livre, avaliacao ou request). E o que permite
    # marcar ciencia a partir do historico, e a chave estavel da lista na tela.
    item_id: UUID
    quando: datetime | None
    sobre_id: UUID
    sobre_nome: str
    titulo: str
    detalhe: str | None
    lido_em: datetime | None
    # Quem deu ciência. Nulo quando ninguém deu, ou quando o tipo não tem leitura —
    # avaliação de cliente não é dirigida à pessoa, é sobre ela.
    lido_por: str | None = None
    # As mesmas informacoes de `detalhe`, mas separadas pelo rotulo que tinham no
    # formulario. `detalhe` fica para busca e exportacao, onde uma linha so serve.
    partes: list[ParteDoHistorico] = field(default_factory=list)


class TeamHistoryQuery(TenantScopedRepository[FeedbackRequest]):
    """Histórico dos três tipos de feedback, restrito ao escopo de equipe.

    O escopo chega pronto do `TeamScopeService` — esta query nunca o amplia. É o
    cenário "parâmetro não amplia escopo" de PAR-05 do lado da leitura: lista de ids
    vazia devolve vazio, e não "todo mundo".
    """

    model = FeedbackRequest

    async def livre(
        self,
        visiveis: set[UUID],
        *,
        incluir_sensiveis: bool = False,
        limite: int = LIMITE_TABELA,
    ) -> list[ItemDeHistorico]:
        """Feedback livre recebido por quem está no escopo.

        `incluir_sensiveis` é falso por padrão porque o sensível não chega ao
        destinatário — é invariante do aggregate, e vale igual aqui: sem isso, a pessoa
        leria no histórico o que a rota de recebidos esconde dela.
        """
        if not visiveis:
            return []
        leitor = aliased(Profile)
        stmt = (
            select(
                FreeFeedback.id,
                FreeFeedback.created_at,
                Profile.id,
                Profile.full_name,
                FreeFeedback.is_anonymous,
                FreeFeedback.positives,
                FreeFeedback.improvements,
                FreeFeedback.message,
                FreeFeedback.read_at,
                leitor.full_name,
            )
            .select_from(FreeFeedback)
            .join(Profile, Profile.id == FreeFeedback.receiver_id)
            .outerjoin(leitor, leitor.id == FreeFeedback.read_by)
            .where(
                FreeFeedback.tenant_id == self.tenant_id,
                FreeFeedback.receiver_id.in_(visiveis),
            )
            .order_by(FreeFeedback.created_at.desc())
            .limit(limite)
        )
        if not incluir_sensiveis:
            stmt = stmt.where(FreeFeedback.is_sensitive.is_(False))
        linhas = (await self._session.execute(stmt)).all()
        return [
            ItemDeHistorico(
                tipo="livre",
                item_id=item_id,
                quando=quando,
                sobre_id=pid,
                sobre_nome=nome,
                titulo="Feedback livre" + (" (anônimo)" if anonimo else ""),
                detalhe=_juntar(positivos, melhorias, mensagem),
                partes=_rotuladas(
                    ("Pontos positivos", positivos),
                    ("Pontos de melhoria", melhorias),
                    ("Mensagem", mensagem),
                ),
                lido_em=lido,
                lido_por=leitor_nome,
            )
            for (
                item_id,
                quando,
                pid,
                nome,
                anonimo,
                positivos,
                melhorias,
                mensagem,
                lido,
                leitor_nome,
            ) in linhas
        ]

    async def clientes(
        self, visiveis: set[UUID], *, limite: int = LIMITE_TABELA
    ) -> list[ItemDeHistorico]:
        if not visiveis:
            return []
        stmt = (
            select(
                ClientEvaluation.id,
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
                item_id=item_id,
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
            for item_id, quando, pid, nome, cliente, nota, negativa in linhas
        ]

    async def ciclos(
        self, visiveis: set[UUID], *, limite: int = LIMITE_TABELA
    ) -> list[ItemDeHistorico]:
        if not visiveis:
            return []
        leitor = aliased(Profile)
        stmt = (
            select(
                FeedbackRequest.id,
                FeedbackRequest.submitted_at,
                Profile.id,
                Profile.full_name,
                FeedbackCycle.name,
                FeedbackRequest.read_at,
                leitor.full_name,
            )
            .select_from(FeedbackRequest)
            .join(Profile, Profile.id == FeedbackRequest.receiver_id)
            .outerjoin(leitor, leitor.id == FeedbackRequest.read_by)
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
                item_id=item_id,
                quando=quando,
                sobre_id=pid,
                sobre_nome=nome,
                titulo=f"Feedback 360 — {ciclo}",
                # Sem o autor, de propósito: quem avaliou não aparece no histórico.
                detalhe=None,
                lido_em=lido,
                lido_por=leitor_nome,
            )
            for item_id, quando, pid, nome, ciclo, lido, leitor_nome in linhas
        ]


def _juntar(*partes: str | None) -> str | None:
    """Junta o que existe, devolve `None` quando não sobra nada."""
    texto = " · ".join(parte.strip() for parte in partes if parte and parte.strip())
    return texto or None


def _rotuladas(*pares: tuple[str, str | None]) -> list[ParteDoHistorico]:
    """As partes com o rótulo que cada uma tem no formulário.

    Concatenar elogio e crítica numa frase só apaga a distinção que o formulário faz
    questão de manter: "explica bem" e "atropela quem fala mais baixo" viram a mesma
    linha, e quem lê o histórico perde justamente o que o feedback separou.
    """
    return [
        ParteDoHistorico(rotulo=rotulo, texto=texto.strip())
        for rotulo, texto in pares
        if texto and texto.strip()
    ]


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
