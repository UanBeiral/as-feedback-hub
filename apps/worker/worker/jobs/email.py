"""Adapter de email (BR-MIGRAR-030 / R-11): provedor trocável por variável de ambiente.

Uma ressalva que precisa estar escrita onde se envia email, e não só na documentação:
**efeito externo é entrega ao-menos-uma-vez.** A notificação no banco é exatamente-uma,
porque entra na mesma transação da marcação da mensagem. O email não — se o provedor
aceitar e o commit falhar depois, a mensagem volta para a fila e o email sai de novo.
Duplicar um aviso é aceitável; perder é pior. Onde isso não servir (cobrança, por
exemplo), o caminho é registrar o envio no banco antes e checar no reprocessamento.

**Configuração ausente e falha do provedor têm tratamentos distintos**, como BR-MIGRAR-030
pede, e a diferença é onde cada uma explode:

- *Configuração ausente* levanta no `build_email_adapter`, antes de o worker aceitar o
  primeiro lote. O container não sobe, e quem fez o deploy vê o motivo no `docker logs`.
  A alternativa — subir e falhar em cada envio — encheria a DLQ em silêncio, e o
  escritório descobriria por um cliente dizendo que não recebeu.
- *Falha do provedor* levanta no `send`, e aí é o despachante que decide: retry com
  backoff e, no limite, DLQ com o motivo à vista. Provedor fora do ar é estado
  temporário, e derrubar o worker por causa disso pararia também as notificações no app,
  que não dependem de email nenhum.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Curto de propósito: o worker despacha em lote e em série, então um provedor lento
# segura a fila inteira. Melhor falhar e tentar de novo no próximo ciclo do que deixar
# vinte avisos esperando por um.
TIMEOUT_SEGUNDOS = 10.0


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


class EnvioDeEmailError(RuntimeError):
    """O provedor recusou ou não respondeu.

    Distinta de `ProvedorNaoConfiguradoError`: esta é temporária e retentável, aquela
    não melhora sozinha.
    """


class ResendEmailAdapter:
    """Envio pelo Resend — o provedor que o legado já usava (R-11).

    Uma conexão HTTP para o adapter inteiro, e não uma por email: o worker manda em lote,
    e reabrir TLS a cada aviso é o custo que aparece justamente no dia de ciclo aberto,
    quando saem quarenta de uma vez.

    O corpo vai como texto puro. O legado mandava HTML, e a diferença não vale o preço:
    quem lê um aviso de feedback quer saber o que aconteceu e clicar num link, e HTML
    traria template, escape e um segundo jeito de o texto sair errado.
    """

    URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, remetente: str) -> None:
        self._remetente = remetente
        self._cliente = httpx.AsyncClient(
            timeout=TIMEOUT_SEGUNDOS,
            headers={"authorization": f"Bearer {api_key}"},
        )

    async def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            resposta = await self._cliente.post(
                self.URL,
                json={"from": self._remetente, "to": [to], "subject": subject, "text": body},
            )
        except httpx.HTTPError as erro:
            raise EnvioDeEmailError(f"Resend não respondeu: {erro}") from erro

        if resposta.status_code >= 400:
            # O corpo do erro entra na mensagem porque é ele que diz *qual* é o problema
            # — domínio não verificado, remetente recusado, chave sem permissão. Sem
            # isso, a DLQ guardaria "422" e ninguém saberia o que corrigir. Truncado,
            # porque a mensagem vai para uma coluna de texto que alguém vai ler.
            raise EnvioDeEmailError(
                f"Resend recusou ({resposta.status_code}): {resposta.text[:300]}"
            )


class SmtpEmailAdapter:
    """Envio por SMTP — a contingência de R-11, e o caminho de quem hospeda o próprio.

    `smtplib` roda em thread porque é bloqueante: chamá-lo direto travaria o loop do
    worker durante o handshake TLS, e com ele o despacho de tudo o mais. Uma dependência
    async a menos vale a thread — o worker manda em série de qualquer jeito.

    Conexão por email, e não reaproveitada como no Resend: servidor SMTP costuma derrubar
    sessão ociosa sem avisar, e uma conexão guardada que morreu entre um lote e outro
    falha no envio seguinte por um motivo que não tem nada a ver com ele.

    **STARTTLS é obrigatório por padrão** (`tls=True`). Cair para texto puro quando o
    servidor não anuncia a extensão é exatamente o downgrade que o STARTTLS existe para
    impedir — e o que passa por aqui inclui link de redefinição de senha. Quem tem relay
    interno sem TLS desliga com `SMTP_TLS=false`, que é uma decisão registrada no `.env`
    e não um silêncio no código.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        remetente: str,
        tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._remetente = remetente
        self._tls = tls

    def _enviar(self, *, to: str, subject: str, body: str) -> None:
        mensagem = EmailMessage()
        mensagem["From"] = self._remetente
        mensagem["To"] = to
        mensagem["Subject"] = subject
        mensagem.set_content(body)

        # 465 é TLS desde o primeiro byte; 587 abre em claro e sobe com STARTTLS. Chutar
        # um dos dois faria o outro falhar com erro de protocolo, que não diz nada a
        # quem configurou a porta certa.
        if self._port == 465:
            with smtplib.SMTP_SSL(self._host, self._port, timeout=TIMEOUT_SEGUNDOS) as smtp:
                if self._user:
                    smtp.login(self._user, self._password)
                smtp.send_message(mensagem)
            return

        with smtplib.SMTP(self._host, self._port, timeout=TIMEOUT_SEGUNDOS) as smtp:
            if self._tls:
                # Sem `try`: servidor que não anuncia STARTTLS levanta aqui, e é o que
                # deve acontecer. Seguir em claro seria entregar a senha e o link de
                # redefinição a quem estiver no caminho.
                smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(mensagem)

    async def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            await asyncio.to_thread(self._enviar, to=to, subject=subject, body=body)
        except (smtplib.SMTPException, OSError) as erro:
            raise EnvioDeEmailError(f"SMTP falhou: {erro}") from erro


