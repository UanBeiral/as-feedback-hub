"""Despachante do outbox e scheduler — PAR-07 / AD-04 / AD-05.

A propriedade central é isolamento entre mensagens: uma mensagem que falha não pode
levar junto as outras do lote, nem a marcação do próprio fracasso. Os dublês de sessão
aqui reproduzem o que importa do SQLAlchemy — `begin_nested` como savepoint e o commit
no fim do lote.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.contexts.engagement.models import OutboxMessage
from app.contexts.engagement.service import MAX_TENTATIVAS
from worker.consumers.outbox import despachar_lote
from worker.handlers import RegistroDeHandlers, TopicoSemHandlerError
from worker.jobs.email import (
    ConsoleEmailAdapter,
    ProvedorNaoConfiguradoError,
    build_email_adapter,
)
from worker.scheduler import Scheduler


def _mensagem(topic: str = "platform_update.published", attempts: int = 0) -> OutboxMessage:
    msg = OutboxMessage(
        id=uuid4(),
        tenant_id=uuid4(),
        topic=topic,
        payload={"update_id": str(uuid4()), "user_id": str(uuid4())},
        idempotency_key=str(uuid4()),
        status="pending",
        attempts=attempts,
    )
    return msg


class _Savepoint:
    """Reproduz `session.begin_nested()`: sai limpo, ou desfaz e propaga."""

    def __init__(self, sessao: FakeSession) -> None:
        self._sessao = sessao

    async def __aenter__(self) -> _Savepoint:
        self._marca = len(self._sessao.escritas)
        return self

    async def __aexit__(self, exc_type: object, *_rest: object) -> bool:
        if exc_type is not None:
            del self._sessao.escritas[self._marca :]
        return False


class FakeSession:
    def __init__(self, mensagens: list[OutboxMessage]) -> None:
        self._mensagens = mensagens
        self.escritas: list[str] = []
        self.commits = 0

    def begin_nested(self) -> _Savepoint:
        return _Savepoint(self)

    async def commit(self) -> None:
        self.commits += 1

    async def execute(self, *_args: object, **_kwargs: object) -> object:
        class _R:
            def scalars(_self) -> object:
                class _S:
                    def all(_s) -> list[OutboxMessage]:
                        return list()

                return _S()

        return _R()


@pytest.fixture(autouse=True)
def _claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitui a reserva de lote: o SELECT ... FOR UPDATE é do banco, não do teste."""
    import worker.consumers.outbox as modulo

    class _RepoFake:
        def __init__(self, session: FakeSession) -> None:
            self._session = session

        async def claim_batch(self, *, limit: int = 20) -> list[OutboxMessage]:
            return self._session._mensagens[:limit]

    monkeypatch.setattr(modulo, "OutboxDispatchRepository", _RepoFake)


async def test_lote_vazio_nao_commita() -> None:
    sessao = FakeSession([])
    resultado = await despachar_lote(sessao, RegistroDeHandlers())  # type: ignore[arg-type]

    assert resultado.houve_trabalho is False
    assert sessao.commits == 0, "fila vazia não deve abrir e fechar transação à toa"


async def test_mensagem_despachada_e_marcada_na_mesma_transacao() -> None:
    msg = _mensagem()
    sessao = FakeSession([msg])
    registro = RegistroDeHandlers()

    @registro.registra("platform_update.published")
    async def _handler(session: FakeSession, mensagem: OutboxMessage) -> None:  # type: ignore[override]
        session.escritas.append("notificacao")

    resultado = await despachar_lote(sessao, registro)  # type: ignore[arg-type]

    assert resultado.despachadas == 1
    assert msg.status == "dispatched"
    assert sessao.escritas == ["notificacao"]
    assert sessao.commits == 1, "efeito e marcação commitam juntos (exatamente-uma-vez)"


