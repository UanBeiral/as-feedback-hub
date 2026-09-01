"""Isolamento multi-tenant (AD-10, R-09).

O legado usava RLS do Supabase; aqui o isolamento vive na camada de repositório. A
escolha tem uma consequência prática: se um repositório esquecer o `tenant_id`, o banco
não segura — nada impede a query de atravessar tenants. Por isso o filtro não é
convenção, é herança: `TenantScopedRepository` monta toda consulta a partir de
`_scoped()`, que já nasce com o `WHERE tenant_id = :tenant`. Repositório de domínio que
escreva `select(Model)` direto está errado, e o teste de isolamento em
`tests/test_tenant_isolation.py` existe para provar isso no CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Quem está pedindo, por qual tenant, com que poderes.

    Resolvido uma vez por requisição pela cadeia de dependencies e repassado adiante:
    nenhum service ou repositório lê o token de novo.
    """

    tenant_id: UUID
    user_id: UUID
    role: str
    flags: frozenset[str]

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def has_role(self, *roles: str) -> bool:
        return self.role in roles


class TenantScopedRepository[TModel: Base]:
    """Base de todo repositório de domínio.

    Subclasses declaram `model` e usam `_scoped()` como ponto de partida obrigatório.
    """

    model: type[TModel]

    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self._session = session
        self._tenant = tenant

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Falha no import, não em produção: um repositório sem `model` ou com um
        # modelo sem `tenant_id` não tem como ser isolado.
        model = getattr(cls, "model", None)
        if model is None:
            raise TypeError(f"{cls.__name__} precisa declarar `model`")
        if not hasattr(model, "tenant_id"):
            raise TypeError(
                f"{cls.__name__}.model ({model.__name__}) não tem `tenant_id`; "
                "tabelas sem tenant não usam TenantScopedRepository"
            )

    @property
    def tenant_id(self) -> UUID:
        return self._tenant.tenant_id

    def _scoped(self) -> Select[tuple[TModel]]:
        return select(self.model).where(self.model.tenant_id == self._tenant.tenant_id)

    async def get(self, entity_id: UUID) -> TModel | None:
        result = await self._session.execute(self._scoped().where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[TModel]:
        result = await self._session.execute(self._scoped().limit(limit).offset(offset))
        return list(result.scalars().all())

    def add(self, entity: TModel) -> TModel:
        """Carimba o tenant na entidade: quem chama não decide o tenant_id."""
        entity.tenant_id = self._tenant.tenant_id
        self._session.add(entity)
        return entity
