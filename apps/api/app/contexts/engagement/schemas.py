"""Contratos de entrada e saída do contexto `engagement` (AD-08)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str
    message: str | None
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationFeed(BaseModel):
    """O que o sino precisa em uma chamada só: a lista e o número."""

    items: list[NotificationOut]
    unread_count: int


class SettingOut(BaseModel):
    key: str
    value: str | None
    updated_at: datetime | None
    updated_by: UUID | None
    # `False` quando o valor vem do catálogo por nunca ter sido gravado — o front
    # precisa distinguir "ninguém configurou" de "alguém configurou assim".
    persisted: bool


class SettingUpdate(BaseModel):
    value: str | None = None
    expected_updated_at: datetime | None = Field(
        default=None,
        description=(
            "Carimbo lido antes de editar. Ausente significa 'a chave não existia'. "
            "Divergência devolve 409 em vez de sobrescrever a edição de outra pessoa."
        ),
    )


class PlatformUpdateIn(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class PlatformUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    draft: bool
    notified_count: int
    published_at: datetime | None
    created_at: datetime


class ContactMessageIn(BaseModel):
    type: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)
    email: EmailStr
    message: str = Field(min_length=1)
    company: str | None = None
    phone: str | None = None


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    company: str | None
    contact_name: str
    email: EmailStr
    phone: str | None
    message: str
    status: str
    created_at: datetime


class ContactStatusUpdate(BaseModel):
    status: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: str
    table_name: str | None
    record_id: UUID | None
    details: dict | None
    created_at: datetime
