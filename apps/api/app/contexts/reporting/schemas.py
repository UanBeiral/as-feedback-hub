"""Contratos do contexto `reporting` (AD-08)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Linha360Out(BaseModel):
    profile_id: UUID
    nome: str
    departamento: str | None
    recebidos: int
    respondidos: int
    percentual: float
    media_nota: float | None


class LinhaClienteOut(BaseModel):
    profile_id: UUID
    nome: str
    avaliacoes: int
    respondidas: int
    media_geral: float | None
    negativas: int


class LinhaEngajamentoOut(BaseModel):
    profile_id: UUID
    nome: str
    solicitados: int
    enviados: int
    percentual: float


class ExecutiveReportIn(BaseModel):
    """Escopo do relatório executivo (BR-MIGRAR-028).

    Os campos são opcionais no schema e obrigatórios na regra, conforme o escopo — a
    validação vive no service porque depende da combinação, não de um campo isolado.
    """

    escopo: str = Field(pattern="^(general|person|specific)$")
    cycle_id: UUID | None = None
    profile_id: UUID | None = None
    giver_id: UUID | None = None
    email_to: EmailStr | None = None


class ExportRequestIn(BaseModel):
    kind: str = Field(pattern="^(report_360|client|engagement|executive)$")
    format: str = Field(pattern="^(xlsx|pdf)$")
    filters: dict[str, Any] = Field(default_factory=dict)
    email_to: EmailStr | None = None


class ExportJobOut(BaseModel):
    id: UUID
    kind: str
    format: str
    status: str
    filters: dict[str, Any]
    error: str | None
    completed_at: datetime | None
    email_to: str | None
    email_sent_at: datetime | None
    email_error: str | None
    # Só aparece quando o arquivo existe: link para algo que não saiu é pior que
    # nenhum link.
    download_path: str | None

    @classmethod
    def de_modelo(cls, job: Any) -> ExportJobOut:
        return cls(
            id=job.id,
            kind=job.kind,
            format=job.format,
            status=job.status,
            filters=job.filters,
            error=job.error,
            completed_at=job.completed_at,
            email_to=job.email_to,
            email_sent_at=job.email_sent_at,
            email_error=job.email_error,
            download_path=(
                f"/api/v1/reports/exports/{job.id}/download" if job.pronto else None
            ),
        )


class ItemDeHistoricoOut(BaseModel):
    tipo: str
    quando: datetime | None
    sobre_id: UUID
    sobre_nome: str
    titulo: str
    detalhe: str | None
    lido_em: datetime | None


class HistoricoDaEquipeOut(BaseModel):
    """As três seções do histórico, como no legado."""

    livre: list[ItemDeHistoricoOut]
    clientes: list[ItemDeHistoricoOut]
    ciclos: list[ItemDeHistoricoOut]


class PeriodoIn(BaseModel):
    desde: date | None = None
    ate: date | None = None
