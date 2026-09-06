"""Acompanhamento da equipe no ciclo — SCR-0030.

A tela responde "quem da minha equipe está devendo o quê". Os testes aqui olham para as
três propriedades que fazem ela ser confiável: o denominador é o mesmo do progresso do
ciclo (BR-MIGRAR-009), quem olha não entra na própria lista, e o escopo vem de fora —
esta classe filtra dentro do que `TeamScopeService` devolveu, nunca amplia.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.contexts.feedback.models import FeedbackCycle
from app.contexts.feedback.service import TeamProgressService
from app.contexts.identity.models import Profile

HOJE = date.today()


class FakeRequestRepository:
    def __init__(self) -> None:
        self.por_avaliador: dict[tuple[UUID, str], int] = {}
        self.nao_lidos: dict[UUID, int] = {}

    async def contagem_por_avaliador(self, cycle_id: UUID) -> dict[tuple[UUID, str], int]:
        return dict(self.por_avaliador)

    async def contagem_nao_lidos_por_avaliado(self, cycle_id: UUID) -> dict[UUID, int]:
        return dict(self.nao_lidos)


class FakeCycleRepository:
    def __init__(self, abertos: list[FeedbackCycle] | None = None) -> None:
        self.abertos = abertos or []

    async def list_by_status(self, status: str) -> list[FeedbackCycle]:
        return self.abertos if status == "open" else []


class FakeProfileRepository:
    def __init__(self, perfis: list[Profile]) -> None:
        self.perfis = perfis

    async def list_by_ids(self, ids: set[UUID]) -> list[Profile]:
        return [p for p in self.perfis if p.id in ids]


def _perfil(nome: str, **campos: Any) -> Profile:
    pid = campos.pop("id", uuid4())
    base = {
        "id": pid,
        "user_id": pid,
        "tenant_id": uuid4(),
        "full_name": nome,
        "role": "colaborador",
        "status": "active",
        "job_title": "Advogado",
        "is_coordinator": False,
    }
    return Profile(**{**base, **campos})


def _ciclo() -> FeedbackCycle:
    return FeedbackCycle(
        id=uuid4(),
        tenant_id=uuid4(),
        name="2º semestre",
        form_id=uuid4(),
        status="open",
        start_date=HOJE,
        end_date=HOJE + timedelta(days=15),
    )


def _servico(perfis: list[Profile], requests: FakeRequestRepository, ciclos=None):
    return TeamProgressService(
        requests=requests,  # type: ignore[arg-type]
        cycles=ciclos or FakeCycleRepository([_ciclo()]),  # type: ignore[arg-type]
        profiles=FakeProfileRepository(perfis),  # type: ignore[arg-type]
    )


async def test_conta_o_que_falta_escrever_e_o_que_falta_ler() -> None:
    """São duas perguntas diferentes, e o legado as separa em duas colunas.

    "Pendentes de enviar" é o que a pessoa deve escrever; "pendentes de leitura" é o que
    escreveram sobre ela e ela ainda não viu. Somar as duas esconderia justamente quem
    já fez a parte dele e está só sem ler.
    """
    ana = _perfil("Ana")
    requests = FakeRequestRepository()
    requests.por_avaliador = {
        (ana.id, "pending"): 2,
        (ana.id, "draft"): 1,
        (ana.id, "submitted"): 3,
    }
    requests.nao_lidos = {ana.id: 4}

    resultado = await _servico([ana], requests).acompanhar({ana.id})

    (linha,) = resultado.membros
    assert linha.pendentes_de_enviar == 3
    assert linha.enviados == 3
    assert linha.pendentes_de_leitura == 4
    assert linha.percentual == 50.0


async def test_cancelado_e_abdicado_ficam_fora_do_denominador() -> None:
    """Mesmo recorte de `CycleProgressService` (BR-MIGRAR-009).

    Se a tela da equipe contasse diferente do progresso do ciclo, voltaríamos ao
    problema que o legado tinha: três telas, três números, nenhum confiável.
    """
    ana = _perfil("Ana")
    requests = FakeRequestRepository()
    requests.por_avaliador = {
        (ana.id, "submitted"): 1,
        (ana.id, "pending"): 1,
        (ana.id, "cancelled"): 5,
        (ana.id, "waived"): 5,
    }

    resultado = await _servico([ana], requests).acompanhar({ana.id})

    (linha,) = resultado.membros
    assert linha.esperados == 2
    assert linha.percentual == 50.0


async def test_quem_olha_sai_da_propria_lista() -> None:
    """O escopo inclui a própria pessoa porque ela vê o próprio histórico.

    A tela de equipe é outra pergunta — "quem trabalha comigo" —, e o gestor aparecendo
    na lista dele inflava o "total de membros" do rodapé.
    """
    gestora = _perfil("Marina")
    ana = _perfil("Ana")

    resultado = await _servico([gestora, ana], FakeRequestRepository()).acompanhar(
        {gestora.id, ana.id}, exceto=gestora.id
    )

    assert [m.full_name for m in resultado.membros] == ["Ana"]
    assert resultado.total_membros == 1


async def test_sem_pedido_nenhum_a_pessoa_esta_em_dia() -> None:
    """0% seria mentira, e dividir por zero seria erro: não há nada pendente."""
    ana = _perfil("Ana")

    resultado = await _servico([ana], FakeRequestRepository()).acompanhar({ana.id})

    (linha,) = resultado.membros
    assert linha.esperados == 0
    assert linha.percentual == 100.0
    assert resultado.percentual == 100.0


async def test_sem_ciclo_aberto_a_equipe_continua_aparecendo() -> None:
    """Entre um ciclo e outro a equipe não deixa de existir.

    Cair num estado vazio faria a tela parecer quebrada em toda virada de ciclo.
    """
    ana = _perfil("Ana")
    bruno = _perfil("Bruno")

    resultado = await _servico(
        [ana, bruno], FakeRequestRepository(), ciclos=FakeCycleRepository([])
    ).acompanhar({ana.id, bruno.id})

    assert resultado.ciclo_id is None
    assert [m.full_name for m in resultado.membros] == ["Ana", "Bruno"]
    assert all(m.esperados == 0 for m in resultado.membros)


async def test_ordena_por_nome_e_nao_pela_ordem_do_banco() -> None:
    """Ordem estável: sem ela a lista dança a cada carregamento."""
    perfis = [_perfil("Zuleica"), _perfil("ana"), _perfil("Bruno")]

    resultado = await _servico(perfis, FakeRequestRepository()).acompanhar(
        {p.id for p in perfis}
    )

    assert [m.full_name for m in resultado.membros] == ["ana", "Bruno", "Zuleica"]


async def test_totais_do_rodape_somam_as_linhas() -> None:
    ana, bruno = _perfil("Ana"), _perfil("Bruno")
    requests = FakeRequestRepository()
    requests.por_avaliador = {
        (ana.id, "submitted"): 3,
        (ana.id, "pending"): 1,
        (bruno.id, "submitted"): 1,
        (bruno.id, "pending"): 3,
    }

    resultado = await _servico([ana, bruno], requests).acompanhar({ana.id, bruno.id})

    assert resultado.enviados == 4
    assert resultado.esperados == 8
    assert resultado.percentual == 50.0


async def test_escopo_vazio_nao_consulta_ciclo_nem_perfis() -> None:
    """Quem não enxerga ninguém recebe lista vazia, sem ir ao banco atrás de nada."""
    resultado = await _servico([], FakeRequestRepository()).acompanhar(set())

    assert resultado.membros == []
    assert resultado.total_membros == 0


# ---------------------------------------------------------------- painel


class FakeProgressoRepo:
    def __init__(self, contagem: dict[str, int] | None = None) -> None:
        self.contagem = contagem or {}
        self.global_contagem: dict[str, int] = {}
        self.departamentos: list[tuple[str, int, int]] = []
        self.recentes: list[Any] = []

    async def contagem_por_status(self, cycle_id: UUID) -> dict[str, int]:
        return dict(self.contagem)

    async def ids_atrasados(self, cycle_id: UUID, hoje=None) -> set[UUID]:
        return set()

    async def contagem_global_por_status(self) -> dict[str, int]:
        return dict(self.global_contagem)

    async def contagem_por_departamento(self, cycle_id: UUID) -> list[tuple[str, int, int]]:
        return list(self.departamentos)

    async def enviados_recentes(self, cycle_id: UUID, *, limite: int = 8) -> list[Any]:
        return list(self.recentes)


class FakeProfileComStatus(FakeProfileRepository):
    def __init__(self, perfis: list[Profile], status: dict[str, int]) -> None:
        super().__init__(perfis)
        self.status = status

    async def contagem_por_status(self) -> dict[str, int]:
        return dict(self.status)


def _painel(requests: FakeProgressoRepo, perfis=None, status=None, ciclos=None):
    from app.contexts.feedback.service import CycleProgressService, DashboardService

    return DashboardService(
        requests=requests,  # type: ignore[arg-type]
        cycles=ciclos or FakeCycleRepository([_ciclo()]),  # type: ignore[arg-type]
        profiles=FakeProfileComStatus(perfis or [], status or {}),  # type: ignore[arg-type]
        progresso=CycleProgressService(requests),  # type: ignore[arg-type]
    )


async def test_painel_usa_o_mesmo_progresso_do_ciclo() -> None:
    """Um painel com conta própria recriaria o problema que BR-MIGRAR-009 resolveu."""
    requests = FakeProgressoRepo({"submitted": 2, "pending": 2, "cancelled": 3})

    painel = await _painel(requests).montar()

    assert painel.progresso.total == 4
    assert painel.progresso.percentual == 50.0
    assert painel.progresso.excluidos == 3


async def test_conclusao_por_departamento_calcula_o_percentual() -> None:
    requests = FakeProgressoRepo({"submitted": 3, "pending": 1})
    requests.departamentos = [("Contencioso", 4, 3), ("Sem departamento", 2, 0)]

    painel = await _painel(requests).montar()

    assert [(d.nome, d.percentual) for d in painel.por_departamento] == [
        ("Contencioso", 75.0),
        ("Sem departamento", 0.0),
    ]


async def test_atividade_nomeia_quem_saiu_em_vez_de_deixar_em_branco() -> None:
    """Perfil desligado some de `list_by_ids`, que só devolve ativos.

    Sem isto a linha ficaria com o nome vazio e pareceria erro de carregamento, quando
    na verdade a atividade aconteceu e a pessoa saiu depois.
    """
    ana = _perfil("Ana")
    saiu = uuid4()
    requests = FakeProgressoRepo({"submitted": 1})
    requests.recentes = [
        type("R", (), {"giver_id": ana.id, "receiver_id": saiu, "submitted_at": None})()
    ]

    painel = await _painel(requests, perfis=[ana]).montar()

    (linha,) = painel.atividade
    assert linha.avaliador == "Ana"
    assert linha.avaliado == "Alguém que saiu"


async def test_sem_ciclo_aberto_o_painel_ainda_conta_pessoas_e_totais() -> None:
    """O escritório existe entre um ciclo e outro; zerar tudo pareceria sistema vazio."""
    requests = FakeProgressoRepo()
    requests.global_contagem = {"submitted": 300, "pending": 54}

    painel = await _painel(
        requests, status={"active": 15, "inactive": 2}, ciclos=FakeCycleRepository([])
    ).montar()

    assert painel.ciclo is None
    assert painel.pessoas_por_status == {"active": 15, "inactive": 2}
    assert painel.total_de_feedbacks == 354
    assert painel.total_enviados == 300
    assert painel.por_departamento == []
