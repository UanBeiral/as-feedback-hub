"""Popula um tenant com dados de demonstração, para exercitar as telas.

**Não é dado de produção e não é o script de migração** (esse nasce em `deploy/migrate/`
quando AMB-010 responder). Existe por um motivo prático: a conferência das telas contra
o oráculo em `docs/conferencia-oraculo.md` compara capturas de um sistema **em uso**, e
tela vazia não prova nada — colunas sem linha, filtro sem opção e badge que nunca
aparece passariam por conferidos sem nunca terem sido vistos.

Cobre as quatro papéis (admin, RH, gestor, colaborador), a coordenação como atributo
(BR-MIGRAR-016), um ciclo aberto com pedidos em todos os estados, feedback livre,
anotações de ciclo, avaliações de cliente respondidas e pendentes, notificações lidas e
não lidas, mensagens do Fale Conosco em cada status, comunicados e auditoria.

Também deixa **defeitos de propósito** na matriz de permissões — par sem recíproco,
pessoa sem cobertura, permissão apontando para inativo — porque a tela de Diagnóstico só
tem o que conferir quando existe o que diagnosticar.

É idempotente por e-mail: rodar de novo em cima do mesmo tenant não duplica pessoas.

Uso:
    PYTHONPATH=apps/api python deploy/seed_demo.py --slug demo --senha "..."
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text

from app.contexts.client_eval.models import (
    ClientEvalAnswer,
    ClientEvalForm,
    ClientEvalFormQuestion,
    ClientEvaluation,
    ClientEvaluationTag,
    ServiceTag,
)
from app.contexts.engagement.models import (
    AuditLog,
    ContactMessage,
    Notification,
    PlatformUpdate,
    TenantSetting,
)
from app.contexts.feedback.models import (
    CycleNote,
    FeedbackAnswer,
    FeedbackCycle,
    FeedbackForm,
    FeedbackFormQuestion,
    FeedbackPermission,
    FeedbackRequest,
    FreeFeedback,
)
from app.contexts.identity.models import (
    CoordinatorMember,
    Department,
    Profile,
    ProfileDepartment,
    Tenant,
    User,
)
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.security import PasswordHasher, generate_public_token

HOJE = datetime.now(UTC).date()
AGORA = datetime.now(UTC)

# As pessoas são identificadas aqui por uma chave curta ("gestor", "coord") e o e-mail é
# derivado dela: escrever o endereço inteiro em cada referência deixaria a matriz de
# permissões ilegível. O domínio é real de propósito — um TLD reservado como `.test` é
# recusado na validação de e-mail, e o login não aceitaria a conta criada.
DOMINIO = "bragaduarte.com.br"


# ---------------------------------------------------------------- pessoas
#
# A equipe é pequena de propósito: grande o bastante para toda tela ter mais de uma
# linha e um caso de borda, pequena o bastante para caber numa captura.

PESSOAS = [
    # chave, nome, papel, cargo, gestor (chave), coordenador?, status, capacidades
    ("admin", "Helena Braga", "admin", "Sócia-administradora", None, False, "active",
     ["can_request_client_feedback", "can_view_feedback_answers", "can_view_team_history",
      "can_generate_reports", "can_view_manager_dashboard"]),
    ("rh", "Carlos Mendes", "rh", "Analista de Gente e Gestão", None, False, "active",
     ["can_view_feedback_answers", "can_view_team_history", "can_generate_reports"]),
    ("gestor", "Marina Duarte", "gestor", "Coordenadora do Contencioso", None, False,
     "active", ["can_request_client_feedback", "can_view_feedback_answers",
                "can_view_team_history", "can_view_manager_dashboard"]),
    # Coordenação é atributo, não papel (BR-MIGRAR-016): este é um colaborador que
    # coordena, e a tela dele tem de mostrar a equipe sem o papel mudar.
    ("coord", "Rafael Antunes", "colaborador", "Advogado sênior", "gestor",
     True, "active", ["can_request_client_feedback", "can_view_team_history"]),
    ("bruna", "Bruna Camargo", "colaborador", "Advogada plena", "gestor",
     False, "active", ["can_request_client_feedback"]),
    ("diego", "Diego Ramos", "colaborador", "Advogado júnior", "gestor",
     False, "active", []),
    ("paula", "Paula Nogueira", "colaborador", "Paralegal", "gestor",
     False, "active", []),
    ("tiago", "Tiago Ferraz", "colaborador", "Estagiário", "gestor",
     False, "active", []),
    # Desligado: a matriz ainda aponta para ele, e é isso que o Diagnóstico precisa achar.
    ("ex", "Sofia Lins", "colaborador", "Advogada plena", "gestor",
     False, "inactive", []),
]

DEPARTAMENTOS = ["Contencioso", "Consultivo", "Administrativo"]

PERGUNTAS_360 = [
    ("Como você avalia a qualidade técnica do trabalho entregue?", "rating", True),
    ("A pessoa cumpre prazos e comunica atrasos com antecedência?", "rating", True),
    ("Como você avalia a colaboração dela com o time?", "rating", True),
    ("O que essa pessoa faz muito bem e deveria continuar fazendo?", "textarea", True),
    ("O que ela poderia fazer diferente para crescer?", "textarea", False),
]

PERGUNTAS_CLIENTE = [
    ("No geral, como você avalia a experiência com {profissional}?", "rating", True, None),
    ("Como você avalia o atendimento recebido pelo profissional?", "rating", True, None),
    ("O profissional foi claro e objetivo nas explicações?", "rating", True, None),
    ("Como avalia a agilidade no retorno às suas demandas?", "rating", True, None),
    ("Você se sentiu ouvido(a) e bem acolhido(a)?", "rating", True, None),
    ("Qual a chance de você recomendar {profissional} a um amigo?", "nps", True, None),
    ("O que o profissional fez de melhor?", "textarea", False,
     "Ex: Foi muito atencioso, explicou tudo com clareza…"),
    ("O que poderia ser melhorado?", "textarea", False,
     "Ex: O retorno das mensagens poderia ser mais rápido…"),
    ("No geral, quão satisfeito(a) você ficou com o atendimento de {profissional}?",
     "rating", True, None),
]

TAGS_DE_SERVICO = [
    "Trabalhista", "Cível", "Criminal", "Tributário", "Empresarial",
    "Contratos", "Consultoria", "Família", "Imobiliário", "Previdenciário",
]


# Ordem de remoção do `--recriar`: filhos antes dos pais. Não há ON DELETE CASCADE na
# maioria das FKs de propósito — apagar dado por engano em produção tem de doer —, então
# a ordem mora aqui, onde só o script de demonstração a usa.
TABELAS_DO_TENANT = [
    "client_eval_answers", "client_evaluation_tags", "client_evaluations",
    "client_eval_form_questions", "client_eval_forms", "service_tags",
    "feedback_answers", "feedback_requests", "feedback_permissions",
    "cycle_notes", "free_feedbacks", "feedback_cycles",
    "feedback_form_questions", "feedback_forms",
    "notifications", "contact_messages", "platform_updates", "audit_logs",
    "outbox_messages", "export_jobs",
    "coordinator_members", "profile_departments", "team_requests",
    "refresh_tokens", "tenant_settings",
]


async def apagar_tenant(session, tenant_id) -> None:
    """Esvazia o tenant inteiro. Só para o tenant de demonstração."""
    for tabela in TABELAS_DO_TENANT:
        await session.execute(text(f"DELETE FROM {tabela} WHERE tenant_id = :t"), {"t": tenant_id})
    # `manager_id` e `department_id` apontam para dentro do próprio conjunto que vai
    # sumir: soltar as referências primeiro evita depender da ordem das linhas.
    await session.execute(
        text("UPDATE profiles SET manager_id = NULL, department_id = NULL WHERE tenant_id = :t"),
        {"t": tenant_id},
    )
    for tabela in ("profiles", "users", "departments", "tenants"):
        coluna = "id" if tabela == "tenants" else "tenant_id"
        await session.execute(
            text(f"DELETE FROM {tabela} WHERE {coluna} = :t"), {"t": tenant_id}
        )


async def seed(slug: str, nome_do_tenant: str, senha: str, recriar: bool = False) -> int:
    settings = get_settings()
    hasher = PasswordHasher(rounds=settings.bcrypt_rounds)
    # Um hash só para todo mundo: bcrypt custa ~100ms por chamada, e nove chamadas
    # transformariam um seed instantâneo em um segundo de espera sem ganho nenhum.
    hash_da_senha = hasher.hash(senha)

    async with get_session_factory()() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()
        if tenant is not None and recriar:
            await apagar_tenant(session, tenant.id)
            await session.flush()
            print(f"tenant {slug} apagado para recriação")
            tenant = None
        if tenant is None:
            tenant = Tenant(id=uuid4(), slug=slug, name=nome_do_tenant)
            session.add(tenant)
            await session.flush()
            print(f"tenant criado: {slug} ({tenant.id})")
        else:
            print(f"tenant já existe: {slug} ({tenant.id})")

        ja_existentes = {
            u.email
            for u in (
                await session.execute(select(User).where(User.tenant_id == tenant.id))
            ).scalars()
        }
        if ja_existentes & {f"{chave}@{DOMINIO}" for chave, *_ in PESSOAS}:
            print("este tenant já foi semeado; use --recriar para refazer do zero")
            return 0

        # ------------------------------------------------------------ departamentos
        departamentos = {}
        for nome in DEPARTAMENTOS:
            depto = Department(id=uuid4(), tenant_id=tenant.id, name=nome)
            session.add(depto)
            departamentos[nome] = depto
        await session.flush()

        # ------------------------------------------------------------ pessoas
        perfis: dict[str, Profile] = {}
        for chave, nome, papel, cargo, _, coordena, status, capacidades in PESSOAS:
            user = User(
                id=uuid4(),
                tenant_id=tenant.id,
                email=f"{chave}@{DOMINIO}",
                password_hash=hash_da_senha,
            )
            session.add(user)
            await session.flush()
            perfil = Profile.for_user(
                user,
                full_name=nome,
                role=papel,
                status=status,
                job_title=cargo,
                is_coordinator=coordena,
                whatsapp=f"1199{abs(hash(chave)) % 10_000_000:07d}",
                **{c: True for c in capacidades},
            )
            session.add(perfil)
            perfis[chave] = perfil
        await session.flush()

        # A hierarquia só pode ser ligada depois que todo mundo existe: `manager_id`
        # aponta para `profiles`, e o gestor pode ter sido criado na linha de baixo.
        for chave, _, _, _, gestor, *_ in PESSOAS:
            if gestor:
                perfis[chave].manager_id = perfis[gestor].id

        contencioso = departamentos["Contencioso"]
        for email in ("gestor", "coord", "bruna",
                      "diego", "paula", "tiago"):
            perfis[email].department_id = contencioso.id
        perfis["admin"].department_id = departamentos["Administrativo"].id
        perfis["rh"].department_id = departamentos["Administrativo"].id

        # Departamento adicional (N:N): a Bruna atende os dois lados da casa.
        session.add(
            ProfileDepartment(
                tenant_id=tenant.id,
                profile_id=perfis["bruna"].id,
                department_id=departamentos["Consultivo"].id,
            )
        )

        # Quem o coordenador coordena — subconjunto da equipe do gestor.
        for email in ("diego", "paula", "tiago"):
            session.add(
                CoordinatorMember(
                    tenant_id=tenant.id,
                    coordinator_id=perfis["coord"].id,
                    member_id=perfis[email].id,
                )
            )
        await session.flush()

        # ------------------------------------------------------------ formulário 360
        formulario = FeedbackForm(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Avaliação 360 — semestral",
            description="Formulário padrão dos ciclos semestrais.",
        )
        session.add(formulario)
        await session.flush()
        perguntas = []
        for ordem, (texto, tipo, obrigatoria) in enumerate(PERGUNTAS_360, start=1):
            q = FeedbackFormQuestion(
                id=uuid4(),
                tenant_id=tenant.id,
                form_id=formulario.id,
                question_text=texto,
                question_type=tipo,
                sort_order=ordem,
                required=obrigatoria,
            )
            session.add(q)
            perguntas.append(q)
        await session.flush()

        # ------------------------------------------------------------ ciclos
        # Um fechado e um aberto: a tela de ciclos precisa dos dois estados, e o
        # relatório precisa de história.
        ciclo_anterior = FeedbackCycle(
            id=uuid4(),
            tenant_id=tenant.id,
            name="1º semestre",
            form_id=formulario.id,
            frequency="semestral",
            status="closed",
            start_date=HOJE - timedelta(days=210),
            end_date=HOJE - timedelta(days=190),
            closed_at=AGORA - timedelta(days=189),
            published_at=AGORA - timedelta(days=188),
        )
        ciclo = FeedbackCycle(
            id=uuid4(),
            tenant_id=tenant.id,
            name="2º semestre",
            form_id=formulario.id,
            frequency="semestral",
            status="open",
            start_date=HOJE - timedelta(days=6),
            end_date=HOJE + timedelta(days=9),
        )
        session.add_all([ciclo_anterior, ciclo])
        await session.flush()

        # ------------------------------------------------------------ permissões
        #
        # A matriz é deliberadamente imperfeita. Cada defeito abaixo é uma categoria
        # que a tela de Diagnóstico tem de acusar; matriz limpa deixaria a tela mais
        # densa do legado sem nada para conferir.
        equipe = ["coord", "bruna", "diego", "paula"]
        for i, a in enumerate(equipe):
            for b in equipe[i + 1 :]:
                session.add(
                    FeedbackPermission(
                        tenant_id=tenant.id,
                        reviewer_id=perfis[a].id,
                        reviewee_id=perfis[b].id,
                        permission_type="peer_to_peer",
                        cycle_id=ciclo.id,
                        active=True,
                    )
                )
                # O recíproco de um dos pares fica faltando de propósito.
                if not (a == "coord" and b == "paula"):
                    session.add(
                        FeedbackPermission(
                            tenant_id=tenant.id,
                            reviewer_id=perfis[b].id,
                            reviewee_id=perfis[a].id,
                            permission_type="peer_to_peer",
                            cycle_id=ciclo.id,
                            active=True,
                        )
                    )

        # Gestor avalia a equipe.
        for email in equipe:
            session.add(
                FeedbackPermission(
                    tenant_id=tenant.id,
                    reviewer_id=perfis["gestor"].id,
                    reviewee_id=perfis[email].id,
                    permission_type="manager_to_report",
                    cycle_id=ciclo.id,
                    active=True,
                )
            )

        # Permissão apontando para quem saiu: gera pedido que ninguém responde.
        session.add(
            FeedbackPermission(
                tenant_id=tenant.id,
                reviewer_id=perfis["gestor"].id,
                reviewee_id=perfis["ex"].id,
                permission_type="manager_to_report",
                cycle_id=ciclo.id,
                active=True,
            )
        )
        # O Tiago não aparece em lado nenhum: some do ciclo sem ninguém notar.
        await session.flush()

        # ------------------------------------------------------------ pedidos
        #
        # Todos os estados que a tela distingue, e um respondido de verdade para o
        # relatório e o histórico terem conteúdo.
        def novo_pedido(giver: str, receiver: str, status: str, **extra) -> FeedbackRequest:
            pedido = FeedbackRequest(
                id=uuid4(),
                tenant_id=tenant.id,
                cycle_id=ciclo.id,
                form_id=formulario.id,
                giver_id=perfis[giver].id,
                receiver_id=perfis[receiver].id,
                status=status,
                due_date=ciclo.end_date,
                **extra,
            )
            session.add(pedido)
            return pedido

        respondido = novo_pedido(
            "gestor", "bruna", "submitted",
            submitted_at=AGORA - timedelta(days=2),
        )
        novo_pedido("gestor", "diego", "pending")
        novo_pedido("gestor", "coord", "pending")
        novo_pedido("coord", "diego", "draft")
        novo_pedido("bruna", "coord", "pending")
        novo_pedido("diego", "bruna", "pending")
        novo_pedido(
            "paula", "coord", "cancelled",
            cancel_justification="Paula entrou de licença antes do fim do ciclo.",
        )
        respondido_anterior = FeedbackRequest(
            id=uuid4(),
            tenant_id=tenant.id,
            cycle_id=ciclo_anterior.id,
            form_id=formulario.id,
            giver_id=perfis["gestor"].id,
            receiver_id=perfis["coord"].id,
            status="submitted",
            due_date=ciclo_anterior.end_date,
            submitted_at=AGORA - timedelta(days=192),
        )
        session.add(respondido_anterior)
        await session.flush()

        notas = {0: 5, 1: 4, 2: 5}
        textos = {
            3: "Assume o caso do começo ao fim e o cliente sente isso. Escreve bem e "
               "entrega antes do prazo com frequência.",
            4: "Poderia delegar mais. Segura tarefa que o time júnior já daria conta, e "
               "isso vira gargalo na semana de audiência.",
        }
        for pedido in (respondido, respondido_anterior):
            for indice, pergunta in enumerate(perguntas):
                session.add(
                    FeedbackAnswer(
                        tenant_id=tenant.id,
                        request_id=pedido.id,
                        question_id=pergunta.id,
                        answer_score=notas.get(indice),
                        answer_text=textos.get(indice),
                    )
                )

        # ------------------------------------------------------------ feedback livre
        session.add_all([
            FreeFeedback(
                tenant_id=tenant.id,
                giver_id=perfis["gestor"].id,
                receiver_id=perfis["diego"].id,
                is_anonymous=False,
                is_sensitive=False,
                positives="Aguentou firme a semana da audiência e não deixou nada cair.",
                improvements="Avise antes quando a carga apertar — dá para redistribuir.",
                message="Obrigada pelo empenho nesta semana.",
                created_at=AGORA - timedelta(days=3),
            ),
            # Anônimo: `giver_id` precisa ser nulo, e o CHECK do banco cobra isso.
            FreeFeedback(
                tenant_id=tenant.id,
                giver_id=None,
                receiver_id=perfis["coord"].id,
                is_anonymous=True,
                is_sensitive=True,
                positives="Domina o assunto como ninguém.",
                improvements="As reuniões dele atropelam quem fala mais baixo.",
                created_at=AGORA - timedelta(days=8),
            ),
        ])

        # ------------------------------------------------------------ anotações
        session.add_all([
            CycleNote(
                tenant_id=tenant.id,
                cycle_id=ciclo.id,
                author_id=perfis["gestor"].id,
                about_user_id=perfis["diego"].id,
                content="Assumiu a sustentação oral de última hora e se saiu bem. "
                        "Lembrar disso na conversa de fechamento do ciclo.",
                created_at=AGORA - timedelta(days=4),
            ),
            CycleNote(
                tenant_id=tenant.id,
                cycle_id=ciclo.id,
                author_id=perfis["gestor"].id,
                about_user_id=perfis["paula"].id,
                content="Terceira vez que a petição volta para revisão por erro de "
                        "citação. Combinar checklist antes do protocolo.",
                created_at=AGORA - timedelta(days=1),
            ),
            CycleNote(
                tenant_id=tenant.id,
                cycle_id=ciclo.id,
                author_id=perfis["coord"].id,
                about_user_id=perfis["tiago"].id,
                content="Chegou há pouco e já está resolvendo diligência sozinho.",
                is_audio_transcription=True,
                created_at=AGORA - timedelta(days=2),
            ),
        ])

        # ------------------------------------------------------------ cliente
        form_cliente = ClientEvalForm(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Atendimento Jurídico Geral",
            is_default=True,
            is_active=True,
        )
        session.add(form_cliente)
        await session.flush()
        perguntas_cliente = []
        for ordem, (texto, tipo, obrigatoria, dica) in enumerate(PERGUNTAS_CLIENTE, start=1):
            q = ClientEvalFormQuestion(
                id=uuid4(),
                tenant_id=tenant.id,
                form_id=form_cliente.id,
                question_text=texto,
                question_type=tipo,
                is_required=obrigatoria,
                display_order=ordem,
                placeholder=dica,
            )
            session.add(q)
            perguntas_cliente.append(q)

        tags = []
        for ordem, nome in enumerate(TAGS_DE_SERVICO, start=1):
            tag = ServiceTag(id=uuid4(), tenant_id=tenant.id, name=nome, display_order=ordem)
            session.add(tag)
            tags.append(tag)
        await session.flush()

        def nova_avaliacao(alvo: str, cliente: str, **extra) -> ClientEvaluation:
            # A validade sai de `extra` quando o chamador quiser um link vencido; o
            # default vale para o caso normal, que é a maioria.
            extra.setdefault("token_expires_at", AGORA + timedelta(days=7))
            avaliacao = ClientEvaluation(
                id=uuid4(),
                tenant_id=tenant.id,
                target_user_id=perfis[alvo].id,
                form_id=form_cliente.id,
                flow_type="requested",
                requested_by=perfis["gestor"].id,
                client_name=cliente,
                token=generate_public_token(),
                **extra,
            )
            session.add(avaliacao)
            return avaliacao

        boa = nova_avaliacao(
            "coord", "Construtora Avelar Ltda.",
            client_whatsapp="11987654321", client_email="contato@avelar.com.br",
            status="submitted", submitted_at=AGORA - timedelta(days=5),
            contact_motivation="praise",
            contact_motivation_text="O Rafael resolveu em duas semanas o que estava "
                                    "parado desde o ano passado.",
            overall_rating=10, recommendation_rating=10,
        )
        ruim = nova_avaliacao(
            "bruna", "Marcos Tavares",
            client_whatsapp="11955554444",
            status="submitted", submitted_at=AGORA - timedelta(days=1),
            contact_motivation="problem",
            contact_motivation_text="Fiquei três semanas sem retorno e tive que ligar "
                                    "duas vezes para saber do meu processo.",
            overall_rating=3, recommendation_rating=2, has_negative=True,
        )
        nova_avaliacao(
            "diego", "Padaria do Vale ME",
            client_whatsapp="11944443333", status="pending",
        )
        nova_avaliacao(
            "coord", "Iolanda Prestes",
            client_whatsapp="11933332222", status="in_progress",
        )
        nova_avaliacao(
            "bruna", "Transportes Serra Azul",
            client_whatsapp="11922221111", status="expired",
            token_expires_at=AGORA - timedelta(days=3),
        )
        await session.flush()

        respostas_boas = [10, 10, 9, 10, 10, 10,
                          "Explicou cada passo numa linguagem que eu entendi.",
                          None, 10]
        respostas_ruins = [3, 2, 5, 1, 4, 2, None,
                           "Retornar as mensagens. Fiquei no vácuo três semanas.", 3]
        for avaliacao, respostas in ((boa, respostas_boas), (ruim, respostas_ruins)):
            for pergunta, valor in zip(perguntas_cliente, respostas, strict=True):
                if valor is None:
                    continue
                session.add(
                    ClientEvalAnswer(
                        tenant_id=tenant.id,
                        evaluation_id=avaliacao.id,
                        question_id=pergunta.id,
                        rating_value=valor if isinstance(valor, int) else None,
                        text_value=valor if isinstance(valor, str) else None,
                    )
                )
        session.add_all([
            ClientEvaluationTag(tenant_id=tenant.id, evaluation_id=boa.id, tag_id=tags[4].id),
            ClientEvaluationTag(tenant_id=tenant.id, evaluation_id=boa.id, tag_id=tags[5].id),
            ClientEvaluationTag(tenant_id=tenant.id, evaluation_id=ruim.id, tag_id=tags[0].id),
        ])

        # ------------------------------------------------------------ engajamento
        session.add_all([
            Notification(
                tenant_id=tenant.id, user_id=perfis["gestor"].id,
                type="client_eval.flagged_negative",
                title="Avaliação negativa de cliente",
                message="Marcos Tavares avaliou o atendimento de Bruna Camargo com nota 3.",
                link="/avaliacoes-clientes",
                created_at=AGORA - timedelta(hours=20),
            ),
            Notification(
                tenant_id=tenant.id, user_id=perfis["gestor"].id,
                type="feedback.request_created",
                title="Você tem feedbacks pendentes",
                message="2 pedidos do ciclo 2º semestre aguardam sua resposta.",
                link="/meus-feedbacks",
                created_at=AGORA - timedelta(days=5),
                read_at=AGORA - timedelta(days=4),
            ),
            Notification(
                tenant_id=tenant.id, user_id=perfis["coord"].id,
                type="feedback.request_created",
                title="Você tem feedbacks pendentes",
                message="1 pedido do ciclo 2º semestre aguarda sua resposta.",
                link="/meus-feedbacks",
                created_at=AGORA - timedelta(days=5),
            ),
        ])

        session.add_all([
            ContactMessage(
                # `type` é texto livre no schema — o legado usa "sugestao" e "critica"
                # (as duas únicas opções vistas em `admin/screenshots/fale-conosco.png`).
                tenant_id=tenant.id, type="critica", company="Construtora Avelar Ltda.",
                contact_name="Regina Avelar", email="regina@avelar.com.br",
                phone="11987650000",
                message="O link da avaliação que recebi por WhatsApp diz que expirou. "
                        "Consigo um novo?",
                status="novo", created_by=perfis["admin"].id,
                created_at=AGORA - timedelta(hours=6),
            ),
            ContactMessage(
                tenant_id=tenant.id, type="sugestao", company="Serra Azul Transportes",
                contact_name="Otávio Serra", email="otavio@serraazul.com.br",
                message="Gostaria de entender como funciona o plano para 40 pessoas.",
                status="em_andamento", created_by=perfis["admin"].id,
                created_at=AGORA - timedelta(days=3),
            ),
            ContactMessage(
                tenant_id=tenant.id, type="critica", contact_name="Diego Ramos",
                email=f"diego@{DOMINIO}",
                message="Não consigo salvar rascunho no formulário de feedback.",
                status="resolvido", created_by=perfis["diego"].id,
                created_at=AGORA - timedelta(days=12),
            ),
        ])

        session.add_all([
            PlatformUpdate(
                tenant_id=tenant.id,
                title="Avaliação de cliente agora é um passo por vez",
                content="A página que o cliente recebe por WhatsApp virou um fluxo de "
                        "etapas curtas. Menos abandono no meio do formulário.",
                created_by=perfis["admin"].id,
                draft=False, notified_count=len(PESSOAS),
                published_at=AGORA - timedelta(days=2),
            ),
            PlatformUpdate(
                tenant_id=tenant.id,
                title="Relatórios com exportação em CSV",
                content="A aba Exportações agora gera o arquivo em segundo plano e avisa "
                        "quando ficar pronto.",
                created_by=perfis["admin"].id,
                draft=False, notified_count=len(PESSOAS),
                published_at=AGORA - timedelta(days=30),
            ),
            PlatformUpdate(
                tenant_id=tenant.id,
                title="Agenda de reuniões (em preparação)",
                content="Rascunho — não publicar antes da fase 2.",
                created_by=perfis["admin"].id,
                draft=True,
            ),
        ])

        session.add_all([
            TenantSetting(
                tenant_id=tenant.id, key="company_name", value=nome_do_tenant,
                updated_by=perfis["admin"].id,
            ),
            TenantSetting(
                tenant_id=tenant.id, key="whatsapp_message_template",
                value="Olá {cliente}! Como foi seu atendimento com {profissional}? "
                      "Sua opinião leva menos de 2 minutos: {link}",
                updated_by=perfis["admin"].id,
            ),
            # Ligada para o gestor enxergar relatórios — é o toggle de BR-MIGRAR-027 que
            # mais muda a navegação, e vale estar ligado em pelo menos um ambiente.
            TenantSetting(
                tenant_id=tenant.id, key="gestor_can_access_reports", value="true",
                updated_by=perfis["admin"].id,
            ),
        ])

        session.add_all([
            AuditLog(
                tenant_id=tenant.id, actor_id=perfis["admin"].id,
                action="profile.updated", table_name="profiles",
                record_id=perfis["diego"].id,
                details={"campo": "can_request_client_feedback", "de": False, "para": True},
                created_at=AGORA - timedelta(days=9),
            ),
            AuditLog(
                tenant_id=tenant.id, actor_id=perfis["admin"].id,
                action="profile.deactivated", table_name="profiles",
                record_id=perfis["ex"].id,
                details={"motivo": "desligamento"},
                created_at=AGORA - timedelta(days=7),
            ),
            AuditLog(
                tenant_id=tenant.id, actor_id=perfis["gestor"].id,
                action="cycle.opened", table_name="feedback_cycles", record_id=ciclo.id,
                details={"nome": ciclo.name},
                created_at=AGORA - timedelta(days=6),
            ),
        ])

        await session.commit()

    # O resumo sai da própria lista: uma cópia à mão sairia de sincronia na primeira vez
    # que alguém mudasse um papel lá em cima.
    largura = max(len(chave) for chave, *_ in PESSOAS) + len(DOMINIO) + 1
    linhas = [
        f"  {f'{chave}@{DOMINIO}':<{largura}}  {nome:<16} {papel}"
        + (" (coordena)" if coordena else "")
        + ("" if status == "active" else f" — {status}")
        for chave, nome, papel, _, _, coordena, status, _ in PESSOAS
    ]
    print(
        "\n".join([
            "",
            f"tenant semeado: {slug}",
            f"  {len(PESSOAS)} pessoas, {len(DEPARTAMENTOS)} departamentos, 2 ciclos",
            f"  senha de todos: {senha}",
            "",
            *linhas,
            "",
            f"Aponte DEFAULT_TENANT_SLUG={slug} no .env e reinicie a API para entrar.",
        ])
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dados de demonstração para exercitar as telas")
    parser.add_argument("--slug", default="demo")
    parser.add_argument("--nome", default="Braga & Duarte Advogados")
    parser.add_argument("--senha", required=True)
    parser.add_argument(
        "--recriar",
        action="store_true",
        help="apaga o tenant inteiro antes de semear (só para o tenant de demonstração)",
    )
    args = parser.parse_args()
    return asyncio.run(seed(args.slug, args.nome, args.senha, args.recriar))


if __name__ == "__main__":
    sys.exit(main())
