"""Contexto client_eval: formulários públicos, avaliações por token, tags de serviço

Este é o domínio que o protótipo criou inteiro fora das migrations, direto pelo
dashboard do Supabase — é o motivo de AMB-010 existir e de o `pg_dump` de produção ser
pré-requisito do cutover. Aqui ele nasce versionado.

`client_evaluations.token UNIQUE` não é conveniência de busca: é o que garante que o
UPDATE condicional da submissão atinge no máximo uma linha, base da idempotência de
BR-MIGRAR-019.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
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
        "client_eval_forms",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        # O formulário `is_default` é o que o fluxo espontâneo usa (AMB-002).
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        *_timestamps(),
    )
    op.create_index("ix_client_eval_forms_tenant_id", "client_eval_forms", ["tenant_id"])

    op.create_table(
        "client_eval_form_questions",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("form_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_eval_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.Text(), nullable=False, server_default="text"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("placeholder", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "question_type IN ('rating','text','textarea','yes_no','nps','multiple_choice')",
            name="tipo_valido"),
    )
    op.create_index("ix_client_eval_form_questions_tenant_id", "client_eval_form_questions",
                    ["tenant_id"])
    op.create_index("ix_client_questions_ordem", "client_eval_form_questions",
                    ["tenant_id", "form_id", "display_order"])

    op.create_table(
        "client_evaluations",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_eval_forms.id"), nullable=False),
        sa.Column("flow_type", sa.Text(), nullable=False, server_default="requested"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        sa.Column("client_name", sa.Text()),
        sa.Column("client_whatsapp", sa.String(20)),
        sa.Column("client_email", sa.Text()),
        # UNIQUE é parte da regra, não detalhe de busca (BR-MIGRAR-019).
        sa.Column("token", sa.String(64), unique=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("contact_motivation", sa.Text()),
        sa.Column("contact_motivation_text", sa.Text()),
        sa.Column("overall_rating", sa.Integer()),
        sa.Column("recommendation_rating", sa.Integer()),
        sa.Column("has_negative", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("tracking_data", postgresql.JSONB()),
        *_timestamps(),
        sa.CheckConstraint("status IN ('pending','in_progress','submitted','expired')",
                           name="status_valido"),
        sa.CheckConstraint("flow_type IN ('requested','spontaneous')", name="fluxo_valido"),
        # Avaliação por link sem token é um registro que ninguém consegue responder.
        sa.CheckConstraint("flow_type <> 'requested' OR token IS NOT NULL",
                           name="requested_exige_token"),
    )
    op.create_index("ix_client_evaluations_tenant_id", "client_evaluations", ["tenant_id"])
    op.create_index("ix_client_evals_tenant_target", "client_evaluations",
                    ["tenant_id", "target_user_id", "status"])
    op.create_index("ix_client_evals_expiracao", "client_evaluations",
                    ["status", "token_expires_at"])

    op.create_table(
        "client_eval_answers",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_evaluations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_eval_form_questions.id"), nullable=False),
        sa.Column("rating_value", sa.Integer()),
        sa.Column("text_value", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("evaluation_id", "question_id", name="uq_client_answers_pergunta"),
        sa.CheckConstraint("rating_value IS NOT NULL OR text_value IS NOT NULL",
                           name="resposta_nao_vazia"),
    )
    op.create_index("ix_client_eval_answers_tenant_id", "client_eval_answers", ["tenant_id"])

    op.create_table(
        "service_tags",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_service_tags_nome"),
    )
    op.create_index("ix_service_tags_tenant_id", "service_tags", ["tenant_id"])

    op.create_table(
        "client_evaluation_tags",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_evaluations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("evaluation_id", "tag_id", name="uq_client_evaluation_tags_par"),
    )
    op.create_index("ix_client_evaluation_tags_tenant_id", "client_evaluation_tags",
                    ["tenant_id"])


def downgrade() -> None:
    op.drop_table("client_evaluation_tags")
    op.drop_table("service_tags")
    op.drop_table("client_eval_answers")
    op.drop_table("client_evaluations")
    op.drop_table("client_eval_form_questions")
    op.drop_table("client_eval_forms")
