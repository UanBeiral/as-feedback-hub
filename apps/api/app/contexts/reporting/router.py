"""Rotas do contexto `reporting`.

O relatório de cliente exige `can_generate_reports` (BR-MIGRAR-029) — capacidade
individual, não papel. O guard está na assinatura da rota **e** a checagem se repete no
service, porque o mesmo cálculo é chamado pelo worker ao gerar a exportação, onde não
existe rota nenhuma para proteger.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import FileResponse

from app.contexts.engagement.repository import OutboxRepository
from app.contexts.engagement.service import OutboxService
from app.contexts.identity.repository import CoordinatorMemberRepository, ProfileRepository
from app.contexts.identity.service import TeamScopeService
from app.contexts.reporting.queries import (
    ClientReportQuery,
    EngagementQuery,
    Report360Query,
    TeamHistoryQuery,
)
from app.contexts.reporting.repository import ExportJobRepository
from app.contexts.reporting.schemas import (
    ExecutiveReportIn,
    ExportJobOut,
    ExportRequestIn,
    HistoricoDaEquipeOut,
    ItemDeHistoricoOut,
    Linha360Out,
    LinhaClienteOut,
    LinhaEngajamentoOut,
)
from app.contexts.reporting.service import (
    ExportService,
    ReportService,
    validar_escopo_executivo,
)
from app.core.di import SessionDep, TenantDep, require_flag
from app.core.errors import NotFoundError
from app.core.tenancy import TenantContext

router = APIRouter(prefix="/reports", tags=["reporting"])

PodeRelatarDep = Annotated[TenantContext, Depends(require_flag("can_generate_reports"))]


def get_report_service(session: SessionDep, tenant: TenantDep) -> ReportService:
    return ReportService(
        report_360=Report360Query(session, tenant),
        clientes=ClientReportQuery(session, tenant),
        engajamento=EngagementQuery(session, tenant),
    )


def get_export_service(session: SessionDep, tenant: TenantDep) -> ExportService:
    return ExportService(
        jobs=ExportJobRepository(session, tenant),
        outbox=OutboxService(OutboxRepository(session, tenant)),
    )


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]


# ---------------------------------------------------------------- consultas

@router.get("/feedback-360", response_model=list[Linha360Out])
async def relatorio_360(
    tenant: TenantDep,
    service: ReportServiceDep,
    cycle_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
    preview: Annotated[bool, Query()] = False,
) -> list[Linha360Out]:
    """Preview traz 50 linhas; a tabela, 100 (BR-MIGRAR-029).

    O limite é da query, não da renderização: o ponto é não trafegar o que ninguém vai
    olhar.
    """
    linhas = await service.feedback_360(
        cycle_id=cycle_id, department_id=department_id, preview=preview
    )
    return [
        Linha360Out(
            profile_id=linha.profile_id,
            nome=linha.nome,
            departamento=linha.departamento,
            recebidos=linha.recebidos,
            respondidos=linha.respondidos,
            percentual=linha.percentual,
            media_nota=linha.media_nota,
        )
        for linha in linhas
    ]


@router.get("/clients", response_model=list[LinhaClienteOut])
async def relatorio_de_clientes(
    tenant: PodeRelatarDep,
    service: ReportServiceDep,
    target_user_id: Annotated[UUID | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    ate: Annotated[date | None, Query()] = None,
    apenas_negativas: Annotated[bool, Query()] = False,
    preview: Annotated[bool, Query()] = False,
) -> list[LinhaClienteOut]:
    linhas = await service.clientes(
        tenant,
        target_user_id=target_user_id,
        desde=desde,
        ate=ate,
        apenas_negativas=apenas_negativas,
        preview=preview,
    )
    return [
        LinhaClienteOut(
            profile_id=linha.profile_id,
            nome=linha.nome,
            avaliacoes=linha.avaliacoes,
            respondidas=linha.respondidas,
            media_geral=linha.media_geral,
            negativas=linha.negativas,
        )
        for linha in linhas
    ]


@router.get("/engagement", response_model=list[LinhaEngajamentoOut])
async def relatorio_de_engajamento(
    tenant: TenantDep,
    service: ReportServiceDep,
    preview: Annotated[bool, Query()] = False,
) -> list[LinhaEngajamentoOut]:
    """Só ciclos fechados, e sem quem nunca teve request (BR-MIGRAR-028)."""
    linhas = await service.engajamento(preview=preview)
    return [
        LinhaEngajamentoOut(
            profile_id=linha.profile_id,
            nome=linha.nome,
            solicitados=linha.solicitados,
            enviados=linha.enviados,
            percentual=linha.percentual,
        )
        for linha in linhas
    ]


@router.get("/team-history", response_model=HistoricoDaEquipeOut)
async def historico_da_equipe(tenant: TenantDep, session: SessionDep) -> HistoricoDaEquipeOut:
    """Histórico dos três tipos de feedback, dentro do escopo de equipe.

    O escopo sai do `TeamScopeService` e entra na query como lista de ids. Nenhum
    parâmetro desta rota amplia o que a pessoa enxerga — no máximo filtraria dentro
    (PAR-05).
    """
    escopo = TeamScopeService(
        profiles=ProfileRepository(session, tenant),
        coordinator_members=CoordinatorMemberRepository(session, tenant),
    )
    visiveis = await escopo.resolve_visible_profile_ids(tenant)
    historico = TeamHistoryQuery(session, tenant)

    def converter(itens: list[Any]) -> list[ItemDeHistoricoOut]:
        # `asdict` pelo mesmo motivo do diagnóstico: dataclass com `slots` não tem
        # `__dict__`, e a falha só aparece quando existe conteúdo para converter.
        return [ItemDeHistoricoOut(**asdict(item)) for item in itens]

    return HistoricoDaEquipeOut(
        livre=converter(await historico.livre(visiveis)),
        clientes=converter(await historico.clientes(visiveis)),
        ciclos=converter(await historico.ciclos(visiveis)),
    )


# ---------------------------------------------------------------- CSV síncrono

@router.get("/engagement.csv")
async def engajamento_csv(tenant: TenantDep, service: ReportServiceDep) -> Response:
    """CSV com separador `;` — é o que o Excel em português entende (BR-MIGRAR-029)."""
    linhas = await service.engajamento()
    csv = ExportService.para_csv(
        ["Pessoa", "Solicitados", "Enviados", "% Engajamento"],
        [[linha.nome, linha.solicitados, linha.enviados, linha.percentual] for linha in linhas],
        nome="engajamento.csv",
    )
    return Response(
        content=csv.conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{csv.nome_do_arquivo}"'},
    )


@router.get("/feedback-360.csv")
async def relatorio_360_csv(
    tenant: TenantDep,
    service: ReportServiceDep,
    cycle_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> Response:
    """A exportação reflete exatamente os filtros ativos (BR-MIGRAR-029)."""
    linhas = await service.feedback_360(cycle_id=cycle_id, department_id=department_id)
    csv = ExportService.para_csv(
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
        nome="feedback-360.csv",
    )
    return Response(
        content=csv.conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{csv.nome_do_arquivo}"'},
    )


# ---------------------------------------------------------------- exportações

@router.post("/exports", response_model=ExportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def solicitar_exportacao(
    payload: ExportRequestIn,
    tenant: TenantDep,
    session: SessionDep,
    service: ExportServiceDep,
) -> ExportJobOut:
    """202: o pedido foi aceito, o arquivo vem depois (AD-07)."""
    job = await service.solicitar(
        tenant,
        kind=payload.kind,
        formato=payload.format,
        filtros=payload.filters,
        email_to=payload.email_to,
    )
    await session.flush()
    await session.refresh(job)
    return ExportJobOut.de_modelo(job)


@router.post("/executive", response_model=ExportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def relatorio_executivo(
    payload: ExecutiveReportIn,
    tenant: PodeRelatarDep,
    session: SessionDep,
    service: ExportServiceDep,
) -> ExportJobOut:
    """Valida o escopo **antes** de gerar (PAR-04).

    Recusar depois de montar o PDF desperdiça trabalho e, pior, entrega um documento
    com escopo errado.
    """
    validar_escopo_executivo(
        escopo=payload.escopo,
        cycle_id=payload.cycle_id,
        profile_id=payload.profile_id,
        giver_id=payload.giver_id,
    )
    job = await service.solicitar(
        tenant,
        kind="executive",
        formato="pdf",
        filtros={
            "escopo": payload.escopo,
            "cycle_id": str(payload.cycle_id) if payload.cycle_id else None,
            "profile_id": str(payload.profile_id) if payload.profile_id else None,
            "giver_id": str(payload.giver_id) if payload.giver_id else None,
        },
        email_to=payload.email_to,
    )
    await session.flush()
    await session.refresh(job)
    return ExportJobOut.de_modelo(job)


@router.get("/exports", response_model=list[ExportJobOut])
async def minhas_exportacoes(tenant: TenantDep, session: SessionDep) -> list[ExportJobOut]:
    repo = ExportJobRepository(session, tenant)
    return [ExportJobOut.de_modelo(j) for j in await repo.list_do_usuario(tenant.user_id)]


@router.get("/exports/{job_id}", response_model=ExportJobOut)
async def status_da_exportacao(
    job_id: UUID, tenant: TenantDep, session: SessionDep
) -> ExportJobOut:
    job = await ExportJobRepository(session, tenant).get(job_id)
    if job is None or job.requested_by != tenant.user_id:
        raise NotFoundError("Exportação não encontrada")
    return ExportJobOut.de_modelo(job)


@router.get("/exports/{job_id}/download")
async def baixar_exportacao(
    job_id: UUID, tenant: TenantDep, session: SessionDep
) -> FileResponse:
    """Download do arquivo gerado.

    Exige sessão e ser o dono do pedido: o link não é público. Um relatório executivo
    tem o feedback de uma pessoa dentro, e link adivinhável seria o vazamento mais
    caro do sistema.
    """
    job = await ExportJobRepository(session, tenant).get(job_id)
    if job is None or job.requested_by != tenant.user_id or not job.pronto:
        raise NotFoundError("Exportação não encontrada")

    assert job.file_path is not None
    return FileResponse(
        job.file_path,
        filename=f"{job.kind}-{job.id}.{job.format}",
        media_type="application/octet-stream",
    )
