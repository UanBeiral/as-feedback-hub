"""Avisos gerados a partir dos eventos de domínio — BR-MIGRAR-023/024/025.

O que estes testes prendem é **quem recebe o quê**. A decisão não veio pronta da spec
(o legado registrou os tipos de notificação, não os destinatários), então ela mora aqui
de forma explícita: se alguém mudar a regra, muda o teste junto e a mudança fica visível
na revisão.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.engagement.models import Notification, OutboxMessage
from worker.handlers import RegistroDeHandlers
from worker.jobs.avisos import PayloadDeAvisoInvalidoError, registra_avisos


class FakeSession:
    def __init__(self) -> None:
        self.notificacoes: list[Notification] = []

    def add(self, entidade: Any) -> None:
        self.notificacoes.append(entidade)

    def por_destinatario(self) -> dict[UUID, Notification]:
        return {n.user_id: n for n in self.notificacoes}


class _Ciclo:
    def __init__(self, nome: str = "Ciclo de setembro") -> None:
        self.id = uuid4()
        self.name = nome
        self.end_date = date(2026, 9, 30)


class _Avaliacao:
    def __init__(self, cliente: str | None = "Cliente Teste") -> None:
        self.id = uuid4()
        self.client_name = cliente


def _mensagem(topico: str, payload: dict[str, Any]) -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        tenant_id=uuid4(),
        topic=topico,
        payload=payload,
        idempotency_key=str(uuid4()),
        status="pending",
    )


@pytest.fixture
def registro(monkeypatch: pytest.MonkeyPatch):
    """Registro real, com os repositórios substituídos por dublês."""
    import worker.jobs.avisos as modulo

    estado: dict[str, Any] = {
        "ciclo": _Ciclo(),
        "avaliadores": [],
        "participantes": [],
        "gestao": [],
        "avaliacao": _Avaliacao(),
    }

    class _CycleRepo:
        def __init__(self, *_a: Any) -> None: ...

        async def get(self, _id: UUID) -> Any:
            return estado["ciclo"]

    class _RequestRepo:
        def __init__(self, *_a: Any) -> None: ...

        async def ids_de_avaliadores_do_ciclo(self, _id: UUID) -> list[UUID]:
            return list(estado["avaliadores"])

        async def ids_de_participantes_do_ciclo(self, _id: UUID) -> list[UUID]:
            return list(estado["participantes"])

    class _ProfileRepo:
        def __init__(self, *_a: Any) -> None: ...

        async def list_ids_por_papel(self, *_papeis: str) -> list[UUID]:
            return list(estado["gestao"])

    class _EvalRepo:
        def __init__(self, *_a: Any) -> None: ...

        async def get(self, _id: UUID) -> Any:
            return estado["avaliacao"]

    monkeypatch.setattr(modulo, "CycleRepository", _CycleRepo)
    monkeypatch.setattr(modulo, "RequestRepository", _RequestRepo)
    monkeypatch.setattr(modulo, "ProfileRepository", _ProfileRepo)
    monkeypatch.setattr(modulo, "ClientEvaluationRepository", _EvalRepo)

    reg = RegistroDeHandlers()
    registra_avisos(reg)
    return reg, estado


async def test_abertura_avisa_quem_tem_feedback_para_dar(registro) -> None:
    """Quem foi só avaliado não recebe: não há ação possível do lado dele."""
    reg, estado = registro
    avaliadores = [uuid4(), uuid4()]
    estado["avaliadores"] = avaliadores
    sessao = FakeSession()

    mensagem = _mensagem("cycle.opened", {"cycle_id": str(estado["ciclo"].id)})
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert set(sessao.por_destinatario()) == set(avaliadores)
    aviso = sessao.notificacoes[0]
    assert aviso.type == "cycle_opened"
    assert estado["ciclo"].name in aviso.title
    assert aviso.link == "/meus-feedbacks"
    assert aviso.message is not None and "30/09/2026" in aviso.message


async def test_abertura_sem_avaliadores_nao_cria_nada(registro) -> None:
    reg, estado = registro
    estado["avaliadores"] = []
    sessao = FakeSession()

    mensagem = _mensagem("cycle.opened", {"cycle_id": str(estado["ciclo"].id)})
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert sessao.notificacoes == []


async def test_destinatario_repetido_recebe_um_aviso_so(registro) -> None:
    reg, estado = registro
    alguem = uuid4()
    estado["avaliadores"] = [alguem, alguem, uuid4()]
    sessao = FakeSession()

    mensagem = _mensagem("cycle.opened", {"cycle_id": str(estado["ciclo"].id)})
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert len(sessao.notificacoes) == 2


async def test_fechamento_avisa_so_a_gestao(registro) -> None:
    """Para quem respondeu, o ciclo fechar não pede ação nenhuma."""
    reg, estado = registro
    gestao = [uuid4(), uuid4()]
    estado["gestao"] = gestao
    estado["avaliadores"] = [uuid4()]
    sessao = FakeSession()

    mensagem = _mensagem(
        "cycle.closed", {"cycle_id": str(estado["ciclo"].id), "automatico": True}
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert set(sessao.por_destinatario()) == set(gestao)
    assert sessao.notificacoes[0].type == "cycle_closed"
    assert "automaticamente" in (sessao.notificacoes[0].message or "")


async def test_fechamento_manual_diz_que_foi_manual(registro) -> None:
    reg, estado = registro
    estado["gestao"] = [uuid4()]
    sessao = FakeSession()

    mensagem = _mensagem(
        "cycle.closed", {"cycle_id": str(estado["ciclo"].id), "automatico": False}
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert "manualmente" in (sessao.notificacoes[0].message or "")


async def test_publicacao_avisa_os_dois_lados(registro) -> None:
    reg, estado = registro
    participantes = [uuid4(), uuid4(), uuid4()]
    estado["participantes"] = participantes
    sessao = FakeSession()

    mensagem = _mensagem("cycle.published", {"cycle_id": str(estado["ciclo"].id)})
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert set(sessao.por_destinatario()) == set(participantes)
    assert sessao.notificacoes[0].type == "cycle_published"


async def test_feedback_enviado_avisa_o_avaliado_sem_dizer_quem_escreveu(registro) -> None:
    """Nomear o avaliador quebraria o anonimato relativo que o 360 pressupõe."""
    reg, _estado = registro
    avaliado = uuid4()
    avaliador = uuid4()
    sessao = FakeSession()

    mensagem = _mensagem(
        "request.submitted",
        {"request_id": str(uuid4()), "user_id": str(avaliado), "giver_id": str(avaliador)},
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert list(sessao.por_destinatario()) == [avaliado]
    aviso = sessao.notificacoes[0]
    assert aviso.type == "feedback_received"
    assert str(avaliador) not in (aviso.message or "")
    assert str(avaliador) not in aviso.title


async def test_avaliacao_de_cliente_avisa_o_avaliado(registro) -> None:
    reg, _estado = registro
    avaliado = uuid4()
    sessao = FakeSession()

    mensagem = _mensagem(
        "client_eval.submitted",
        {"evaluation_id": str(uuid4()), "user_id": str(avaliado)},
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert list(sessao.por_destinatario()) == [avaliado]
    assert sessao.notificacoes[0].type == "client_feedback_received"


async def test_avaliacao_negativa_sobe_para_a_gestao(registro) -> None:
    """O único aviso que sobe na hierarquia — alguém precisa ligar para o cliente hoje."""
    reg, estado = registro
    avaliado = uuid4()
    gestao = [uuid4(), uuid4()]
    estado["gestao"] = gestao
    sessao = FakeSession()

    mensagem = _mensagem(
        "client_eval.flagged_negative",
        {"evaluation_id": str(estado["avaliacao"].id), "user_id": str(avaliado)},
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert set(sessao.por_destinatario()) == {avaliado, *gestao}
    assert sessao.notificacoes[0].type == "client_feedback_negative"
    assert "Cliente Teste" in (sessao.notificacoes[0].message or "")


async def test_avaliacao_negativa_sem_nome_do_cliente_nao_quebra(registro) -> None:
    reg, estado = registro
    estado["avaliacao"] = _Avaliacao(cliente=None)
    estado["gestao"] = []
    sessao = FakeSession()

    mensagem = _mensagem(
        "client_eval.flagged_negative",
        {"evaluation_id": str(uuid4()), "user_id": str(uuid4())},
    )
    await reg.resolve(mensagem.topic)(sessao, mensagem)

    assert "Um cliente" in (sessao.notificacoes[0].message or "")


@pytest.mark.parametrize(
    "topico,payload",
    [
        ("cycle.opened", {}),
        ("cycle.closed", {"cycle_id": "isto-não-é-uuid"}),
        ("request.submitted", {"request_id": "x"}),
        ("client_eval.submitted", {}),
    ],
)
async def test_payload_invalido_falha_a_mensagem(registro, topico: str, payload: dict) -> None:
    """Falha explícita: a mensagem vai para a DLQ com o motivo, em vez de sumir."""
    reg, _estado = registro
    sessao = FakeSession()

    with pytest.raises(PayloadDeAvisoInvalidoError):
        await reg.resolve(topico)(sessao, _mensagem(topico, payload))

    assert sessao.notificacoes == []


def test_todo_topico_enfileirado_tem_handler() -> None:
    """O guard que faltava.

    Um tópico sem handler não quebra nada visível: as mensagens acumulam tentativas e
    morrem na DLQ, e o efeito prático é notificação que nunca chega. Este teste compara
    o que o domínio publica com o que o worker sabe despachar, para que a próxima
    divergência apareça no CI e não meses depois.
    """
    import re
    from pathlib import Path

    from worker.jobs.email import ConsoleEmailAdapter
    from worker.jobs.notifications import registra_handlers

    raiz = Path(__file__).resolve().parents[2] / "api" / "app"
    publicados = {
        topico
        for arquivo in raiz.rglob("*.py")
        for topico in re.findall(r'topic="([a-z_.]+)"', arquivo.read_text(encoding="utf-8"))
    }
    assert publicados, "nenhum tópico encontrado — o teste perdeu o alvo"

    registro = registra_handlers(ConsoleEmailAdapter("teste@exemplo.com"))
    sem_handler = sorted(
        topico for topico in publicados if not _tem_handler(registro, topico)
    )

    assert not sem_handler, f"tópicos publicados sem handler no worker: {sem_handler}"


def _tem_handler(registro: RegistroDeHandlers, topico: str) -> bool:
    from worker.handlers import TopicoSemHandlerError

    try:
        registro.resolve(topico)
    except TopicoSemHandlerError:
        return False
    return True
