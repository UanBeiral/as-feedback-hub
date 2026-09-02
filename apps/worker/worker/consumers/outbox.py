"""Despachante do transactional outbox (AD-04 / AMB-006).

O ciclo de um lote:

1. `claim_batch` reserva mensagens prontas com `FOR UPDATE SKIP LOCKED` — outros
   workers pegam outras, ninguém espera na fila.
2. Cada handler roda dentro de um **savepoint**. Se ele falhar, só o que ele escreveu
   é desfeito; a mensagem continua na transação para ser marcada como `failed`. Sem o
   savepoint, um erro de banco dentro do handler aborta a transação inteira e o worker
   perderia até o registro de que tentou.
3. Sucesso e marcação commitam juntos. É daí que vem a exatamente-uma-vez de PAR-07:
   morrer entre criar a notificação e marcar a mensagem desfaz as duas coisas, e o
   próximo lote reprocessa a mensagem intacta.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.engagement.repository import OutboxDispatchRepository
from app.contexts.engagement.service import OutboxService
from worker.handlers import RegistroDeHandlers, TopicoSemHandlerError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoDoLote:
    reivindicadas: int = 0
    despachadas: int = 0
    falhadas: int = 0
    mortas: int = 0

    @property
    def houve_trabalho(self) -> bool:
        return self.reivindicadas > 0


async def despachar_lote(
    session: AsyncSession, registro: RegistroDeHandlers, *, limite: int = 20
) -> ResultadoDoLote:
    """Processa um lote e commita. Devolve o que aconteceu, para o log e as métricas."""
    mensagens = await OutboxDispatchRepository(session).claim_batch(limit=limite)
    if not mensagens:
        return ResultadoDoLote()

    despachadas = falhadas = mortas = 0

    for mensagem in mensagens:
        try:
            handler = registro.resolve(mensagem.topic)
        except TopicoSemHandlerError as exc:
            OutboxService.mark_failed(mensagem, str(exc))
            logger.warning("outbox: %s (id=%s)", exc, mensagem.id)
            falhadas += 1
            if mensagem.status == "dead":
                mortas += 1
            continue

        try:
            async with session.begin_nested():
                await handler(session, mensagem)
        except Exception as exc:  # noqa: BLE001 — a falha é dado, não interrupção
            OutboxService.mark_failed(mensagem, repr(exc))
            falhadas += 1
            if mensagem.status == "dead":
                mortas += 1
                logger.error(
                    "outbox: mensagem %s foi para a DLQ após %s tentativas: %r",
                    mensagem.id,
                    mensagem.attempts,
                    exc,
                )
            else:
                logger.warning(
                    "outbox: tentativa %s de %s falhou, reagendada para %s: %r",
                    mensagem.attempts,
                    mensagem.id,
                    mensagem.next_attempt_at,
                    exc,
                )
        else:
            OutboxService.mark_dispatched(mensagem)
            despachadas += 1

    await session.commit()
    return ResultadoDoLote(
        reivindicadas=len(mensagens),
        despachadas=despachadas,
        falhadas=falhadas,
        mortas=mortas,
    )
