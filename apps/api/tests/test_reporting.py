"""Relatórios e exportações — PAR-04 (engajamento e escopo executivo), BR-MIGRAR-029/030.

Os cálculos em si dependem de SQL e são exercitados contra o Postgres no smoke; aqui
ficam as regras que são decisão, não consulta: validação de escopo, limites, formato do
CSV, capacidade individual e o ciclo de vida do job de exportação.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.reporting.models import ExportJob
from app.contexts.reporting.queries import (
    LIMITE_PREVIEW,
    LIMITE_TABELA,
    LinhaDe360,
    LinhaDeEngajamento,
)
from app.contexts.reporting.repository import ExportJobDispatchRepository
from app.contexts.reporting.service import (
    SEPARADOR_CSV,
    ExportService,
    ReportService,
    validar_escopo_executivo,
)
from app.core.errors import AuthorizationError, ValidationError
from app.core.tenancy import TenantContext


def _contexto(*flags: str) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(), user_id=uuid4(), role="admin", flags=frozenset(flags)
    )


# ---------------------------------------------------------------- escopo executivo


def test_escopo_geral_dispensa_ciclo_e_pessoa() -> None:
    validar_escopo_executivo(escopo="general", cycle_id=None, profile_id=None, giver_id=None)


@pytest.mark.parametrize("escopo", ["person", "specific"])
def test_escopo_por_pessoa_exige_ciclo_e_pessoa(escopo: str) -> None:
    """PAR-04: recusa com a orientação de preenchimento do legado."""
    with pytest.raises(ValidationError) as exc:
        validar_escopo_executivo(
            escopo=escopo, cycle_id=None, profile_id=None, giver_id=uuid4()
        )
    assert set(exc.value.details["faltando"]) == {"cycle_id", "profile_id"}


def test_escopo_especifico_exige_avaliador() -> None:
    """O cenário nomeado em PAR-04: escopo específico sem avaliador é recusado."""
    with pytest.raises(ValidationError) as exc:
        validar_escopo_executivo(
            escopo="specific", cycle_id=uuid4(), profile_id=uuid4(), giver_id=None
        )
    assert exc.value.details["faltando"] == ["giver_id"]


def test_escopo_especifico_completo_passa() -> None:
    validar_escopo_executivo(
        escopo="specific", cycle_id=uuid4(), profile_id=uuid4(), giver_id=uuid4()
    )


def test_escopo_inventado_e_recusado() -> None:
    with pytest.raises(ValidationError):
        validar_escopo_executivo(
            escopo="tudo", cycle_id=uuid4(), profile_id=uuid4(), giver_id=None
        )


# ---------------------------------------------------------------- CSV


def test_csv_usa_ponto_e_virgula() -> None:
    """BR-MIGRAR-029: vírgula quebraria o Excel em português, que é onde isto abre."""
    csv = ExportService.para_csv(
        ["Pessoa", "Enviados"], [["Ana", 3], ["Bruno", 5]], nome="teste.csv"
    )

    linhas = csv.conteudo.strip().splitlines()
    assert linhas[0] == f"Pessoa{SEPARADOR_CSV}Enviados"
    assert linhas[1] == f"Ana{SEPARADOR_CSV}3"
    assert csv.nome_do_arquivo == "teste.csv"


def test_csv_termina_linha_no_formato_do_excel() -> None:
    csv = ExportService.para_csv(["A"], [["x"]], nome="t.csv")
    assert csv.conteudo.endswith("\r\n")


def test_csv_escapa_o_separador_dentro_do_valor() -> None:
    """Nome com ponto e vírgula não pode virar duas colunas."""
    csv = ExportService.para_csv(["Nome"], [["Silva; Souza"]], nome="t.csv")
    assert '"Silva; Souza"' in csv.conteudo


# ---------------------------------------------------------------- limites e flags


class FakeQuery:
    def __init__(self) -> None:
        self.limite_recebido: int | None = None

    async def linhas(self, **kwargs: Any) -> list[Any]:
        self.limite_recebido = kwargs.get("limite")
        return []


async def test_preview_e_tabela_usam_limites_diferentes() -> None:
    """BR-MIGRAR-029: preview 50, tabela 100 — aplicados na query."""
    q360, clientes, engajamento = FakeQuery(), FakeQuery(), FakeQuery()
    service = ReportService(q360, clientes, engajamento, FakeQuery())  # type: ignore[arg-type]

    await service.feedback_360(cycle_id=None, department_id=None, preview=True)
    assert q360.limite_recebido == LIMITE_PREVIEW

    await service.feedback_360(cycle_id=None, department_id=None, preview=False)
    assert q360.limite_recebido == LIMITE_TABELA

    await service.engajamento(preview=True)
    assert engajamento.limite_recebido == LIMITE_PREVIEW


async def test_relatorio_de_cliente_exige_a_capacidade() -> None:
    """BR-MIGRAR-029: `can_generate_reports` é capacidade individual, não papel."""
    service = ReportService(FakeQuery(), FakeQuery(), FakeQuery(), FakeQuery())  # type: ignore[arg-type]

    with pytest.raises(AuthorizationError):
        await service.clientes(_contexto())

    await service.clientes(_contexto("can_generate_reports"))


# ---------------------------------------------------------------- job de exportação


class FakeExportRepository:
    def __init__(self) -> None:
        self.jobs: list[ExportJob] = []

    def add(self, job: ExportJob) -> ExportJob:
        self.jobs.append(job)
        return job


class FakeOutbox:
    def __init__(self) -> None:
        self.chaves: list[str] = []

    async def enqueue(self, *, topic: str, payload: dict, idempotency_key: str) -> bool:
        self.chaves.append(idempotency_key)
        return True


async def test_pedido_de_xlsx_vira_job_e_mensagem() -> None:
    repo, outbox = FakeExportRepository(), FakeOutbox()
    tenant = _contexto("can_generate_reports")

    job = await ExportService(repo, outbox).solicitar(  # type: ignore[arg-type]
        tenant, kind="engagement", formato="xlsx", filtros={"x": 1}
    )

    assert job.status == "pending"
    assert job.requested_by == tenant.user_id
    assert job.filters == {"x": 1}
    assert outbox.chaves == [f"export.requested:{job.id}"]


async def test_id_do_job_existe_antes_do_flush() -> None:
    """A chave de idempotência precisa dele, e o default da coluna só age no INSERT."""
    repo, outbox = FakeExportRepository(), FakeOutbox()

    job = await ExportService(repo, outbox).solicitar(  # type: ignore[arg-type]
        _contexto(), kind="client", formato="pdf", filtros={}
    )

    assert isinstance(job.id, UUID)


async def test_csv_nao_vira_job() -> None:
    """CSV sai em milissegundos; orquestrar um job para isso seria cerimônia à toa."""
    with pytest.raises(ValidationError):
        await ExportService(FakeExportRepository(), FakeOutbox()).solicitar(  # type: ignore[arg-type]
            _contexto(), kind="engagement", formato="csv", filtros={}
        )


def _job(status: str = "pending") -> ExportJob:
    return ExportJob(
        id=uuid4(),
        tenant_id=uuid4(),
        requested_by=uuid4(),
        kind="engagement",
        format="xlsx",
        filters={},
        status=status,
    )


def test_job_pronto_registra_arquivo_e_limpa_erro() -> None:
    job = _job()
    job.error = "falha anterior"

    ExportJobDispatchRepository.marcar_pronto(job, "/data/exports/x.xlsx")

    assert job.status == "done"
    assert job.file_path == "/data/exports/x.xlsx"
    assert job.error is None
    assert job.completed_at is not None
    assert job.pronto is True


def test_job_falho_guarda_o_motivo() -> None:
    """Silêncio aqui vira "cliquei em exportar e nunca chegou"."""
    job = _job()

    ExportJobDispatchRepository.marcar_falho(job, "filtro sem linhas")

    assert job.status == "failed"
    assert job.error == "filtro sem linhas"
    assert job.pronto is False


def test_erro_gigante_nao_estoura_a_coluna() -> None:
    job = _job()
    ExportJobDispatchRepository.marcar_falho(job, "x" * 5000)
    assert job.error is not None and len(job.error) == 1000


# ---------------------------------------------------------------- read models


def test_percentual_de_360_nao_divide_por_zero() -> None:
    linha = LinhaDe360(
        profile_id=uuid4(),
        nome="Ana",
        departamento=None,
        recebidos=0,
        respondidos=0,
        media_nota=None,
    )
    assert linha.percentual == 0.0


def test_percentual_de_engajamento() -> None:
    linha = LinhaDeEngajamento(profile_id=uuid4(), nome="Ana", solicitados=8, enviados=6)
    assert linha.percentual == 75.0


def test_item_de_historico_e_serializavel() -> None:
    """Mesma regressão do diagnóstico: dataclass com `slots` não tem `__dict__`."""
    from dataclasses import asdict
    from datetime import UTC, datetime

    from app.contexts.reporting.queries import ItemDeHistorico
    from app.contexts.reporting.schemas import ItemDeHistoricoOut

    item = ItemDeHistorico(
        tipo="livre",
        item_id=uuid4(),
        quando=datetime.now(UTC),
        sobre_id=uuid4(),
        sobre_nome="Ana",
        titulo="Feedback livre",
        detalhe=None,
        lido_em=None,
    )

    assert ItemDeHistoricoOut(**asdict(item)).sobre_nome == "Ana"
    with pytest.raises(TypeError):
        vars(item)


class _SessaoQueGravaStatement:
    """Sessão falsa que guarda o `select` e devolve nada.

    O que estes testes verificam é a cláusula que a query monta, não o resultado — e
    para isso um banco de verdade seria máquina demais para responder "o `WHERE` tem
    `is_sensitive`?".
    """

    def __init__(self) -> None:
        self.statements: list[object] = []

    async def execute(self, statement):
        self.statements.append(statement)

        class _Vazio:
            @staticmethod
            def all():
                return []

        return _Vazio()


@pytest.mark.asyncio
async def test_historico_esconde_sensivel_por_padrao() -> None:
    """Sensível não chega a quem recebeu — no histórico vale igual à caixa de recebidos."""
    from app.contexts.reporting.queries import TeamHistoryQuery

    sessao = _SessaoQueGravaStatement()
    tenant = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="gestor", flags=frozenset())
    query = TeamHistoryQuery(sessao, tenant)  # type: ignore[arg-type]

    await query.livre({uuid4()})
    assert "is_sensitive" in str(sessao.statements[-1])

    await query.livre({uuid4()}, incluir_sensiveis=True)
    assert "is_sensitive" not in str(sessao.statements[-1])


@pytest.mark.asyncio
async def test_historico_de_escopo_vazio_nao_vira_todo_mundo() -> None:
    """PAR-05 do lado da leitura: sem escopo, nada — e não "sem filtro"."""
    from app.contexts.reporting.queries import TeamHistoryQuery

    sessao = _SessaoQueGravaStatement()
    tenant = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="gestor", flags=frozenset())
    query = TeamHistoryQuery(sessao, tenant)  # type: ignore[arg-type]

    assert await query.livre(set()) == []
    assert await query.clientes(set()) == []
    assert await query.ciclos(set()) == []
    assert sessao.statements == [], "escopo vazio nao deveria nem consultar"


@pytest.mark.asyncio
async def test_historico_de_uma_pessoa_consulta_so_ela() -> None:
    """SCR-0037: o recorte entra na consulta, não depois dela.

    Filtrar o resultado daria o mesmo hoje e viraria vazamento no dia em que a consulta
    ganhasse paginação — a primeira página traria gente de fora e o filtro a esconderia
    sem que ninguém percebesse que ela veio.
    """
    from app.contexts.reporting.queries import TeamHistoryQuery

    sessao = _SessaoQueGravaStatement()
    tenant = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="gestor", flags=frozenset())
    alvo = uuid4()

    await TeamHistoryQuery(sessao, tenant).ciclos({alvo})  # type: ignore[arg-type]

    sql = str(sessao.statements[-1])
    assert "IN (" in sql.replace("in (", "IN ("), "o id da pessoa precisa entrar no WHERE"


def test_escopo_geral_nao_exige_ciclo_nem_pessoa() -> None:
    """BR-MIGRAR-028: ciclo e pessoa são obrigatórios **exceto** no escopo geral."""
    validar_escopo_executivo(escopo="general", cycle_id=None, profile_id=None, giver_id=None)


@pytest.mark.asyncio
async def test_executivo_geral_gera_o_retrato_do_escritorio() -> None:
    """O par do teste acima, do lado do worker.

    Por um tempo a API aceitava `general` com 202 e o job falhava até a DLQ dizendo que
    exigia ciclo e pessoa: as duas metades da mesma regra discordavam, e nada acusava
    porque nenhuma tela chegava a pedir o relatório geral.
    """
    from worker.jobs.exports import _dados

    job = ExportJob(
        id=uuid4(),
        tenant_id=uuid4(),
        requested_by=uuid4(),
        kind="executive",
        format="pdf",
        filters={"escopo": "general", "cycle_id": None, "profile_id": None},
        status="pending",
    )

    cabecalho, linhas = await _dados(_SessaoQueGravaStatement(), job)  # type: ignore[arg-type]

    assert cabecalho[0] == "Pessoa", "o geral é por pessoa do escritório, não por pergunta"
    assert linhas == []
