"""Configurações, notificações, auditoria e "Fale Conosco" — BR-MIGRAR-023/026/027."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.engagement.models import SETTINGS_CATALOG
from app.contexts.engagement.service import (
    AuditService,
    ContactMessageService,
    NotificationService,
    SettingsService,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.tenancy import TenantContext


def _contexto(role: str = "admin") -> TenantContext:
    return TenantContext(tenant_id=uuid4(), user_id=uuid4(), role=role, flags=frozenset())


# ------------------------------------------------------------------ settings


class _Setting:
    def __init__(self, key: str, value: str | None, updated_by: UUID, updated_at: datetime):
        self.key = key
        self.value = value
        self.updated_by = updated_by
        self.updated_at = updated_at


class FakeSettingRepository:
    def __init__(self, gravadas: list[_Setting] | None = None) -> None:
        self.gravadas = gravadas or []

    async def list_all_settings(self) -> list[_Setting]:
        return list(self.gravadas)

    async def upsert(
        self,
        *,
        key: str,
        value: str | None,
        updated_by: UUID,
        expected_updated_at: datetime | None,
    ) -> bool:
        atual = next((s for s in self.gravadas if s.key == key), None)
        if expected_updated_at is None:
            if atual is not None:
                return False  # já existe: quem achou que criava, perdeu a corrida
            self.gravadas.append(_Setting(key, value, updated_by, datetime.now(UTC)))
            return True
        if atual is None or atual.updated_at != expected_updated_at:
            return False
        atual.value = value
        atual.updated_by = updated_by
        atual.updated_at = datetime.now(UTC)
        return True


async def test_catalogo_devolve_as_oito_chaves_mesmo_sem_nada_gravado() -> None:
    catalogo = await SettingsService(FakeSettingRepository()).list_catalog()  # type: ignore[arg-type]

    assert {s.key for s in catalogo} == set(SETTINGS_CATALOG)
    assert all(not s.persisted for s in catalogo)


async def test_toggles_nascem_desligados() -> None:
    """Deny-by-default também vale para configuração global."""
    catalogo = {s.key: s for s in await SettingsService(FakeSettingRepository()).list_catalog()}  # type: ignore[arg-type]

    for toggle in (
        "gestor_can_access_reports",
        "gestor_can_access_agenda",
        "colaborador_can_generate_own_report",
    ):
        assert catalogo[toggle].value == "false"


async def test_valor_gravado_vence_o_default_e_e_marcado_como_persistido() -> None:
    agora = datetime.now(UTC)
    repo = FakeSettingRepository([_Setting("company_name", "A&S", uuid4(), agora)])

    catalogo = {s.key: s for s in await SettingsService(repo).list_catalog()}  # type: ignore[arg-type]

    assert catalogo["company_name"].value == "A&S"
    assert catalogo["company_name"].persisted is True
    assert catalogo["logo_url"].persisted is False


async def test_chave_fora_do_catalogo_e_recusada() -> None:
    service = SettingsService(FakeSettingRepository())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        await service.upsert(
            _contexto(), key="chave_inventada", value="x", expected_updated_at=None
        )


async def test_edicao_concorrente_e_recusada_em_vez_de_sobrescrever() -> None:
    """BR-MIGRAR-027: upsert com concorrência otimista.

    Duas pessoas abrem a mesma configuração; a segunda a salvar está trabalhando em
    cima de um valor que já não existe. Recusar é o comportamento certo — sobrescrever
    em silêncio é o que o legado fazia.
    """
    agora = datetime.now(UTC)
    repo = FakeSettingRepository([_Setting("company_name", "A&S", uuid4(), agora)])
    service = SettingsService(repo)  # type: ignore[arg-type]

    await service.upsert(
        _contexto(), key="company_name", value="A&S Advogados", expected_updated_at=agora
    )

    with pytest.raises(ConflictError):
        await service.upsert(
            _contexto(), key="company_name", value="Outro nome", expected_updated_at=agora
        )
    assert repo.gravadas[0].value == "A&S Advogados"


async def test_criar_chave_que_ja_existe_tambem_conflita() -> None:
    repo = FakeSettingRepository([_Setting("logo_url", "a.png", uuid4(), datetime.now(UTC))])
    with pytest.raises(ConflictError):
        await SettingsService(repo).upsert(  # type: ignore[arg-type]
            _contexto(), key="logo_url", value="b.png", expected_updated_at=None
        )


async def test_quem_salvou_fica_registrado() -> None:
    repo = FakeSettingRepository()
    tenant = _contexto()

    await SettingsService(repo).upsert(  # type: ignore[arg-type]
        tenant, key="company_name", value="A&S", expected_updated_at=None
    )

    assert repo.gravadas[0].updated_by == tenant.user_id


# ------------------------------------------------------------- notificações


class _Notificacao:
    def __init__(self, user_id: UUID) -> None:
        self.id = uuid4()
        self.user_id = user_id
        self.type = "cycle_opened"
        self.title = "Novo ciclo aberto"
        self.message: str | None = None
        self.link: str | None = None
        self.read_at: datetime | None = None
        self.created_at = datetime.now(UTC)


class FakeNotificationRepository:
    def __init__(self, notificacoes: list[_Notificacao]) -> None:
        self.notificacoes = notificacoes

    async def list_for_user(
        self, user_id: UUID, *, apenas_nao_lidas: bool = False, limit: int = 50
    ) -> list[_Notificacao]:
        itens = [n for n in self.notificacoes if n.user_id == user_id]
        if apenas_nao_lidas:
            itens = [n for n in itens if n.read_at is None]
        return itens

    async def count_unread(self, user_id: UUID) -> int:
        return len([n for n in self.notificacoes if n.user_id == user_id and n.read_at is None])

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> int:
        alvo = next(
            (
                n
                for n in self.notificacoes
                if n.id == notification_id and n.user_id == user_id and n.read_at is None
            ),
            None,
        )
        if alvo is None:
            return 0
        alvo.read_at = datetime.now(UTC)
        return 1

    async def mark_all_read(self, user_id: UUID) -> int:
        alvos = [n for n in self.notificacoes if n.user_id == user_id and n.read_at is None]
        for n in alvos:
            n.read_at = datetime.now(UTC)
        return len(alvos)

    async def get(self, notification_id: UUID) -> _Notificacao | None:
        return next((n for n in self.notificacoes if n.id == notification_id), None)


async def test_marcar_como_lida_derruba_a_contagem_do_sino() -> None:
    tenant = _contexto("colaborador")
    minhas = [_Notificacao(tenant.user_id), _Notificacao(tenant.user_id)]
    service = NotificationService(FakeNotificationRepository(minhas))  # type: ignore[arg-type]

    assert (await service.feed(tenant)).unread_count == 2
    await service.mark_read(tenant, minhas[0].id)
    assert (await service.feed(tenant)).unread_count == 1


async def test_marcar_de_novo_o_que_ja_estava_lido_nao_e_erro() -> None:
    tenant = _contexto("colaborador")
    minha = _Notificacao(tenant.user_id)
    service = NotificationService(FakeNotificationRepository([minha]))  # type: ignore[arg-type]

    await service.mark_read(tenant, minha.id)
    await service.mark_read(tenant, minha.id)  # idempotente


async def test_notificacao_de_outra_pessoa_nao_pode_ser_marcada() -> None:
    tenant = _contexto("colaborador")
    alheia = _Notificacao(uuid4())
    service = NotificationService(FakeNotificationRepository([alheia]))  # type: ignore[arg-type]

    with pytest.raises(NotFoundError):
        await service.mark_read(tenant, alheia.id)
    assert alheia.read_at is None


async def test_ler_todas_zera_a_contagem() -> None:
    tenant = _contexto("colaborador")
    minhas = [_Notificacao(tenant.user_id) for _ in range(3)]
    service = NotificationService(FakeNotificationRepository(minhas))  # type: ignore[arg-type]

    assert await service.mark_all_read(tenant) == 3
    assert (await service.feed(tenant)).unread_count == 0


# ---------------------------------------------------------------- auditoria


class FakeAuditRepository:
    def __init__(self) -> None:
        self.linhas: list[dict[str, Any]] = []

    async def record(self, **campos: Any) -> None:
        self.linhas.append(campos)


class FakeOutbox:
    def __init__(self) -> None:
        self.chaves: list[str] = []

    async def enqueue(self, *, topic: str, payload: dict, idempotency_key: str) -> bool:
        self.chaves.append(idempotency_key)
        return True


async def test_auditoria_registra_o_ator_nao_o_alvo() -> None:
    """BR-MIGRAR-026: `actor_id` é quem fez, não quem sofreu."""
    tenant = _contexto()
    alvo = uuid4()
    audit = FakeAuditRepository()

    await AuditService(audit, FakeOutbox()).record(  # type: ignore[arg-type]
        tenant, action="member.removed", table_name="profiles", record_id=alvo
    )

    assert audit.linhas[0]["actor_id"] == tenant.user_id
    assert audit.linhas[0]["record_id"] == alvo


async def test_auditoria_enfileira_notificacao_por_envolvido() -> None:
    tenant = _contexto()
    envolvidos = [uuid4(), uuid4()]
    outbox = FakeOutbox()

    await AuditService(FakeAuditRepository(), outbox).record(  # type: ignore[arg-type]
        tenant, action="member.removed", record_id=uuid4(), notificar=envolvidos
    )

    assert len(outbox.chaves) == 2


async def test_auditoria_sem_envolvidos_nao_enfileira_nada() -> None:
    outbox = FakeOutbox()
    await AuditService(FakeAuditRepository(), outbox).record(  # type: ignore[arg-type]
        _contexto(), action="settings.updated"
    )
    assert outbox.chaves == []


# --------------------------------------------------------------- fale conosco


class _Contato:
    def __init__(self, status: str = "novo") -> None:
        self.id = uuid4()
        self.status = status


class FakeContactRepository:
    def __init__(self, mensagem: _Contato | None = None) -> None:
        self.mensagem = mensagem
        self.adicionadas: list[Any] = []

    async def get(self, message_id: UUID) -> _Contato | None:
        if self.mensagem is not None and self.mensagem.id == message_id:
            return self.mensagem
        return None

    def add(self, entidade: Any) -> Any:
        self.adicionadas.append(entidade)
        return entidade


@pytest.mark.parametrize(
    "de,para",
    [("novo", "em_andamento"), ("novo", "resolvido"), ("em_andamento", "resolvido")],
)
async def test_transicoes_permitidas(de: str, para: str) -> None:
    mensagem = _Contato(de)
    service = ContactMessageService(FakeContactRepository(mensagem))  # type: ignore[arg-type]

    assert (await service.change_status(mensagem.id, novo_status=para)).status == para


@pytest.mark.parametrize(
    "de,para",
    [
        ("resolvido", "novo"),
        ("resolvido", "em_andamento"),
        ("em_andamento", "novo"),
        ("novo", "arquivado"),
    ],
)
async def test_transicoes_nao_confirmadas_sao_recusadas(de: str, para: str) -> None:
    """O modelo não inventa estados nem caminhos que ninguém verificou no legado."""
    mensagem = _Contato(de)
    service = ContactMessageService(FakeContactRepository(mensagem))  # type: ignore[arg-type]

    with pytest.raises(ConflictError):
        await service.change_status(mensagem.id, novo_status=para)
    assert mensagem.status == de


async def test_mudar_status_de_mensagem_inexistente_e_404() -> None:
    service = ContactMessageService(FakeContactRepository())  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        await service.change_status(uuid4(), novo_status="resolvido")


async def test_contato_registra_quem_abriu() -> None:
    tenant = _contexto("colaborador")
    repo = FakeContactRepository()

    mensagem = await ContactMessageService(repo).create(  # type: ignore[arg-type]
        tenant,
        type="sugestao",
        contact_name="Fulano",
        email="fulano@exemplo.com",
        message="Ideia",
        company=None,
        phone=None,
    )

    assert mensagem.created_by == tenant.user_id
    assert repo.adicionadas == [mensagem]


def test_janela_de_retry_e_coerente_com_o_teto() -> None:
    """Sanidade da constante: o backoff completo cabe em algumas horas, não em dias."""
    from app.contexts.engagement.repository import backoff_exponencial
    from app.contexts.engagement.service import MAX_TENTATIVAS

    agora = datetime.now(UTC)
    total = sum(
        (backoff_exponencial(n) - agora).total_seconds() for n in range(1, MAX_TENTATIVAS)
    )
    assert timedelta(minutes=10) < timedelta(seconds=total) < timedelta(hours=4)
