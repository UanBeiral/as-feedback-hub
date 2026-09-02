"""Modelos do contexto `identity`.

Cobre os aggregates UserAccount, Profile e TeamScope. Três diferenças deliberadas em
relação ao legado, todas registradas em `target_data_model.md`:

- `auth.users` do Supabase vira `users` + `refresh_tokens` (BR-DESCARTAR-005).
- Toda FK que era "uuid solto" no legado — `coordinator_members`, `team_requests` —
  passa a ser FK física. A dívida existia porque o protótipo não conseguia referenciar
  `auth.users`; aqui a tabela é nossa, então não há motivo para manter.
- `tenant_id NOT NULL` em tudo, com índice composto começando por ele (AD-10).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

ROLES = ("admin", "rh", "gestor", "colaborador")
USER_STATUSES = ("active", "inactive", "deleted")
TEAM_REQUEST_STATUSES = ("pending", "approved", "rejected")

# Flags de capacidade (BR-MIGRAR-013/015). São atributos do perfil, nunca papéis.
CAPABILITY_FLAGS = (
    "can_request_client_feedback",
    "can_view_feedback_answers",
    "can_view_team_history",
    "can_generate_reports",
    "can_view_manager_dashboard",
)


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Única tabela sem `tenant_id`: ela *é* o tenant."""

    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")

    __table_args__ = (
        CheckConstraint("status IN ('active','inactive')", name="status_valido"),
    )


class User(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Credencial. Substitui `auth.users` do Supabase.

    `password_hash` guarda bcrypt justamente para aceitar o export do GoTrue sem
    obrigar redefinição em massa (R-07 / AMB-013).
    """

    __tablename__ = "users"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        CheckConstraint("status IN ('active','inactive','deleted')", name="status_valido"),
    )

    @property
    def can_sign_in(self) -> bool:
        """BR-MIGRAR-016/018: usuário inativo ou removido não emite sessão."""
        return self.status == "active"


class RefreshToken(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Sessão renovável. Guardamos só o digest — ver `core/security.py`.

    `used_at` não existe para auditoria: é o detector de reúso. Um refresh token é de
    uso único, então uma segunda apresentação do mesmo token significa que ele vazou, e
    a resposta correta é derrubar todas as sessões daquele usuário.
    """

    __tablename__ = "refresh_tokens"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (Index("ix_refresh_tokens_user", "tenant_id", "user_id", "expires_at"),)


class Department(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),)


class Profile(TenantScopedMixin, TimestampMixin, Base):
    """Pessoa dentro do tenant: papel, capacidades e posição na hierarquia.

    `role` é um único valor; coordenação e capacidades são atributos separados
    (BR-MIGRAR-015). Foi assim que o legado se enrolou: tratava "coordenador" como se
    fosse um papel, e acabou com telas duplicadas por papel.

    **`id` é o mesmo `id` do `User`**, e não um uuid próprio. Não é economia de coluna:
    no legado `profiles.id` *é* o `auth.users.id`, e o `data_migration_plan.md` migra
    com os UUIDs preservados. Se o app criasse perfis com id novo, metade da base teria
    `profile.id == user.id` e a outra metade não — e todo FK para `profiles(id)` nos
    outros contextos herdaria essa loteria. O CHECK abaixo transforma a promessa em
    invariante do banco; use `Profile.for_user()` para não ter que lembrar dela.
    """

    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    department_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("departments.id")
    )
    manager_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("profiles.id"))
    is_coordinator: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    whatsapp: Mapped[str | None] = mapped_column(Text)
    # "Cargo" nas telas: aparece na tabela de usuários do admin, em Minha Equipe
    # (gestor e coordenador), em Meu Perfil e na busca de Solicitar Avaliação. O DDL de
    # `target_data_model.md` esqueceu esta coluna; sem ela, quatro telas do subset
    # literal perdem uma coluna visível e o dado morre no cutover.
    job_title: Mapped[str | None] = mapped_column(Text)

    # Capacidades. NOT NULL com default false é o deny-by-default no schema
    # (BR-MIGRAR-013): no legado eram nuláveis, e NULL era lido como permissão.
    can_request_client_feedback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    can_view_feedback_answers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    can_view_team_history: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    can_generate_reports: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    can_view_manager_dashboard: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin','rh','gestor','colaborador')", name="role_valido"),
        CheckConstraint("status IN ('active','inactive','deleted')", name="status_valido"),
        CheckConstraint("id = user_id", name="id_igual_ao_user"),
        Index("ix_profiles_tenant_status", "tenant_id", "status"),
        Index("ix_profiles_tenant_manager", "tenant_id", "manager_id"),
    )

    @classmethod
    def for_user(cls, user: User, **campos: object) -> Profile:
        """Único jeito correto de criar um perfil: id e tenant vêm do usuário."""
        return cls(id=user.id, user_id=user.id, tenant_id=user.tenant_id, **campos)  # type: ignore[arg-type]

    @property
    def flags(self) -> frozenset[str]:
        """Capacidades habilitadas, no formato que o token e os guards consomem."""
        return frozenset(name for name in CAPABILITY_FLAGS if getattr(self, name))


class ProfileDepartment(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Departamentos adicionais de um perfil (N:N), além do `department_id` principal."""

    __tablename__ = "profile_departments"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "department_id", name="uq_profile_departments_par"),
    )


class CoordinatorMember(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """Membro sob coordenação. Compõe o escopo do coordenador junto com `manager_id`
    (BR-MIGRAR-017: união deduplicada, nunca substituição)."""

    __tablename__ = "coordinator_members"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    coordinator_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("coordinator_id", "member_id", name="uq_coordinator_members_par"),
        CheckConstraint("coordinator_id <> member_id", name="sem_auto_coordenacao"),
        Index("ix_coordinator_members_tenant_coord", "tenant_id", "coordinator_id"),
    )


class TeamRequest(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """Pedido de inclusão de alguém na equipe.

    Só `pending → approved` e `pending → rejected` estão confirmados no legado
    (AMB-004). Qualquer outra transição é recusada com 409 pelo service — o modelo
    não inventa estados que ninguém verificou.
    """

    __tablename__ = "team_requests"

    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    requester_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    requested_member_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    approved_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("profiles.id")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')", name="status_valido"),
        Index("ix_team_requests_tenant_status", "tenant_id", "status"),
    )
