"""Cria o tenant inicial e o primeiro admin.

Existe para tornar a fundação exercitável: sem uma conta, não há como testar o login.
NÃO é o script de migração de dados — esse nasce em `deploy/migrate/` depois que o
`pg_dump` de produção responder AMB-010.

Uso:
    PYTHONPATH=apps/api python deploy/seed_tenant.py \
        --slug as --nome "A&S" --email admin@exemplo.com --senha "..."
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import uuid4

from app.contexts.identity.models import Profile, Tenant, User
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.security import PasswordHasher
from sqlalchemy import select


async def seed(slug: str, nome: str, email: str, senha: str) -> int:
    settings = get_settings()
    hasher = PasswordHasher(rounds=settings.bcrypt_rounds)

    async with get_session_factory()() as session:
        existente = await session.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = existente.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=uuid4(), slug=slug, name=nome)
            session.add(tenant)
            await session.flush()
            print(f"tenant criado: {slug} ({tenant.id})")
        else:
            print(f"tenant já existe: {slug} ({tenant.id})")

        ja_tem = await session.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        )
        if ja_tem.scalar_one_or_none() is not None:
            print(f"usuário {email} já existe neste tenant; nada a fazer")
            return 0

        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email=email,
            password_hash=hasher.hash(senha),
        )
        session.add(user)
        await session.flush()

        # O perfil é obrigatório: sem ele o login recusa a sessão, porque papel e
        # capacidades vivem no Profile, não no User. `for_user` garante o id do perfil
        # igual ao do usuário, invariante que o banco cobra com CHECK.
        session.add(Profile.for_user(user, full_name=nome + " — Admin", role="admin"))
        await session.commit()
        print(f"admin criado: {email}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed do tenant inicial")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", required=True)
    args = parser.parse_args()
    return asyncio.run(seed(args.slug, args.nome, args.email, args.senha))


if __name__ == "__main__":
    sys.exit(main())
