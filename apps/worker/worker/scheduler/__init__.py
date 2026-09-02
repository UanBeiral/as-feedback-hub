"""Scheduler do worker — substituto do `pg_cron` (AD-05 / BR-DESCARTAR-003).

O legado agendava jobs com `cron.schedule(...)` executado no SQL Editor: o agendamento
existia só dentro do banco, não estava em migration nenhuma, e ninguém no repositório
sabia o que rodava nem quando (é o AMB-008, ainda aberto contra a produção). Aqui todo
job agendado é código versionado, com nome e intervalo visíveis em `JOBS`.

Quem registra os jobs é `worker/jobs/schedule.py` — a agenda inteira do sistema em um
arquivo só. Hoje há dois, ambos de `feedback`: fechamento de ciclo com carência
(BR-MIGRAR-005) e expiração de requests vencidos (BR-MIGRAR-003/007). A expiração de
tokens públicos entra com `client_eval`.

O `pg_cron` de produção precisa ser inventariado (AMB-008) antes de considerarmos esta
lista completa: o que roda hoje lá dentro é a especificação do que ainda falta aqui.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

JobAgendado = Callable[[], Awaitable[None]]


@dataclass
class _Entrada:
    nome: str
    intervalo: timedelta
    job: JobAgendado
    proxima_execucao: datetime


@dataclass
class Scheduler:
    """Relógio simples: cada job tem um intervalo e a hora da próxima execução.

    Não há persistência do agendamento de propósito. Com uma réplica só (a restrição
    registrada no `docker-compose.yml`), reiniciar o worker adia o job em no máximo um
    intervalo. Persistir exigiria eleição de líder para escalar, e esse problema só vale
    a pena quando houver motivo para mais de uma réplica.
    """

    _entradas: list[_Entrada] = field(default_factory=list)

    def registra(self, nome: str, intervalo: timedelta) -> Callable[[JobAgendado], JobAgendado]:
        def _decorator(job: JobAgendado) -> JobAgendado:
            if any(e.nome == nome for e in self._entradas):
                raise ValueError(f"job {nome!r} já registrado")
            self._entradas.append(
                _Entrada(
                    nome=nome,
                    intervalo=intervalo,
                    job=job,
                    proxima_execucao=datetime.now(UTC) + intervalo,
                )
            )
            return job

        return _decorator

    @property
    def jobs(self) -> list[str]:
        return [e.nome for e in self._entradas]

    async def tick(self, agora: datetime | None = None) -> list[str]:
        """Roda o que venceu. Devolve os nomes executados.

        Um job que levanta exceção não impede os outros, e não reagenda diferente: o
        erro vai para o log e a próxima execução segue o intervalo normal. Job agendado
        que falha em silêncio é como o legado perdia fechamento de ciclo.
        """
        agora = agora or datetime.now(UTC)
        executados: list[str] = []

        for entrada in self._entradas:
            if entrada.proxima_execucao > agora:
                continue
            entrada.proxima_execucao = agora + entrada.intervalo
            try:
                await entrada.job()
            except Exception:
                logger.exception("scheduler: job %s falhou", entrada.nome)
            else:
                executados.append(entrada.nome)

        return executados


scheduler = Scheduler()