class ProvedorNaoConfiguradoError(RuntimeError):
    """Provedor selecionado por env sem a configuração que ele exige.

    Levantar aqui é melhor que enviar silenciosamente por outro caminho, e melhor que
    subir o worker para falhar em cada mensagem: o container não sobe, e quem fez o
    deploy lê o motivo no log em vez de descobrir pela DLQ.
    """


def build_email_adapter(settings: Settings) -> EmailAdapter:
    provedor = settings.email_provider.lower().strip()

    if provedor == "console":
        return ConsoleEmailAdapter(settings.email_from)

    if provedor == "resend":
        if not settings.resend_api_key:
            raise ProvedorNaoConfiguradoError(
                "EMAIL_PROVIDER=resend exige RESEND_API_KEY. O domínio de EMAIL_FROM "
                "também precisa estar verificado no Resend, ou todo envio volta 403."
            )
        return ResendEmailAdapter(settings.resend_api_key, settings.email_from)

    if provedor == "smtp":
        if not settings.smtp_host:
            raise ProvedorNaoConfiguradoError("EMAIL_PROVIDER=smtp exige SMTP_HOST.")
        # Usuário vazio é servidor sem autenticação, que existe em rede interna — mas
        # usuário sem senha é quase sempre variável esquecida no deploy, e o erro que
        # apareceria é "autenticação falhou", que manda procurar no lugar errado.
        if settings.smtp_user and not settings.smtp_password:
            raise ProvedorNaoConfiguradoError(
                "SMTP_USER definido sem SMTP_PASSWORD. Deixe os dois em branco para "
                "servidor sem autenticação."
            )
        # Senha em conexão sem TLS é senha entregue a quem estiver no caminho. Relay
        # interno sem TLS existe e é legítimo — com autenticação, não.
        if settings.smtp_user and not settings.smtp_tls and settings.smtp_port != 465:
            raise ProvedorNaoConfiguradoError(
                "SMTP_TLS=false com SMTP_USER manda a senha em texto puro. Use TLS, ou "
                "um relay sem autenticação."
            )
        return SmtpEmailAdapter(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            remetente=settings.email_from,
            tls=settings.smtp_tls,
        )

    raise ProvedorNaoConfiguradoError(
        f"EMAIL_PROVIDER={settings.email_provider!r} não existe. "
        "Os valores aceitos são 'console', 'resend' e 'smtp'."
    )
