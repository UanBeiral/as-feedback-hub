"""Contexto reporting: export_jobs

Única tabela do contexto — o resto é leitura. Ela existe para o worker ter o que
processar quando alguém pede um PDF ou XLSX (AD-07). No legado esses arquivos eram
montados no browser com jspdf/xlsx, e um relatório grande travava a aba de quem pediu.

`filters jsonb` guarda o filtro que estava na tela, não o resultado: é o que permite
reprocessar um job que falhou sem pedir ao usuário que remonte tudo, e é o que faz o
arquivo refletir o banco no momento em que foi gerado.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("file_path", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        # Envio por email é passo separado e pode falhar sozinho sem invalidar o
        # arquivo (BR-MIGRAR-030) — por isso o erro dele tem coluna própria.
        sa.Column("email_to", sa.Text()),
        sa.Column("email_sent_at", sa.DateTime(timezone=True)),
        sa.Column("email_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("kind IN ('report_360','client','engagement','executive')",
                           name="tipo_valido"),
        sa.CheckConstraint("format IN ('csv','xlsx','pdf')", name="formato_valido"),
        sa.CheckConstraint("status IN ('pending','processing','done','failed')",
                           name="status_valido"),
        # `done` sem arquivo é um job que mentiu que terminou.
        sa.CheckConstraint("status <> 'done' OR file_path IS NOT NULL",
                           name="concluido_tem_arquivo"),
    )
    op.create_index("ix_export_jobs_tenant_id", "export_jobs", ["tenant_id"])
    op.create_index("ix_export_jobs_tenant_status", "export_jobs", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_table("export_jobs")
