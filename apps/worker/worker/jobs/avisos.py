"""Handlers que transformam eventos de domínio em avisos (BR-MIGRAR-023/024/025).

Cada handler roda dentro da transação do despachante, junto com a marcação da mensagem
— é isso que dá a exatamente-uma-vez: se o processo morrer no meio, notificação e
marcação caem juntas e a mensagem volta intacta para a fila.

Duas decisões que valem explicação, porque não vieram prontas da spec:

- **Quem recebe cada aviso.** O legado registrou os *tipos* de notificação
  (`cycle_opened`, `client_feedback_received`, `client_feedback_negative`…) mas não a
  lista de destinatários de cada um. As escolhas abaixo estão comentadas uma a uma, e
  todas seguem o mesmo princípio: avisa quem precisa **fazer** alguma coisa com a
  informação. Aviso que não pede ação nenhuma vira ruído, e sino com ruído é sino que
  ninguém abre.
- **Um evento pode virar N notificações.** A abertura de ciclo avisa todos os
  avaliadores. Como tudo acontece na mesma transação, ou as N entram, ou nenhuma entra
  e a mensagem é reprocessada — não existe "avisou metade".
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.client_eval.repository import ClientEvaluationRepository
from app.contexts.engagement.models import Notification, OutboxMessage
from app.contexts.feedback.repository import CycleRepository, RequestRepository
from app.contexts.identity.repository import ProfileRepository
from app.core.tenancy import TenantContext

logger = logging.getLogger(__name__)


class PayloadDeAvisoInvalidoError(ValueError):
    """Mensagem sem o que o handler precisa para saber a quem avisar."""


def _contexto(mensagem: OutboxMessage) -> TenantContext:
    """O worker atravessa tenants; cada mensagem carrega o seu, e é ele que vale."""
    return TenantContext(
        tenant_id=mensagem.tenant_id,
        user_id=mensagem.tenant_id,
        role="system",
        flags=frozenset(),
    )


def _uuid(mensagem: OutboxMessage, campo: str) -> UUID:
    try:
        return UUID(str(mensagem.payload[campo]))
    except (KeyError, ValueError, TypeError) as exc:
        raise PayloadDeAvisoInvalidoError(f"payload sem `{campo}` válido") from exc


def _notificar(
    session: AsyncSession,
    mensagem: OutboxMessage,
    *,
    destinatarios: list[UUID],
    tipo: str,
    titulo: str,
    texto: str | None = None,
    link: str | None = None,
) -> int:
    """Cria uma notificação por destinatário. Devolve quantas foram criadas."""
    unicos = list(dict.fromkeys(destinatarios))
    for destinatario in unicos:
        session.add(
            Notification(
                tenant_id=mensagem.tenant_id,
                user_id=destinatario,
                type=tipo,
                title=titulo,
                message=texto,
                link=link,
            )
        )
    return len(unicos)


def registra_avisos(registro: object) -> None:
    """Registra os handlers de aviso no registro de tópicos do despachante."""
    registrar = registro.registra  # type: ignore[attr-defined]

    @registrar("cycle.opened")
    async def ciclo_aberto(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa quem tem feedback para dar (`cycle_opened` no legado).

        Só os avaliadores com pedido em aberto: quem foi só avaliado não tem nada a
        fazer com este aviso, e receberia uma notificação sem ação possível.
        """
        cycle_id = _uuid(mensagem, "cycle_id")
        contexto = _contexto(mensagem)

        ciclo = await CycleRepository(session, contexto).get(cycle_id)
        if ciclo is None:
            raise PayloadDeAvisoInvalidoError(f"ciclo {cycle_id} não existe neste tenant")

        destinatarios = await RequestRepository(session, contexto).ids_de_avaliadores_do_ciclo(
            cycle_id
        )
        criadas = _notificar(
            session,
            mensagem,
            destinatarios=destinatarios,
            tipo="cycle_opened",
            titulo=f"Ciclo aberto: {ciclo.name}",
            texto=(
                "Você tem feedbacks para responder neste ciclo."
                + (f" O prazo é {ciclo.end_date:%d/%m/%Y}." if ciclo.end_date else "")
            ),
            link="/meus-feedbacks",
        )
        logger.info("avisos: ciclo %s aberto, %s pessoa(s) avisada(s)", ciclo.name, criadas)

    @registrar("cycle.closed")
    async def ciclo_fechado(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa a administração de que a coleta terminou.

        Não avisa o time inteiro: para quem respondeu (ou não), o ciclo fechar não pede
        ação nenhuma. Quem precisa agir é admin/RH, que decide publicar os resultados.
        """
        cycle_id = _uuid(mensagem, "cycle_id")
        contexto = _contexto(mensagem)

        ciclo = await CycleRepository(session, contexto).get(cycle_id)
        if ciclo is None:
            raise PayloadDeAvisoInvalidoError(f"ciclo {cycle_id} não existe neste tenant")

        gestao = await ProfileRepository(session, contexto).list_ids_por_papel("admin", "rh")
        automatico = bool(mensagem.payload.get("automatico"))
        _notificar(
            session,
            mensagem,
            destinatarios=gestao,
            tipo="cycle_closed",
            titulo=f"Ciclo fechado: {ciclo.name}",
            texto=(
                "Fechado automaticamente após a carência."
                if automatico
                else "Fechado manualmente."
            )
            + " Os resultados podem ser publicados.",
            link="/admin/ciclos",
        )

    @registrar("cycle.published")
    async def ciclo_publicado(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa todo mundo que participou — dos dois lados.

        Publicar é o momento em que o resultado fica visível, e isso interessa tanto a
        quem avaliou quanto a quem foi avaliado.
        """
        cycle_id = _uuid(mensagem, "cycle_id")
        contexto = _contexto(mensagem)

        ciclo = await CycleRepository(session, contexto).get(cycle_id)
        if ciclo is None:
            raise PayloadDeAvisoInvalidoError(f"ciclo {cycle_id} não existe neste tenant")

        participantes = await RequestRepository(
            session, contexto
        ).ids_de_participantes_do_ciclo(cycle_id)
        _notificar(
            session,
            mensagem,
            destinatarios=participantes,
            tipo="cycle_published",
            titulo=f"Resultados disponíveis: {ciclo.name}",
            texto="Os feedbacks deste ciclo já podem ser consultados.",
            link="/meus-feedbacks",
        )

    @registrar("request.submitted")
    async def feedback_enviado(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa quem **recebeu** o feedback, nunca revelando quem escreveu.

        O `user_id` do payload é o avaliado, e é de propósito: mandar o nome do
        avaliador junto transformaria o aviso em quebra do anonimato relativo que o
        360 pressupõe.
        """
        destinatario = _uuid(mensagem, "user_id")
        _notificar(
            session,
            mensagem,
            destinatarios=[destinatario],
            tipo="feedback_received",
            titulo="Você recebeu um feedback",
            texto="Um feedback sobre você foi enviado neste ciclo.",
            link="/meus-feedbacks",
        )

    @registrar("client_eval.submitted")
    async def avaliacao_de_cliente(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa o avaliado de que um cliente respondeu (`client_feedback_received`)."""
        avaliado = _uuid(mensagem, "user_id")
        _notificar(
            session,
            mensagem,
            destinatarios=[avaliado],
            tipo="client_feedback_received",
            titulo="Um cliente avaliou seu atendimento",
            link="/avaliacoes-clientes",
        )

    @registrar("client_eval.flagged_negative")
    async def avaliacao_negativa(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avaliação negativa: avisa o avaliado **e** a gestão (BR-MIGRAR-021).

        É o único aviso que sobe na hierarquia. O motivo é o propósito da sinalização:
        alguém precisa poder ligar para esse cliente hoje, e depender de o avaliado
        reportar o próprio problema é o jeito mais provável de isso não acontecer.
        """
        evaluation_id = _uuid(mensagem, "evaluation_id")
        avaliado = _uuid(mensagem, "user_id")
        contexto = _contexto(mensagem)

        avaliacao = await ClientEvaluationRepository(session, contexto).get(evaluation_id)
        cliente = (avaliacao.client_name if avaliacao else None) or "Um cliente"

        gestao = await ProfileRepository(session, contexto).list_ids_por_papel("admin", "rh")
        criadas = _notificar(
            session,
            mensagem,
            destinatarios=[avaliado, *gestao],
            tipo="client_feedback_negative",
            titulo="Avaliação de cliente sinalizada",
            texto=f"{cliente} deixou uma avaliação que precisa de atenção.",
            link="/avaliacoes-clientes",
        )
        logger.warning(
            "avisos: avaliação %s sinalizada como negativa, %s aviso(s) enviado(s)",
            evaluation_id,
            criadas,
        )
