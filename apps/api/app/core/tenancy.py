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

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base
from app.core.errors import AuthenticationError


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


# Revalidação de sessão a cada requisição (PAR-08 § "Acesso revogado imediatamente").
#
# O access token vale 15 minutos e carrega papel e flags (AD-03). Sem esta consulta,
# um usuário removido continuaria usando a sessão até o token expirar — e PAR-08 marca
# esse cenário como @critico, ou seja, bloqueador de cutover. A troca consciente é uma
# leitura indexada por requisição.
#
# A consulta usa SQL textual de propósito: `core/` não importa modelos de contexto, ou
# a dependência se inverte (`identity` depende de `core`, nunca o contrário). O preço é
# esta única referência a nomes de tabela fora do contexto dono deles.
_SESSAO_ATIVA = text(
    """
    SELECT u.status AS user_status,
           t.status AS tenant_status,
           p.status AS profile_status
      FROM users u
      JOIN tenants t ON t.id = u.tenant_id
      LEFT JOIN profiles p ON p.user_id = u.id
     WHERE u.id = :user_id AND u.tenant_id = :tenant_id
    """
)


async def assert_session_active(session: AsyncSession, *, tenant_id: UUID, user_id: UUID) -> None:
    """Recusa a requisição se usuário, perfil ou tenant deixaram de estar ativos.

    Falha fechada: linha ausente (usuário apagado de verdade, ou perfil nunca criado)
    também nega. A mensagem é a mesma em todos os casos — quem perdeu o acesso não
    precisa saber qual dos três estados mudou.
    """
    row = (
        await session.execute(_SESSAO_ATIVA, {"user_id": user_id, "tenant_id": tenant_id})
    ).mappings().first()

    if row is None or any(
        row[campo] != "active" for campo in ("user_status", "tenant_status", "profile_status")
    ):
        raise AuthenticationError("Sessão encerrada. Entre novamente.")


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

    async def remove(self, entity: TModel) -> None:
        """Remoção física, para o que não tem histórico a preservar.

        Soft-delete é a regra para gente (`profiles.status`, BR-MIGRAR-018); isto serve
        ao que é descartável de verdade — uma anotação pessoal, um rascunho. Se a
        entidade participa de histórico, não é este o método. A checagem de tenant é
        redundante com o `_scoped()` de quem buscou a entidade, e existe porque remoção
        é irreversível: custa uma comparação e fecha o caminho de quem passar um objeto
        vindo de outra consulta.
        """
        if entity.tenant_id != self._tenant.tenant_id:
            raise ValueError("tentativa de remover entidade de outro tenant")
        await self._session.delete(entity)
