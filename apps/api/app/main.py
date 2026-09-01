"""Composição da aplicação FastAPI.

Este arquivo só monta peças: configuração, middlewares, tradução de erros e routers.
Toda decisão de negócio está nos contexts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.contexts.identity.router import router as identity_router
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.errors import DomainError, domain_error_handler


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="A&S Feedback Hub API",
        version="0.1.0",
        description="API multi-tenant de feedback 360 e avaliação de clientes.",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Um handler para toda a família de erros de domínio: services levantam exceções
    # de negócio e nunca precisam conhecer status HTTP.
    app.add_exception_handler(DomainError, domain_error_handler)

    app.include_router(identity_router, prefix="/api/v1")

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
