"""Casos de uso do contexto `client_eval`.

A superfície pública é o lugar onde um erro custa mais caro: quem chama não está
logado, não tem sessão para revogar, e o link circula por WhatsApp. Três decisões
sustentam isso:

1. **A submissão é um UPDATE condicional atômico** (BR-MIGRAR-019). Não há "verifica
   depois grava" — a verificação *é* a gravação.
2. **A segunda submissão é sucesso, não erro.** O cliente que clicou duas vezes não
   precisa ver mensagem de falha; ele já respondeu, e é isso que a confirmação diz.
3. **O fluxo espontâneo nasce desligado** (AMB-002). Um endpoint que cria registro sem
   convite é superfície de spam; ele só existe quando o tenant liga.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.contexts.client_eval.models import (
    DIAS_DE_VALIDADE_DO_TOKEN,
    ClientEvalFormQuestion,
    ClientEvaluation,
)
from app.contexts.client_eval.repository import (
    ClientEvaluationRepository,
    ClientFormRepository,
    PublicEvaluationRepository,
)
from app.contexts.engagement.service import OutboxService
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import generate_public_token
from app.core.tenancy import TenantContext

# Nota que dispara a sinalização automática (BR-MIGRAR-021). O legado não registrou o
# limiar em lugar nenhum; 4 numa escala de 0–10 é a leitura conservadora — a escala é a
# das estrelas do wizard público e a dos relatórios ("Nota Geral 9/10"). O valor é
# configurável por tenant justamente para o cliente ajustar sem deploy.
NOTA_NEGATIVA_PADRAO = 4


@dataclass(frozen=True, slots=True)
class PoliticaDeSinalizacao:
    """Como o tenant decide que uma avaliação é negativa (BR-MIGRAR-021)."""

    nota_maxima: int = NOTA_NEGATIVA_PADRAO
    palavras: tuple[str, ...] = ()

    @classmethod
    def de_settings(cls, valores: dict[str, str | None]) -> PoliticaDeSinalizacao:
        """Lê do catálogo de settings, tolerando chave ausente ou mal formatada.

        Configuração quebrada não pode derrubar a submissão de um cliente: o pior caso
        aceitável é deixar de sinalizar, nunca recusar a avaliação.
        """
        bruto = valores.get("client_eval_negative_keywords") or "[]"
        try:
            palavras = tuple(str(p) for p in json.loads(bruto))
        except (ValueError, TypeError):
            palavras = ()

        try:
            nota = int(valores.get("client_eval_negative_rating_max") or NOTA_NEGATIVA_PADRAO)
        except (ValueError, TypeError):
            nota = NOTA_NEGATIVA_PADRAO

        return cls(nota_maxima=nota, palavras=palavras)

    def sinaliza(self, *, notas: list[int], textos: list[str]) -> bool:
        if any(nota <= self.nota_maxima for nota in notas):
            return True
        if not self.palavras:
            return False
        corpo = _normalizar(" ".join(textos))
        return any(_normalizar(p) in corpo for p in self.palavras if p.strip())


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento: "péssimo" e "pessimo" são a mesma reclamação."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


class ClientEvaluationService:
    """Lado interno: quem pede a avaliação e quem lê o resultado."""

    def __init__(
        self,
        evaluations: ClientEvaluationRepository,
        forms: ClientFormRepository,
        outbox: OutboxService,
    ) -> None:
        self._evaluations = evaluations
        self._forms = forms
        self._outbox = outbox

    async def request_evaluation(
        self,
        tenant: TenantContext,
        *,
        target_user_id: UUID,
        form_id: UUID | None,
        client_name: str | None,
        client_whatsapp: str | None,
        client_email: str | None,
        dias_de_validade: int = DIAS_DE_VALIDADE_DO_TOKEN,
    ) -> ClientEvaluation:
        """Gera o link com token e validade (comando `request_evaluation`).

        O token nasce aqui e não é regravável: pedir de novo cria outro registro, com
        outro link. Reaproveitar o token de uma avaliação existente permitiria que um
        link antigo, já compartilhado, abrisse uma coleta nova.
        """
        formulario = (
            await self._forms.get(form_id) if form_id else await self._forms.get_default()
        )
        if formulario is None:
            raise NotFoundError("Formulário de avaliação não encontrado")
        if not formulario.is_active:
            raise ConflictError("Formulário inativo não gera novos links")

        avaliacao = self._evaluations.add(
            ClientEvaluation(
                target_user_id=target_user_id,
                form_id=formulario.id,
                flow_type="requested",
                requested_by=tenant.user_id,
                client_name=client_name,
                client_whatsapp=_so_digitos(client_whatsapp),
                client_email=client_email,
                token=generate_public_token(),
                token_expires_at=datetime.now(UTC) + timedelta(days=dias_de_validade),
                status="pending",
            )
        )
        return avaliacao


@dataclass(frozen=True, slots=True)
class ResultadoDaSubmissao:
    evaluation: ClientEvaluation
    ja_respondida: bool
    """`True` quando esta chamada não foi a que gravou — o cliente enviou duas vezes."""


class PublicEvaluationService:
    """Lado público: o cliente, sem sessão, com um token na mão."""

    def __init__(
        self,
        publico: PublicEvaluationRepository,
        outbox_por_tenant: object,
        politica: PoliticaDeSinalizacao,
    ) -> None:
        self._publico = publico
        self._outbox_por_tenant = outbox_por_tenant
        self._politica = politica

    async def open_by_token(
        self, token: str
    ) -> tuple[ClientEvaluation, list[ClientEvalFormQuestion]]:
        """Abre o formulário (PAR-03).

        Token inexistente, expirado ou já usado recebem a **mesma** recusa. Distinguir
        "não existe" de "já foi respondido" contaria a um estranho que aquele link um
        dia valeu — e o link circula por WhatsApp.
        """
        avaliacao = await self._publico.get_por_token(token)
        if avaliacao is None:
            raise NotFoundError("Link inválido ou expirado")
        if avaliacao.status not in ("pending", "in_progress"):
            raise NotFoundError("Link inválido ou expirado")
        if avaliacao.token_expires_at is None or avaliacao.token_expires_at <= datetime.now(UTC):
            raise NotFoundError("Link inválido ou expirado")

        await self._publico.marcar_em_andamento(token)
        perguntas = await self._publico.perguntas_do_formulario(
            avaliacao.tenant_id, avaliacao.form_id
        )
        return avaliacao, perguntas

    async def submit_by_token(
        self,
        token: str,
        *,
        respostas: dict[UUID, tuple[int | None, str | None]],
        client_name: str | None = None,
        client_whatsapp: str | None = None,
        client_email: str | None = None,
        contact_motivation: str | None = None,
        contact_motivation_text: str | None = None,
        overall_rating: int | None = None,
        recommendation_rating: int | None = None,
        tracking_data: dict | None = None,
    ) -> ResultadoDaSubmissao:
        """Submissão idempotente por construção (BR-MIGRAR-019 / PAR-03).

        A reivindicação atômica decide quem grava. Quem chegou depois recebe a mesma
        confirmação, sem erro — inclusive o duplo clique, que é o caso comum.
        """
        avaliacao = await self._publico.reivindicar_para_submissao(token)
        if avaliacao is None:
            # Não ganhou a corrida: ou já estava respondida (idempotente), ou o link
            # não vale mais (recusa).
            existente = await self._publico.get_por_token(token)
            if existente is not None and existente.status == "submitted":
                return ResultadoDaSubmissao(evaluation=existente, ja_respondida=True)
            raise NotFoundError("Link inválido ou expirado")

        perguntas = {
            q.id: q
            for q in await self._publico.perguntas_do_formulario(
                avaliacao.tenant_id, avaliacao.form_id
            )
        }
        _validar_respostas(perguntas, respostas)

        for question_id, (nota, texto) in respostas.items():
            if nota is None and not (texto or "").strip():
                continue
            self._publico.registrar_resposta(
                tenant_id=avaliacao.tenant_id,
                evaluation_id=avaliacao.id,
                question_id=question_id,
                rating_value=nota,
                text_value=texto,
            )

        if client_name:
            avaliacao.client_name = client_name
        if client_whatsapp:
            avaliacao.client_whatsapp = _so_digitos(client_whatsapp)
        if client_email:
            avaliacao.client_email = client_email
        avaliacao.contact_motivation = contact_motivation or avaliacao.contact_motivation
        avaliacao.contact_motivation_text = contact_motivation_text
        avaliacao.overall_rating = overall_rating
        avaliacao.recommendation_rating = recommendation_rating
        avaliacao.tracking_data = tracking_data

        notas = [n for n, _ in respostas.values() if n is not None]
        notas += [r for r in (overall_rating, recommendation_rating) if r is not None]
        textos = [t for _, t in respostas.values() if t]
        if contact_motivation_text:
            textos.append(contact_motivation_text)
        avaliacao.has_negative = self._politica.sinaliza(notas=notas, textos=textos)

        outbox: OutboxService = self._outbox_por_tenant(avaliacao.tenant_id)  # type: ignore[operator]
        await outbox.enqueue(
            topic="client_eval.submitted",
            payload={
                "evaluation_id": str(avaliacao.id),
                "user_id": str(avaliacao.target_user_id),
            },
            idempotency_key=f"client_eval.submitted:{avaliacao.id}",
        )
        if avaliacao.has_negative:
            # Aviso separado: nota baixa não pode se perder no meio das notificações
            # comuns — é o caso em que alguém precisa ligar para o cliente hoje.
            await outbox.enqueue(
                topic="client_eval.flagged_negative",
                payload={
                    "evaluation_id": str(avaliacao.id),
                    "user_id": str(avaliacao.target_user_id),
                },
                idempotency_key=f"client_eval.flagged_negative:{avaliacao.id}",
            )

        return ResultadoDaSubmissao(evaluation=avaliacao, ja_respondida=False)

    async def criar_espontanea(
        self,
        *,
        tenant_id: UUID,
        form_id: UUID,
        target_user_id: UUID,
        habilitado: bool,
        respostas: dict[UUID, tuple[int | None, str | None]],
        client_name: str | None = None,
        client_whatsapp: str | None = None,
        client_email: str | None = None,
        contact_motivation: str | None = None,
        contact_motivation_text: str | None = None,
        overall_rating: int | None = None,
        recommendation_rating: int | None = None,
        tracking_data: dict | None = None,
    ) -> ClientEvaluation:
        """Fluxo espontâneo: cliente avalia sem ter sido convidado (AMB-002).

        Nasce desligado por tenant, e a checagem é a primeira linha: um endpoint que
        cria registro sem convite é superfície de spam aberta na internet. Quando ligado,
        grava direto como `submitted` — não há token para reivindicar, o envio é o
        próprio ato de criar.
        """
        if not habilitado:
            raise ValidationError(
                "Fluxo espontâneo não habilitado neste tenant",
                details={"chave": "client_eval_spontaneous_enabled"},
            )

        perguntas = {
            q.id: q for q in await self._publico.perguntas_do_formulario(tenant_id, form_id)
        }
        _validar_respostas(perguntas, respostas)

        avaliacao = ClientEvaluation(
            tenant_id=tenant_id,
            target_user_id=target_user_id,
            form_id=form_id,
            flow_type="spontaneous",
            token=None,
            token_expires_at=None,
            status="submitted",
            submitted_at=datetime.now(UTC),
            client_name=client_name,
            client_whatsapp=_so_digitos(client_whatsapp),
            client_email=client_email,
            contact_motivation=contact_motivation,
            contact_motivation_text=contact_motivation_text,
            overall_rating=overall_rating,
            recommendation_rating=recommendation_rating,
            tracking_data=tracking_data,
        )
        self._publico.adicionar(avaliacao)
        await self._publico.flush()

        for question_id, (nota, texto) in respostas.items():
            if nota is None and not (texto or "").strip():
                continue
            self._publico.registrar_resposta(
                tenant_id=tenant_id,
                evaluation_id=avaliacao.id,
                question_id=question_id,
                rating_value=nota,
                text_value=texto,
            )

        notas = [n for n, _ in respostas.values() if n is not None]
        notas += [r for r in (overall_rating, recommendation_rating) if r is not None]
        textos = [t for _, t in respostas.values() if t]
        avaliacao.has_negative = self._politica.sinaliza(notas=notas, textos=textos)

        outbox: OutboxService = self._outbox_por_tenant(tenant_id)  # type: ignore[operator]
        await outbox.enqueue(
            topic="client_eval.submitted",
            payload={"evaluation_id": str(avaliacao.id), "user_id": str(target_user_id)},
            idempotency_key=f"client_eval.submitted:{avaliacao.id}",
        )
        return avaliacao


def _validar_respostas(
    perguntas: dict[UUID, ClientEvalFormQuestion],
    respostas: dict[UUID, tuple[int | None, str | None]],
) -> None:
    desconhecidas = [str(qid) for qid in respostas if qid not in perguntas]
    if desconhecidas:
        raise ValidationError(
            "Resposta para pergunta que não é deste formulário",
            details={"question_ids": desconhecidas},
        )

    faltando = [
        str(q.id)
        for q in perguntas.values()
        if q.is_required and not _preenchida(respostas.get(q.id))
    ]
    if faltando:
        raise ValidationError(
            "Respostas obrigatórias em branco", details={"question_ids": faltando}
        )


def _preenchida(valor: tuple[int | None, str | None] | None) -> bool:
    if valor is None:
        return False
    nota, texto = valor
    return nota is not None or bool((texto or "").strip())


def _so_digitos(numero: str | None) -> str | None:
    """WhatsApp normalizado como no legado: só dígitos, para comparar e mascarar."""
    if not numero:
        return numero
    return "".join(c for c in numero if c.isdigit()) or None
