"""Descrição de departamento e sensibilidade na auditoria

Duas colunas que a conferência contra o oráculo cobrou (#19 e #35/#36 em
`docs/conferencia-resultado.md`), decididas pelo cliente em 06/09/2026.

`departments.description` o legado tem e o DDL alvo esqueceu — a tabela de
departamentos mostra a coluna, e sem o campo ela nasce vazia para sempre.

`audit_logs.is_sensitive` sustenta dois cartões e a legenda do gráfico do painel de
auditoria. É **coluna e não derivação**: a classificação é gravada no INSERT, junto com
o fato. Derivar na consulta faria toda mudança futura no catálogo de ações reescrever o
passado — e reescrever o passado é exatamente o que uma auditoria append-only não pode
fazer. O `server_default` é `false` porque a coluna nasce em cima de linhas existentes; o
backfill abaixo classifica as que já estão lá com o catálogo de hoje.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Espelha `ACOES_SENSIVEIS` em `app/contexts/engagement/service.py`. A duplicação é
# deliberada: uma migration não deve importar código de aplicação, que muda embaixo dela.
ACOES_SENSIVEIS = (
    "profile.role_changed",
    "profile.flags_changed",
    "profile.soft_deleted",
    "user.password_reset",
    "request.cancelled",
)


def upgrade() -> None:
    op.add_column("departments", sa.Column("description", sa.Text()))

    op.add_column(
        "audit_logs",
        sa.Column(
            "is_sensitive", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.execute(
        sa.text("UPDATE audit_logs SET is_sensitive = true WHERE action = ANY(:acoes)").bindparams(
            sa.bindparam("acoes", value=list(ACOES_SENSIVEIS), type_=sa.ARRAY(sa.Text()))
        )
    )
    # O índice serve os dois usos da tela: o cartão dos últimos 7 dias e o gráfico de 14.
    op.create_index(
        "ix_audit_logs_sensiveis",
        "audit_logs",
        ["tenant_id", "is_sensitive", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_sensiveis", table_name="audit_logs")
    op.drop_column("audit_logs", "is_sensitive")
    op.drop_column("departments", "description")
