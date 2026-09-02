"""Escreve o OpenAPI da API em um arquivo, sem subir servidor.

É a primeira metade de AD-08: o contrato sai daqui e vira o client TypeScript do front
(`npm run gen:api`). Sem isto, alguém redefiniria os tipos à mão no front — que é
exatamente o que BR-DESCARTAR-004 mandou parar de fazer, depois de o legado acumular
`as any` para contornar tipos desatualizados.

Uso:
    JWT_SECRET=... PYTHONPATH=apps/api python apps/api/scripts/dump_openapi.py [destino]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# O schema não depende de segredo real, mas `Settings` exige um: gerar contrato não
# pode obrigar quem roda o codegen a ter as credenciais do ambiente.
os.environ.setdefault("JWT_SECRET", "apenas-para-gerar-o-contrato-openapi-1234")

from app.main import create_app  # noqa: E402

DESTINO_PADRAO = Path("apps/web/openapi.json")


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO_PADRAO
    destino.parent.mkdir(parents=True, exist_ok=True)

    esquema = create_app().openapi()
    destino.write_text(
        json.dumps(esquema, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    caminhos = len(esquema.get("paths", {}))
    print(f"OpenAPI escrito em {destino} ({caminhos} rotas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