async def test_handler_que_falha_nao_deixa_escrita_pela_metade() -> None:
    msg = _mensagem()
    sessao = FakeSession([msg])
    registro = RegistroDeHandlers()

    @registro.registra("platform_update.published")
    async def _handler(session: FakeSession, mensagem: OutboxMessage) -> None:  # type: ignore[override]
        session.escritas.append("notificacao")
        raise RuntimeError("provedor caiu")

    resultado = await despachar_lote(sessao, registro)  # type: ignore[arg-type]

    assert resultado.falhadas == 1
    assert msg.status == "failed"
    assert msg.attempts == 1
    assert msg.last_error is not None and "provedor caiu" in msg.last_error
    assert sessao.escritas == [], "o savepoint desfez o que o handler tinha escrito"
    assert sessao.commits == 1, "mas a marcação de falha precisa persistir"


async def test_uma_mensagem_ruim_nao_derruba_as_boas() -> None:
    """O ponto de PAR-07 § DLQ: a fila continua andando."""
    ruim = _mensagem()
    boas = [_mensagem() for _ in range(3)]
    sessao = FakeSession([boas[0], ruim, boas[1], boas[2]])
    registro = RegistroDeHandlers()

    @registro.registra("platform_update.published")
    async def _handler(session: FakeSession, mensagem: OutboxMessage) -> None:  # type: ignore[override]
        if mensagem is ruim:
            raise RuntimeError("payload estranho")
        session.escritas.append(str(mensagem.id))

    resultado = await despachar_lote(sessao, registro)  # type: ignore[arg-type]

    assert (resultado.reivindicadas, resultado.despachadas, resultado.falhadas) == (4, 3, 1)
    assert all(m.status == "dispatched" for m in boas)
    assert ruim.status == "failed"


async def test_mensagem_na_ultima_tentativa_vai_para_a_dlq() -> None:
    msg = _mensagem(attempts=MAX_TENTATIVAS - 1)
    sessao = FakeSession([msg])
    registro = RegistroDeHandlers()

    @registro.registra("platform_update.published")
    async def _handler(session: FakeSession, mensagem: OutboxMessage) -> None:  # type: ignore[override]
        raise RuntimeError("de novo não")

    resultado = await despachar_lote(sessao, registro)  # type: ignore[arg-type]

    assert msg.status == "dead"
    assert resultado.mortas == 1


async def test_topico_sem_handler_falha_a_mensagem_e_nao_o_worker() -> None:
    """Mensagem órfã (tópico removido, deploy pela metade) não pode parar a fila."""
    msg = _mensagem(topic="topico.que.ninguem.conhece")
    sessao = FakeSession([msg])

    resultado = await despachar_lote(sessao, RegistroDeHandlers())  # type: ignore[arg-type]

    assert resultado.falhadas == 1
    assert msg.status == "failed"
    assert msg.last_error is not None and "sem handler" in msg.last_error


async def test_claim_enxerga_mensagem_sem_next_attempt_at() -> None:
    """Regressão encontrada só contra o Postgres de verdade.

    `NULL <= now()` é NULL em SQL, não falso, então uma linha com `next_attempt_at`
    nulo nunca casava com o filtro e ficava presa em `pending` para sempre — sem erro,
    sem log, sem sintoma além da notificação que não chega. Só aparece com quem insere
    sem preencher o campo: ETL, SQL manual, contexto novo.
    """
    from sqlalchemy.dialects import postgresql

    from app.contexts.engagement.repository import OutboxDispatchRepository

    capturado: list[object] = []

    class _SessaoQueCaptura:
        async def execute(self, stmt: object, *_a: object, **_k: object) -> object:
            capturado.append(stmt)

            class _R:
                def scalars(_self) -> object:
                    class _S:
                        def all(_s) -> list[object]:
                            return []

                    return _S()

            return _R()

    await OutboxDispatchRepository(_SessaoQueCaptura()).claim_batch()  # type: ignore[arg-type]

    sql = str(capturado[0].compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]
    assert "next_attempt_at IS NULL" in sql, f"claim não tolera nulo: {sql}"
    assert "FOR UPDATE" in sql and "SKIP LOCKED" in sql, "a reserva precisa travar a linha"


# --------------------------------------------------------------- registro


def test_prefixo_cobre_topico_dinamico() -> None:
    registro = RegistroDeHandlers()

    async def _h(session: object, mensagem: object) -> None: ...

    registro.registra_prefixo("audit.")(_h)  # type: ignore[arg-type]

    assert registro.resolve("audit.member.removed") is _h
    with pytest.raises(TopicoSemHandlerError):
        registro.resolve("outro.assunto")


