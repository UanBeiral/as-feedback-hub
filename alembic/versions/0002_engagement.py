"""Contexto engagement: notificações, outbox, auditoria, settings, comunicados, contatos

O centro desta migration é `outbox_messages`. Ela é o que substitui as Edge Functions
com `waitUntil` do legado (BR-DESCARTAR-002): a intenção de comunicar passa a ser uma
linha gravada na mesma transação do comando de origem, e o despacho vira trabalho do
worker, com retry e DLQ (AMB-006).

Duas restrições merecem destaque:
- `UNIQUE (topic, idempotency_key)` implementa BR-MIGRAR-024 no banco, não na aplicação.
- `tenant_settings.updated_by NOT NULL` sana a dívida 🟡 do legado: configuração global
  muda o comportamento de todo o escritório e precisa de dono.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        # FK física: era uuid solto apontando para auth.users no legado.
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False, server_default="general"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("link", sa.Text()),
        # Não lida é read_at IS NULL — sem coluna booleana (BR-MIGRAR-023).
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])
    op.create_index("ix_notifications_destinatario", "notifications",
                    ["tenant_id", "user_id", "read_at"])

    op.create_table(
        "outbox_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("topic", "idempotency_key",
                            name="uq_outbox_messages_idempotencia"),
        sa.CheckConstraint("status IN ('pending','dispatched','failed','dead')",
                           name="status_valido"),
        sa.CheckConstraint("attempts >= 0", name="attempts_nao_negativo"),
    )
    op.create_index("ix_outbox_messages_tenant_id", "outbox_messages", ["tenant_id"])
    op.create_index("ix_outbox_pendentes", "outbox_messages", ["status", "next_attempt_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        # actor_id, nunca user_id (BR-MIGRAR-026). Nulável: o ator pode ter sido
        # removido depois, e perder a linha por isso anularia o propósito da trilha.
        sa.Column("actor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text()),
        sa.Column("record_id", postgresql.UUID(as_uuid=True)),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_tenant_tempo", "audit_logs", ["tenant_id", "created_at"])

    op.create_table(
        "tenant_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_chave"),
    )
    op.create_index("ix_tenant_settings_tenant_id", "tenant_settings", ["tenant_id"])

    op.create_table(
        "platform_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        sa.Column("notified_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draft", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_platform_updates_tenant_id", "platform_updates", ["tenant_id"])
    op.create_index("ix_platform_updates_tenant_draft", "platform_updates",
                    ["tenant_id", "draft"])

    op.create_table(
        "contact_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("company", sa.Text()),
        sa.Column("contact_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text()),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="novo"),
        # FK física: era uuid solto no legado.
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('novo','em_andamento','resolvido')",
                           name="status_valido"),
    )
    op.create_index("ix_contact_messages_tenant_id", "contact_messages", ["tenant_id"])
    op.create_index("ix_contact_messages_tenant_status", "contact_messages",
                    ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_table("contact_messages")
    op.drop_table("platform_updates")
    op.drop_table("tenant_settings")
    op.drop_table("audit_logs")
    op.drop_table("outbox_messages")
    op.drop_table("notifications")
