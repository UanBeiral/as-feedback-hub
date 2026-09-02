"""Processo do worker: despacha o outbox e roda o scheduler.

Um processo, dois relógios. O despacho roda em rajada — enquanto houver mensagem, o
próximo lote vem sem espera; quando a fila esvazia, dorme `WORKER_POLL_SECONDS`. Assim
uma publicação para 40 pessoas sai em segundos, e uma fila vazia não castiga o banco com
polling apertado.

Encerramento é limpo: SIGTERM (o que o Docker manda no `stop`) marca a parada e o loop
termina o lote em curso antes de sair. Matar no meio de um lote também é seguro — a
transação cai inteira e as mensagens voltam para a fila —, mas sair no ponto certo evita
retrabalho e log de erro que ninguém precisa investigar.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_factory
from worker.consumers.outbox import despachar_lote
from worker.jobs.email import build_email_adapter
from worker.jobs.notifications import registra_handlers

# Import por efeito colateral: registra os jobs agendados no scheduler global.
from worker.jobs.schedule import scheduler

logger = logging.getLogger("worker")


async def executar(parar: asyncio.Event) -> None:
    settings = get_settings()
    registro = registra_handlers(build_email_adapter(settings))
    fabrica = get_session_factory()

    logger.info(
        "worker iniciado | tópicos=%s | jobs agendados=%s | intervalo=%ss",
        registro.topicos,
        scheduler.jobs or "nenhum (ver worker/scheduler/__init__.py)",
        settings.worker_poll_seconds,
    )

    while not parar.is_set():
        try:
            async with fabrica() as session:
                resultado = await despachar_lote(
                    session, registro, limite=settings.worker_batch_size
                )
        except Exception:
            # O loop não morre por causa de um lote: banco reiniciando, conexão caída,
            # bug em handler não coberto. Loga e tenta de novo no próximo intervalo.
            logger.exception("worker: lote falhou por inteiro")
            resultado = None
        else:
            if resultado.houve_trabalho:
                logger.info(
                    "outbox: %s reivindicadas, %s despachadas, %s falhas, %s na DLQ",
                    resultado.reivindicadas,
                    resultado.despachadas,
                    resultado.falhadas,
                    resultado.mortas,
                )

        await scheduler.tick()

        # Fila com trabalho: emenda o próximo lote. Fila vazia: dorme, mas acorda na
        # hora se o sinal de parada chegar antes.
        if resultado is not None and resultado.houve_trabalho:
            continue
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(parar.wait(), timeout=settings.worker_poll_seconds)

    logger.info("worker encerrado")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    parar = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sinal in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows não tem SIGTERM no loop
            loop.add_signal_handler(sinal, parar.set)

    try:
        await executar(parar)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
