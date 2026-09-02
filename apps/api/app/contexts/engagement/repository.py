"""Repositórios do contexto `engagement`.

Todos herdam `TenantScopedRepository`: nenhuma consulta aqui nasce sem `tenant_id`
(AD-10). A única query que atravessa tenants é a varredura do worker por mensagens
pendentes, e ela vive em `OutboxDispatchRepository` — fora da hierarquia escopada, com
justificativa registrada no teste de isolamento.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.engagement.models import (
    AuditLog,
    ContactMessage,
    Notification,
    OutboxMessage,
    PlatformUpdate,
    TenantSetting,
)
from app.core.tenancy import TenantScopedRepository


class NotificationRepository(TenantScopedRepository[Notification]):
    model = Notification

    async def list_for_user(
        self, user_id: UUID, *, apenas_nao_lidas: bool = False, limit: int = 50
    ) -> list[Notification]:
        stmt = self._scoped().where(Notification.user_id == user_id)
        if apenas_nao_lidas:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_unread(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> int:
        """Marca uma notificação do próprio usuário. Devolve quantas linhas mudaram.

        O `user_id` entra no WHERE, e não numa checagem prévia: assim ninguém marca
        como lida a notificação de outra pessoa, nem por bug nem por id adivinhado —
        e o escopo é aplicado pelo banco, não pela boa memória de quem escreve o service.
        """
        result = await self._session.execute(
            update(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.id == notification_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        return int(result.rowcount or 0)

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(Notification)
            .where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        return int(result.rowcount or 0)


class OutboxRepository(TenantScopedRepository[OutboxMessage]):
    model = OutboxMessage

    async def enqueue(
        self, *, topic: str, payload: dict[str, Any], idempotency_key: str
    ) -> bool:
        """Grava a intenção de efeito auxiliar na transação em curso (AD-04).

        `ON CONFLICT DO NOTHING` sobre `(topic, idempotency_key)` é o que torna o
        enfileiramento idempotente (BR-MIGRAR-024): reexecutar o comando de origem não
        gera segunda cópia da mesma comunicação. Devolve `False` quando a mensagem já
        existia — informação útil para quem quer contar o que realmente foi criado.

        Não faz commit: quem decide isso é a transação da requisição, e é exatamente
        essa amarração que dá a garantia do outbox.
        """
        stmt = (
            pg_insert(OutboxMessage)
            .values(
                tenant_id=self.tenant_id,
                topic=topic,
                payload=payload,
                idempotency_key=idempotency_key,
                status="pending",
                attempts=0,
                next_attempt_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(constraint="uq_outbox_messages_idempotencia")
            .returning(OutboxMessage.id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_by_status(self, status: str, *, limit: int = 100) -> list[OutboxMessage]:
        stmt = (
            self._scoped()
            .where(OutboxMessage.status == status)
            .order_by(OutboxMessage.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class OutboxDispatchRepository:
    """Lado do worker: varre e despacha, sem contexto de tenant.

    É a segunda exceção legítima ao isolamento por herança, e pelo mesmo motivo do
    `AuthRepository`: o worker não roda dentro de uma sessão de usuário — ele processa
    a fila de todos os tenants. O `tenant_id` viaja **dentro** da mensagem e é aplicado
    por quem consome, não perdido.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_batch(self, *, limit: int = 20) -> list[OutboxMessage]:
        """Reserva um lote de mensagens prontas para despacho.

        `FOR UPDATE SKIP LOCKED` é o que permite mais de um worker sem coordenação
        externa: cada um leva mensagens diferentes, ninguém espera pelo outro, e uma
        mensagem travada por um worker que morreu volta a ficar disponível quando a
        transação dele cai.
        """
        stmt = (
            select(OutboxMessage)
            .where(
                OutboxMessage.status.in_(("pending", "failed")),
                OutboxMessage.next_attempt_at <= datetime.now(UTC),
            )
            .order_by(OutboxMessage.next_attempt_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class AuditLogRepository(TenantScopedRepository[AuditLog]):
    model = AuditLog

    async def record(
        self,
        *,
        actor_id: UUID | None,
        action: str,
        table_name: str | None = None,
        record_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append-only: só existe inserção, de propósito. Sem update, sem delete."""
        await self._session.execute(
            insert(AuditLog).values(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                details=details,
            )
        )

    async def list_recent(self, *, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        stmt = (
            self._scoped()
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class TenantSettingRepository(TenantScopedRepository[TenantSetting]):
    model = TenantSetting

    async def list_all_settings(self) -> list[TenantSetting]:
        return list((await self._session.execute(self._scoped())).scalars().all())

    async def get_by_key(self, key: str) -> TenantSetting | None:
        stmt = self._scoped().where(TenantSetting.key == key)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert(
        self, *, key: str, value: str | None, updated_by: UUID, expected_updated_at: datetime | None
    ) -> bool:
        """Upsert por chave com concorrência otimista (BR-MIGRAR-027).

        `expected_updated_at` é o carimbo que o cliente leu antes de editar. Se outra
        pessoa salvou a mesma chave nesse meio-tempo, o UPDATE não encontra linha e
        devolvemos `False` — melhor recusar do que sobrescrever em silêncio a mudança
        de alguém, que é o que o legado fazia.

        `None` significa "não existia quando li": vira INSERT, e o conflito de chave
        única resolve a corrida entre dois criadores simultâneos.
        """
        if expected_updated_at is None:
            stmt = (
                pg_insert(TenantSetting)
                .values(
                    tenant_id=self.tenant_id, key=key, value=value, updated_by=updated_by
                )
                .on_conflict_do_nothing(constraint="uq_tenant_settings_chave")
                .returning(TenantSetting.id)
            )
            return (await self._session.execute(stmt)).scalar_one_or_none() is not None

        result = await self._session.execute(
            update(TenantSetting)
            .where(
                TenantSetting.tenant_id == self.tenant_id,
                TenantSetting.key == key,
                TenantSetting.updated_at == expected_updated_at,
            )
            .values(value=value, updated_by=updated_by, updated_at=datetime.now(UTC))
        )
        return bool(result.rowcount)


class PlatformUpdateRepository(TenantScopedRepository[PlatformUpdate]):
    model = PlatformUpdate

    async def list_published(self, *, limit: int = 50) -> list[PlatformUpdate]:
        stmt = (
            self._scoped()
            .where(PlatformUpdate.draft.is_(False))
            .order_by(PlatformUpdate.published_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_all(self, *, limit: int = 50) -> list[PlatformUpdate]:
        stmt = self._scoped().order_by(PlatformUpdate.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())


class ContactMessageRepository(TenantScopedRepository[ContactMessage]):
    model = ContactMessage

    async def list_by_status(
        self, status: str | None = None, *, limit: int = 100
    ) -> list[ContactMessage]:
        stmt = self._scoped()
        if status is not None:
            stmt = stmt.where(ContactMessage.status == status)
        stmt = stmt.order_by(ContactMessage.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())


def backoff_exponencial(attempts: int, *, base_segundos: int = 60, teto_horas: int = 6) -> datetime:
    """Próxima tentativa: 1min, 2min, 4min, 8min… até o teto (AMB-006).

    O teto existe para uma mensagem velha não virar uma tentativa por semana; e o
    crescimento exponencial, para uma indisponibilidade de provedor não virar tempestade
    de retry em cima de quem já está caído.
    """
    atraso = min(base_segundos * (2**max(attempts - 1, 0)), teto_horas * 3600)
    return datetime.now(UTC) + timedelta(seconds=atraso)
