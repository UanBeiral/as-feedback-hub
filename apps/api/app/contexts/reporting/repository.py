"""Escrita do contexto `reporting`: só o pedido de exportação.

O resto do contexto é leitura pura (`queries.py`). Esta é a única tabela que ele
possui, e ela existe para o worker ter o que processar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.reporting.models import ExportJob
from app.core.tenancy import TenantScopedRepository


class ExportJobRepository(TenantScopedRepository[ExportJob]):
    model = ExportJob

    async def list_do_usuario(self, requested_by: UUID, *, limit: int = 20) -> list[ExportJob]:
        stmt = (
            self._scoped()
            .where(ExportJob.requested_by == requested_by)
            .order_by(ExportJob.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class ExportJobDispatchRepository:
    """Lado do worker: busca o job pelo id que veio na mensagem de outbox.

    Sem contexto de tenant pelo mesmo motivo do despachante: o worker atravessa
    tenants. O `tenant_id` do job encontrado é que passa a valer daí em diante.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: UUID) -> ExportJob | None:
        return (
            await self._session.execute(select(ExportJob).where(ExportJob.id == job_id))
        ).scalar_one_or_none()

    @staticmethod
    def marcar_pronto(job: ExportJob, caminho: str) -> None:
        job.status = "done"
        job.file_path = caminho
        job.error = None
        job.completed_at = datetime.now(UTC)

    @staticmethod
    def marcar_falho(job: ExportJob, erro: str) -> None:
        """Falha de geração é do job, não do sistema: fica registrada e visível.

        O usuário que pediu precisa saber que o arquivo não sai — silêncio aqui vira
        "cliquei em exportar e nunca chegou".
        """
        job.status = "failed"
        job.error = erro[:1000]
        job.completed_at = datetime.now(UTC)
