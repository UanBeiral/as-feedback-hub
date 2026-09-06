"""Rotas do contexto `client_eval` — duas superfícies, uma delas aberta.

`router` é interno e exige sessão como qualquer outro. `public_router` fica sob
`/public/`, sem autenticação, e é o único ponto do sistema alcançável por quem não tem
conta. Três cuidados moram nele:

- O prefixo `/public/` não é cosmético: o Nginx aplica `limit_req` justamente nele
  (AD-06). Rota pública fora desse prefixo nasce sem rate limiting.
- Nenhuma resposta pública distingue "token não existe" de "token já usado".
- Do escritório só saem o nome de quem será avaliado, o nome da empresa e quais
  motivações estão ligadas — o suficiente para desenhar o wizard, nada além disso.
"""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.contexts.client_eval.models import ClientEvaluationTag
from app.contexts.client_eval.repository import (
    ClientAnswerRepository,
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
    ClientQuestionUpdateIn,
    EvaluationDetailOut,
    EvaluationOut,
    PublicFormOut,
    PublicQuestionOut,
    PublicSpontaneousIn,
    PublicSubmitIn,
    PublicSubmitOut,
    ReordenarPerguntasIn,
    RequestEvaluationIn,
    RequestEvaluationOut,
    RespostaDoClienteOut,
    ServiceTagOut,
)
from app.contexts.client_eval.service import (
    ClientEvaluationService,
    PoliticaDeSinalizacao,
    PublicEvaluationService,
)
from app.contexts.engagement.repository import OutboxRepository, TenantSettingRepository
from app.contexts.engagement.service import OutboxService
from app.contexts.identity.repository import (
    AuthRepository,
    CoordinatorMemberRepository,
    ProfileRepository,
)
from app.contexts.identity.service import TeamScopeService
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


@router.put("/client-eval/forms/{form_id}", response_model=ClientFormOut)
async def update_client_form(
    form_id: UUID, payload: ClientFormIn, tenant: AdminDep, session: SessionDep
) -> ClientFormOut:
    """Renomeia, ativa/desativa e define o formulário padrão do fluxo espontâneo."""
    repo = ClientFormRepository(session, tenant)
    form = await repo.get(form_id)
    if form is None:
        raise NotFoundError("Formulário não encontrado")

    # Só um padrão por tenant: `get_default` devolve o primeiro que achar, e dois
    # marcados fariam o fluxo espontâneo sortear qual formulário o cliente responde.
    if payload.is_default and not form.is_default:
        atual = await repo.get_default()
        if atual is not None and atual.id != form_id:
            atual.is_default = False

    form.name = payload.name
    form.is_default = payload.is_default
    form.is_active = payload.is_active
    await session.flush()
    return ClientFormOut.model_validate(form)


@router.get(
    "/client-eval/forms/{form_id}/questions", response_model=list[ClientQuestionOut]
)
async def list_client_questions(
    form_id: UUID,
    tenant: AdminDep,
    session: SessionDep,
    incluir_arquivadas: Annotated[bool, Query(alias="incluir_arquivadas")] = False,
) -> list[ClientQuestionOut]:
    """As perguntas que o cliente responde no wizard público (SCR-0043).

    `tem_resposta` vem junto porque é o que a tela precisa para saber se "remover" apaga
    ou arquiva — e para explicar à pessoa por que uma pergunta não some mais.
    """
    repo = ClientQuestionRepository(session, tenant)
    perguntas = await repo.list_by_form(form_id, incluir_arquivadas=incluir_arquivadas)
    saida = []
    for pergunta in perguntas:
        item = ClientQuestionOut.model_validate(pergunta)
        item.tem_resposta = await repo.tem_resposta(pergunta.id)
        saida.append(item)
    return saida


@router.put(
    "/client-eval/forms/{form_id}/questions/order",
    response_model=list[ClientQuestionOut],
)
async def reorder_client_questions(
    form_id: UUID, payload: ReordenarPerguntasIn, tenant: AdminDep, session: SessionDep
) -> list[ClientQuestionOut]:
    """Regrava a ordem inteira (BR-MIGRAR-020).

    Ids que não são do formulário são ignorados em silêncio, e perguntas que ficaram de
    fora da lista vão para o fim: a ordem resultante é sempre completa e sem buraco,
    mesmo que a tela mande uma lista defasada.
    """
    repo = ClientQuestionRepository(session, tenant)
    perguntas = {p.id: p for p in await repo.list_by_form(form_id, incluir_arquivadas=True)}

    ordem = 0
    for question_id in payload.question_ids:
        pergunta = perguntas.pop(question_id, None)
        if pergunta is not None:
            pergunta.display_order = ordem
            ordem += 1
    for restante in perguntas.values():
        restante.display_order = ordem
        ordem += 1

    await session.flush()
    return [
        ClientQuestionOut.model_validate(p)
        for p in await repo.list_by_form(form_id, incluir_arquivadas=True)
    ]


