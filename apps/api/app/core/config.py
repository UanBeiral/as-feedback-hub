"""Configuração da API.

Fonte única de verdade para variáveis de ambiente. Segredo sem default: a aplicação
falha ao subir em vez de rodar com credencial fraca.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    debug: bool = False

    # Banco
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/asfeedback"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Fila / cache
    redis_url: str = "redis://localhost:6379/0"

    # Tenancy. O primeiro corte da migração roda com um tenant só (o cliente atual),
    # então o login aceita e-mail sem qualificar o tenant. Quando entrar o segundo
    # cliente, a resolução passa a vir do subdomínio e este default sai de cena.
    default_tenant_slug: str = "as"

    # Auth — AD-03: JWT curto + refresh rotativo
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    bcrypt_rounds: int = 12

    # Email — BR-MIGRAR-030 / R-11 (provider trocável por env)
    email_provider: str = "console"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "nao-responda@exemplo.com"

    # Worker (AD-04/AD-05). O intervalo só vale para fila vazia: com trabalho, os
    # lotes se emendam sem espera.
    worker_poll_seconds: int = 5
    worker_batch_size: int = 20

    # Web
    cors_origins: str = "http://localhost:3000"
    public_base_url: str = "http://localhost:3000"

    @field_validator("bcrypt_rounds")
    @classmethod
    def _rounds_sane(cls, v: int) -> int:
        # Abaixo de 10 é fraco; acima de 15 o login fica lento demais para uso interativo.
        if not 10 <= v <= 15:
            raise ValueError("bcrypt_rounds deve estar entre 10 e 15")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
