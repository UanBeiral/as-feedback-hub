"""Agenda dos jobs — o que era `pg_cron` no legado, agora versionado (AD-05).

Importar este módulo registra os jobs no scheduler global. É o único lugar do sistema
onde se lê "o que roda sozinho, e de quanto em quanto tempo" — no legado essa resposta
só existia dentro do banco de produção, criada pelo SQL Editor, e é por isso que o
inventário virou uma pendência do cutover (AMB-008).

Os intervalos são folgados de propósito: nada aqui é sensível a minutos. Fechar um
ciclo uma hora depois da carência não muda nada para ninguém; rodar de minuto em minuto
só geraria carga e log.
"""

from __future__ import annotations

from datetime import timedelta

from app.core.db import get_session_factory
from worker.jobs.cycles import (
    expirar_requests_vencidos,
    expirar_tokens_publicos,
    fechar_ciclos_vencidos,
    listar_tenants_ativos,
)
from worker.scheduler import scheduler


@scheduler.registra("fechar-ciclos-vencidos", timedelta(hours=1))
async def _fechar_ciclos() -> None:
    """Fechamento automático com carência de 3 dias (BR-MIGRAR-005)."""
    async with get_session_factory()() as session:
        await fechar_ciclos_vencidos(session)


@scheduler.registra("expirar-requests-vencidos", timedelta(hours=6))
async def _expirar_requests() -> None:
    """Expiração de pendências além do prazo + carência (BR-MIGRAR-003/007)."""
    async with get_session_factory()() as session:
        await expirar_requests_vencidos(session, await listar_tenants_ativos(session))


@scheduler.registra("expirar-tokens-publicos", timedelta(hours=1))
async def _expirar_tokens() -> None:
    """Links de avaliação de cliente vencidos (PAR-06 § expiração de tokens).

    De hora em hora, e não uma vez por dia: um link expirado que ainda abre o formulário
    é o cliente respondendo algo que ninguém vai considerar válido.
    """
    async with get_session_factory()() as session:
        await expirar_tokens_publicos(session)
