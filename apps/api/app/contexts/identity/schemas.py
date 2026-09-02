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