def test_prefixo_mais_especifico_vence() -> None:
    registro = RegistroDeHandlers()

    async def _generico(session: object, mensagem: object) -> None: ...
    async def _especifico(session: object, mensagem: object) -> None: ...

    registro.registra_prefixo("audit.")(_generico)  # type: ignore[arg-type]
    registro.registra_prefixo("audit.member.")(_especifico)  # type: ignore[arg-type]

    assert registro.resolve("audit.member.removed") is _especifico
    assert registro.resolve("audit.settings.updated") is _generico


def test_exato_vence_prefixo() -> None:
    registro = RegistroDeHandlers()

    async def _por_prefixo(session: object, mensagem: object) -> None: ...
    async def _exato(session: object, mensagem: object) -> None: ...

    registro.registra_prefixo("audit.")(_por_prefixo)  # type: ignore[arg-type]
    registro.registra("audit.member.removed")(_exato)  # type: ignore[arg-type]

    assert registro.resolve("audit.member.removed") is _exato


def test_registro_duplicado_e_erro_de_programacao() -> None:
    registro = RegistroDeHandlers()

    async def _h(session: object, mensagem: object) -> None: ...

    registro.registra("t")(_h)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        registro.registra("t")(_h)  # type: ignore[arg-type]


# --------------------------------------------------------------- scheduler


async def test_job_so_roda_quando_vence() -> None:
    scheduler = Scheduler()
    execucoes: list[int] = []

    @scheduler.registra("teste", timedelta(minutes=10))
    async def _job() -> None:
        execucoes.append(1)

    agora = datetime.now(UTC)
    assert await scheduler.tick(agora) == []
    assert await scheduler.tick(agora + timedelta(minutes=11)) == ["teste"]
    assert len(execucoes) == 1


async def test_job_que_falha_nao_para_os_outros() -> None:
    scheduler = Scheduler()
    rodou: list[str] = []

    @scheduler.registra("quebrado", timedelta(seconds=1))
    async def _quebrado() -> None:
        raise RuntimeError("boom")

    @scheduler.registra("saudavel", timedelta(seconds=1))
    async def _saudavel() -> None:
        rodou.append("saudavel")

    executados = await scheduler.tick(datetime.now(UTC) + timedelta(seconds=2))

    assert executados == ["saudavel"]
    assert rodou == ["saudavel"]


async def test_agenda_do_sistema_esta_declarada() -> None:
    """A lista do que roda sozinho fica aqui, e muda conscientemente.

    No legado essa resposta só existia dentro do banco de produção (AMB-008). Se um job
    novo entrar sem passar por este teste, voltamos a ter agendamento que ninguém sabe
    que existe.
    """
    import worker.jobs.schedule  # noqa: F401 — registra os jobs por efeito colateral
    from worker.scheduler import scheduler as global_

    assert sorted(global_.jobs) == ["expirar-requests-vencidos", "fechar-ciclos-vencidos"]


# --------------------------------------------------------------- email


async def test_adapter_console_nao_explode(caplog: pytest.LogCaptureFixture) -> None:
    adapter = ConsoleEmailAdapter("nao-responda@exemplo.com")
    await adapter.send(to="alguem@exemplo.com", subject="Oi", body="corpo")


def test_provedor_nao_implementado_falha_alto() -> None:
    """Melhor a mensagem ir para a DLQ do que sumir achando que foi enviada."""
    from app.core.config import Settings

    settings = Settings(  # type: ignore[call-arg]
        jwt_secret="chave-de-teste-com-mais-de-32-caracteres-ok",
        email_provider="resend",
    )
    with pytest.raises(ProvedorNaoConfiguradoError):
        build_email_adapter(settings)


def test_provedor_console_e_o_default_de_desenvolvimento() -> None:
    from app.core.config import Settings

    settings = Settings(jwt_secret="chave-de-teste-com-mais-de-32-caracteres-ok")  # type: ignore[call-arg]
    assert isinstance(build_email_adapter(settings), ConsoleEmailAdapter)


def test_asyncio_disponivel() -> None:
    # Sanidade do ambiente de teste do worker (asyncio_mode=auto).
    assert asyncio.get_event_loop_policy() is not None
