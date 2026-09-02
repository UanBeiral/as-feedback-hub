"""Transactional outbox — PAR-07 / AD-04 / AMB-006.

O que estes testes prendem é o contrato que o worker vai depender: idempotência no
enfileiramento, backoff crescente com teto, e DLQ no limite de tentativas sem levar
junto a operação que originou a mensagem.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from app.contexts.engagement.models import OutboxMessage
from app.contexts.engagement.repository import backoff_exponencial
from app.contexts.engagement.service import (
    MAX_TENTATIVAS,
    OutboxService,
    PlatformUpdateService,
)
from app.core.errors import ConflictError, NotFoundError
from app.core.tenancy import TenantContext


class FakeOutboxRepository:
    """Reproduz o UNIQUE (topic, idempotency_key) do banco."""

    def __init__(self) -> None:
        self.mensagens: list[dict[str, Any]] = []
        self._chaves: set[tuple[str, str]] = set()

    async def enqueue(self, *, topic: str, payload: dict[str, Any], idempotency_key: str) -> bool:
        if (topic, idempotency_key) in self._chaves:
            return False
        self._chaves.add((topic, idempotency_key))
        self.mensagens.append(
            {"topic": topic, "payload": payload, "idempotency_key": idempotency_key}
        )
        return True


class FakePlatformUpdateRepository:
    def __init__(self, comunicado: Any = None) -> None:
        self.comunicado = comunicado
        self.adicionados: list[Any] = []

    async def get(self, update_id: Any) -> Any:
        if self.comunicado is not None and self.comunicado.id == update_id:
            return self.comunicado
        return None

    def add(self, entidade: Any) -> Any:
        self.adicionados.append(entidade)
        return entidade


def _contexto(role: str = "admin") -> TenantContext:
    return TenantContext(tenant_id=uuid4(), user_id=uuid4(), role=role, flags=frozenset())


def _mensagem() -> OutboxMessage:
    return OutboxMessage(
        tenant_id=uuid4(),
        topic="platform_update.published",
        payload={},
        idempotency_key="k",
        status="pending",
        attempts=0,
    )


async def test_enfileirar_a_mesma_chave_duas_vezes_grava_uma(  ) -> None:
    """BR-MIGRAR-024: idempotência por `update_id + user_id`."""
    repo = FakeOutboxRepository()
    service = OutboxService(repo)  # type: ignore[arg-type]

    primeira = await service.enqueue(topic="t", payload={"a": 1}, idempotency_key="u1:p1")
    segunda = await service.enqueue(topic="t", payload={"a": 1}, idempotency_key="u1:p1")

    assert primeira is True
    assert segunda is False
    assert len(repo.mensagens) == 1


async def test_chaves_diferentes_no_mesmo_topico_convivem() -> None:
    repo = FakeOutboxRepository()
    service = OutboxService(repo)  # type: ignore[arg-type]

    await service.enqueue(topic="t", payload={}, idempotency_key="u1:p1")
    await service.enqueue(topic="t", payload={}, idempotency_key="u1:p2")

    assert len(repo.mensagens) == 2


def test_despacho_bem_sucedido_limpa_reagendamento() -> None:
    msg = _mensagem()
    msg.next_attempt_at = datetime.now(UTC)
    msg.last_error = "erro anterior"

    OutboxService.mark_dispatched(msg)

    assert msg.status == "dispatched"
    assert msg.next_attempt_at is None
    assert msg.last_error is None


def test_falha_reagenda_com_backoff_e_guarda_o_motivo() -> None:
    msg = _mensagem()
    antes = datetime.now(UTC)

    OutboxService.mark_failed(msg, "provedor de email fora do ar")

    assert msg.status == "failed"
    assert msg.attempts == 1
    assert msg.last_error == "provedor de email fora do ar"
    assert msg.next_attempt_at is not None and msg.next_attempt_at > antes


def test_mensagem_vai_para_a_dlq_no_limite_de_tentativas() -> None:
    """PAR-07: no limite, `dead` — sem bloquear as demais e sem tocar na origem."""
    msg = _mensagem()
    for _ in range(MAX_TENTATIVAS):
        OutboxService.mark_failed(msg, "timeout")

    assert msg.status == "dead"
    assert msg.attempts == MAX_TENTATIVAS
    assert msg.next_attempt_at is None, "mensagem morta não é reagendada"


def test_erro_gigante_nao_estoura_a_coluna() -> None:
    msg = _mensagem()
    OutboxService.mark_failed(msg, "x" * 5000)
    assert msg.last_error is not None and len(msg.last_error) == 1000


def test_backoff_cresce_e_para_no_teto() -> None:
    agora = datetime.now(UTC)
    atrasos = [
        (backoff_exponencial(n, base_segundos=60, teto_horas=6) - agora).total_seconds()
        for n in (1, 2, 3, 4)
    ]

    assert atrasos == pytest.approx([60, 120, 240, 480], abs=2)
    # Uma mensagem velha não pode virar uma tentativa por semana.
    teto = (backoff_exponencial(50, base_segundos=60, teto_horas=6) - agora).total_seconds()
    assert teto == pytest.approx(6 * 3600, abs=2)


class _Comunicado:
    def __init__(self) -> None:
        self.id = uuid4()
        self.draft = True
        self.published_at: datetime | None = None
        self.notified_count = 0


async def test_publicar_enfileira_uma_mensagem_por_destinatario() -> None:
    destinatarios = [uuid4(), uuid4(), uuid4()]
    comunicado = _Comunicado()
    outbox = FakeOutboxRepository()
    service = PlatformUpdateService(
        FakePlatformUpdateRepository(comunicado),  # type: ignore[arg-type]
        OutboxService(outbox),  # type: ignore[arg-type]
        destinatarios=destinatarios,
    )

    publicado = await service.publish(comunicado.id)

    assert publicado.draft is False
    assert publicado.published_at is not None
    assert publicado.notified_count == 3
    assert {m["idempotency_key"] for m in outbox.mensagens} == {
        f"{comunicado.id}:{d}" for d in destinatarios
    }


async def test_republicar_nao_gera_segunda_comunicacao() -> None:
    """O guard de `draft` recusa; e mesmo se não recusasse, a chave deduplicaria."""
    comunicado = _Comunicado()
    outbox = FakeOutboxRepository()
    repo = FakePlatformUpdateRepository(comunicado)
    destinatarios = [uuid4()]

    def _service() -> PlatformUpdateService:
        return PlatformUpdateService(
            repo,  # type: ignore[arg-type]
            OutboxService(outbox),  # type: ignore[arg-type]
            destinatarios=destinatarios,
        )

    await _service().publish(comunicado.id)
    with pytest.raises(ConflictError):
        await _service().publish(comunicado.id)

    comunicado.draft = True  # como se alguém tivesse forçado o rascunho de volta
    novamente = await _service().publish(comunicado.id)

    assert len(outbox.mensagens) == 1
    assert novamente.notified_count == 0, "ninguém foi notificado de novo"


async def test_publicar_comunicado_inexistente_e_404() -> None:
    service = PlatformUpdateService(
        FakePlatformUpdateRepository(None),  # type: ignore[arg-type]
        OutboxService(FakeOutboxRepository()),  # type: ignore[arg-type]
        destinatarios=[],
    )
    with pytest.raises(NotFoundError):
        await service.publish(uuid4())


async def test_rascunho_nasce_sem_notificar_ninguem() -> None:
    repo = FakePlatformUpdateRepository()
    outbox = FakeOutboxRepository()
    service = PlatformUpdateService(
        repo,  # type: ignore[arg-type]
        OutboxService(outbox),  # type: ignore[arg-type]
        destinatarios=[uuid4()],
    )

    rascunho = await service.create_draft(_contexto(), title="t", content="c")

    assert rascunho.draft is True
    assert outbox.mensagens == [], "rascunho não comunica nada"


def test_reagendamento_respeita_o_relogio() -> None:
    """Sanidade do cálculo: a próxima tentativa é sempre no futuro."""
    msg = _mensagem()
    OutboxService.mark_failed(msg, "erro")
    assert msg.next_attempt_at is not None
    assert msg.next_attempt_at - datetime.now(UTC) > timedelta(seconds=30)
