"""Casos de uso do contexto `reporting`.

Duas responsabilidades, e a fronteira entre elas é o que AD-07 decidiu:

- **CSV é síncrono.** Texto separado por `;` (BR-MIGRAR-029), montado na hora e
  devolvido na resposta. Não vale a pena orquestrar um job para algo que sai em
  milissegundos.
- **PDF e XLSX viram job.** Vão para `export_jobs` + outbox, e o worker gera o arquivo
  e disponibiliza por link. No legado eram montados no browser, e um relatório grande
  travava a aba de quem pediu.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from app.contexts.engagement.service import OutboxService
from app.contexts.reporting.models import ExportJob
from app.contexts.reporting.queries import (
    LIMITE_PREVIEW,
    LIMITE_TABELA,
    ClientReportQuery,
    EngagementQuery,
    Report360Query,
)
from app.contexts.reporting.repository import ExportJobRepository
from app.core.errors import AuthorizationError, ValidationError
from app.core.tenancy import TenantContext

# Separador do legado. Vírgula quebraria o Excel em português, que é onde estes
# arquivos são abertos (BR-MIGRAR-029).
SEPARADOR_CSV = ";"

# Escopos do relatório executivo (BR-MIGRAR-028).
ESCOPOS = ("general", "person", "specific")


@dataclass(frozen=True, slots=True)
class Csv:
    conteudo: str
    nome_do_arquivo: str


class ReportService:
    """Consultas dos três relatórios, com os limites de linha da regra."""

    def __init__(
        self,
        report_360: Report360Query,
        clientes: ClientReportQuery,
        engajamento: EngagementQuery,
    ) -> None:
        self._360 = report_360
        self._clientes = clientes
        self._engajamento = engajamento

    async def feedback_360(
        self,
        *,
        cycle_id: UUID | None,
        department_id: UUID | None,
        preview: bool = False,
    ) -> list[Any]:
        return await self._360.linhas(
            cycle_id=cycle_id,
            department_id=department_id,
            limite=LIMITE_PREVIEW if preview else LIMITE_TABELA,
        )

    async def clientes(
        self,
        tenant: TenantContext,
        *,
        target_user_id: UUID | None = None,
        desde: date | None = None,
        ate: date | None = None,
        apenas_negativas: bool = False,
        preview: bool = False,
    ) -> list[Any]:
        """Relatório de cliente respeita `can_generate_reports` (BR-MIGRAR-029).

        É capacidade individual, não papel: não adianta ser admin se a flag não está
        no perfil (BR-MIGRAR-013/015). A checagem fica no service, e não só no guard da
        rota, porque este método também é chamado pelo worker ao gerar a exportação.
        """
        if not tenant.has_flag("can_generate_reports"):
            raise AuthorizationError(
                "Capacidade de gerar relatórios não habilitada",
                details={"required_flags": ["can_generate_reports"]},
            )
        return await self._clientes.linhas(
            target_user_id=target_user_id,
            desde=desde,
            ate=ate,
            apenas_negativas=apenas_negativas,
            limite=LIMITE_PREVIEW if preview else LIMITE_TABELA,
        )

    async def engajamento(self, *, preview: bool = False) -> list[Any]:
        return await self._engajamento.linhas(
            limite=LIMITE_PREVIEW if preview else LIMITE_TABELA
        )


def validar_escopo_executivo(
    *, escopo: str, cycle_id: UUID | None, profile_id: UUID | None, giver_id: UUID | None
) -> None:
    """Validação de escopo do relatório executivo (BR-MIGRAR-028 / PAR-04).

    A regra do legado, preservada: ciclo e pessoa são obrigatórios, exceto no escopo
    geral; e escopo específico exige dizer **de quem** é a avaliação. A validação vem
    antes de qualquer geração — recusar depois de montar o PDF desperdiça trabalho e,
    pior, entrega um documento com escopo errado.
    """
    if escopo not in ESCOPOS:
        raise ValidationError("Escopo inválido", details={"escopos": list(ESCOPOS)})

    if escopo != "general":
        faltando = [
            campo
            for campo, valor in (("cycle_id", cycle_id), ("profile_id", profile_id))
            if valor is None
        ]
        if faltando:
            raise ValidationError(
                "Informe o ciclo e a pessoa para gerar o relatório",
                details={"faltando": faltando},
            )

    if escopo == "specific" and giver_id is None:
        raise ValidationError(
            "Escopo específico exige informar o avaliador",
            details={"faltando": ["giver_id"]},
        )


class ExportService:
    """Exportações: CSV na hora, PDF/XLSX por job (AD-07)."""

    def __init__(self, jobs: ExportJobRepository, outbox: OutboxService) -> None:
        self._jobs = jobs
        self._outbox = outbox

    @staticmethod
    def para_csv(cabecalho: list[str], linhas: list[list[Any]], *, nome: str) -> Csv:
        """CSV com separador `;` e quebra de linha compatível com Excel."""
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=SEPARADOR_CSV, lineterminator="\r\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
        return Csv(conteudo=buffer.getvalue(), nome_do_arquivo=nome)

    async def solicitar(
        self,
        tenant: TenantContext,
        *,
        kind: str,
        formato: str,
        filtros: dict[str, Any],
        email_to: str | None = None,
    ) -> ExportJob:
        """Registra o pedido e enfileira o processamento, na mesma transação (AD-04).

        Se o worker estiver fora do ar, o pedido fica gravado e o arquivo sai quando
        ele voltar — em vez de o usuário receber um erro e perder os filtros que
        montou.
        """
        if formato == "csv":
            raise ValidationError(
                "CSV é gerado na hora, sem job",
                details={"endpoint": "/reports/<tipo>.csv"},
            )

        # O id é gerado aqui, e não pelo default da coluna, porque a chave de
        # idempotência da mensagem de outbox precisa dele **antes** do flush — e o
        # default do ORM só age no INSERT.
        job = self._jobs.add(
            ExportJob(
                id=uuid4(),
                requested_by=tenant.user_id,
                kind=kind,
                format=formato,
                filters=filtros,
                status="pending",
                email_to=email_to,
            )
        )
        await self._outbox.enqueue(
            topic="export.requested",
            payload={"job_id": str(job.id), "user_id": str(tenant.user_id)},
            idempotency_key=f"export.requested:{job.id}",
        )
        return job
