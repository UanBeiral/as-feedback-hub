"""Rotas do contexto `feedback`.

Duas coisas que a spec cobra e que ficam visíveis já na assinatura das rotas:

- **A invariante falha na API, não na UI** (PAR-01). No legado, quem não era admin
  simplesmente não via o botão de abrir ciclo — chamar a API direto funcionava. Aqui
  `AdminDep` está na assinatura de `POST /cycles/{id}/open`, e a negação é do servidor.
- **Progresso vem de um lugar só** (PAR-04). A rota de progresso chama o mesmo
  `CycleProgressService` que qualquer dashboard usará; não existe cálculo alternativo
  para "a tela do gestor".
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.contexts.engagement.repository import AuditLogRepository, OutboxRepository
from app.contexts.engagement.service import AuditService, OutboxService
from app.contexts.feedback.diagnostics import DiagnosticsService
from app.contexts.feedback.repository import (
    AnswerRepository,
    CycleNoteRepository,
    CycleRepository,
    FormRepository,
    FreeFeedbackRepository,
    PermissionRepository,
    QuestionRepository,
    RequestRepository,
)
from app.contexts.feedback.schemas import (
    AnswerOut,
    AnswersIn,
    AtividadeDoCicloOut,
    CancelIn,
    ConclusaoDoDepartamentoOut,
    CycleIn,
    CycleNoteIn,
    CycleNoteOut,
    CycleOut,
    DashboardOut,
    DiagnosticoOut,
    ExtendIn,
    FormIn,
    FormOut,
    FreeFeedbackIn,
    FreeFeedbackOut,
    MembroDaEquipeOut,
    OpenCycleOut,
    ParDePermissaoOut,
    PermissionIn,
    PermissionOut,
    PessoaComCargaOut,
    ProgressOut,
    QuestionIn,
    QuestionOut,
    ReorderIn,
    RequestDetailOut,
    RequestOut,
    TeamProgressOut,
)
from app.contexts.feedback.service import (
    CycleNoteService,
    CycleProgressService,
    CycleService,
    DashboardService,
    FormService,
    FreeFeedbackService,
    PermissionService,
    RequestService,
    TeamProgressService,
)
from app.contexts.identity.repository import CoordinatorMemberRepository, ProfileRepository
from app.contexts.identity.service import TeamScopeService
from app.core.di import SessionDep, TenantDep, require_role
from app.core.tenancy import TenantContext

router = APIRouter(tags=["feedback"])

AdminDep = Annotated[TenantContext, Depends(require_role("admin", "rh"))]
# Cancelar request é ato de gestão sobre o trabalho de outra pessoa.
GestaoDep = Annotated[TenantContext, Depends(require_role("admin", "rh", "gestor"))]


def get_form_service(session: SessionDep, tenant: TenantDep) -> FormService:
    return FormService(FormRepository(session, tenant), QuestionRepository(session, tenant))


def get_permission_service(session: SessionDep, tenant: TenantDep) -> PermissionService:
    return PermissionService(PermissionRepository(session, tenant))


async def get_cycle_service(session: SessionDep, tenant: TenantDep) -> CycleService:
    return CycleService(
        cycles=CycleRepository(session, tenant),
        permissions=PermissionRepository(session, tenant),
        requests=RequestRepository(session, tenant),
        outbox=OutboxService(OutboxRepository(session, tenant)),
        # A elegibilidade sai de `identity`: só perfil ativo participa da geração
        # (BR-MIGRAR-001).
        perfis_ativos=await ProfileRepository(session, tenant).list_active_ids(),
    )


def get_request_service(session: SessionDep, tenant: TenantDep) -> RequestService:
    outbox = OutboxService(OutboxRepository(session, tenant))
    return RequestService(
        requests=RequestRepository(session, tenant),
        answers=AnswerRepository(session, tenant),
        questions=QuestionRepository(session, tenant),
        outbox=outbox,
        audit=AuditService(AuditLogRepository(session, tenant), outbox),
    )


def get_progress_service(session: SessionDep, tenant: TenantDep) -> CycleProgressService:
    return CycleProgressService(RequestRepository(session, tenant))


def get_dashboard_service(session: SessionDep, tenant: TenantDep) -> DashboardService:
    requests = RequestRepository(session, tenant)
    return DashboardService(
        requests=requests,
        cycles=CycleRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
        progresso=CycleProgressService(requests),
    )


def get_team_progress_service(session: SessionDep, tenant: TenantDep) -> TeamProgressService:
    return TeamProgressService(
        requests=RequestRepository(session, tenant),
        cycles=CycleRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
    )


def get_team_scope(session: SessionDep, tenant: TenantDep) -> TeamScopeService:
    """Mesma construção de `identity`: o escopo é resolvido lá e consumido aqui.

    Não é duplicação de regra — a regra continua sendo uma só, em `TeamScopeService`.
    É só a fábrica, que o FastAPI precisa ter no módulo que declara a rota.
    """
    return TeamScopeService(
        profiles=ProfileRepository(session, tenant),
        coordinator_members=CoordinatorMemberRepository(session, tenant),
    )


FormServiceDep = Annotated[FormService, Depends(get_form_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
CycleServiceDep = Annotated[CycleService, Depends(get_cycle_service)]
RequestServiceDep = Annotated[RequestService, Depends(get_request_service)]
ProgressServiceDep = Annotated[CycleProgressService, Depends(get_progress_service)]
TeamProgressServiceDep = Annotated[TeamProgressService, Depends(get_team_progress_service)]
TeamScopeDep = Annotated[TeamScopeService, Depends(get_team_scope)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


# ---------------------------------------------------------------- formulários

@router.get("/forms", response_model=list[FormOut])
async def list_forms(tenant: TenantDep, session: SessionDep) -> list[FormOut]:
    repo = FormRepository(session, tenant)
    return [FormOut.model_validate(f) for f in await repo.list_active()]


@router.post("/forms", response_model=FormOut, status_code=status.HTTP_201_CREATED)
async def create_form(
    payload: FormIn, tenant: AdminDep, session: SessionDep, service: FormServiceDep
) -> FormOut:
    form = await service.create(name=payload.name, description=payload.description)
    await session.flush()
    await session.refresh(form)
    return FormOut.model_validate(form)


@router.get("/forms/{form_id}/questions", response_model=list[QuestionOut])
async def list_questions(
    form_id: UUID, tenant: TenantDep, session: SessionDep
) -> list[QuestionOut]:
    repo = QuestionRepository(session, tenant)
    return [QuestionOut.model_validate(q) for q in await repo.list_by_form(form_id)]


@router.post(
    "/forms/{form_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED
)
async def add_question(
    form_id: UUID,
    payload: QuestionIn,
    tenant: AdminDep,
    session: SessionDep,
    service: FormServiceDep,
) -> QuestionOut:
    pergunta = await service.add_question(
        form_id,
        question_text=payload.question_text,
        question_type=payload.question_type,
        required=payload.required,
        help_text=payload.help_text,
        sort_order=payload.sort_order,
    )
    await session.flush()
    await session.refresh(pergunta)
    return QuestionOut.model_validate(pergunta)


@router.put("/forms/{form_id}/questions/order", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_questions(
    form_id: UUID, payload: ReorderIn, tenant: AdminDep, service: FormServiceDep
) -> None:
    await service.reorder(form_id, payload.question_ids)


@router.post("/forms/{form_id}/archive", response_model=FormOut)
async def archive_form(form_id: UUID, tenant: AdminDep, service: FormServiceDep) -> FormOut:
    return FormOut.model_validate(await service.archive(form_id))


# ---------------------------------------------------------------- permissões

@router.get("/permissions/diagnostics", response_model=DiagnosticoOut)
async def diagnostico_de_permissoes(tenant: AdminDep, session: SessionDep) -> DiagnosticoOut:
    """O que vai dar errado no próximo ciclo — antes de ele abrir.

    Declarada acima de `/permissions` com parâmetro de propósito: caminho literal
    precisa vir antes de rota com placeholder, senão `diagnostics` seria lido como id.
    """
    service = DiagnosticsService(
        permissions=PermissionRepository(session, tenant),
        cycles=CycleRepository(session, tenant),
        requests=RequestRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
    )
    d = await service.gerar()
    return DiagnosticoOut(
        pontos_de_atencao=d.pontos_de_atencao,
        ciclo_ativo=d.ciclo_ativo.name if d.ciclo_ativo else None,
        dias_para_fechar=d.dias_para_fechar,
        permissoes_ativas=d.permissoes_ativas,
        usuarios_ativos=d.usuarios_ativos,
        requests_a_criar=d.requests_a_criar,
        # `asdict`, e não `vars`: as dataclasses do diagnóstico usam `slots=True` e
        # portanto não têm `__dict__`. Com as listas vazias o erro não aparecia — só
        # com dado de verdade, que é o pior momento para descobrir.
        sem_request=[ParDePermissaoOut(**asdict(p)) for p in d.sem_request],
        par_reverso_faltando=[ParDePermissaoOut(**asdict(p)) for p in d.par_reverso_faltando],
        sem_cobertura=[PessoaComCargaOut(**asdict(p)) for p in d.sem_cobertura],
        com_usuario_inativo=[ParDePermissaoOut(**asdict(p)) for p in d.com_usuario_inativo],
        media_por_avaliador=d.media_por_avaliador,
        media_por_avaliado=d.media_por_avaliado,
        poucos_avaliadores=[PessoaComCargaOut(**asdict(p)) for p in d.poucos_avaliadores],
        poucos_avaliados=[PessoaComCargaOut(**asdict(p)) for p in d.poucos_avaliados],
    )


@router.post("/permissions/deactivate-inactive")
async def desativar_permissoes_com_inativos(
    tenant: AdminDep, session: SessionDep
) -> dict[str, int]:
    """Ação em massa do diagnóstico: desliga o que aponta para quem saiu."""
    service = DiagnosticsService(
        permissions=PermissionRepository(session, tenant),
        cycles=CycleRepository(session, tenant),
        requests=RequestRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
    )
    return {"desativadas": await service.desativar_permissoes_com_inativos()}


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    tenant: AdminDep,
    session: SessionDep,
    cycle_id: Annotated[UUID | None, Query()] = None,
) -> list[PermissionOut]:
    repo = PermissionRepository(session, tenant)
    regras = (
        await repo.list_ativas_para_ciclo(cycle_id)
        if cycle_id is not None
        else await repo.list_all()
    )
    return [PermissionOut.model_validate(r) for r in regras]


@router.post("/permissions", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
async def save_permission(
    payload: PermissionIn,
    tenant: AdminDep,
    session: SessionDep,
    service: PermissionServiceDep,
) -> PermissionOut:
    """`peer_to_peer` cria a recíproca na mesma transação (BR-MIGRAR-002)."""
    regra = await service.save(
        reviewer_id=payload.reviewer_id,
        reviewee_id=payload.reviewee_id,
        permission_type=payload.permission_type,
        cycle_id=payload.cycle_id,
        active=payload.active,
    )
    await session.flush()
    await session.refresh(regra)
    return PermissionOut.model_validate(regra)


# ---------------------------------------------------------------- ciclos

@router.get("/cycles", response_model=list[CycleOut])
async def list_cycles(
    tenant: TenantDep,
    session: SessionDep,
    status_filtro: Annotated[list[str] | None, Query(alias="status")] = None,
) -> list[CycleOut]:
    repo = CycleRepository(session, tenant)
    return [CycleOut.model_validate(c) for c in await repo.list_by_status(*(status_filtro or []))]


@router.post("/cycles", response_model=CycleOut, status_code=status.HTTP_201_CREATED)
async def create_cycle(
    payload: CycleIn, tenant: AdminDep, session: SessionDep, service: CycleServiceDep
) -> CycleOut:
    cycle = await service.create(
        name=payload.name,
        form_id=payload.form_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        frequency=payload.frequency,
        evaluated_start=payload.evaluated_start,
        evaluated_end=payload.evaluated_end,
    )
    await session.flush()
    await session.refresh(cycle)
    return CycleOut.model_validate(cycle)


@router.post("/cycles/{cycle_id}/open", response_model=OpenCycleOut)
async def open_cycle(
    cycle_id: UUID, tenant: AdminDep, service: CycleServiceDep
) -> OpenCycleOut:
    """Um comando: estado, requests e evento na mesma transação (PAR-01)."""
    resultado = await service.open(cycle_id)
    return OpenCycleOut(
        cycle=CycleOut.model_validate(resultado.cycle),
        requests_criados=resultado.requests_criados,
        pares_elegiveis=resultado.pares_elegiveis,
    )


@router.post("/cycles/{cycle_id}/regenerate-requests", response_model=OpenCycleOut)
async def regenerate_requests(
    cycle_id: UUID, tenant: AdminDep, service: CycleServiceDep
) -> OpenCycleOut:
    resultado = await service.regenerate_requests(cycle_id)
    return OpenCycleOut(
        cycle=CycleOut.model_validate(resultado.cycle),
        requests_criados=resultado.requests_criados,
        pares_elegiveis=resultado.pares_elegiveis,
    )


@router.post("/cycles/{cycle_id}/close", response_model=CycleOut)
async def close_cycle(cycle_id: UUID, tenant: AdminDep, service: CycleServiceDep) -> CycleOut:
    return CycleOut.model_validate(await service.close(cycle_id))


@router.post("/cycles/{cycle_id}/publish", response_model=CycleOut)
async def publish_cycle(cycle_id: UUID, tenant: AdminDep, service: CycleServiceDep) -> CycleOut:
    return CycleOut.model_validate(await service.publish(cycle_id))


@router.post("/cycles/{cycle_id}/archive", response_model=CycleOut)
async def archive_cycle(cycle_id: UUID, tenant: AdminDep, service: CycleServiceDep) -> CycleOut:
    return CycleOut.model_validate(await service.archive(cycle_id))


@router.post("/cycles/{cycle_id}/extend", response_model=CycleOut)
async def extend_cycle(
    cycle_id: UUID, payload: ExtendIn, tenant: AdminDep, service: CycleServiceDep
) -> CycleOut:
    """Estender o período avaliado adia o fechamento automático (BR-MIGRAR-006)."""
    return CycleOut.model_validate(
        await service.extend_evaluated_period(cycle_id, evaluated_end=payload.evaluated_end)
    )


@router.get("/cycles/{cycle_id}/progress", response_model=ProgressOut)
async def cycle_progress(
    cycle_id: UUID, tenant: TenantDep, service: ProgressServiceDep
) -> ProgressOut:
    progresso = await service.calcular(cycle_id)
    return ProgressOut(
        total=progresso.total,
        concluidos=progresso.concluidos,
        pendentes=progresso.pendentes,
        atrasados=progresso.atrasados,
        excluidos=progresso.excluidos,
        percentual=progresso.percentual,
    )


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(service: DashboardServiceDep) -> DashboardOut:
    """Agregados do painel inicial (SCR-0003).

    Aberta a qualquer sessão, e não só ao admin: os números são do escritório inteiro e
    o legado já os mostrava ao gestor. Nada de pessoa sai daqui além de contagens e do
    par avaliador/avaliado da atividade recente, que qualquer um do escritório já vê.
    """
    painel = await service.montar()
    return DashboardOut(
        cycle_id=painel.ciclo.id if painel.ciclo else None,
        cycle_name=painel.ciclo.name if painel.ciclo else None,
        cycle_end_date=painel.ciclo.end_date if painel.ciclo else None,
        progresso=ProgressOut(
            total=painel.progresso.total,
            concluidos=painel.progresso.concluidos,
            pendentes=painel.progresso.pendentes,
            atrasados=painel.progresso.atrasados,
            excluidos=painel.progresso.excluidos,
            percentual=painel.progresso.percentual,
        ),
        pessoas_ativas=painel.pessoas_por_status.get("active", 0),
        # Inativo e removido caem juntos: para o painel a pergunta é "quem não está
        # trabalhando", e a diferença entre desligado e suspenso é da tela de usuários.
        pessoas_inativas=(
            painel.pessoas_por_status.get("inactive", 0)
            + painel.pessoas_por_status.get("deleted", 0)
        ),
        por_departamento=[
            ConclusaoDoDepartamentoOut(
                nome=d.nome, esperados=d.esperados, enviados=d.enviados, percentual=d.percentual
            )
            for d in painel.por_departamento
        ],
        atividade=[
            AtividadeDoCicloOut(quando=a.quando, avaliador=a.avaliador, avaliado=a.avaliado)
            for a in painel.atividade
        ],
        total_de_feedbacks=painel.total_de_feedbacks,
        total_enviados=painel.total_enviados,
    )


@router.get("/team/progress", response_model=TeamProgressOut)
async def team_progress(
    tenant: TenantDep,
    scope: TeamScopeDep,
    service: TeamProgressServiceDep,
) -> TeamProgressOut:
    """Acompanhamento da equipe no ciclo aberto (SCR-0030).

    O escopo sai de `TeamScopeService`, o mesmo de `/auth/my-team` — nada aqui amplia o
    que aquele serviço devolveu (R-04 / R-09). Quem está olhando sai da própria lista:
    o escopo inclui a pessoa porque ela pode ver o próprio histórico, e esta tela
    responde outra pergunta.
    """
    visiveis = await scope.resolve_visible_profile_ids(tenant)
    acompanhamento = await service.acompanhar(visiveis, exceto=tenant.user_id)
    return TeamProgressOut(
        cycle_id=acompanhamento.ciclo_id,
        cycle_name=acompanhamento.ciclo_nome,
        membros=[
            MembroDaEquipeOut(
                profile_id=m.profile_id,
                full_name=m.full_name,
                job_title=m.job_title,
                role=m.role,
                is_coordinator=m.is_coordinator,
                status=m.status,
                pendentes_de_enviar=m.pendentes_de_enviar,
                enviados=m.enviados,
                pendentes_de_leitura=m.pendentes_de_leitura,
                percentual=m.percentual,
            )
            for m in acompanhamento.membros
        ],
        total_membros=acompanhamento.total_membros,
        enviados=acompanhamento.enviados,
        esperados=acompanhamento.esperados,
        percentual=acompanhamento.percentual,
    )


# ---------------------------------------------------------------- requests

async def _nomes_dos_envolvidos(
    session: SessionDep, tenant: TenantDep, requests: list
) -> dict[UUID, str]:
    """Resolve uuid → nome para as duas pontas dos pedidos, numa consulta só.

    Uma consulta, e não uma por pedido: a lista costuma repetir as mesmas pessoas, e o
    conjunto colapsa isso antes de ir ao banco.
    """
    ids = {r.giver_id for r in requests} | {r.receiver_id for r in requests}
    if not ids:
        return {}
    perfis = await ProfileRepository(session, tenant).list_by_ids(ids)
    return {p.id: p.full_name for p in perfis}


@router.get("/requests/mine", response_model=list[RequestOut])
async def my_requests(
    tenant: TenantDep,
    session: SessionDep,
    incluir_enviados: Annotated[bool, Query(alias="incluir_enviados")] = False,
) -> list[RequestOut]:
    repo = RequestRepository(session, tenant)
    status_alvo = ("pending", "draft", "submitted") if incluir_enviados else ("pending", "draft")
    pedidos = await repo.list_para_avaliador(tenant.user_id, status=status_alvo)
    nomes = await _nomes_dos_envolvidos(session, tenant, pedidos)
    return [RequestOut.de_modelo(r, nomes) for r in pedidos]


@router.get("/requests/{request_id}", response_model=RequestDetailOut)
async def request_detail(
    request_id: UUID, tenant: TenantDep, session: SessionDep
) -> RequestDetailOut:
    """Traz perguntas e respostas juntas — é o que o formulário precisa para retomar."""
    requests = RequestRepository(session, tenant)
    request = await requests.get(request_id)
    if request is None or request.giver_id != tenant.user_id:
        from app.core.errors import NotFoundError

        raise NotFoundError("Request não encontrado")

    perguntas = await QuestionRepository(session, tenant).list_by_form(request.form_id)
    respostas = await AnswerRepository(session, tenant).list_do_request(request_id)
    nomes = await _nomes_dos_envolvidos(session, tenant, [request])
    return RequestDetailOut(
        **RequestOut.de_modelo(request, nomes).model_dump(),
        questions=[QuestionOut.model_validate(q) for q in perguntas],
        answers=[AnswerOut.model_validate(a) for a in respostas],
    )


@router.get("/requests/received", response_model=list[RequestOut])
async def received_requests(tenant: TenantDep, session: SessionDep) -> list[RequestOut]:
    """Feedbacks que a pessoa recebeu. `read_at` nulo é o que o sino conta."""
    repo = RequestRepository(session, tenant)
    recebidos = await repo.list_recebidos(tenant.user_id)
    nomes = await _nomes_dos_envolvidos(session, tenant, recebidos)
    return [RequestOut.de_modelo(r, nomes) for r in recebidos]


@router.post("/requests/{request_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_request_read(
    request_id: UUID, tenant: TenantDep, service: RequestServiceDep
) -> None:
    await service.mark_read(tenant, request_id)


@router.put("/requests/{request_id}/draft", response_model=RequestOut)
async def save_draft(
    request_id: UUID, payload: AnswersIn, tenant: TenantDep, service: RequestServiceDep
) -> RequestOut:
    return RequestOut.model_validate(
        await service.save_draft(tenant, request_id, payload.como_mapa())
    )


@router.post("/requests/{request_id}/submit", response_model=RequestOut)
async def submit_request(
    request_id: UUID, payload: AnswersIn, tenant: TenantDep, service: RequestServiceDep
) -> RequestOut:
    return RequestOut.model_validate(
        await service.submit(tenant, request_id, payload.como_mapa())
    )


@router.post("/requests/{request_id}/waive", response_model=RequestOut)
async def waive_request(
    request_id: UUID, tenant: TenantDep, service: RequestServiceDep
) -> RequestOut:
    return RequestOut.model_validate(await service.waive(tenant, request_id))


@router.post("/requests/{request_id}/resume", response_model=RequestOut)
async def resume_request(
    request_id: UUID, tenant: TenantDep, service: RequestServiceDep
) -> RequestOut:
    return RequestOut.model_validate(await service.resume(tenant, request_id))


@router.post("/requests/{request_id}/cancel", response_model=RequestOut)
async def cancel_request(
    request_id: UUID, payload: CancelIn, tenant: GestaoDep, service: RequestServiceDep
) -> RequestOut:
    """Cancelar exige justificativa e registra auditoria com `actor_id` (PAR-02)."""
    return RequestOut.model_validate(
        await service.cancel(tenant, request_id, justificativa=payload.justificativa)
    )


# ---------------------------------------------------------------- feedback livre

@router.post(
    "/free-feedbacks", response_model=FreeFeedbackOut, status_code=status.HTTP_201_CREATED
)
async def send_free_feedback(
    payload: FreeFeedbackIn, tenant: TenantDep, session: SessionDep
) -> FreeFeedbackOut:
    service = FreeFeedbackService(FreeFeedbackRepository(session, tenant))
    feedback = await service.send(
        tenant,
        receiver_id=payload.receiver_id,
        is_anonymous=payload.is_anonymous,
        is_sensitive=payload.is_sensitive,
        positives=payload.positives,
        improvements=payload.improvements,
        message=payload.message,
    )
    await session.flush()
    await session.refresh(feedback)
    return FreeFeedbackOut.model_validate(feedback)


@router.get("/free-feedbacks/received", response_model=list[FreeFeedbackOut])
async def received_free_feedbacks(
    tenant: TenantDep, session: SessionDep
) -> list[FreeFeedbackOut]:
    """O sensível não aparece para o destinatário — só para a gestão."""
    repo = FreeFeedbackRepository(session, tenant)
    recebidos = await repo.list_recebidos(tenant.user_id, gestao=tenant.has_role("admin", "rh"))
    return [FreeFeedbackOut.model_validate(f) for f in recebidos]


@router.get("/free-feedbacks/sensitive", response_model=list[FreeFeedbackOut])
async def sensitive_free_feedbacks(
    tenant: AdminDep, session: SessionDep
) -> list[FreeFeedbackOut]:
    repo = FreeFeedbackRepository(session, tenant)
    return [FreeFeedbackOut.model_validate(f) for f in await repo.list_sensiveis()]


@router.post("/free-feedbacks/{feedback_id}/read", response_model=FreeFeedbackOut)
async def read_free_feedback(
    feedback_id: UUID, tenant: TenantDep, session: SessionDep
) -> FreeFeedbackOut:
    service = FreeFeedbackService(FreeFeedbackRepository(session, tenant))
    return FreeFeedbackOut.model_validate(await service.mark_read(tenant, feedback_id))


# ---------------------------------------------------------------- caderno do ciclo

@router.get("/cycle-notes", response_model=list[CycleNoteOut])
async def my_notes(
    tenant: TenantDep,
    session: SessionDep,
    cycle_id: Annotated[UUID | None, Query()] = None,
) -> list[CycleNoteOut]:
    """Anotação é privada do autor: a listagem nunca sai do próprio `user_id`."""
    repo = CycleNoteRepository(session, tenant)
    return [
        CycleNoteOut.model_validate(n) for n in await repo.list_do_autor(tenant.user_id, cycle_id)
    ]


@router.post("/cycle-notes", response_model=CycleNoteOut, status_code=status.HTTP_201_CREATED)
async def write_note(
    payload: CycleNoteIn, tenant: TenantDep, session: SessionDep
) -> CycleNoteOut:
    service = CycleNoteService(CycleNoteRepository(session, tenant))
    nota = await service.write(
        tenant,
        cycle_id=payload.cycle_id,
        about_user_id=payload.about_user_id,
        content=payload.content,
        is_audio_transcription=payload.is_audio_transcription,
    )
    await session.flush()
    await session.refresh(nota)
    return CycleNoteOut.model_validate(nota)


@router.delete("/cycle-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: UUID, tenant: TenantDep, session: SessionDep) -> None:
    service = CycleNoteService(CycleNoteRepository(session, tenant))
    await service.delete(tenant, note_id)
