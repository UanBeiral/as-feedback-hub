"""Configuração dos testes.

As variáveis de ambiente são definidas antes de qualquer import de `app.*`: Settings
falha ao instanciar sem `JWT_SECRET`, e é assim que queremos que se comporte.
"""

from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "chave-de-teste-com-mais-de-32-caracteres-ok")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
