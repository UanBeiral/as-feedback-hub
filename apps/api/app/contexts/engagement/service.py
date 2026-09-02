"""Casos de uso do contexto `engagement`.

O contrato que atravessa este arquivo é BR-MIGRAR-025: **falha de efeito auxiliar não
desfaz a operação principal**. Ele se materializa em uma regra simples de seguir e fácil
de quebrar sem perceber — nenhum service daqui fala com provedor externo. O que eles
fazem é gravar a *intenção* (`OutboxService.enqueue`) na mesma transação do comando de
origem. Quem fala com o mundo é o worker, depois do commit, e o pior que pode acontecer
lá é a mensagem ir para a DLQ com a operação de origem intacta.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.contexts.engagement.models import (
    SETTINGS_CATALOG,
    ContactMessage,
    OutboxMessage,
    PlatformUpdate,
)
from app.contexts.engagement.repository import (
    AuditLogRepository,
    ContactMessageRepository,
    NotificationRepository,
    OutboxRepository,
    PlatformUpdateRepository,
    TenantSettingRepository,
    backoff_exponencial,
)
from app.contexts.engagement.schemas import (
    NotificationFeed,
    NotificationOut,
    SettingOut,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.tenancy import TenantContext

# Tentativas antes da DLQ (AMB-006). Com o backoff de `backoff_exponencial`, cinco
# tentativas cobrem ~2h de indisponibilidade do provedor antes de desistir — tempo de
# sobra para uma queda comum, curto o bastante para o problema aparecer no mesmo dia.
MAX_TENTATIVAS = 5

# Transições confirmadas do "Fale Conosco". Reabrir um chamado resolvido não está no
# legado, então não inventamos: quem precisar, abre outro.
TRANSICOES_CONTATO: dict[str, frozenset[str]] = {
    "novo": frozenset({"em_andamento", "resolvido"}),
    "em_andamento": frozenset({"resolvido"}),
    "resolvido": frozenset(),
}


class OutboxService:
    """Escrita e ciclo de vida das mensagens de efeito auxiliar (AD-04)."""

    def __init__(self, outbox: OutboxRepository) -> None:
        self._outbox = outbox

    async def enqueue(
        self, *, topic: str, payload: dict[str, Any], idempotency_key: str
    ) -> bool:
        """Enfileira dentro da transação em curso. `False` = já existia."""
        return await self._outbox.enqueue(
            topic=topic, payload=payload, idempotency_key=idempotency_key
        )

    @staticmethod
    def mark_dispatched(mensagem: OutboxMessage) -> None:
        """Sucesso de despacho.

        Chamado pelo worker **na mesma transação** em que o efeito é aplicado. É isso
        que dá a exatamente-uma-vez de PAR-07: se o worker morre depois de criar a
        notificação e antes de marcar, as duas coisas caem juntas e a mensagem volta
        para a fila intacta.
        """
        mensagem.status = "dispatched"
        mensagem.next_attempt_at = None
        mensagem.last_error = None

    @staticmethod
    def mark_failed(mensagem: OutboxMessage, erro: str) -> None:
        """Falha de despacho: reagenda com backoff, ou manda para a DLQ no limite.

        `dead` não é um erro pior que `failed` — é o reconhecimento de que insistir
        parou de fazer sentido. A mensagem fica no banco, com o motivo, sem bloquear
        as outras (PAR-07 § "Retry com backoff e DLQ").
        """
        mensagem.attempts += 1
        mensagem.last_error = erro[:1000]
        if mensagem.attempts >= MAX_TENTATIVAS:
            mensagem.status = "dead"
            mensagem.next_attempt_at = None
        else:
            mensagem.status = "failed"
            mensagem.next_attempt_at = backoff_exponencial(mensagem.attempts)


class NotificationService:
    def __init__(self, notifications: NotificationRepository) -> None:
        self._notifications = notifications

    async def feed(
        self, tenant: TenantContext, *, apenas_nao_lidas: bool = False
    ) -> NotificationFeed:
        itens = await self._notifications.list_for_user(
            tenant.user_id, apenas_nao_lidas=apenas_nao_lidas
        )
        return NotificationFeed(
            items=[NotificationOut.model_validate(n) for n in itens],
            unread_count=await self._notifications.count_unread(tenant.user_id),
        )

    async def mark_read(self, tenant: TenantContext, notification_id: UUID) -> None:
        """Idempotente: marcar de novo o que já estava lido não é erro.

        Mas notificação de outra pessoa (ou de outro tenant) também não encontra linha,
        e aí precisamos distinguir. A diferença é feita com uma leitura extra, só no
        caminho em que o UPDATE não achou nada — o caminho comum continua com uma query.
        """
        if await self._notifications.mark_read(tenant.user_id, notification_id):
            return

        existente = await self._notifications.get(notification_id)
        if existente is None or existente.user_id != tenant.user_id:
            raise NotFoundError("Notificação não encontrada")

    async def mark_all_read(self, tenant: TenantContext) -> int:
        return await self._notifications.mark_all_read(tenant.user_id)


class AuditService:
    """Registro de ações sensíveis (BR-MIGRAR-026).

    A spec descreve a auditoria como evento pós-commit via outbox. Aqui ela é escrita
    direto, na transação do comando — e a diferença é menor do que parece: a mensagem
    de outbox *também* seria um INSERT na mesma transação, com o mesmo perfil de falha.
    O que o outbox protege é a chamada externa (email, push), não uma escrita no nosso
    próprio banco. Gravar direto dá auditoria imediatamente legível na tela de
    Auditoria, em vez de depender do worker estar de pé. Ver `docs/spec-deviations.md`.
    """

    def __init__(self, audit: AuditLogRepository, outbox: OutboxService) -> None:
        self._audit = audit
        self._outbox = outbox

    async def record(
        self,
        tenant: TenantContext,
        *,
        action: str,
        table_name: str | None = None,
        record_id: UUID | None = None,
        details: dict[str, Any] | None = None,
        notificar: list[UUID] | None = None,
    ) -> None:
        await self._audit.record(
            actor_id=tenant.user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            details=details,
        )
        # "…e tenta notificar envolvidos" (BR-MIGRAR-026). Tenta é a palavra certa: a
        # notificação vira mensagem de outbox e a auditoria não depende do sucesso dela.
        for destinatario in notificar or []:
            await self._outbox.enqueue(
                topic=f"audit.{action}",
                payload={"action": action, "record_id": str(record_id) if record_id else None},
                idempotency_key=f"{action}:{record_id}:{destinatario}",
            )


class SettingsService:
    """Configurações do tenant (BR-MIGRAR-027)."""

    def __init__(self, settings: TenantSettingRepository) -> None:
        self._settings = settings

    async def list_catalog(self) -> list[SettingOut]:
        """As oito chaves, sempre — as gravadas e as que ainda têm o default.

        Devolver só o que existe no banco empurraria o catálogo para dentro do front,
        e a próxima chave nova apareceria em uma tela e não na outra.
        """
        gravadas = {s.key: s for s in await self._settings.list_all_settings()}
        catalogo: list[SettingOut] = []
        for key, default in SETTINGS_CATALOG.items():
            atual = gravadas.get(key)
            catalogo.append(
                SettingOut(
                    key=key,
                    value=atual.value if atual else default,
                    updated_at=atual.updated_at if atual else None,
                    updated_by=atual.updated_by if atual else None,
                    persisted=atual is not None,
                )
            )
        return catalogo

    async def upsert(
        self,
        tenant: TenantContext,
        *,
        key: str,
        value: str | None,
        expected_updated_at: datetime | None,
    ) -> None:
        if key not in SETTINGS_CATALOG:
            raise ValidationError(
                "Chave de configuração fora do catálogo",
                details={"key": key, "catalogo": sorted(SETTINGS_CATALOG)},
            )

        aplicado = await self._settings.upsert(
            key=key,
            value=value,
            updated_by=tenant.user_id,
            expected_updated_at=expected_updated_at,
        )
        if not aplicado:
            raise ConflictError(
                "A configuração mudou desde que você a abriu. Recarregue e revise.",
                details={"key": key},
            )


class PlatformUpdateService:
    def __init__(
        self,
        updates: PlatformUpdateRepository,
        outbox: OutboxService,
        destinatarios: list[UUID],
    ) -> None:
        self._updates = updates
        self._outbox = outbox
        self._destinatarios = destinatarios

    async def create_draft(
        self, tenant: TenantContext, *, title: str, content: str
    ) -> PlatformUpdate:
        comunicado = PlatformUpdate(
            title=title, content=content, created_by=tenant.user_id, draft=True
        )
        return self._updates.add(comunicado)

    async def publish(self, update_id: UUID) -> PlatformUpdate:
        """Publica e enfileira uma mensagem por destinatário.

        A chave de idempotência é `update_id:user_id` — a mesma do legado, preservada
        por BR-MIGRAR-024. Republicar por engano não gera segunda comunicação para
        ninguém, e é por isso que `notified_count` conta o que foi realmente
        enfileirado, não o tamanho da lista.
        """
        comunicado = await self._updates.get(update_id)
        if comunicado is None:
            raise NotFoundError("Comunicado não encontrado")
        if not comunicado.draft:
            raise ConflictError("Comunicado já publicado")

        enfileiradas = 0
        for destinatario in self._destinatarios:
            if await self._outbox.enqueue(
                topic="platform_update.published",
                payload={"update_id": str(update_id), "user_id": str(destinatario)},
                idempotency_key=f"{update_id}:{destinatario}",
            ):
                enfileiradas += 1

        comunicado.draft = False
        comunicado.published_at = datetime.now(UTC)
        comunicado.notified_count = enfileiradas
        return comunicado


class ContactMessageService:
    def __init__(self, mensagens: ContactMessageRepository) -> None:
        self._mensagens = mensagens

    async def create(self, tenant: TenantContext, **campos: Any) -> ContactMessage:
        return self._mensagens.add(ContactMessage(created_by=tenant.user_id, **campos))

    async def change_status(self, message_id: UUID, *, novo_status: str) -> ContactMessage:
        mensagem = await self._mensagens.get(message_id)
        if mensagem is None:
            raise NotFoundError("Mensagem não encontrada")

        permitidas = TRANSICOES_CONTATO.get(mensagem.status, frozenset())
        if novo_status not in permitidas:
            raise ConflictError(
                "Transição de status não permitida",
                details={
                    "de": mensagem.status,
                    "para": novo_status,
                    "permitidas": sorted(permitidas),
                },
            )

        mensagem.status = novo_status
        return mensagem
