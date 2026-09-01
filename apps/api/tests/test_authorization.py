"""Guards de autorização (AD-02 / R-04).

A propriedade que interessa é *negar por padrão*: o teste que mais importa não é o do
caminho feliz, é o que prova que a ausência de permissão bloqueia. No legado a flag
nula era lida como permissão concedida — este arquivo existe para que isso não volte.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.di import require_flag, require_role
from app.core.errors import AuthorizationError
from app.core.tenancy import TenantContext


def _contexto(role: str, flags: frozenset[str] = frozenset()) -> TenantContext:
    return TenantContext(tenant_id=uuid4(), user_id=uuid4(), role=role, flags=flags)


def test_papel_permitido_passa() -> None:
    guard = require_role("admin", "rh")
    ctx = _contexto("rh")
    assert guard(ctx) is ctx


def test_papel_nao_listado_e_bloqueado() -> None:
    guard = require_role("admin", "rh")
    with pytest.raises(AuthorizationError):
        guard(_contexto("colaborador"))


def test_flag_ausente_bloqueia() -> None:
    guard = require_flag("can_generate_reports")
    with pytest.raises(AuthorizationError):
        guard(_contexto("gestor"))


def test_flag_presente_passa() -> None:
    guard = require_flag("can_generate_reports")
    ctx = _contexto("gestor", frozenset({"can_generate_reports"}))
    assert guard(ctx) is ctx


def test_admin_nao_tem_passe_livre_em_flag() -> None:
    """Decisão explícita: papel não substitui capacidade.

    Se um admin precisa da capacidade, ela é concedida no perfil dele. Assim existe um
    lugar só para auditar quem pode o quê — que é exatamente o que faltava no legado.
    """
    guard = require_flag("can_view_feedback_answers")
    with pytest.raises(AuthorizationError):
        guard(_contexto("admin"))


def test_require_all_exige_todas_as_flags() -> None:
    guard = require_flag("can_generate_reports", "can_view_team_history")
    with pytest.raises(AuthorizationError):
        guard(_contexto("gestor", frozenset({"can_generate_reports"})))


def test_require_any_aceita_uma_flag() -> None:
    guard = require_flag("can_generate_reports", "can_view_team_history", require_all=False)
    ctx = _contexto("gestor", frozenset({"can_generate_reports"}))
    assert guard(ctx) is ctx


def test_erro_de_autorizacao_diz_o_que_faltou() -> None:
    guard = require_flag("can_generate_reports", "can_view_team_history")
    with pytest.raises(AuthorizationError) as exc:
        guard(_contexto("gestor", frozenset({"can_generate_reports"})))
    assert exc.value.details["missing"] == ["can_view_team_history"]
    assert exc.value.status_code == 403
