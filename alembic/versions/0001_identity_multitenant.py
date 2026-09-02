"""Fundação multi-tenant: contexto identity

`tenants` nasce primeiro e todas as outras tabelas apontam para ela com `tenant_id
NOT NULL`. Não há tabela de domínio sem tenant, e não há default: quem insere precisa
dizer de quem é a linha (AD-10).

Diferenças conscientes em relação ao legado:
- FKs físicas em `coordinator_members` e `team_requests`, que o protótipo não tinha
  porque não conseguia referenciar `auth.users`.
- Flags de capacidade `NOT NULL DEFAULT false` — no legado eram nuláveis, e NULL
  acabava lido como permissão concedida (BR-MIGRAR-013).
- `citext` no e-mail: o Supabase tratava e-mail como case-insensitive, e mudar isso
  em silêncio criaria contas duplicadas na migração.
- `profiles.id` não tem default: é sempre o `id` do usuário, como no legado e como o
  `data_migration_plan.md` exige (IDs preservados). O CHECK `id = user_id` faz o banco
  cobrar isso de todo mundo — ETL e aplicação.
- `profiles.job_title` ("Cargo"): coluna visível em quatro telas do subset literal que
  o DDL de `target_data_model.md` não listou.

Revision ID: 0001
Revises:
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active','inactive')", name="status_valido"),
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),
    )
    op.create_index("ix_departments_tenant_id", "departments", ["tenant_id"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        sa.CheckConstraint("status IN ('active','inactive','deleted')",
                           name="status_valido"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_tenant_id", "refresh_tokens", ["tenant_id"])
    op.create_index("ix_refresh_tokens_user", "refresh_tokens",
                    ["tenant_id", "user_id", "expires_at"])

    op.create_table(
        "profiles",
        # Sem default: o id do perfil é o id do usuário (ver docstring).
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("department_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("departments.id")),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        sa.Column("is_coordinator", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("whatsapp", sa.Text()),
        sa.Column("job_title", sa.Text()),
        sa.Column("can_request_client_feedback", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("can_view_feedback_answers", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("can_view_team_history", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("can_generate_reports", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("can_view_manager_dashboard", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('admin','rh','gestor','colaborador')",
                           name="role_valido"),
        sa.CheckConstraint("status IN ('active','inactive','deleted')",
                           name="status_valido"),
        sa.CheckConstraint("id = user_id", name="id_igual_ao_user"),
    )
    op.create_index("ix_profiles_tenant_id", "profiles", ["tenant_id"])
    op.create_index("ix_profiles_tenant_status", "profiles", ["tenant_id", "status"])
    op.create_index("ix_profiles_tenant_manager", "profiles", ["tenant_id", "manager_id"])

    op.create_table(
        "profile_departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("profile_id", "department_id", name="uq_profile_departments_par"),
    )
    op.create_index("ix_profile_departments_tenant_id", "profile_departments", ["tenant_id"])

    op.create_table(
        "coordinator_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("coordinator_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("coordinator_id", "member_id", name="uq_coordinator_members_par"),
        sa.CheckConstraint("coordinator_id <> member_id",
                           name="sem_auto_coordenacao"),
    )
    op.create_index("ix_coordinator_members_tenant_id", "coordinator_members", ["tenant_id"])
    op.create_index("ix_coordinator_members_tenant_coord", "coordinator_members",
                    ["tenant_id", "coordinator_id"])

    op.create_table(
        "team_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("requested_member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # Só os três estados confirmados no legado (AMB-004). Transições não
        # verificadas são recusadas pelo service com 409, não inventadas aqui.
        sa.CheckConstraint("status IN ('pending','approved','rejected')",
                           name="status_valido"),
    )
    op.create_index("ix_team_requests_tenant_id", "team_requests", ["tenant_id"])
    op.create_index("ix_team_requests_tenant_status", "team_requests", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_table("team_requests")
    op.drop_table("coordinator_members")
    op.drop_table("profile_departments")
    op.drop_table("profiles")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("departments")
    op.drop_table("tenants")
