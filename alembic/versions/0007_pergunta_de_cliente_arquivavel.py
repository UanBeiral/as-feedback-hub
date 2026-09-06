"""Pergunta de formulário de cliente pode ser arquivada

Fecha #45 da conferência: a aba de Formulários de Cliente Externo precisa de "remover", e
remover uma pergunta já respondida esbarra no FK de `client_eval_answers`.

Apagar mesmo assim não é opção — seria destruir a resposta de um cliente para limpar um
formulário. Então "remover" tem dois significados, e a coluna é o que permite distinguir:
pergunta nunca respondida some de verdade; pergunta com resposta é **arquivada**, sai dos
formulários novos e continua explicando os relatórios antigos.

`is_active` e não `archived_at` para acompanhar `client_eval_forms.is_active`, que já é
booleano — duas convenções para o mesmo conceito na mesma tabela vizinha custam mais que
o timestamp valeria.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "client_eval_form_questions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # O índice de ordem passa a filtrar por ativa: é sempre assim que o wizard público
    # lê a lista, e ele é a consulta mais quente do sistema.
    op.drop_index("ix_client_questions_ordem", table_name="client_eval_form_questions")
    op.create_index(
        "ix_client_questions_ordem",
        "client_eval_form_questions",
        ["tenant_id", "form_id", "is_active", "display_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_client_questions_ordem", table_name="client_eval_form_questions")
    op.create_index(
        "ix_client_questions_ordem",
        "client_eval_form_questions",
        ["tenant_id", "form_id", "display_order"],
    )
    op.drop_column("client_eval_form_questions", "is_active")
