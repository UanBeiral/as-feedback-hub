"""Contratos do contexto `feedback` (AD-08).

O detalhe que mais importa aqui é `AnswerIn`: o front manda uma lista de respostas, e é
o schema que garante que cada uma tem pergunta e conteúdo antes de o service olhar.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FormIn(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None


class QuestionIn(BaseModel):
    question_text: str = Field(min_length=1)
    question_type: str = Field(pattern="^(rating|textarea)$")
    required: bool = True
    help_text: str | None = None
    sort_order: int | None = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    required: bool
    help_text: str | None
    sort_order: int


class FormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    archived_at: datetime | None


class ReorderIn(BaseModel):
    question_ids: list[UUID] = Field(min_length=1)


class PermissionIn(BaseModel):
    reviewer_id: UUID
    reviewee_id: UUID
    permission_type: str
    cycle_id: UUID | None = None
    active: bool = True


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    permission_type: str
    cycle_id: UUID | None
    active: bool


class CycleIn(BaseModel):
    name: str = Field(min_length=1)
    form_id: UUID
    start_date: date
    end_date: date
    frequency: str | None = None
    evaluated_start: date | None = None
    evaluated_end: date | None = None


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    form_id: UUID
    frequency: str | None
    status: str
    start_date: date
    end_date: date
    evaluated_start: date | None
    evaluated_end: date | None
    closed_at: datetime | None
    published_at: datetime | None


class ExtendIn(BaseModel):
    evaluated_end: date


class OpenCycleOut(BaseModel):
    cycle: CycleOut
    requests_criados: int
    pares_elegiveis: int


class ProgressOut(BaseModel):
    """O número que todos os papéis veem — vindo do mesmo serviço (PAR-04)."""

    total: int
    concluidos: int
    pendentes: int
    atrasados: int
    excluidos: int
    percentual: float


class ParDePermissaoOut(BaseModel):
    permission_id: UUID
    reviewer_id: UUID
    reviewer_nome: str
    reviewee_id: UUID
    reviewee_nome: str
    permission_type: str


class PessoaComCargaOut(BaseModel):
    profile_id: UUID
    nome: str
    quantidade: int


class DiagnosticoOut(BaseModel):
    """Retrato do que vai dar errado no próximo ciclo, se nada mudar."""

    pontos_de_atencao: int
    ciclo_ativo: str | None
    dias_para_fechar: int | None
    permissoes_ativas: int
    usuarios_ativos: int
    requests_a_criar: int

    sem_request: list[ParDePermissaoOut]
    par_reverso_faltando: list[ParDePermissaoOut]
    sem_cobertura: list[PessoaComCargaOut]
    com_usuario_inativo: list[ParDePermissaoOut]

    media_por_avaliador: float
    media_por_avaliado: float
    poucos_avaliadores: list[PessoaComCargaOut]
    poucos_avaliados: list[PessoaComCargaOut]


class AnswerIn(BaseModel):
    question_id: UUID
    answer_text: str | None = None
    answer_score: int | None = None

    @model_validator(mode="after")
    def _tem_conteudo(self) -> AnswerIn:
        if not (self.answer_text or "").strip() and self.answer_score is None:
            raise ValueError("resposta sem texto nem nota")
        return self


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(default_factory=list)

    def como_mapa(self) -> dict[UUID, tuple[str | None, int | None]]:
        return {a.question_id: (a.answer_text, a.answer_score) for a in self.answers}


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: UUID
    answer_text: str | None
    answer_score: int | None


class CancelIn(BaseModel):
    justificativa: str = Field(min_length=1)


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cycle_id: UUID
    form_id: UUID
    giver_id: UUID
    receiver_id: UUID
    status: str
    due_date: date | None
    submitted_at: datetime | None
    cancel_justification: str | None


class RequestDetailOut(RequestOut):
    """Request com o que o formulário precisa para renderizar e retomar o rascunho."""

    questions: list[QuestionOut]
    answers: list[AnswerOut]


class FreeFeedbackIn(BaseModel):
    receiver_id: UUID
    is_anonymous: bool = False
    is_sensitive: bool = False
    positives: str | None = None
    improvements: str | None = None
    message: str | None = None


class FreeFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # `giver_id` só existe quando não é anônimo — e aí é nulo no banco, não escondido
    # na serialização (AMB-001).
    giver_id: UUID | None
    receiver_id: UUID
    is_anonymous: bool
    is_sensitive: bool
    positives: str | None
    improvements: str | None
    message: str | None
    read_at: datetime | None
    created_at: datetime


class CycleNoteIn(BaseModel):
    cycle_id: UUID
    about_user_id: UUID
    content: str = Field(min_length=1)
    is_audio_transcription: bool = False


class CycleNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cycle_id: UUID
    about_user_id: UUID
    content: str
    is_audio_transcription: bool
    created_at: datetime
