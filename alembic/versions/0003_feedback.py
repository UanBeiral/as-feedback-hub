"""Contexto feedback: formulários, ciclos, permissões, requests, respostas, notas

Três diferenças em relação ao legado que valem registro:

- `feedback_requests` não tem `response_data jsonb`. O legado guardava as respostas em
  dois lugares (o jsonb e `feedback_answers`) e as duas cópias divergiram — reconciliar
  é trabalho do ETL (AMB-011). Aqui a fonte de verdade é uma só.
- `feedback_answers` ganha FKs físicas: `request_id` e `question_id` eram uuid solto.
- `status = 'reviewed'` não entra no CHECK do request (AMB-003): estado sem gatilho
  conhecido no legado.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _tenant_fk() -> sa.Column:
    return sa.Column(
        "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "feedback_forms",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_feedback_forms_tenant_id", "feedback_forms", ["tenant_id"])

    op.create_table(
        "feedback_form_questions",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("form_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.Text(), nullable=False, server_default="textarea"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("help_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("question_type IN ('rating','textarea')", name="tipo_valido"),
    )
    op.create_index("ix_feedback_form_questions_tenant_id", "feedback_form_questions",
                    ["tenant_id"])
    op.create_index("ix_form_questions_ordem", "feedback_form_questions",
                    ["tenant_id", "form_id", "sort_order"])

    op.create_table(
        "feedback_cycles",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_forms.id"), nullable=False),
        sa.Column("frequency", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        # Override manual do período avaliado (BR-MIGRAR-006); estender adia o
        # fechamento automático.
        sa.Column("evaluated_start", sa.Date()),
        sa.Column("evaluated_end", sa.Date()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("status IN ('draft','open','closed','published','archived')",
                           name="status_valido"),
        sa.CheckConstraint("end_date >= start_date", name="periodo_coerente"),
    )
    op.create_index("ix_feedback_cycles_tenant_id", "feedback_cycles", ["tenant_id"])
    op.create_index("ix_cycles_tenant_status", "feedback_cycles", ["tenant_id", "status"])
    op.create_index("ix_cycles_fechamento", "feedback_cycles", ["status", "end_date"])

    op.create_table(
        "feedback_permissions",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_type", sa.Text(), nullable=False, server_default="peer"),
        # NULL = permissão permanente, vale para todo ciclo (como no legado).
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_cycles.id", ondelete="SET NULL")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("reviewer_id", "reviewee_id", "permission_type", "cycle_id",
                            name="uq_feedback_permissions_regra"),
        sa.CheckConstraint("reviewer_id <> reviewee_id OR permission_type = 'self'",
                           name="auto_avaliacao_so_com_tipo_self"),
    )
    op.create_index("ix_feedback_permissions_tenant_id", "feedback_permissions", ["tenant_id"])
    op.create_index("ix_permissions_tenant_ativa", "feedback_permissions",
                    ["tenant_id", "active"])

    op.create_table(
        "feedback_requests",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_forms.id"), nullable=False),
        sa.Column("giver_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_justification", sa.Text()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("read_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        *_timestamps(),
        # A chave natural que torna a geração de requests idempotente (BR-MIGRAR-010).
        sa.UniqueConstraint("cycle_id", "giver_id", "receiver_id", "form_id",
                            name="uq_feedback_requests_par"),
        sa.CheckConstraint(
            "status IN ('pending','draft','submitted','expired','waived','cancelled')",
            name="status_valido"),
        sa.CheckConstraint("status <> 'cancelled' OR cancel_justification IS NOT NULL",
                           name="cancelamento_exige_justificativa"),
    )
    op.create_index("ix_feedback_requests_tenant_id", "feedback_requests", ["tenant_id"])
    op.create_index("ix_requests_tenant_cycle", "feedback_requests",
                    ["tenant_id", "cycle_id", "status"])
    op.create_index("ix_requests_giver", "feedback_requests", ["tenant_id", "giver_id", "status"])

    op.create_table(
        "feedback_answers",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_form_questions.id"), nullable=False),
        sa.Column("answer_text", sa.Text()),
        sa.Column("answer_score", sa.Integer()),
        *_timestamps(),
        sa.UniqueConstraint("request_id", "question_id", name="uq_feedback_answers_pergunta"),
        sa.CheckConstraint("answer_text IS NOT NULL OR answer_score IS NOT NULL",
                           name="resposta_nao_vazia"),
    )
    op.create_index("ix_feedback_answers_tenant_id", "feedback_answers", ["tenant_id"])

    op.create_table(
        "free_feedbacks",
        _uuid_pk(),
        _tenant_fk(),
        # SET NULL só para anonimização explícita (AMB-001), nunca por remoção de
        # usuário — soft-delete de profile mantém a FK válida.
        sa.Column("giver_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("positives", sa.Text()),
        sa.Column("improvements", sa.Text()),
        sa.Column("message", sa.Text()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("read_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        *_timestamps(),
        # Anonimato por construção: não existe linha anônima com autor guardado.
        sa.CheckConstraint("NOT is_anonymous OR giver_id IS NULL",
                           name="anonimo_nao_guarda_autor"),
    )
    op.create_index("ix_free_feedbacks_tenant_id", "free_feedbacks", ["tenant_id"])
    op.create_index("ix_free_feedbacks_receiver", "free_feedbacks",
                    ["tenant_id", "receiver_id", "read_at"])

    op.create_table(
        "cycle_notes",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("feedback_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("about_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_audio_transcription", sa.Boolean(), nullable=False,
                  server_default="false"),
        *_timestamps(),
    )
    op.create_index("ix_cycle_notes_tenant_id", "cycle_notes", ["tenant_id"])
    op.create_index("ix_cycle_notes_autor", "cycle_notes", ["tenant_id", "author_id", "cycle_id"])


def downgrade() -> None:
    op.drop_table("cycle_notes")
    op.drop_table("free_feedbacks")
    op.drop_table("feedback_answers")
    op.drop_table("feedback_requests")
    op.drop_table("feedback_permissions")
    op.drop_table("feedback_cycles")
    op.drop_table("feedback_form_questions")
    op.drop_table("feedback_forms")
