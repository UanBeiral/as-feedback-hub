"""Repositórios do contexto `client_eval`.

`PublicEvaluationRepository` é a quarta — e última prevista — exceção ao isolamento por
herança. O motivo é diferente das outras três e vale a leitura: aqui não existe sessão
de usuário porque **quem chama é o cliente do escritório, pela internet aberta**. O
token faz as vezes de credencial e de resolvedor de tenant ao mesmo tempo: a linha
encontrada por ele carrega o `tenant_id`, e é a partir dali que tudo passa a ser
escopado. Nenhum método daqui aceita filtro que não seja o token.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.client_eval.models import (
    ClientEvalAnswer,
    ClientEvalForm,
    ClientEvalFormQuestion,
    ClientEvaluation,
    ClientEvaluationTag,
    ServiceTag,
)
from app.core.tenancy import TenantScopedRepository

# Estados em que a avaliação ainda aceita resposta. `in_progress` entra junto com
# `pending` porque abrir o link não pode fechar a porta: o DDL da spec cita só
# `pending`, mas a máquina de estados dela mesma passa por `in_progress` antes do envio.
STATUS_RESPONDIVEIS = ("pending", "in_progress")


class ClientFormRepository(TenantScopedRepository[ClientEvalForm]):
    model = ClientEvalForm

    async def list_active(self) -> list[ClientEvalForm]:
        stmt = self._scoped().where(ClientEvalForm.is_active.is_(True)).order_by(
            ClientEvalForm.name
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_default(self) -> ClientEvalForm | None:
        """Formulário do fluxo espontâneo (o cliente que avalia sem ter sido convidado)."""
        stmt = self._scoped().where(
            ClientEvalForm.is_default.is_(True), ClientEvalForm.is_active.is_(True)
        )
        return (await self._session.execute(stmt)).scalars().first()


class ClientQuestionRepository(TenantScopedRepository[ClientEvalFormQuestion]):
    model = ClientEvalFormQuestion

    async def list_by_form(self, form_id: UUID) -> list[ClientEvalFormQuestion]:
        stmt = (
            self._scoped()
            .where(ClientEvalFormQuestion.form_id == form_id)
            .order_by(ClientEvalFormQuestion.display_order, ClientEvalFormQuestion.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class ClientEvaluationRepository(TenantScopedRepository[ClientEvaluation]):
    model = ClientEvaluation

    async def list_do_avaliado(
        self, target_user_id: UUID, *, limit: int = 100
    ) -> list[ClientEvaluation]:
        stmt = (
            self._scoped()
            .where(ClientEvaluation.target_user_id == target_user_id)
            .order_by(ClientEvaluation.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_por_status(self, *status: str, limit: int = 200) -> list[ClientEvaluation]:
        stmt = self._scoped().order_by(ClientEvaluation.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(ClientEvaluation.status.in_(status))
        return list((await self._session.execute(stmt)).scalars().all())

    async def contar_negativas(self) -> int:
        stmt = (
            select(func.count())
            .select_from(ClientEvaluation)
            .where(
                ClientEvaluation.tenant_id == self.tenant_id,
                ClientEvaluation.has_negative.is_(True),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())


class ClientAnswerRepository(TenantScopedRepository[ClientEvalAnswer]):
    model = ClientEvalAnswer

    async def list_da_avaliacao(self, evaluation_id: UUID) -> list[ClientEvalAnswer]:
        stmt = self._scoped().where(ClientEvalAnswer.evaluation_id == evaluation_id)
        return list((await self._session.execute(stmt)).scalars().all())


class ServiceTagRepository(TenantScopedRepository[ServiceTag]):
    model = ServiceTag

    async def list_active(self) -> list[ServiceTag]:
        stmt = (
            self._scoped()
            .where(ServiceTag.is_active.is_(True))
            .order_by(ServiceTag.display_order, ServiceTag.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class ClientEvaluationTagRepository(TenantScopedRepository[ClientEvaluationTag]):
    model = ClientEvaluationTag

    async def list_da_avaliacao(self, evaluation_id: UUID) -> list[ClientEvaluationTag]:
        stmt = self._scoped().where(ClientEvaluationTag.evaluation_id == evaluation_id)
        return list((await self._session.execute(stmt)).scalars().all())


class PublicEvaluationRepository:
    """Acesso pelo token — sem sessão, sem tenant no contexto (ver docstring do módulo)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_por_token(self, token: str) -> ClientEvaluation | None:
        """Busca só pelo token. Sem filtro adicional: não há tenant ainda."""
        stmt = select(ClientEvaluation).where(ClientEvaluation.token == token)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def marcar_em_andamento(self, token: str) -> int:
        """Registra que o cliente abriu o link, sem fechar nenhuma porta.

        Condicionado a `pending` para não sobrescrever nada: reabrir uma avaliação já em
        andamento não muda estado, e reabrir uma já enviada não a desfaz.
        """
        result = await self._session.execute(
            update(ClientEvaluation)
            .where(
                ClientEvaluation.token == token,
                ClientEvaluation.status == "pending",
                ClientEvaluation.token_expires_at > datetime.now(UTC),
            )
            .values(status="in_progress")
        )
        return int(result.rowcount or 0)

    async def reivindicar_para_submissao(self, token: str) -> ClientEvaluation | None:
        """Guard atômico de BR-MIGRAR-019.

        Um único UPDATE condicional casa token + estado respondível + validade e devolve
        a linha afetada. Duas submissões simultâneas com o mesmo token não competem em
        código: a segunda não encontra linha, porque a primeira já mudou o estado dentro
        da mesma instrução. Quem perde a corrida recebe a confirmação idempotente que o
        cenário `@idempotencia` de PAR-03 exige — não um erro.

        Fazer isso com "SELECT, verifica, UPDATE" abriria a janela entre a leitura e a
        escrita, que é exatamente onde o duplo clique do cliente entra.
        """
        stmt = (
            update(ClientEvaluation)
            .where(
                ClientEvaluation.token == token,
                ClientEvaluation.status.in_(STATUS_RESPONDIVEIS),
                ClientEvaluation.token_expires_at > datetime.now(UTC),
            )
            .values(status="submitted", submitted_at=datetime.now(UTC))
            .returning(ClientEvaluation)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def perguntas_do_formulario(
        self, tenant_id: UUID, form_id: UUID
    ) -> list[ClientEvalFormQuestion]:
        """Perguntas na ordem persistida (BR-MIGRAR-020), já escopadas pelo tenant da linha."""
        stmt = (
            select(ClientEvalFormQuestion)
            .where(
                ClientEvalFormQuestion.tenant_id == tenant_id,
                ClientEvalFormQuestion.form_id == form_id,
            )
            .order_by(ClientEvalFormQuestion.display_order, ClientEvalFormQuestion.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    def adicionar(self, avaliacao: ClientEvaluation) -> ClientEvaluation:
        """Usado só pelo fluxo espontâneo: o `tenant_id` vem preenchido pelo service,
        porque aqui não há contexto de sessão para carimbá-lo."""
        self._session.add(avaliacao)
        return avaliacao

    async def flush(self) -> None:
        await self._session.flush()

    def registrar_resposta(
        self,
        *,
        tenant_id: UUID,
        evaluation_id: UUID,
        question_id: UUID,
        rating_value: int | None,
        text_value: str | None,
    ) -> None:
        self._session.add(
            ClientEvalAnswer(
                tenant_id=tenant_id,
                evaluation_id=evaluation_id,
                question_id=question_id,
                rating_value=rating_value,
                text_value=text_value,
            )
        )


class ExpiredTokenRepository:
    """Lado do scheduler: tokens vencidos de todos os tenants (PAR-06)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def expirar(self, agora: datetime | None = None) -> int:
        """Marca como `expired` o que venceu sem resposta.

        Um UPDATE só, sem carregar linha: o job não precisa dos objetos, precisa do
        efeito. Idempotente porque o filtro exclui o que já saiu de `pending`/
        `in_progress`.
        """
        result = await self._session.execute(
            update(ClientEvaluation)
            .where(
                ClientEvaluation.status.in_(STATUS_RESPONDIVEIS),
                ClientEvaluation.token_expires_at.is_not(None),
                ClientEvaluation.token_expires_at <= (agora or datetime.now(UTC)),
            )
            .values(status="expired")
        )
        return int(result.rowcount or 0)
