"""Modelos do contexto `feedback` — o núcleo do sistema.

Três decisões que mudam em relação ao legado, todas registradas em
`target_data_model.md`:

- **`feedback_answers` é a única fonte de verdade das respostas.** O legado mantinha as
  mesmas respostas em dois lugares: linhas em `feedback_answers` e uma cópia em
  `feedback_requests.response_data jsonb`. Duas cópias divergem — e divergiram, é a
  reconciliação que o `data_migration_plan.md` tem de fazer no cutover (AMB-011). Aqui
  o jsonb não existe.

- **`reviewed` não existe** na máquina do request (AMB-003): o status aparecia no mapa
  de status dos relatórios do legado, mas ninguém achou o gatilho que o produzia.
  Modelar um estado que nada alcança é convidar código morto.

- **FKs físicas em `feedback_answers`**: `request_id` e `question_id` eram uuid solto no
  protótipo, porque o PostgREST não reclamava. Resposta órfã é dado que ninguém
  consegue interpretar depois.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

# Máquina do ciclo (BR-MIGRAR-004).
CYCLE_STATUSES = ("draft", "open", "closed", "published", "archived")

# Máquina do request (BR-MIGRAR-003). `reviewed` fora — ver docstring do módulo.
REQUEST_STATUSES = ("pending", "draft", "submitted", "expired", "waived", "cancelled")

QUESTION_TYPES = ("rating", "textarea")

# Tipos observados no legado (`AdminPermissoes.tsx`). `peer_to_peer` é o único com
# efeito reverso automático (BR-MIGRAR-002).
PERMISSION_TYPES = (
    "peer",
    "peer_to_peer",
    "manager",
    "manager_to_report",
    "subordinate",
    "upward",
    "self",
    "custom",
)

# Carência antes do fechamento automático (BR-MIGRAR-005) e janela de atraso
# (BR-MIGRAR-007). O mesmo número serve aos dois porque é o mesmo conceito: no legado,
# "venceu mas ainda dá para entregar".
DIAS_DE_CARENCIA = 3


class FeedbackForm(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "feedback_forms"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FeedbackFormQuestion(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    __tablename__ = "feedback_form_questions"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    form_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="textarea")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    help_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("question_type IN ('rating','textarea')", name="tipo_valido"),
        Index("ix_form_questions_ordem", "tenant_id", "form_id", "sort_order"),
    )


class FeedbackCycle(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Ciclo de feedback 360.

    `evaluated_start/end` existem porque o período *avaliado* pode divergir das datas do
    ciclo (BR-MIGRAR-006): abre-se em maio um ciclo que avalia abril. Quando são nulos,
    vale a regra automática do legado (mês anterior ao início). E quando `evaluated_end`
    é estendido à mão, ele adia o fechamento automático — é a válvula que o gestor usa
    para dar mais prazo sem mexer nas datas oficiais.
    """

    __tablename__ = "feedback_cycles"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    form_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_forms.id"), nullable=False
    )
    frequency: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    evaluated_start: Mapped[date | None] = mapped_column(Date)
    evaluated_end: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','open','closed','published','archived')", name="status_valido"
        ),
        CheckConstraint("end_date >= start_date", name="periodo_coerente"),
        Index("ix_cycles_tenant_status", "tenant_id", "status"),
        # O job de fechamento varre por status + data final: é a query do scheduler.
        Index("ix_cycles_fechamento", "status", "end_date"),
    )

    @property
    def prazo_final(self) -> date:
        """Data que o fechamento automático observa.

        A extensão manual do período avaliado vence a data oficial — é para isso que
        ela existe (PAR-06 § "Período avaliado estendido adia o fechamento").
        """
        if self.evaluated_end is not None and self.evaluated_end > self.end_date:
            return self.evaluated_end
        return self.end_date


class FeedbackPermission(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Quem avalia quem. É a matriz que a abertura do ciclo lê para gerar requests.

    `cycle_id` nulo significa permissão permanente, valendo para todo ciclo — era assim
    no legado e continua sendo.
    """

    __tablename__ = "feedback_permissions"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    reviewee_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    permission_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="peer")
    cycle_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_cycles.id", ondelete="SET NULL")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "reviewer_id",
            "reviewee_id",
            "permission_type",
            "cycle_id",
            name="uq_feedback_permissions_regra",
        ),
        CheckConstraint("reviewer_id <> reviewee_id OR permission_type = 'self'",
                        name="auto_avaliacao_so_com_tipo_self"),
        Index("ix_permissions_tenant_ativa", "tenant_id", "active"),
    )


class FeedbackRequest(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Pedido de feedback de uma pessoa sobre outra, dentro de um ciclo.

    A unicidade por `(cycle, giver, receiver, form)` é o que torna a geração de requests
    idempotente (BR-MIGRAR-010): reabrir a geração não duplica nada, e o banco garante
    isso mesmo se o service esquecer.
    """

    __tablename__ = "feedback_requests"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    cycle_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_cycles.id", ondelete="CASCADE"), nullable=False
    )
    form_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_forms.id"), nullable=False
    )
    giver_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    receiver_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    due_date: Mapped[date | None] = mapped_column(Date)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_justification: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id")
    )

    __table_args__ = (
        UniqueConstraint(
            "cycle_id", "giver_id", "receiver_id", "form_id", name="uq_feedback_requests_par"
        ),
        CheckConstraint(
            "status IN ('pending','draft','submitted','expired','waived','cancelled')",
            name="status_valido",
        ),
        CheckConstraint(
            "status <> 'cancelled' OR cancel_justification IS NOT NULL",
            name="cancelamento_exige_justificativa",
        ),
        Index("ix_requests_tenant_cycle", "tenant_id", "cycle_id", "status"),
        Index("ix_requests_giver", "tenant_id", "giver_id", "status"),
    )


class FeedbackAnswer(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    __tablename__ = "feedback_answers"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    request_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("feedback_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_form_questions.id"), nullable=False
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("request_id", "question_id", name="uq_feedback_answers_pergunta"),
        # Uma resposta é texto ou nota; vazia nas duas não é resposta, é linha à toa.
        CheckConstraint(
            "answer_text IS NOT NULL OR answer_score IS NOT NULL", name="resposta_nao_vazia"
        ),
    )


class FreeFeedback(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Feedback espontâneo entre colegas, fora de ciclo.

    `is_anonymous` com `giver_id` nulo é anonimização **por design**, não por política:
    não existe coluna com o autor para alguém consultar depois, o que é o default
    conservador de AMB-001. `is_sensitive` esconde do destinatário e mostra à gestão.
    """

    __tablename__ = "free_feedbacks"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    giver_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    receiver_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    positives: Mapped[str | None] = mapped_column(Text)
    improvements: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id")
    )

    __table_args__ = (
        CheckConstraint(
            "NOT is_anonymous OR giver_id IS NULL", name="anonimo_nao_guarda_autor"
        ),
        Index("ix_free_feedbacks_receiver", "tenant_id", "receiver_id", "read_at"),
    )


class CycleNote(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Anotação do avaliador sobre alguém durante o ciclo — o "caderno do ciclo"."""

    __tablename__ = "cycle_notes"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    cycle_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("feedback_cycles.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    about_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_audio_transcription: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    __table_args__ = (
        Index("ix_cycle_notes_autor", "tenant_id", "author_id", "cycle_id"),
    )
