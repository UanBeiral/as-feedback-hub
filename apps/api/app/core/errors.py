"""Erros de domínio e o tradutor para HTTP.

Services levantam erros de domínio e não sabem o que é um status code. O mapeamento
para HTTP acontece uma vez, no handler registrado em `main.py`.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base de todo erro de regra de negócio."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    """Estado atual do recurso impede a operação (ex.: transição de status inválida)."""

    status_code = 409
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class AuthenticationError(DomainError):
    status_code = 401
    code = "unauthenticated"


class AuthorizationError(DomainError):
    """Autenticado, mas sem poder para esta ação ou fora do escopo (AD-02)."""

    status_code = 403
    code = "forbidden"


class RateLimitError(DomainError):
    status_code = 429
    code = "rate_limited"


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
        headers=headers,
    )