@router.put(
    "/client-eval/forms/{form_id}/questions/{question_id}",
    response_model=ClientQuestionOut,
)
async def update_client_question(
    form_id: UUID,
    question_id: UUID,
    payload: ClientQuestionUpdateIn,
    tenant: AdminDep,
    session: SessionDep,
) -> ClientQuestionOut:
    repo = ClientQuestionRepository(session, tenant)
    pergunta = await repo.get(question_id)
    if pergunta is None or pergunta.form_id != form_id:
        raise NotFoundError("Pergunta não encontrada")

    pergunta.question_text = payload.question_text
    pergunta.question_type = payload.question_type
    pergunta.is_required = payload.is_required
    pergunta.placeholder = payload.placeholder
    await session.flush()
    return ClientQuestionOut.model_validate(pergunta)


@router.delete(
    "/client-eval/forms/{form_id}/questions/{question_id}",
    response_model=ClientQuestionOut,
)
async def remove_client_question(
    form_id: UUID, question_id: UUID, tenant: AdminDep, session: SessionDep
) -> ClientQuestionOut:
    """Apaga a pergunta, ou arquiva se alguém já respondeu.

    Apagar uma pergunta respondida destruiria a resposta de um cliente para limpar um
    formulário. Arquivada, ela sai dos formulários novos e continua explicando os
    relatórios antigos — e a resposta segue lá.

    Devolve a pergunta em vez de 204 justamente para a tela saber qual dos dois
    aconteceu, sem ter que recarregar a lista para descobrir.
    """
    repo = ClientQuestionRepository(session, tenant)
    pergunta = await repo.get(question_id)
    if pergunta is None or pergunta.form_id != form_id:
        raise NotFoundError("Pergunta não encontrada")

    if await repo.tem_resposta(question_id):
        pergunta.is_active = False
        await session.flush()
        saida = ClientQuestionOut.model_validate(pergunta)
        saida.tem_resposta = True
        return saida

    saida = ClientQuestionOut.model_validate(pergunta)
    await repo.remove(pergunta)
    await session.flush()
    return saida


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


async def _avaliados_visiveis(session: SessionDep, tenant: TenantContext) -> set[UUID] | None:
    """Sobre quem esta pessoa pode ler avaliação de cliente. `None` = todo o escritório.

    A união é a mesma de sempre: **si mesma**, porque o que um cliente disse sobre você é
    seu; **a equipe**, pelo escopo de BR-MIGRAR-017; e quem tem `can_view_feedback_answers`,
    que é a capacidade criada exatamente para isso.

    Admin e RH veem tudo — são eles que respondem por reclamação de cliente.

    Antes disto a listagem devolvia **todas as avaliações do escritório para qualquer
    autenticado**: quem tinha login via quais clientes reclamaram de quem. O detalhe, que
    traz o texto, tornaria isso muito pior.
    """
    if tenant.has_role("admin", "rh") or tenant.has_flag("can_view_feedback_answers"):
        return None

    escopo = TeamScopeService(
        profiles=ProfileRepository(session, tenant),
        coordinator_members=CoordinatorMemberRepository(session, tenant),
    )
    return await escopo.resolve_visible_profile_ids(tenant) | {tenant.user_id}


@router.get("/client-eval/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(
    tenant: TenantDep,
    session: SessionDep,
    status_filtro: Annotated[list[str] | None, Query(alias="status")] = None,
) -> list[EvaluationOut]:
    """WhatsApp completo só para admin/RH; para o resto, mascarado (BR-MIGRAR-022)."""
    repo = ClientEvaluationRepository(session, tenant)
    avaliacoes = await repo.list_por_status(
        *(status_filtro or []), visiveis=await _avaliados_visiveis(session, tenant)
    )
    completo = tenant.has_role("admin", "rh")
    return [EvaluationOut.de_modelo(a, whatsapp_completo=completo) for a in avaliacoes]


