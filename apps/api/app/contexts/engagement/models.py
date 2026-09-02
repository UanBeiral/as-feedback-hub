"""Modelos do contexto `engagement`.

Aqui moram os efeitos auxiliares do sistema: o que é comunicado, o que é registrado e
o que é configurado. Duas peças merecem explicação antes do código:

- **`outbox_messages` é o coração do AD-04.** O legado disparava efeito auxiliar dentro
  da request (Edge Function com `waitUntil`), e quando a função falhava a notificação
  simplesmente não acontecia — sem registro, sem retry, sem ninguém sabendo
  (BR-DESCARTAR-002). Aqui a mensagem é gravada na **mesma transação** do comando que a
  originou: ou a operação principal e a intenção de comunicar entram juntas, ou nenhuma
  entra. O despacho vem depois, pelo worker, e falhar no despacho nunca desfaz a
  operação de origem (BR-MIGRAR-025).

- **`audit_logs` é append-only e usa `actor_id`**, nunca `user_id` (BR-MIGRAR-026). O
  nome importa: quem aparece na linha é quem *fez*, não quem *sofreu* a ação — foi
  justamente essa confusão que tornou a auditoria do legado ambígua nas remoções de
  membro, onde os dois existem.
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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

OUTBOX_STATUSES = ("pending", "dispatched", "failed", "dead")
CONTACT_STATUSES = ("novo", "em_andamento", "resolvido")

# Catálogo de configurações (BR-MIGRAR-027): oito chaves, com o default que vale quando
# a chave nunca foi gravada. Os três toggles são `false` por default — deny-by-default
# vale para configuração global do mesmo jeito que vale para capacidade individual.
SETTINGS_CATALOG: dict[str, str | None] = {
    "company_name": None,
    "logo_url": None,
    "client_feedback_motivations": '{"praise":true,"evaluate":true,"problem":true,"other":true}',
    "whatsapp_message_template": None,
    "calendar_keywords": "[]",
    "gestor_can_access_reports": "false",
    "gestor_can_access_agenda": "false",
    "colaborador_can_generate_own_report": "false",
}


class Notification(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Aviso para uma pessoa. Não lida é `read_at IS NULL` (BR-MIGRAR-023).

    Sem coluna booleana de "lida": duas fontes de verdade para o mesmo fato divergem
    mais cedo ou mais tarde, e o legado já provou isso com `is_active` vs `status` em
    `profiles`.
    """

    __tablename__ = "notifications"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    # FK física: no legado era uuid solto apontando para `auth.users`.
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False, server_default="general")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # O sino consulta "não lidas deste usuário" a cada carga de página: é a query
        # mais frequente do contexto, e `read_at` entra no índice por isso.
        Index("ix_notifications_destinatario", "tenant_id", "user_id", "read_at"),
    )

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class OutboxMessage(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Intenção de efeito auxiliar, gravada na transação do comando de origem (AD-04).

    `UNIQUE (topic, idempotency_key)` é o que garante BR-MIGRAR-024: a mesma comunicação
    de ciclo para a mesma pessoa não entra duas vezes na fila, ainda que o comando de
    origem seja repetido. A chave é natural, do domínio (`update_id:user_id`), não um
    uuid aleatório — uuid novo a cada tentativa não deduplicaria nada.
    """

    __tablename__ = "outbox_messages"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # Nulável porque `dispatched`/`dead` não têm próxima tentativa; com default para
    # que um INSERT que omita o campo nasça pronta para despacho, e não invisível.
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Fora do DDL da spec: uma DLQ sem o motivo da morte não é operável — quem for
    # investigar às 7h da manhã precisa saber o que falhou (ver docs/spec-deviations.md).
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("topic", "idempotency_key", name="uq_outbox_messages_idempotencia"),
        CheckConstraint(
            "status IN ('pending','dispatched','failed','dead')", name="status_valido"
        ),
        CheckConstraint("attempts >= 0", name="attempts_nao_negativo"),
        # O worker varre por status + horário: é a única query quente da tabela.
        Index("ix_outbox_pendentes", "status", "next_attempt_at"),
    )


class AuditLog(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Trilha append-only de ações sensíveis (BR-MIGRAR-026).

    `actor_id` é nulável de propósito: o ator pode ter sido removido depois, e perder a
    linha inteira de auditoria por causa disso seria o oposto do objetivo.
    """

    __tablename__ = "audit_logs"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    table_name: Mapped[str | None] = mapped_column(Text)
    record_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_audit_logs_tenant_tempo", "tenant_id", "created_at"),)


class TenantSetting(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Configuração key/value por tenant (BR-MIGRAR-027).

    `updated_by` é NOT NULL — dívida do legado sanada. Configuração global muda o
    comportamento de todo mundo no escritório; saber quem mudou não é luxo.
    """

    __tablename__ = "tenant_settings"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_chave"),)


class PlatformUpdate(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Comunicado publicado pelo admin, com contagem de quem foi notificado."""

    __tablename__ = "platform_updates"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id")
    )
    notified_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_platform_updates_tenant_draft", "tenant_id", "draft"),)


class ContactMessage(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Mensagem do "Fale Conosco". Máquina: novo → em_andamento → resolvido."""

    __tablename__ = "contact_messages"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="novo")
    # FK física: era uuid solto no legado.
    created_by: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('novo','em_andamento','resolvido')", name="status_valido"),
        Index("ix_contact_messages_tenant_status", "tenant_id", "status"),
    )
