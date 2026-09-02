"""Jobs agendados do ciclo de feedback (AD-05 / BR-MIGRAR-005/007).

Substituem o `auto-cycle-manager` que rodava por `pg_cron` no legado — agendamento que
existia só dentro do banco, sem versionamento e sem ninguém saber o que fazia
(BR-DESCARTAR-003; o inventário do que roda hoje lá é AMB-008, ainda aberto).

Dois jobs, com propósitos diferentes que é fácil confundir:

- **fechar_ciclos_vencidos**: fecha o *ciclo* quando o prazo venceu há mais que a
  carência de 3 dias. É a decisão administrativa de encerrar a coleta.
- **expirar_requests_vencidos**: marca como `expired` os *requests* que passaram do
  prazo + carência. É o que tira a pendência da lista de quem nunca respondeu.

O ciclo pode fechar com requests ainda abertos; eles expiram por conta própria. Foi
assim no legado e é o comportamento que a paridade cobra.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.client_eval.repository import ExpiredTokenRepository
from app.contexts.engagement.repository import OutboxRepository
from app.contexts.engagement.service import OutboxService
from app.contexts.feedback.repository import CycleDueRepository, RequestRepository
from app.contexts.identity.models import Tenant
from app.core.tenancy import TenantContext

logger = logging.getLogger(__name__)


async def fechar_ciclos_vencidos(session: AsyncSession, hoje: date | None = None) -> list[str]:
    """Fecha os ciclos cuja carência acabou. Devolve os nomes fechados.

    Idempotente por construção (PAR-06 § "Job re-executado não repete efeitos"): o
    filtro só enxerga `status='open'`, então um ciclo já fechado não é candidato de
    novo. E o evento de outbox usa `cycle.closed:{id}` como chave de idempotência —
    ainda que o job rodasse duas vezes no mesmo ciclo, a notificação sairia uma vez só.
    """
    hoje = hoje or datetime.now(UTC).date()
    vencidos = await CycleDueRepository(session).vencidos(hoje)
    if not vencidos:
        return []

    fechados: list[str] = []
    for cycle in vencidos:
        # O worker atravessa tenants; cada ciclo carrega o seu, e é ele que vale para
        # a mensagem de outbox — nada aqui roda "sem tenant".
        contexto = TenantContext(
            tenant_id=cycle.tenant_id,
            user_id=cycle.tenant_id,  # ator do sistema; não há usuário nesta operação
            role="system",
            flags=frozenset(),
        )
        outbox = OutboxService(OutboxRepository(session, contexto))

        cycle.status = "closed"
        cycle.closed_at = datetime.now(UTC)
        await outbox.enqueue(
            topic="cycle.closed",
            payload={"cycle_id": str(cycle.id), "automatico": True},
            idempotency_key=f"cycle.closed:{cycle.id}",
        )
        fechados.append(cycle.name)
        logger.info(
            "scheduler: ciclo %s (%s) fechado automaticamente após a carência",
            cycle.name,
            cycle.id,
        )

    await session.commit()
    return fechados


async def expirar_requests_vencidos(
    session: AsyncSession, tenant_ids: list[UUID], hoje: date | None = None
) -> int:
    """Expira requests em aberto além do prazo + carência (BR-MIGRAR-003/007).

    Recebe os tenants explicitamente porque o `RequestRepository` é escopado, e é assim
    que o job atravessa tenants **sem furar o isolamento**: um escopo por vez, nunca uma
    query global sobre a tabela. Custa uma consulta por tenant; com um escritório por
    instalação, é troco.
    """
    hoje = hoje or datetime.now(UTC).date()
    total = 0
    for tenant_id in tenant_ids:
        contexto = TenantContext(
            tenant_id=tenant_id, user_id=tenant_id, role="system", flags=frozenset()
        )
        expirados = await RequestRepository(session, contexto).expirar_vencidos(hoje)
        if expirados:
            logger.info("scheduler: %s requests expirados no tenant %s", expirados, tenant_id)
        total += expirados

    await session.commit()
    return total


async def expirar_tokens_publicos(session: AsyncSession, agora: datetime | None = None) -> int:
    """Expira avaliações de cliente cujo link venceu sem resposta (PAR-06).

    Um UPDATE só, atravessando tenants: o job não precisa dos objetos, precisa do
    efeito. Idempotente porque o filtro exclui o que já saiu de `pending`/`in_progress`
    — rodar duas vezes no mesmo minuto muda zero linhas na segunda.
    """
    expiradas = await ExpiredTokenRepository(session).expirar(agora)
    if expiradas:
        logger.info("scheduler: %s avaliações de cliente expiradas", expiradas)
    await session.commit()
    return expiradas


async def listar_tenants_ativos(session: AsyncSession) -> list[UUID]:
    """Tenants que o job precisa percorrer. Inativo não recebe processamento."""
    resultado = await session.execute(
        select(Tenant.id).where(Tenant.status == "active").order_by(Tenant.slug)
    )
    return list(resultado.scalars().all())
