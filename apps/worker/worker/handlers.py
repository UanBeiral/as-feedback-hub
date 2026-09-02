"""Registro de handlers de tópico do outbox.

Um handler é `async def (session, mensagem) -> None`. Ele recebe a **mesma sessão** do
despachante e escreve nela: é isso que faz o efeito e a marcação da mensagem entrarem
na mesma transação, dando a exatamente-uma-vez de PAR-07 para o que é escrita no nosso
banco. Efeito externo (email) é outra história, e está documentado em `jobs/email.py`.

O registro aceita tópico exato e prefixo. O prefixo existe por causa da auditoria, que
publica `audit.<action>` — o conjunto de ações não é fechado, e exigir registro exato
significaria uma linha nova aqui a cada ação sensível criada em qualquer contexto.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.engagement.models import OutboxMessage

Handler = Callable[[AsyncSession, OutboxMessage], Awaitable[None]]


class TopicoSemHandlerError(Exception):
    """Nenhum handler cobre o tópico.

    Vira falha da mensagem, não do worker: uma mensagem órfã (tópico removido, deploy
    pela metade) não pode derrubar o despacho das outras. Depois de `MAX_TENTATIVAS`
    ela vai para a DLQ, onde alguém decide o que fazer.
    """


class RegistroDeHandlers:
    def __init__(self) -> None:
        self._exatos: dict[str, Handler] = {}
        self._prefixos: list[tuple[str, Handler]] = []

    def registra(self, topico: str) -> Callable[[Handler], Handler]:
        def _decorator(fn: Handler) -> Handler:
            if topico in self._exatos:
                raise ValueError(f"tópico {topico!r} já tem handler")
            self._exatos[topico] = fn
            return fn

        return _decorator

    def registra_prefixo(self, prefixo: str) -> Callable[[Handler], Handler]:
        def _decorator(fn: Handler) -> Handler:
            self._prefixos.append((prefixo, fn))
            # Prefixo mais longo primeiro: `audit.member.` vence `audit.` quando os
            # dois existem, senão o registro mais genérico engoliria o específico.
            self._prefixos.sort(key=lambda par: len(par[0]), reverse=True)
            return fn

        return _decorator

    def resolve(self, topico: str) -> Handler:
        handler = self._exatos.get(topico)
        if handler is not None:
            return handler
        for prefixo, candidato in self._prefixos:
            if topico.startswith(prefixo):
                return candidato
        raise TopicoSemHandlerError(f"sem handler para o tópico {topico!r}")

    @property
    def topicos(self) -> list[str]:
        return sorted(self._exatos) + sorted(f"{p}*" for p, _ in self._prefixos)
