"""Contratos de entrada e saída do contexto `identity`.

São estes schemas que viram o OpenAPI, e o OpenAPI que vira o client do front (AD-08).
Nenhum modelo do SQLAlchemy atravessa a borda: o que sai daqui é o que o front pode ver.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)
    tenant_slug: str | None = Field(
        default=None,
        description="Opcional enquanto houver um tenant só; obrigatório quando houver mais.",
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class CapabilityFlags(BaseModel):
    can_request_client_feedback: bool = False
    can_view_feedback_answers: bool = False
    can_view_team_history: bool = False
    can_generate_reports: bool = False
    can_view_manager_dashboard: bool = False


class CurrentUser(BaseModel):
    """O que o front precisa saber para montar a navegação — e nada além disso."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    profile_id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    role: str
    job_title: str | None
    is_coordinator: bool
    department_id: UUID | None
    manager_id: UUID | None
    flags: CapabilityFlags


class ProfileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: str
    job_title: str | None
    status: str
    is_coordinator: bool
    department_id: UUID | None
    manager_id: UUID | None


class RegisterUserIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1)
    role: str = Field(pattern="^(admin|rh|gestor|colaborador)$")
    job_title: str | None = None
    department_id: UUID | None = None
    manager_id: UUID | None = None


class ProfileUpdateIn(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    whatsapp: str | None = None
    department_id: UUID | None = None


class OwnProfileIn(BaseModel):
    """O que a própria pessoa pode mudar. Papel e capacidades não estão aqui."""

    full_name: str | None = None
    job_title: str | None = None
    whatsapp: str | None = None


class OwnPasswordIn(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: str = Field(min_length=8, max_length=72)


class RoleIn(BaseModel):
    role: str = Field(pattern="^(admin|rh|gestor|colaborador)$")


class FlagsIn(BaseModel):
    """PATCH de capacidades: só as chaves enviadas mudam (BR-MIGRAR-013)."""

    flags: dict[str, bool] = Field(min_length=1)


class CoordinatorIn(BaseModel):
    is_coordinator: bool


class ManagerIn(BaseModel):
    manager_id: UUID | None = None


class DepartmentsIn(BaseModel):
    department_ids: list[UUID] = Field(default_factory=list)


class PasswordResetIn(BaseModel):
    nova_senha: str = Field(min_length=8, max_length=72)


class DepartmentIn(BaseModel):
    name: str = Field(min_length=1)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class CoordinatorMemberIn(BaseModel):
    coordinator_id: UUID
    member_id: UUID


class TeamRequestIn(BaseModel):
    requested_member_id: UUID


class TeamRequestRejectIn(BaseModel):
    motivo: str | None = None


class TeamRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    requested_member_id: UUID
    status: str
    rejection_reason: str | None
    resolved_at: datetime | None


class ActiveRoleIn(BaseModel):
    """Troca de contexto ativo (BR-MIGRAR-016).

    Só desce na hierarquia: a troca restringe a visão, nunca concede poder.
    """

    active_role: str = Field(pattern="^(admin|rh|gestor|colaborador)$")


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    active_role: str
