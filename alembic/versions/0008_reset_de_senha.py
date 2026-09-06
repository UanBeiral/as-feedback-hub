"""Token de redefinição de senha (SCR-0038)

Fecha a #5 da conferência: o legado tinha "Esqueci minha senha" no login, e no sistema
novo o texto dizia para procurar o administrador — honesto, mas era a ausência da tela.

Tabela própria, e não uma coluna em `users`: o token nasce, expira e é gasto, e um pedido
novo não pode apagar o anterior sem que se saiba qual dos dois links chegou primeiro ao
e-mail da pessoa. Só o digest é guardado, como nos refresh tokens — quem lê o banco não
consegue montar o link.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("requested_ip", sa.String(length=45)),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_digest", name="uq_password_reset_digest"),
    )
    op.create_index("ix_password_reset_tenant", "password_reset_tokens", ["tenant_id"])
    # A limpeza dos vencidos varre por data; a confirmação busca pelo digest, que já é
    # único. Um índice por usuário serviria para listar pedidos, e ninguém os lista.
    op.create_index("ix_password_reset_expira", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_expira", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tenant", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
