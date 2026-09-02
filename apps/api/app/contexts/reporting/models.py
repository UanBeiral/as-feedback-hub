"""Modelo do contexto `reporting`.

O contexto é de leitura — `target_architecture.md` registra que ele foge do quarteto
completo de propósito. A única coisa que ele **escreve** é o pedido de exportação
pesada: `export_jobs` é o registro de "alguém pediu um PDF", que o worker processa
depois e disponibiliza por link (AD-07).

Por que o pedido vira linha em vez de a API gerar o arquivo na hora: no legado, PDF e
XLSX eram montados no browser com jspdf/xlsx, e um relatório grande travava a aba de
quem pediu. Passar isso para o servidor síncrono só mudaria de lugar o travamento —
seria o worker de requisições HTTP preso montando planilha.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

EXPORT_KINDS = ("report_360", "client", "engagement", "executive")
EXPORT_FORMATS = ("csv", "xlsx", "pdf")
EXPORT_STATUSES = ("pending", "processing", "done", "failed")


class ExportJob(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Pedido de exportação assíncrona.

    `filters` guarda o filtro exato que o usuário estava vendo (BR-MIGRAR-029: "a
    exportação reflete exatamente os filtros ativos"). Guardar o filtro em vez do
    resultado é o que permite reprocessar um job que falhou sem pedir ao usuário que
    remonte a tela.
    """

    __tablename__ = "export_jobs"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    requested_by: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    file_path: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Email de destino quando o pedido inclui envio (BR-MIGRAR-030). A falha do envio
    # não invalida o arquivo: são dois passos, e só o segundo pode dar errado sozinho.
    email_to: Mapped[str | None] = mapped_column(Text)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('report_360','client','engagement','executive')", name="tipo_valido"
        ),
        CheckConstraint("format IN ('csv','xlsx','pdf')", name="formato_valido"),
        CheckConstraint(
            "status IN ('pending','processing','done','failed')", name="status_valido"
        ),
        # `done` sem arquivo é um job que mentiu que terminou.
        CheckConstraint(
            "status <> 'done' OR file_path IS NOT NULL", name="concluido_tem_arquivo"
        ),
        Index("ix_export_jobs_tenant_status", "tenant_id", "status"),
    )

    @property
    def pronto(self) -> bool:
        return self.status == "done" and self.file_path is not None
