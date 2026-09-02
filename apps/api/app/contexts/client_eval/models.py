"""Modelos do contexto `client_eval` — avaliação de cliente pelo link público.

É o único contexto com superfície aberta na internet, e isso muda o desenho:

- **O token é a credencial.** Não há sessão, não há usuário logado. Quem abre o link
  prova quem é apresentando um segredo de alta entropia com validade — e é ele que
  resolve o tenant, porque não há mais nada a resolver.
- **`UNIQUE (token)` é parte da regra**, não detalhe de schema: a submissão é um UPDATE
  condicional que casa token + estado + validade, e a unicidade é o que garante que ele
  atinge no máximo uma linha (BR-MIGRAR-019).
- **`client_whatsapp` sai mascarado por padrão** (BR-MIGRAR-022). O dado bruto é de
  cliente, não do escritório; quem precisa dele inteiro tem que ter permissão para isso.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

EVAL_STATUSES = ("pending", "in_progress", "submitted", "expired")
FLOW_TYPES = ("requested", "spontaneous")

# Tipos de pergunta do formulário público (BR-MIGRAR-020). Mais rico que o do feedback
# interno porque o cliente responde uma vez só e sem treinamento.
CLIENT_QUESTION_TYPES = ("rating", "text", "textarea", "yes_no", "nps", "multiple_choice")

MOTIVACOES = ("praise", "evaluate", "problem", "other")

# Validade padrão do link, em dias. O legado não deixou o número registrado em lugar
# nenhum — é uma escolha nossa, conservadora, e vale confirmar com o cliente antes da
# homologação.
DIAS_DE_VALIDADE_DO_TOKEN = 30


class ClientEvalForm(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Formulário público. `is_default` é o que o fluxo espontâneo usa."""

    __tablename__ = "client_eval_forms"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class ClientEvalFormQuestion(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    __tablename__ = "client_eval_form_questions"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    form_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("client_eval_forms.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="text")
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    placeholder: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "question_type IN ('rating','text','textarea','yes_no','nps','multiple_choice')",
            name="tipo_valido",
        ),
        Index("ix_client_questions_ordem", "tenant_id", "form_id", "display_order"),
    )


class ClientEvaluation(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Avaliação de um cliente sobre alguém do escritório.

    `token` é global e único: é por ele que a requisição pública encontra a linha, sem
    tenant no contexto. Índice único garante que o UPDATE condicional da submissão
    atinge no máximo uma linha, o que é a base da idempotência de BR-MIGRAR-019.
    """

    __tablename__ = "client_evaluations"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    target_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    form_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("client_eval_forms.id"), nullable=False
    )
    flow_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="requested")
    requested_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id")
    )
    client_name: Mapped[str | None] = mapped_column(Text)
    client_whatsapp: Mapped[str | None] = mapped_column(String(20))
    client_email: Mapped[str | None] = mapped_column(Text)
    token: Mapped[str | None] = mapped_column(String(64), unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contact_motivation: Mapped[str | None] = mapped_column(Text)
    contact_motivation_text: Mapped[str | None] = mapped_column(Text)
    overall_rating: Mapped[int | None] = mapped_column(Integer)
    recommendation_rating: Mapped[int | None] = mapped_column(Integer)
    # `default` (Python, aplicado no INSERT) além do `server_default` (DDL): o segundo
    # cobre quem escreve por SQL direto — ETL, script de migração —, o primeiro cobre o
    # INSERT do ORM que omita a coluna. Nenhum dos dois preenche o atributo de um objeto
    # recém-construído, que segue `None` até o flush.
    has_negative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracking_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','in_progress','submitted','expired')", name="status_valido"
        ),
        CheckConstraint("flow_type IN ('requested','spontaneous')", name="fluxo_valido"),
        # Fluxo por link sem token é um registro que ninguém consegue responder.
        CheckConstraint(
            "flow_type <> 'requested' OR token IS NOT NULL", name="requested_exige_token"
        ),
        Index("ix_client_evals_tenant_target", "tenant_id", "target_user_id", "status"),
        # O job de expiração varre por status + validade.
        Index("ix_client_evals_expiracao", "status", "token_expires_at"),
    )

    @property
    def status_exibicao(self) -> str:
        """Mapeamento de exibição do legado (BR-MIGRAR-022).

        `pending` e `in_progress` são a mesma coisa para quem olha a lista: o cliente
        ainda não respondeu. A distinção interessa ao servidor, não à tela.
        """
        return {
            "pending": "pendente",
            "in_progress": "pendente",
            "submitted": "respondido",
            "expired": "expirado",
        }[self.status]


class ClientEvalAnswer(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    __tablename__ = "client_eval_answers"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    evaluation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("client_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("client_eval_form_questions.id"), nullable=False
    )
    rating_value: Mapped[int | None] = mapped_column(Integer)
    text_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("evaluation_id", "question_id", name="uq_client_answers_pergunta"),
        CheckConstraint(
            "rating_value IS NOT NULL OR text_value IS NOT NULL", name="resposta_nao_vazia"
        ),
    )


class ServiceTag(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Catálogo de tipos de serviço que o cliente marca na avaliação."""

    __tablename__ = "service_tags"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_service_tags_nome"),)


class ClientEvaluationTag(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    __tablename__ = "client_evaluation_tags"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    evaluation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("client_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("service_tags.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("evaluation_id", "tag_id", name="uq_client_evaluation_tags_par"),
    )


def mascarar_whatsapp(numero: str | None) -> str | None:
    """Esconde o meio do número, preservando o fim (BR-MIGRAR-022).

    Os últimos dígitos bastam para alguém conferir "é este cliente mesmo?" na tela, sem
    entregar a lista de contatos inteira para qualquer papel que abra o relatório. O
    mascaramento é do servidor: o número completo não sai da API sem permissão, então
    não adianta abrir o DevTools.
    """
    if not numero:
        return numero
    digitos = "".join(c for c in numero if c.isdigit())
    if len(digitos) <= 4:
        return "*" * len(digitos)
    return f"{'*' * (len(digitos) - 4)}{digitos[-4:]}"
