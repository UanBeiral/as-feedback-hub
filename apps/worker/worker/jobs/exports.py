"""Geração de exportações pesadas no worker (AD-07 / BR-MIGRAR-029/030).

O handler roda dentro do savepoint do despachante, então a regra vale aqui também:
o que este arquivo escreve no banco entra junto com a marcação da mensagem. O arquivo
em disco é a exceção — ele é efeito externo, e por isso a ordem importa: gera o
arquivo, **depois** marca o job como pronto. Se o processo morrer no meio, sobra um
arquivo órfão no disco (barato) em vez de um job "pronto" apontando para nada (caro).

O envio por email é o último passo e o único que pode falhar sozinho: BR-MIGRAR-030 é
explícito em que falha de email **não invalida o relatório gerado**. Por isso ele grava
`email_error` e não derruba o job.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.engagement.models import OutboxMessage
from app.contexts.reporting.models import ExportJob
from app.contexts.reporting.queries import (
    ClientReportQuery,
    EngagementQuery,
    ExecutiveDataQuery,
    Report360Query,
)
from app.contexts.reporting.repository import ExportJobDispatchRepository
from app.core.config import get_settings
from app.core.tenancy import TenantContext
from worker.jobs.email import EmailAdapter

logger = logging.getLogger(__name__)


class ExportacaoVaziaError(RuntimeError):
    """Filtro que não devolve linha nenhuma.

    Falha explícita em vez de planilha vazia: quem abre um arquivo em branco conclui
    que o sistema perdeu os dados, não que o filtro não achou nada.
    """


def _contexto_do_job(job: ExportJob) -> TenantContext:
    """O worker não tem sessão; o tenant vem do job, e as flags também.

    `can_generate_reports` entra no contexto porque a checagem já foi feita na API, na
    hora do pedido — repetir aqui sem a informação real bloquearia um job legítimo.
    """
    return TenantContext(
        tenant_id=job.tenant_id,
        user_id=job.requested_by,
        role="system",
        flags=frozenset({"can_generate_reports"}),
    )


async def _dados(session: AsyncSession, job: ExportJob) -> tuple[list[str], list[list[object]]]:
    """Recalcula o relatório a partir dos filtros guardados no job.

    Recalcular, e não guardar o resultado no pedido: entre o clique e o processamento
    o dado pode ter mudado, e o arquivo tem que refletir o banco no momento em que foi
    gerado — é o que a pessoa vai comparar com a tela.
    """
    contexto = _contexto_do_job(job)
    filtros = job.filters or {}

    if job.kind == "engagement":
        linhas = await EngagementQuery(session, contexto).linhas()
        return (
            ["Pessoa", "Solicitados", "Enviados", "% Engajamento"],
            [[linha.nome, linha.solicitados, linha.enviados, linha.percentual] for linha in linhas],
        )

    if job.kind == "report_360":
        cycle_id = filtros.get("cycle_id")
        department_id = filtros.get("department_id")
        linhas = await Report360Query(session, contexto).linhas(
            cycle_id=UUID(cycle_id) if cycle_id else None,
            department_id=UUID(department_id) if department_id else None,
        )
        return (
            ["Pessoa", "Departamento", "Recebidos", "Respondidos", "% Conclusão", "Nota média"],
            [
                [
                    linha.nome,
                    linha.departamento or "",
                    linha.recebidos,
                    linha.respondidos,
                    linha.percentual,
                    linha.media_nota if linha.media_nota is not None else "",
                ]
                for linha in linhas
            ],
        )

    if job.kind == "client":
        alvo = filtros.get("target_user_id")
        linhas = await ClientReportQuery(session, contexto).linhas(
            target_user_id=UUID(alvo) if alvo else None,
            apenas_negativas=bool(filtros.get("apenas_negativas")),
        )
        return (
            ["Pessoa", "Avaliações", "Respondidas", "Nota média", "Negativas"],
            [
                [
                    linha.nome,
                    linha.avaliacoes,
                    linha.respondidas,
                    linha.media_geral if linha.media_geral is not None else "",
                    linha.negativas,
                ]
                for linha in linhas
            ],
        )

    if job.kind == "executive":
        cycle_id = filtros.get("cycle_id")
        profile_id = filtros.get("profile_id")
        giver_id = filtros.get("giver_id")
        if not cycle_id or not profile_id:
            # Escopo geral não tem relatório executivo por pessoa; a validação da API
            # já barra o caso, e chegar aqui significa job forjado ou spec mudada.
            raise ExportacaoVaziaError("Relatório executivo exige ciclo e pessoa")

        linhas = await ExecutiveDataQuery(session, contexto).respostas_da_pessoa(
            cycle_id=UUID(cycle_id),
            profile_id=UUID(profile_id),
            giver_id=UUID(giver_id) if giver_id else None,
        )
        return (
            ["Pergunta", "Resposta", "Nota"],
            [[p, t or "", n if n is not None else ""] for p, t, n in linhas],
        )

    raise ExportacaoVaziaError(f"Tipo de exportação desconhecido: {job.kind}")


def _caminho(job: ExportJob) -> Path:
    """Um diretório por tenant (AD-09): nada de arquivos de clientes diferentes juntos."""
    base = Path(get_settings().export_dir) / str(job.tenant_id)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{job.kind}-{job.id}.{job.format}"


def _gerar_xlsx(caminho: Path, cabecalho: list[str], linhas: list[list[object]]) -> None:
    from openpyxl import Workbook

    planilha = Workbook()
    aba = planilha.active
    aba.title = "Relatório"
    aba.append(cabecalho)
    for linha in linhas:
        aba.append(list(linha))
    planilha.save(caminho)


def _gerar_pdf(
    caminho: Path, titulo: str, cabecalho: list[str], linhas: list[list[object]]
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    documento = SimpleDocTemplate(str(caminho), pagesize=A4, title=titulo)
    estilos = getSampleStyleSheet()
    tabela = Table(
        [cabecalho] + [[str(c) for c in linha] for linha in linhas], repeatRows=1
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    documento.build(
        [
            Paragraph(titulo, estilos["Title"]),
            Paragraph(
                f"Gerado em {datetime.now(UTC):%d/%m/%Y %H:%M} UTC", estilos["Normal"]
            ),
            Spacer(1, 12),
            tabela,
        ]
    )


async def processar_exportacao(
    session: AsyncSession, mensagem: OutboxMessage, email: EmailAdapter
) -> None:
    """Handler do tópico `export.requested`."""
    job_id = UUID(str(mensagem.payload["job_id"]))
    repo = ExportJobDispatchRepository(session)
    job = await repo.get(job_id)
    if job is None or job.tenant_id != mensagem.tenant_id:
        raise ExportacaoVaziaError(f"Job {job_id} não encontrado neste tenant")

    if job.status == "done":
        # Reprocessamento após uma falha parcial: o arquivo já existe, nada a refazer.
        return

    job.status = "processing"
    cabecalho, linhas = await _dados(session, job)
    if not linhas:
        raise ExportacaoVaziaError("O filtro selecionado não devolveu nenhuma linha")

    caminho = _caminho(job)
    titulo = {
        "report_360": "Relatório de Feedback 360",
        "client": "Relatório de Avaliações de Clientes",
        "engagement": "Relatório de Engajamento",
        "executive": "Relatório Executivo",
    }[job.kind]

    if job.format == "xlsx":
        _gerar_xlsx(caminho, cabecalho, linhas)
    else:
        _gerar_pdf(caminho, titulo, cabecalho, linhas)

    repo.marcar_pronto(job, str(caminho))
    logger.info("export: job %s gerado em %s", job.id, caminho)

    if job.email_to:
        # Último passo, e o único que fala com o mundo. Falhar aqui é registrado e
        # informado, mas não desfaz o arquivo (BR-MIGRAR-030).
        try:
            await email.send(
                to=job.email_to,
                subject=titulo,
                body=(
                    f"O {titulo.lower()} que você pediu está pronto. "
                    "Acesse o sistema para baixá-lo."
                ),
            )
            job.email_sent_at = datetime.now(UTC)
            job.email_error = None
        except Exception as exc:  # noqa: BLE001 — falha de email não invalida o arquivo
            job.email_error = repr(exc)[:1000]
            logger.warning("export: job %s gerado, mas o email falhou: %r", job.id, exc)
