"""Autenticação: hash de senha e tokens (AD-03).

Duas decisões que valem explicação:

1. **bcrypt, e não argon2.** Não é preferência: o legado guarda as senhas no Supabase
   Auth (GoTrue), que usa bcrypt. Escolher bcrypt aqui é o que permite importar os
   hashes existentes e migrar sem obrigar todo mundo a redefinir a senha (R-07).
   `PasswordHasher.verify` aceita os prefixos `$2a$`/`$2b$`/`$2y$` que aparecem no
   export, e `needs_rehash` sinaliza quando o custo do hash antigo ficou abaixo do
   nosso — o serviço de login regrava a senha no formato atual nesse momento. Assim o
   sistema funciona nos dois cenários de AMB-013, com ou sem hashes exportáveis.

2. **Refresh token opaco, guardado como digest.** O access token é curto e stateless;
   o refresh é um segredo aleatório cujo SHA-256 vai para o banco. Vazamento de dump
   não permite renovar sessão, e a rotação a cada uso detecta reúso de token roubado.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import UUID, uuid4

import bcrypt
import jwt

from app.core.config import Settings

# bcrypt ignora tudo além de 72 bytes. Truncar em silêncio faria duas senhas
# diferentes virarem a mesma credencial, então rejeitamos explicitamente.
MAX_PASSWORD_BYTES = 72

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    """Token ausente, malformado, expirado ou com assinatura inválida."""


class PasswordTooLongError(ValueError):
    def __init__(self) -> None:
        super().__init__(f"Senha excede {MAX_PASSWORD_BYTES} bytes suportados pelo bcrypt")


class PasswordHasher:
    def __init__(self, rounds: int) -> None:
        self._rounds = rounds

    def hash(self, plain: str) -> str:
        encoded = plain.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            raise PasswordTooLongError
        return bcrypt.hashpw(encoded, bcrypt.gensalt(self._rounds)).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        encoded = plain.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            return False
        try:
            return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
        except (ValueError, TypeError):
            # Hash corrompido ou de algoritmo desconhecido: falha como senha errada,
            # sem vazar a diferença para quem está tentando entrar.
            return False

    def dummy_verify(self) -> None:
        """Queima o mesmo tempo de um `verify` real.

        Sem isto, "e-mail não existe" responde em microssegundos e "senha errada"
        em centenas de milissegundos — diferença suficiente para enumerar quem tem
        conta no sistema só cronometrando o login.
        """
        bcrypt.checkpw(b"__no_such_user__", _dummy_hash(self._rounds).encode("utf-8"))

    def needs_rehash(self, hashed: str) -> bool:
        """True quando o hash veio com custo menor que o nosso (típico do export
        Supabase, que usa cost 10) e deve ser regravado no próximo login válido."""
        cost = _bcrypt_cost(hashed)
        return cost is None or cost < self._rounds


@lru_cache(maxsize=8)
def _dummy_hash(rounds: int) -> str:
    return bcrypt.hashpw(b"__no_such_user__", bcrypt.gensalt(rounds)).decode("utf-8")


def _bcrypt_cost(hashed: str) -> int | None:
    # Formato: $2b$12$<22 chars de salt><31 chars de digest>
    parts = hashed.split("$")
    if len(parts) < 4 or not parts[1].startswith("2"):
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


# Hierarquia de papéis, do mais poderoso ao menos (BR-MIGRAR-014). Serve a **uma** coisa:
# decidir para quais papéis alguém pode trocar o contexto ativo. Trocar sempre desce.
PODER_DO_PAPEL = {"admin": 3, "rh": 2, "gestor": 1, "colaborador": 0}


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    tenant_id: UUID
    role: str
    flags: frozenset[str]
    expires_at: datetime
    # Papel ativo (BR-MIGRAR-016): o contexto que a pessoa escolheu enxergar. Nunca
    # amplia autorização — quem manda nisso é `role`, o papel persistido.
    active_role: str = ""

    @property
    def contexto_ativo(self) -> str:
        return self.active_role or self.role


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """O `plain` só existe em memória: vai para o cliente e nunca é persistido."""

    plain: str
    digest: str
    expires_at: datetime


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)

    def create_access_token(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
        flags: frozenset[str],
        active_role: str | None = None,
    ) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + self._access_ttl
        payload = {
            "sub": str(user_id),
            "tid": str(tenant_id),
            "role": role,
            "arole": active_role or role,
            "flags": sorted(flags),
            "typ": ACCESS_TOKEN_TYPE,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm), expires_at

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        if payload.get("typ") != ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("Tipo de token inesperado")

        try:
            return AccessClaims(
                user_id=UUID(payload["sub"]),
                tenant_id=UUID(payload["tid"]),
                role=payload["role"],
                flags=frozenset(payload.get("flags", [])),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
                # Token emitido antes desta versão não tem `arole`; cair no papel
                # persistido é o comportamento seguro.
                active_role=payload.get("arole") or payload["role"],
            )
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError("Claims ausentes ou inválidas") from exc

    def create_refresh_token(self) -> RefreshToken:
        plain = secrets.token_urlsafe(48)
        return RefreshToken(
            plain=plain,
            digest=hash_refresh_token(plain),
            expires_at=datetime.now(UTC) + self._refresh_ttl,
        )


def hash_refresh_token(plain: str) -> str:
    """SHA-256 basta: o token já é aleatório de alta entropia, não uma senha humana."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def pode_assumir(papel_persistido: str, papel_ativo: str) -> bool:
    """Trocar de contexto ativo só desce na hierarquia (BR-MIGRAR-016 / PAR-05).

    Um admin pode olhar o sistema como gestor para ver o que a equipe vê; um gestor
    não pode se declarar admin. É por isso que a troca não é autorização: ela nunca
    concede nada, só restringe o que a pessoa enxerga.
    """
    if papel_ativo not in PODER_DO_PAPEL or papel_persistido not in PODER_DO_PAPEL:
        return False
    return PODER_DO_PAPEL[papel_ativo] <= PODER_DO_PAPEL[papel_persistido]


def generate_public_token() -> str:
    """Token de avaliação de cliente enviado por link (BR-MIGRAR-019)."""
    return secrets.token_urlsafe(32)
