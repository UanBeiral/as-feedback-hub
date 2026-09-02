"""Contratos do contexto `client_eval`.

Dois públicos diferentes, dois conjuntos de schemas. O que vai para a página pública
não carrega nada do escritório além do necessário para renderizar o formulário — nem o
nome de quem está sendo avaliado, se não for para aparecer.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.contexts.client_eval.models import mascarar_whatsapp


class ClientFormIn(BaseModel):
    name: str = Field(min_length=1)
    is_default: bool = False
    is_active: bool = True


class ClientFormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_default: bool
    is_active: bool


class ClientQuestionIn(BaseModel):
    question_text: str = Field(min_length=1)
    question_type: str = Field(pattern="^(rating|text|textarea|yes_no|nps|multiple_choice)$")
    is_required: bool = True
    display_order: int | None = None
    placeholder: str | None = None


class ClientQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    is_required: bool
    display_order: int
    placeholder: str | None


class RequestEvaluationIn(BaseModel):
    target_user_id: UUID
    form_id: UUID | None = None
    client_name: str | None = None
    client_whatsapp: str | None = None
    client_email: EmailStr | None = None
    dias_de_validade: int = Field(default=30, ge=1, le=180)


class RequestEvaluationOut(BaseModel):
    """O token sai **uma vez**, na criação — é ele que vira o link do WhatsApp.

    Nas listagens o token não aparece: quem tem acesso à lista não precisa poder
    responder no lugar do cliente.
    """

    id: UUID
    token: str
    token_expires_at: datetime
    public_path: str


class EvaluationOut(BaseModel):
    """Serialização interna, com WhatsApp mascarado por padrão (BR-MIGRAR-022)."""

    id: UUID
    target_user_id: UUID
    flow_type: str
    status: str
    status_exibicao: str
    client_name: str | None
    client_whatsapp: str | None
    client_email: EmailStr | None
    overall_rating: int | None
    recommendation_rating: int | None
    has_negative: bool
    submitted_at: datetime | None
    created_at: datetime

    @classmethod
    def de_modelo(cls, avaliacao: object, *, whatsapp_completo: bool = False) -> EvaluationOut:
        numero = getattr(avaliacao, "client_whatsapp", None)
        return cls(
            id=avaliacao.id,  # type: ignore[attr-defined]
            target_user_id=avaliacao.target_user_id,  # type: ignore[attr-defined]
            flow_type=avaliacao.flow_type,  # type: ignore[attr-defined]
            status=avaliacao.status,  # type: ignore[attr-defined]
            status_exibicao=avaliacao.status_exibicao,  # type: ignore[attr-defined]
            client_name=avaliacao.client_name,  # type: ignore[attr-defined]
            client_whatsapp=numero if whatsapp_completo else mascarar_whatsapp(numero),
            client_email=avaliacao.client_email,  # type: ignore[attr-defined]
            overall_rating=avaliacao.overall_rating,  # type: ignore[attr-defined]
            recommendation_rating=avaliacao.recommendation_rating,  # type: ignore[attr-defined]
            has_negative=avaliacao.has_negative,  # type: ignore[attr-defined]
            submitted_at=avaliacao.submitted_at,  # type: ignore[attr-defined]
            created_at=avaliacao.created_at,  # type: ignore[attr-defined]
        )


class ServiceTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_order: int


# ------------------------------------------------------------------ público


class PublicQuestionOut(BaseModel):
    """O que a página pública precisa para renderizar — e nada mais."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    is_required: bool
    placeholder: str | None


class PublicFormOut(BaseModel):
    """Tudo que o wizard público precisa para desenhar as 16 etapas — e nada mais.

    Os dados de contato voltam **completos**, sem o mascaramento de BR-MIGRAR-022: ali
    o alvo é a listagem interna, onde o WhatsApp do cliente é dado de terceiro. Aqui
    quem tem o token é o próprio cliente, e a etapa de identificação nasce preenchida
    com o que o escritório já digitou na solicitação (SCR-0035 etapa 1) — pedir de novo
    o número para quem recebeu o link naquele número seria trabalho inventado.
    """

    questions: list[PublicQuestionOut]
    service_tags: list[ServiceTagOut]
    # Nome de quem será avaliado: o cliente precisa saber sobre quem está falando.
    target_name: str | None
    # Pré-preenchimento da etapa de identificação. Campos **obrigatórios no contrato**,
    # ainda que anuláveis: o front precisa distinguir "o escritório não preencheu" de
    # "esta versão da API não manda o campo", e sem isso o TypeScript gerado espalha
    # `?.` por toda a tela.
    client_name: str | None
    client_whatsapp: str | None
    client_email: EmailStr | None
    # Motivações ligadas pelo tenant (setting `client_feedback_motivations`). A etapa 2
    # some inteira quando o escritório desliga todas — e o wizard pula direto adiante.
    motivations: list[str]
    # Identidade do escritório na capa: o cliente precisa saber quem está perguntando.
    # Só o nome — o `logo_url` do catálogo de settings aponta para host arbitrário, e
    # carregar imagem de terceiro na única página aberta na internet é superfície que
    # esta tela não precisa ter.
    company_name: str | None


class PublicAnswerIn(BaseModel):
    question_id: UUID
    rating_value: int | None = None
    text_value: str | None = None

    @model_validator(mode="after")
    def _tem_conteudo(self) -> PublicAnswerIn:
        if self.rating_value is None and not (self.text_value or "").strip():
            raise ValueError("resposta sem nota nem texto")
        return self


class PublicSubmitIn(BaseModel):
    answers: list[PublicAnswerIn] = Field(default_factory=list)
    client_name: str | None = None
    client_whatsapp: str | None = None
    client_email: EmailStr | None = None
    contact_motivation: str | None = Field(
        default=None, pattern="^(praise|evaluate|problem|other)$"
    )
    contact_motivation_text: str | None = None
    # Escala 0–10, a mesma das estrelas do wizard e a mesma que os relatórios exibem
    # ("Nota Geral 9/10" em `reports/screens.md`). Ver DEV-A12 em docs/spec-deviations.md.
    overall_rating: int | None = Field(default=None, ge=0, le=10)
    recommendation_rating: int | None = Field(default=None, ge=0, le=10)
    service_tag_ids: list[UUID] = Field(default_factory=list)

    def como_mapa(self) -> dict[UUID, tuple[int | None, str | None]]:
        return {a.question_id: (a.rating_value, a.text_value) for a in self.answers}


class PublicSpontaneousIn(PublicSubmitIn):
    """Fluxo espontâneo: como o envio por token, mas dizendo sobre quem é a avaliação.

    Sem convite não há registro prévio, então o cliente precisa indicar quem atendeu.
    """

    target_user_id: UUID


class PublicSubmitOut(BaseModel):
    """Confirmação. A mesma para o primeiro envio e para o duplo clique (PAR-03)."""

    status: str = "submitted"
    mensagem: str = "Avaliação recebida. Obrigado!"
