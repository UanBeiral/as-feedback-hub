"""Handlers que transformam mensagem de outbox em notificação (BR-MIGRAR-023/024/026).

O que estes handlers escrevem no nosso banco é exatamente-uma-vez, porque roda na mesma
transação da marcação da mensagem. O email que sai junto é ao-menos-uma-vez — ver a
ressalva em `jobs/email.py`.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.engagement.models import Notification, OutboxMessage, PlatformUpdate
from app.contexts.identity.models import Profile, User
from worker.handlers import RegistroDeHandlers
from worker.jobs.avisos import registra_avisos
from worker.jobs.email import EmailAdapter

logger = logging.getLogger(__name__)


class PayloadInvalidoError(ValueError):
    """Mensagem sem os campos que o handler precisa.

    Não é retentável de verdade — vai falhar igual nas próximas tentativas e terminar
    na DLQ. É o comportamento certo mesmo assim: a mensagem fica visível com o motivo,
    em vez de ser descartada em silêncio por não parecer importante.
    """


def _uuid(mensagem: OutboxMessage, campo: str) -> UUID:
    try:
        return UUID(str(mensagem.payload[campo]))
    except (KeyError, ValueError) as exc:
        raise PayloadInvalidoError(f"payload sem `{campo}` válido") from exc


async def _email_do_perfil(session: AsyncSession, tenant_id: UUID, profile_id: UUID) -> str | None:
    """O email vive em `users`; o destinatário chega como perfil.

    `profiles.id = users.id` é invariante do banco (CHECK), então a junção é direta —
    mas fazemos pelo `user_id` explícito, que é o que continua verdadeiro se a
    invariante um dia mudar.
    """
    stmt = (
        select(User.email)
        .join(Profile, Profile.user_id == User.id)
        .where(
            Profile.id == profile_id,
            Profile.tenant_id == tenant_id,
            Profile.status == "active",
            User.status == "active",
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def registra_handlers(email: EmailAdapter) -> RegistroDeHandlers:
    """Constrói o registro com o adapter injetado.

    Os handlers precisam do adapter, e o registro é global por tópico: a fábrica existe
    para o adapter entrar por injeção em vez de virar import de módulo — é o que permite
    o teste rodar sem provedor nenhum.
    """
    registro_local = RegistroDeHandlers()
    # Eventos de ciclo e de avaliação de cliente viram aviso em `jobs/avisos.py`, que é
    # onde mora a decisão de quem recebe o quê.
    registra_avisos(registro_local)

    @registro_local.registra("platform_update.published")
    async def notificar_comunicado(session: AsyncSession, mensagem: OutboxMessage) -> None:
        update_id = _uuid(mensagem, "update_id")
        user_id = _uuid(mensagem, "user_id")

        comunicado = await session.get(PlatformUpdate, update_id)
        if comunicado is None or comunicado.tenant_id != mensagem.tenant_id:
            raise PayloadInvalidoError(f"comunicado {update_id} não existe neste tenant")

        session.add(
            Notification(
                tenant_id=mensagem.tenant_id,
                user_id=user_id,
                type="platform_update",
                title=comunicado.title,
                message=comunicado.content[:500],
                link="/atualizacoes",
            )
        )

        destinatario = await _email_do_perfil(session, mensagem.tenant_id, user_id)
        if destinatario is None:
            # Pessoa desligada entre a publicação e o despacho: a notificação no app
            # fica registrada, mas não há para onde mandar email. Não é erro.
            logger.info("outbox: %s sem email ativo, só notificação no app", user_id)
            return

        await email.send(
            to=destinatario,
            subject=f"Novidade: {comunicado.title}",
            body=comunicado.content,
        )

    @registro_local.registra("export.requested")
    async def gerar_exportacao(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Delegação: a geração vive em `jobs/exports.py`, que é onde está o assunto."""
        from worker.jobs.exports import processar_exportacao

        await processar_exportacao(session, mensagem, email)

    @registro_local.registra_prefixo("audit.")
    async def notificar_envolvido(session: AsyncSession, mensagem: OutboxMessage) -> None:
        """Avisa quem foi afetado por uma ação sensível (BR-MIGRAR-026).

        A trilha de auditoria já foi gravada na transação do comando — aqui só sai o
        aviso. Se este despacho falhar para sempre, a auditoria continua íntegra, que é
        a garantia que BR-MIGRAR-025 pede.
        """
        acao = mensagem.payload.get("action") or mensagem.topic.removeprefix("audit.")
        destinatario_id = _uuid(mensagem, "user_id")

        session.add(
            Notification(
                tenant_id=mensagem.tenant_id,
                user_id=destinatario_id,
                type="audit",
                title=f"Ação registrada: {acao}",
                message=None,
                link=None,
            )
        )

    return registro_local
