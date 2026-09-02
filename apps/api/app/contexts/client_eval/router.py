"""Rotas do contexto `client_eval` — duas superfícies, uma delas aberta.

`router` é interno e exige sessão como qualquer outro. `public_router` fica sob
`/public/`, sem autenticação, e é o único ponto do sistema alcançável por quem não tem
conta. Três cuidados moram nele:

- O prefixo `/public/` não é cosmético: o Nginx aplica `limit_req` justamente nele
  (AD-06). Rota pública fora desse prefixo nasce sem rate limiting.
- Nenhuma resposta pública distingue "token não existe" de "token já usado".
- Nada do escritório vaza junto do formulário além do nome de quem será avaliado.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.contexts.client_eval.models import ClientEvaluationTag
from app.contexts.client_eval.repository import (
    ClientEvaluationRepository,
    ClientEvaluationTagRepository,
    ClientFormRepository,
    ClientQuestionRepository,
    PublicEvaluationRepository,
    ServiceTagRepository,
)
from app.contexts.client_eval.schemas import (
    ClientFormIn,
    ClientFormOut,
    ClientQuestionIn,
    ClientQuestionOut,
    EvaluationOut,
    PublicFormOut,
    PublicQuestionOut,
    PublicSpontaneousIn,
    PublicSubmitIn,
    PublicSubmitOut,
    RequestEvaluationIn,
    RequestEvaluationOut,
    ServiceTagOut,
)
from app.contexts.client_eval.service import (
    ClientEvaluationService,
    PoliticaDeSinalizacao,
    PublicEvaluationService,
)
from app.contexts.engagement.repository import OutboxRepository, TenantSettingRepository
from app.contexts.engagement.service import OutboxService
from app.contexts.identity.repository import AuthRepository, ProfileRepository
from app.core.config import get_settings
from app.core.di import SessionDep, TenantDep, client_ip, require_flag, require_role
from app.core.errors import NotFoundError
from app.core.tenancy import TenantContext

router = APIRouter(tags=["client_eval"])
public_router = APIRouter(prefix="/public", tags=["public"])

AdminDep = Annotated[TenantContext, Depends(require_role("admin", "rh"))]
# Pedir avaliação de cliente é capacidade individual, não papel (BR-MIGRAR-015).
PodePedirDep = Annotated[TenantContext, Depends(require_flag("can_request_client_feedback"))]


def get_evaluation_service(session: SessionDep, tenant: TenantDep) -> ClientEvaluationService:
    return ClientEvaluationService(
        evaluations=ClientEvaluationRepository(session, tenant),
        forms=ClientFormRepository(session, tenant),
        outbox=OutboxService(OutboxRepository(session, tenant)),
    )


EvaluationServiceDep = Annotated[ClientEvaluationService, Depends(get_evaluation_service)]


# ---------------------------------------------------------------- interno

@router.get("/client-eval/forms", response_model=list[ClientFormOut])
async def list_client_forms(tenant: TenantDep, session: SessionDep) -> list[ClientFormOut]:
    repo = ClientFormRepository(session, tenant)
    return [ClientFormOut.model_validate(f) for f in await repo.list_active()]


@router.post(
    "/client-eval/forms", response_model=ClientFormOut, status_code=status.HTTP_201_CREATED
)
async def create_client_form(
    payload: ClientFormIn, tenant: AdminDep, session: SessionDep
) -> ClientFormOut:
    repo = ClientFormRepository(session, tenant)
    from app.contexts.client_eval.models import ClientEvalForm

    form = repo.add(
        ClientEvalForm(
            name=payload.name, is_default=payload.is_default, is_active=payload.is_active
        )
    )
    await session.flush()
    await session.refresh(form)
    return ClientFormOut.model_validate(form)


@router.post(
    "/client-eval/forms/{form_id}/questions",
    response_model=ClientQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_client_question(
    form_id: UUID, payload: ClientQuestionIn, tenant: AdminDep, session: SessionDep
) -> ClientQuestionOut:
    from app.contexts.client_eval.models import ClientEvalFormQuestion

    perguntas = ClientQuestionRepository(session, tenant)
    ordem = payload.display_order
    if ordem is None:
        existentes = await perguntas.list_by_form(form_id)
        ordem = max((q.display_order for q in existentes), default=-1) + 1

    pergunta = perguntas.add(
        ClientEvalFormQuestion(
            form_id=form_id,
            question_text=payload.question_text,
            question_type=payload.question_type,
            is_required=payload.is_required,
            display_order=ordem,
            placeholder=payload.placeholder,
        )
    )
    await session.flush()
    await session.refresh(pergunta)
    return ClientQuestionOut.model_validate(pergunta)


@router.post(
    "/client-eval/requests",
    response_model=RequestEvaluationOut,
    status_code=status.HTTP_201_CREATED,
)
async def request_evaluation(
    payload: RequestEvaluationIn,
    tenant: PodePedirDep,
    session: SessionDep,
    service: EvaluationServiceDep,
) -> RequestEvaluationOut:
    """Gera o link para mandar ao cliente. O token só sai aqui."""
    avaliacao = await service.request_evaluation(
        tenant,
        target_user_id=payload.target_user_id,
        form_id=payload.form_id,
        client_name=payload.client_name,
        client_whatsapp=payload.client_whatsapp,
        client_email=payload.client_email,
        dias_de_validade=payload.dias_de_validade,
    )
    await session.flush()
    await session.refresh(avaliacao)
    assert avaliacao.token is not None and avaliacao.token_expires_at is not None
    return RequestEvaluationOut(
        id=avaliacao.id,
        token=avaliacao.token,
        token_expires_at=avaliacao.token_expires_at,
        public_path=f"/avaliacao/{avaliacao.token}",
    )


@router.get("/client-eval/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(
    tenant: TenantDep,
    session: SessionDep,
    status_filtro: Annotated[list[str] | None, Query(alias="status")] = None,
) -> list[EvaluationOut]:
    """WhatsApp completo só para admin/RH; para o resto, mascarado (BR-MIGRAR-022)."""
    repo = ClientEvaluationRepository(session, tenant)
    avaliacoes = await repo.list_por_status(*(status_filtro or []))
    completo = tenant.has_role("admin", "rh")
    return [EvaluationOut.de_modelo(a, whatsapp_completo=completo) for a in avaliacoes]


@router.get("/client-eval/evaluations/mine", response_model=list[EvaluationOut])
async def my_evaluations(tenant: TenantDep, session: SessionDep) -> list[EvaluationOut]:
    """As avaliações que o próprio usuário recebeu de clientes."""
    repo = ClientEvaluationRepository(session, tenant)
    return [
        EvaluationOut.de_modelo(a, whatsapp_completo=False)
        for a in await repo.list_do_avaliado(tenant.user_id)
    ]


@router.get("/client-eval/service-tags", response_model=list[ServiceTagOut])
async def list_service_tags(tenant: TenantDep, session: SessionDep) -> list[ServiceTagOut]:
    repo = ServiceTagRepository(session, tenant)
    return [ServiceTagOut.model_validate(t) for t in await repo.list_active()]


# ---------------------------------------------------------------- público

async def _politica(session: SessionDep, tenant_id: UUID) -> PoliticaDeSinalizacao:
    """Lê a política de sinalização do tenant dono da avaliação (BR-MIGRAR-021)."""
    contexto = TenantContext(
        tenant_id=tenant_id, user_id=tenant_id, role="public", flags=frozenset()
    )
    settings = await TenantSettingRepository(session, contexto).list_all_settings()
    return PoliticaDeSinalizacao.de_settings({s.key: s.value for s in settings})


def _outbox_factory(session: SessionDep):
    """Outbox escopado no tenant que o token resolveu — não antes."""

    def _para(tenant_id: UUID) -> OutboxService:
        contexto = TenantContext(
            tenant_id=tenant_id, user_id=tenant_id, role="public", flags=frozenset()
        )
        return OutboxService(OutboxRepository(session, contexto))

    return _para


@public_router.get("/evaluations/{token}", response_model=PublicFormOut)
async def open_public_form(token: str, session: SessionDep) -> PublicFormOut:
    """Abre o formulário dinâmico pelo token (PAR-03).

    Token inválido, expirado ou já usado devolvem a mesma recusa — quem tem o link não
    descobre por aqui se ele um dia valeu.
    """
    publico = PublicEvaluationRepository(session)
    service = PublicEvaluationService(publico, _outbox_factory(session), PoliticaDeSinalizacao())
    avaliacao, perguntas = await service.open_by_token(token)

    contexto = TenantContext(
        tenant_id=avaliacao.tenant_id,
        user_id=avaliacao.tenant_id,
        role="public",
        flags=frozenset(),
    )
    tags = await ServiceTagRepository(session, contexto).list_active()
    avaliado = await ProfileRepository(session, contexto).get(avaliacao.target_user_id)

    return PublicFormOut(
        questions=[PublicQuestionOut.model_validate(q) for q in perguntas],
        service_tags=[ServiceTagOut.model_validate(t) for t in tags],
        target_name=avaliado.full_name if avaliado else None,
    )


@public_router.post("/evaluations/{token}", response_model=PublicSubmitOut)
async def submit_public_form(
    token: str, payload: PublicSubmitIn, request: Request, session: SessionDep
) -> PublicSubmitOut:
    """Submissão idempotente (PAR-03 @idempotencia).

    Segunda submissão com o mesmo token devolve a **mesma confirmação**, sem erro: o
    cliente que clicou duas vezes não fez nada errado.
    """
    publico = PublicEvaluationRepository(session)
    avaliacao_previa = await publico.get_por_token(token)
    if avaliacao_previa is None:
        raise NotFoundError("Link inválido ou expirado")

    service = PublicEvaluationService(
        publico,
        _outbox_factory(session),
        await _politica(session, avaliacao_previa.tenant_id),
    )
    resultado = await service.submit_by_token(
        token,
        respostas=payload.como_mapa(),
        client_name=payload.client_name,
        client_whatsapp=payload.client_whatsapp,
        client_email=payload.client_email,
        contact_motivation=payload.contact_motivation,
        contact_motivation_text=payload.contact_motivation_text,
        overall_rating=payload.overall_rating,
        recommendation_rating=payload.recommendation_rating,
        tracking_data={"ip": client_ip(request), "user_agent": request.headers.get("user-agent")},
    )

    if not resultado.ja_respondida and payload.service_tag_ids:
        contexto = TenantContext(
            tenant_id=resultado.evaluation.tenant_id,
            user_id=resultado.evaluation.tenant_id,
            role="public",
            flags=frozenset(),
        )
        tags = ClientEvaluationTagRepository(session, contexto)
        validas = {t.id for t in await ServiceTagRepository(session, contexto).list_active()}
        for tag_id in payload.service_tag_ids:
            if tag_id in validas:
                tags.add(
                    ClientEvaluationTag(evaluation_id=resultado.evaluation.id, tag_id=tag_id)
                )

    return PublicSubmitOut()


@public_router.post(
    "/evaluations", response_model=PublicSubmitOut, status_code=status.HTTP_201_CREATED
)
async def spontaneous_evaluation(
    payload: PublicSpontaneousIn, request: Request, session: SessionDep
) -> PublicSubmitOut:
    """Fluxo espontâneo — sem convite, sem token (AMB-002).

    Nasce **desligado** por tenant e só existe quando alguém liga a chave: um endpoint
    que cria registro sem convite é superfície de spam aberta na internet. Enquanto o
    tenant não habilitar, responde recusa.

    Sem token, o tenant vem da configuração de instalação (`DEFAULT_TENANT_SLUG`) — é o
    mesmo caminho do login enquanto houver um escritório só. Quando entrar o segundo,
    aqui e o login passam a resolver por subdomínio, juntos.
    """
    tenant_row = await AuthRepository(session).get_tenant_by_slug(
        get_settings().default_tenant_slug
    )
    if tenant_row is None:
        raise NotFoundError("Instalação não encontrada")

    contexto = TenantContext(
        tenant_id=tenant_row.id, user_id=tenant_row.id, role="public", flags=frozenset()
    )
    settings_do_tenant = {
        s.key: s.value
        for s in await TenantSettingRepository(session, contexto).list_all_settings()
    }
    habilitado = (settings_do_tenant.get("client_eval_spontaneous_enabled") or "false") == "true"

    formulario = await ClientFormRepository(session, contexto).get_default()
    if formulario is None:
        raise NotFoundError("Formulário público não configurado")

    service = PublicEvaluationService(
        PublicEvaluationRepository(session),
        _outbox_factory(session),
        PoliticaDeSinalizacao.de_settings(settings_do_tenant),
    )
    await service.criar_espontanea(
        tenant_id=tenant_row.id,
        form_id=formulario.id,
        target_user_id=payload.target_user_id,
        habilitado=habilitado,
        respostas=payload.como_mapa(),
        client_name=payload.client_name,
        client_whatsapp=payload.client_whatsapp,
        client_email=payload.client_email,
        contact_motivation=payload.contact_motivation,
        contact_motivation_text=payload.contact_motivation_text,
        overall_rating=payload.overall_rating,
        recommendation_rating=payload.recommendation_rating,
        tracking_data={"ip": client_ip(request), "user_agent": request.headers.get("user-agent")},
    )
    return PublicSubmitOut()
