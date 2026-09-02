"""Rotas do contexto `engagement`.

Cada rota declara na assinatura quem pode chamá-la (AD-02). Endpoint sem guard não é
endpoint público — é bug —, então aqui não existe rota sem `TenantDep` ou sem
`require_role`. O que é do próprio usuário (o sino de notificações) não precisa de
papel; o que é configuração ou triagem do escritório é de admin/RH.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.contexts.engagement.repository import (
    AuditLogRepository,
    ContactMessageRepository,
    NotificationRepository,
    OutboxRepository,
    PlatformUpdateRepository,
    TenantSettingRepository,
)
from app.contexts.engagement.schemas import (
    AuditLogOut,
    ContactMessageIn,
    ContactMessageOut,
    ContactStatusUpdate,
    NotificationFeed,
    PlatformUpdateIn,
    PlatformUpdateOut,
    SettingOut,
    SettingUpdate,
)
from app.contexts.engagement.service import (
    ContactMessageService,
    NotificationService,
    OutboxService,
    PlatformUpdateService,
    SettingsService,
)
from app.contexts.identity.repository import ProfileRepository
from app.core.di import SessionDep, TenantDep, require_role
from app.core.tenancy import TenantContext

router = APIRouter(tags=["engagement"])

# Configuração e triagem são do escritório, não da pessoa: admin e RH.
AdminDep = Annotated[TenantContext, Depends(require_role("admin", "rh"))]


def get_notification_service(session: SessionDep, tenant: TenantDep) -> NotificationService:
    return NotificationService(NotificationRepository(session, tenant))


def get_settings_service(session: SessionDep, tenant: TenantDep) -> SettingsService:
    return SettingsService(TenantSettingRepository(session, tenant))


def get_contact_service(session: SessionDep, tenant: TenantDep) -> ContactMessageService:
    return ContactMessageService(ContactMessageRepository(session, tenant))


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
ContactServiceDep = Annotated[ContactMessageService, Depends(get_contact_service)]


# ---------------------------------------------------------------- notificações

@router.get("/notifications", response_model=NotificationFeed)
async def list_notifications(
    tenant: TenantDep,
    service: NotificationServiceDep,
    apenas_nao_lidas: Annotated[bool, Query(alias="unread")] = False,
) -> NotificationFeed:
    """Lista e contagem em uma chamada só — é o que o sino consome a cada página."""
    return await service.feed(tenant, apenas_nao_lidas=apenas_nao_lidas)


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: UUID, tenant: TenantDep, service: NotificationServiceDep
) -> None:
    await service.mark_read(tenant, notification_id)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    tenant: TenantDep, service: NotificationServiceDep
) -> None:
    await service.mark_all_read(tenant)


# ---------------------------------------------------------------- configurações

@router.get("/settings", response_model=list[SettingOut])
async def list_settings(tenant: TenantDep, service: SettingsServiceDep) -> list[SettingOut]:
    """Leitura é de qualquer autenticado: os toggles decidem o que a navegação mostra.

    Escrita continua restrita a admin/RH — e a autorização final de cada recurso é
    checada no servidor, nunca por escondido de menu (BR-MIGRAR-016).
    """
    return await service.list_catalog()


@router.put("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def update_setting(
    key: str, payload: SettingUpdate, tenant: AdminDep, service: SettingsServiceDep
) -> None:
    await service.upsert(
        tenant,
        key=key,
        value=payload.value,
        expected_updated_at=payload.expected_updated_at,
    )


# ---------------------------------------------------------------- comunicados

@router.get("/platform-updates", response_model=list[PlatformUpdateOut])
async def list_platform_updates(
    tenant: TenantDep, session: SessionDep
) -> list[PlatformUpdateOut]:
    """Todo mundo vê os publicados; admin/RH também vê os rascunhos."""
    repo = PlatformUpdateRepository(session, tenant)
    comunicados = (
        await repo.list_all() if tenant.has_role("admin", "rh") else await repo.list_published()
    )
    return [PlatformUpdateOut.model_validate(c) for c in comunicados]


@router.post(
    "/platform-updates", response_model=PlatformUpdateOut, status_code=status.HTTP_201_CREATED
)
async def create_platform_update(
    payload: PlatformUpdateIn, tenant: AdminDep, session: SessionDep
) -> PlatformUpdateOut:
    service = PlatformUpdateService(
        PlatformUpdateRepository(session, tenant),
        OutboxService(OutboxRepository(session, tenant)),
        destinatarios=[],
    )
    comunicado = await service.create_draft(
        tenant, title=payload.title, content=payload.content
    )
    await session.flush()
    await session.refresh(comunicado)
    return PlatformUpdateOut.model_validate(comunicado)


@router.post("/platform-updates/{update_id}/publish", response_model=PlatformUpdateOut)
async def publish_platform_update(
    update_id: UUID, tenant: AdminDep, session: SessionDep
) -> PlatformUpdateOut:
    """Publicar enfileira uma mensagem por destinatário, na mesma transação (AD-04).

    Se o worker estiver fora do ar, a publicação acontece do mesmo jeito e as mensagens
    esperam na fila — que é exatamente o cenário "efeito auxiliar não desfaz operação
    principal" de PAR-07.
    """
    destinatarios = await ProfileRepository(session, tenant).list_active_ids()
    service = PlatformUpdateService(
        PlatformUpdateRepository(session, tenant),
        OutboxService(OutboxRepository(session, tenant)),
        destinatarios=sorted(destinatarios),
    )
    comunicado = await service.publish(update_id)
    await session.flush()
    return PlatformUpdateOut.model_validate(comunicado)


# ---------------------------------------------------------------- fale conosco

@router.post(
    "/contact-messages", response_model=ContactMessageOut, status_code=status.HTTP_201_CREATED
)
async def create_contact_message(
    payload: ContactMessageIn,
    tenant: TenantDep,
    session: SessionDep,
    service: ContactServiceDep,
) -> ContactMessageOut:
    mensagem = await service.create(tenant, **payload.model_dump())
    # `created_at` e `status` vêm de server_default: sem flush + refresh o objeto ainda
    # não os conhece, e em sessão async tocar no atributo dispara MissingGreenlet.
    await session.flush()
    await session.refresh(mensagem)
    return ContactMessageOut.model_validate(mensagem)


@router.get("/contact-messages", response_model=list[ContactMessageOut])
async def list_contact_messages(
    tenant: AdminDep,
    session: SessionDep,
    status_filtro: Annotated[str | None, Query(alias="status")] = None,
) -> list[ContactMessageOut]:
    repo = ContactMessageRepository(session, tenant)
    return [
        ContactMessageOut.model_validate(m) for m in await repo.list_by_status(status_filtro)
    ]


@router.patch("/contact-messages/{message_id}", response_model=ContactMessageOut)
async def change_contact_status(
    message_id: UUID,
    payload: ContactStatusUpdate,
    tenant: AdminDep,
    service: ContactServiceDep,
) -> ContactMessageOut:
    mensagem = await service.change_status(message_id, novo_status=payload.status)
    return ContactMessageOut.model_validate(mensagem)


# ---------------------------------------------------------------- auditoria

@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    tenant: AdminDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogOut]:
    repo = AuditLogRepository(session, tenant)
    return [
        AuditLogOut.model_validate(linha)
        for linha in await repo.list_recent(limit=limit, offset=offset)
    ]
