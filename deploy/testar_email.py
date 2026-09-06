"""Manda um email de teste pelo provedor configurado.

    PYTHONPATH=apps/api:apps/worker python deploy/testar_email.py voce@empresa.com.br

Existe por causa de R-11: o risco não é o código do adapter, é o **domínio** — chave sem
permissão, remetente não verificado, DKIM ausente. Nada disso aparece em teste
automatizado, porque em teste o provedor é um dublê. Só aparece quando um email de
verdade sai para uma caixa de verdade, e é melhor que isso aconteça na véspera do corte
do que no dia em que o primeiro ciclo abrir.

O script não é fixture de teste nem roda no CI: é ferramenta de operação, do mesmo
tamanho e com o mesmo propósito de `seed_demo.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime

from app.core.config import get_settings
from worker.jobs.email import (
    EnvioDeEmailError,
    ProvedorNaoConfiguradoError,
    build_email_adapter,
)


async def enviar(destino: str) -> int:
    settings = get_settings()
    print(f"provedor : {settings.email_provider}")
    print(f"remetente: {settings.email_from}")
    print(f"destino  : {destino}")

    try:
        adapter = build_email_adapter(settings)
    except ProvedorNaoConfiguradoError as erro:
        # Configuração ausente: o worker também recusaria subir com isto, e a mensagem
        # é a mesma que apareceria no `docker logs`.
        print(f"\nconfiguração incompleta: {erro}", file=sys.stderr)
        return 2

    agora = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    try:
        await adapter.send(
            to=destino,
            subject="Teste de envio — A&S Feedback Hub",
            body=(
                "Se este email chegou, o provedor está configurado e o domínio aceita "
                f"o remetente.\n\nEnviado em {agora} por deploy/testar_email.py.\n\n"
                "Confira também se a mensagem caiu no spam: SPF e DKIM ausentes não "
                "impedem a entrega, mas mudam onde ela para."
            ),
        )
    except EnvioDeEmailError as erro:
        print(f"\nprovedor recusou: {erro}", file=sys.stderr)
        return 1

    print("\nenviado. Confira a caixa — inclusive o spam.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destino", help="para quem mandar o teste")
    return asyncio.run(enviar(parser.parse_args().destino))


if __name__ == "__main__":
    raise SystemExit(main())
