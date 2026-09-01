"""Rotas do contexto `identity`.

O router é fino de propósito: traduz HTTP para chamada de service e de volta. Nenhuma
regra de negócio mora aqui — se aparecer um `if` sobre papel ou status neste arquivo,
ele está no lugar errado.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contexts.identity.repository import (
    AuthRepository,
    CoordinatorMemberRepository,
    ProfileRepository,
)
from app.contexts.identity.schemas import (
    CurrentUser,
    LoginRequest,
    ProfileSummary,
    RefreshRequest,
    TokenPair,
)
from app.contexts.identity.service import AuthService, TeamScopeService
from app.core.di import (
    PasswordHasherDep,
    SessionDep,
    SettingsDep,
    TenantDep,
    TokenServiceDep,
    client_ip,
)

router = APIRouter(prefix="/auth", tags=["identity"])


def get_auth_service(
    session: SessionDep,
    hasher: PasswordHasherDep,
    tokens: TokenServiceDep,
    settings: SettingsDep,
) -> AuthService:
    return AuthService(
        repository=AuthRepository(session),
        hasher=hasher,
        tokens=tokens,
        default_tenant_slug=settings.default_tenant_slug,
    )


def get_team_scope_service(session: SessionDep, tenant: TenantDep) -> TeamScopeService:
    return TeamScopeService(
        profiles=ProfileRepository(session, tenant),
        coordinator_members=CoordinatorMemberRepository(session, tenant),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TeamScopeDep = Annotated[TeamScopeService, Depends(get_team_scope_service)]


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.authenticate(
        email=payload.email,
        password=payload.password,
        tenant_slug=payload.tenant_slug,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.refresh_session(
        refresh_token=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, service: AuthServiceDep) -> None:
    await service.logout(refresh_token=payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(tenant: TenantDep, service: AuthServiceDep) -> None:
    """Derruba todas as sessões do usuário — o botão de pânico depois de um vazamento."""
    await service.logout_all(tenant)


@router.get("/me", response_model=CurrentUser)
async def me(tenant: TenantDep, service: AuthServiceDep) -> CurrentUser:
    return await service.describe_current_user(tenant)


@router.get("/my-team", response_model=list[ProfileSummary])
async def my_team(
    tenant: TenantDep,
    session: SessionDep,
    scope: TeamScopeDep,
) -> list[ProfileSummary]:
    """Equipe visível para quem está pedindo, já resolvida por `TeamScopeService`."""
    visible = await scope.resolve_visible_profile_ids(tenant)
    if not visible:
        return []
    profiles = ProfileRepository(session, tenant)
    return [
        ProfileSummary.model_validate(p)
        for p in await profiles.list_active()
        if p.id in visible
    ]
