"""Adapter de email (BR-MIGRAR-030 / R-11): provedor trocável por variável de ambiente.

Uma ressalva que precisa estar escrita onde se envia email, e não só na documentação:
**efeito externo é entrega ao-menos-uma-vez.** A notificação no banco é exatamente-uma,
porque entra na mesma transação da marcação da mensagem. O email não — se o provedor
aceitar e o commit falhar depois, a mensagem volta para a fila e o email sai de novo.
Duplicar um aviso é aceitável; perder é pior. Onde isso não servir (cobrança, por
exemplo), o caminho é registrar o envio no banco antes e checar no reprocessamento.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailAdapter(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailAdapter:
    """Escreve no log em vez de enviar. É o provedor de desenvolvimento.

    Não é um stub vazio de propósito: em desenvolvimento a pergunta que aparece é
    "esse email saiu, e com que texto?", e o log responde as duas.
    """

    def __init__(self, remetente: str) -> None:
        self._remetente = remetente

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info(
            "[email:console] de=%s para=%s assunto=%r corpo=%r",
            self._remetente,
            to,
            subject,
            body[:200],
        )


class ProvedorNaoConfiguradoError(RuntimeError):
    """Provedor selecionado por env que ainda não tem implementação.

    Levantar aqui é melhor que enviar silenciosamente por outro caminho: o despachante
    trata como falha, a mensagem tenta de novo e termina na DLQ com o motivo à vista —
    em vez de "o cliente jura que não recebeu" seis meses depois.
    """


def build_email_adapter(settings: Settings) -> EmailAdapter:
    provedor = settings.email_provider.lower()
    if provedor == "console":
        return ConsoleEmailAdapter(settings.email_from)
    raise ProvedorNaoConfiguradoError(
        f"EMAIL_PROVIDER={settings.email_provider!r} ainda não implementado. "
        "Hoje só existe 'console'; Resend e SMTP entram junto com o envio de "
        "relatórios (BR-MIGRAR-029/030)."
    )