# `/mine` precisa vir **antes** da rota com placeholder: declarada depois, "mine" seria
# lido como `evaluation_id` e o UUID inválido devolveria 422 em vez da lista.
@router.get("/client-eval/evaluations/mine", response_model=list[EvaluationOut])
async def my_evaluations(tenant: TenantDep, session: SessionDep) -> list[EvaluationOut]:
    """As avaliações que o próprio usuário recebeu de clientes."""
    repo = ClientEvaluationRepository(session, tenant)
    return [
        EvaluationOut.de_modelo(a, whatsapp_completo=False)
        for a in await repo.list_do_avaliado(tenant.user_id)
    ]


@router.get("/client-eval/evaluations/{evaluation_id}", response_model=EvaluationDetailOut)
async def evaluation_detail(
    evaluation_id: UUID, tenant: TenantDep, session: SessionDep
) -> EvaluationDetailOut:
    """O que o cliente respondeu, pergunta por pergunta.

    Fora do escopo é **404 e não 403**, como no detalhe de request: o erro não confirma
    que a avaliação existe nem sobre quem ela é.

    Avaliação ainda não respondida não tem o que mostrar, mas não é erro — a tela abre e
    diz que está pendente. Recusar aqui obrigaria a lista a esconder o link, e o que a
    pessoa quer saber é justamente se já respondeu.
    """
    avaliacao = await ClientEvaluationRepository(session, tenant).get(evaluation_id)
    visiveis = await _avaliados_visiveis(session, tenant)
    if avaliacao is None or (visiveis is not None and avaliacao.target_user_id not in visiveis):
        raise NotFoundError("Avaliação não encontrada")

    perfis = await ProfileRepository(session, tenant).list_by_ids({avaliacao.target_user_id})
    respostas = await ClientAnswerRepository(session, tenant).list_com_pergunta(evaluation_id)
    servicos = await ServiceTagRepository(session, tenant).nomes_da_avaliacao(evaluation_id)

    return EvaluationDetailOut(
        avaliacao=EvaluationOut.de_modelo(
            avaliacao, whatsapp_completo=tenant.has_role("admin", "rh")
        ),
        avaliado_nome=perfis[0].full_name if perfis else "—",
        motivacao=avaliacao.contact_motivation,
        motivacao_texto=avaliacao.contact_motivation_text,
        servicos=servicos,
        respostas=[
            RespostaDoClienteOut(
                question_id=pergunta.id,
                pergunta=pergunta.question_text,
                tipo=pergunta.question_type,
                nota=resposta.rating_value,
                texto=resposta.text_value,
            )
            for resposta, pergunta in respostas
        ],
    )


@router.get("/client-eval/service-tags", response_model=list[ServiceTagOut])
async def list_service_tags(tenant: TenantDep, session: SessionDep) -> list[ServiceTagOut]:
    repo = ServiceTagRepository(session, tenant)
    return [ServiceTagOut.model_validate(t) for t in await repo.list_active()]


# ---------------------------------------------------------------- público

# Ordem das quatro motivações na etapa 2 do wizard (SCR-0035). É a ordem do legado, e
# o catálogo de settings guarda só o liga/desliga de cada uma.
MOTIVACOES = ("praise", "evaluate", "problem", "other")


def _motivacoes_ligadas(settings_do_tenant: dict[str, str | None]) -> list[str]:
    """Quais motivações o escritório deixou ligadas (`client_feedback_motivations`).

    Configuração ausente ou quebrada libera as quatro: a etapa é opcional para o
    resultado, e sumir com ela por causa de um JSON torto seria pior que mostrá-la.
    """
    bruto = settings_do_tenant.get("client_feedback_motivations")
    if not bruto:
        return list(MOTIVACOES)
    try:
        escolhas = json.loads(bruto)
    except (ValueError, TypeError):
        return list(MOTIVACOES)
    if not isinstance(escolhas, dict):
        return list(MOTIVACOES)
    return [m for m in MOTIVACOES if escolhas.get(m, True)]


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
    settings_do_tenant = {
        s.key: s.value
        for s in await TenantSettingRepository(session, contexto).list_all_settings()
    }

    return PublicFormOut(
        questions=[PublicQuestionOut.model_validate(q) for q in perguntas],
        service_tags=[ServiceTagOut.model_validate(t) for t in tags],
        target_name=avaliado.full_name if avaliado else None,
        client_name=avaliacao.client_name,
        client_whatsapp=avaliacao.client_whatsapp,
        client_email=avaliacao.client_email,
        motivations=_motivacoes_ligadas(settings_do_tenant),
        company_name=settings_do_tenant.get("company_name"),
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
