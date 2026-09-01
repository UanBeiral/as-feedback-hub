"""Injeção de dependências e a cadeia de autorização (AD-02).

A cadeia é `sessão → tenant → papel → flag → escopo`, e **nega por padrão**: cada elo
só deixa passar o que reconhece explicitamente. Um endpoint sem guard não é um endpoint
público — é um bug, e `require_role`/`require_flag` existem para que a permissão fique
declarada na assinatura da rota, visível na revisão.

Onde os poderes vêm: o access token carrega papel e flags resolvidos no login. Como ele
vale 15 minutos (AD-03), uma permissão revogada continua valendo até o token expirar.
É a troca consciente do JWT curto — nada de consulta ao banco a cada requisição. Ações
sensíveis que não toleram essa janela devem revalidar contra o banco no próprio service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import InvalidTokenError, PasswordHasher, TokenService
from app.core.tenancy import TenantContext

# auto_error=False: queremos a nossa própria 401 no formato de erro do domínio.
_bearer = HTTPBearer(auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_password_hasher(settings: SettingsDep) -> PasswordHasher:
    return PasswordHasher(rounds=settings.bcrypt_rounds)


def get_token_service(settings: SettingsDep) -> TokenService:
    return TokenService(settings)


PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


async def get_tenant_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    tokens: TokenServiceDep,
) -> TenantContext:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Credenciais ausentes")

    try:
        claims = tokens.decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AuthenticationError("Token inválido ou expirado") from exc

    return TenantContext(
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        role=claims.role,
        flags=claims.flags,
    )


TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]


def require_role(*roles: str) -> Callable[[TenantContext], TenantContext]:
    """Guard de papel. `require_role("admin", "rh")` deixa passar só esses dois."""
    allowed = frozenset(roles)

    def _guard(tenant: TenantDep) -> TenantContext:
        if not tenant.has_role(*allowed):
            raise AuthorizationError(
                "Papel sem permissão para esta ação",
                details={"required_roles": sorted(allowed), "role": tenant.role},
            )
        return tenant

    return _guard


def require_flag(*flags: str, require_all: bool = True) -> Callable[[TenantContext], TenantContext]:
    """Guard de capacidade (BR-MIGRAR-013: flag ausente vale `false`).

    `admin` não recebe passe livre aqui de propósito: se um admin precisa da capacidade,
    ela é concedida no perfil dele, e a permissão continua auditável em um lugar só.
    """
    required = frozenset(flags)

    def _guard(tenant: TenantDep) -> TenantContext:
        granted = required & tenant.flags
        ok = granted == required if require_all else bool(granted)
        if not ok:
            raise AuthorizationError(
                "Capacidade não habilitada para este usuário",
                details={"required_flags": sorted(required), "missing": sorted(required - granted)},
            )
        return tenant

    return _guard


def client_ip(request: Request) -> str:
    """IP real atrás do Nginx. Só o primeiro salto do X-Forwarded-For é confiável,
    e apenas porque o proxy da nossa VPS reescreve o header (AD-06)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
