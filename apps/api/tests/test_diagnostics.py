"""Diagnóstico de permissões — a tela que evita o ciclo sair errado.

Cada teste corresponde a uma categoria da tela. O que está sob teste é a comparação
entre a matriz e a realidade: quem está ativo, o que o ciclo gerou, quem sobrou de fora.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.contexts.feedback.diagnostics import DiagnosticsService
from app.contexts.feedback.models import FeedbackCycle, FeedbackPermission, FeedbackRequest

HOJE = date(2026, 9, 15)


class _Perfil:
    def __init__(self, nome: str) -> None:
        self.id = uuid4()
        self.full_name = nome


class FakePermissionRepository:
    def __init__(self, regras: list[FeedbackPermission]) -> None:
        self.regras = regras

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[FeedbackPermission]:
        return list(self.regras)


class FakeCycleRepository:
    def __init__(self, ciclo: FeedbackCycle | None) -> None:
        self.ciclo = ciclo

    async def list_by_status(self, *status: str) -> list[FeedbackCycle]:
        return [self.ciclo] if self.ciclo else []


class FakeRequestRepository:
    def __init__(self, pares: list[tuple[UUID, UUID]]) -> None:
        self.pares = pares

    async def list_do_ciclo(self, cycle_id: UUID) -> list[Any]:
        return [
            FeedbackRequest(
                id=uuid4(),
                cycle_id=cycle_id,
                form_id=uuid4(),
                giver_id=giver,
                receiver_id=receiver,
                status="pending",
            )
            for giver, receiver in self.pares
        ]


class FakeProfileRepository:
    def __init__(self, perfis: list[_Perfil]) -> None:
        self.perfis = perfis

    async def list_active(self, limit: int = 500, offset: int = 0) -> list[_Perfil]:
        return list(self.perfis)


def _permissao(
    reviewer: UUID, reviewee: UUID, *, tipo: str = "peer_to_peer", ativa: bool = True
) -> FeedbackPermission:
    return FeedbackPermission(
        id=uuid4(),
        reviewer_id=reviewer,
        reviewee_id=reviewee,
        permission_type=tipo,
        cycle_id=None,
        active=ativa,
    )


def _ciclo() -> FeedbackCycle:
    return FeedbackCycle(
        id=uuid4(),
        name="Ciclo de setembro",
        form_id=uuid4(),
        status="open",
        start_date=HOJE - timedelta(days=15),
        end_date=HOJE + timedelta(days=6),
    )


def _service(
    regras: list[FeedbackPermission],
    perfis: list[_Perfil],
    *,
    ciclo: FeedbackCycle | None = None,
    pares_gerados: list[tuple[UUID, UUID]] | None = None,
) -> DiagnosticsService:
    return DiagnosticsService(  # type: ignore[arg-type]
        permissions=FakePermissionRepository(regras),
        cycles=FakeCycleRepository(ciclo),
        requests=FakeRequestRepository(pares_gerados or []),
        profiles=FakeProfileRepository(perfis),
    )


async def test_permissao_sem_request_no_ciclo_ativo() -> None:
    """A categoria mais grave: a pessoa não vê o feedback e não recebe lembrete."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")
    ciclo = _ciclo()
    regras = [_permissao(ana.id, bruno.id), _permissao(bruno.id, ana.id)]

    # Só um dos pares virou request.
    d = await _service(
        regras, [ana, bruno], ciclo=ciclo, pares_gerados=[(ana.id, bruno.id)]
    ).gerar(HOJE)

    assert len(d.sem_request) == 1
    assert d.sem_request[0].reviewer_nome == "Bruno"
    assert d.sem_request[0].reviewee_nome == "Ana"


async def test_sem_ciclo_aberto_nao_acusa_request_faltando() -> None:
    """Sem ciclo aberto não existe request a faltar — acusar seria alarme falso."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")

    d = await _service([_permissao(ana.id, bruno.id)], [ana, bruno]).gerar(HOJE)

    assert d.sem_request == []
    assert d.ciclo_ativo is None
    assert d.dias_para_fechar is None


async def test_par_reciproco_faltando() -> None:
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")

    d = await _service([_permissao(ana.id, bruno.id)], [ana, bruno]).gerar(HOJE)

    assert len(d.par_reverso_faltando) == 1
    assert d.par_reverso_faltando[0].reviewer_nome == "Ana"


async def test_par_completo_nao_e_acusado() -> None:
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")
    regras = [_permissao(ana.id, bruno.id), _permissao(bruno.id, ana.id)]

    d = await _service(regras, [ana, bruno]).gerar(HOJE)

    assert d.par_reverso_faltando == []


async def test_tipo_nao_reciproco_nao_exige_reverso() -> None:
    """Só `peer_to_peer` tem recíproca; cobrar dos outros seria ruído."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")

    d = await _service([_permissao(ana.id, bruno.id, tipo="manager")], [ana, bruno]).gerar(HOJE)

    assert d.par_reverso_faltando == []


async def test_permissao_apontando_para_quem_saiu() -> None:
    """Não dá erro, mas gera pedido que ninguém responde e polui o relatório."""
    ana = _Perfil("Ana")
    desligado = uuid4()

    d = await _service([_permissao(ana.id, desligado)], [ana]).gerar(HOJE)

    assert len(d.com_usuario_inativo) == 1
    assert d.com_usuario_inativo[0].reviewee_nome == "(removido)"


async def test_usuario_sem_cobertura() -> None:
    """Não avalia e não é avaliado: sai do ciclo sem ninguém notar."""
    ana, bruno, sozinho = _Perfil("Ana"), _Perfil("Bruno"), _Perfil("Sozinho")
    regras = [_permissao(ana.id, bruno.id), _permissao(bruno.id, ana.id)]

    d = await _service(regras, [ana, bruno, sozinho]).gerar(HOJE)

    assert [p.nome for p in d.sem_cobertura] == ["Sozinho"]


async def test_permissao_inativa_nao_conta_para_cobertura() -> None:
    """Regra desligada não cobre ninguém — quem só aparece nela está fora."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")

    d = await _service([_permissao(ana.id, bruno.id, ativa=False)], [ana, bruno]).gerar(HOJE)

    assert {p.nome for p in d.sem_cobertura} == {"Ana", "Bruno"}
    assert d.permissoes_ativas == 0


async def test_pontos_de_atencao_soma_so_o_que_pede_acao() -> None:
    """Desequilíbrio de carga fica fora: é calibragem, não defeito."""
    ana, bruno, sozinho = _Perfil("Ana"), _Perfil("Bruno"), _Perfil("Sozinho")
    regras = [_permissao(ana.id, bruno.id)]  # sem recíproca

    d = await _service(regras, [ana, bruno, sozinho]).gerar(HOJE)

    # 1 recíproca faltando + 1 sem cobertura. As três pessoas aparecem em
    # "poucas avaliações", e isso não entra na conta.
    assert d.pontos_de_atencao == 2
    assert len(d.poucos_avaliadores) == 3


async def test_carga_inclui_quem_tem_zero() -> None:
    """Ausência é o caso mais grave e some de um dicionário montado só com presentes."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")

    d = await _service([_permissao(ana.id, bruno.id)], [ana, bruno]).gerar(HOJE)

    por_nome = {p.nome: p.quantidade for p in d.poucos_avaliadores}
    assert por_nome == {"Ana": 1, "Bruno": 0}


async def test_previsao_do_proximo_ciclo_conta_pares_unicos() -> None:
    """Dois tipos de permissão para o mesmo par geram um pedido só (BR-MIGRAR-010)."""
    ana, bruno = _Perfil("Ana"), _Perfil("Bruno")
    regras = [
        _permissao(ana.id, bruno.id, tipo="peer_to_peer"),
        _permissao(ana.id, bruno.id, tipo="manager"),
    ]

    d = await _service(regras, [ana, bruno]).gerar(HOJE)

    assert d.requests_a_criar == 1


async def test_dias_para_fechar_usa_o_prazo_estendido() -> None:
    """Estender o período avaliado adia o fechamento — o diagnóstico precisa saber."""
    ana = _Perfil("Ana")
    ciclo = _ciclo()
    ciclo.evaluated_end = ciclo.end_date + timedelta(days=10)

    d = await _service([], [ana], ciclo=ciclo).gerar(HOJE)

    assert d.dias_para_fechar == 16


async def test_desativar_permissoes_com_inativos() -> None:
    """Desativa em vez de apagar: a permissão é histórico de como o ciclo foi montado."""
    ana = _Perfil("Ana")
    boa = _permissao(ana.id, ana.id, tipo="self")
    ruim = _permissao(ana.id, uuid4())
    service = _service([boa, ruim], [ana])

    assert await service.desativar_permissoes_com_inativos() == 1
    assert ruim.active is False
    assert boa.active is True


async def test_desativar_e_idempotente() -> None:
    ana = _Perfil("Ana")
    ruim = _permissao(ana.id, uuid4())
    service = _service([ruim], [ana])

    assert await service.desativar_permissoes_com_inativos() == 1
    assert await service.desativar_permissoes_com_inativos() == 0


@pytest.mark.parametrize("pessoas,esperado", [(0, 0.0), (2, 0.5)])
async def test_media_nao_divide_por_zero(pessoas: int, esperado: float) -> None:
    perfis = [_Perfil(f"P{i}") for i in range(pessoas)]
    regras = [_permissao(perfis[0].id, perfis[1].id)] if pessoas >= 2 else []

    d = await _service(regras, perfis).gerar(HOJE)

    assert d.media_por_avaliador == esperado


def test_dataclasses_do_diagnostico_sao_serializaveis() -> None:
    """Regressão: `vars()` não funciona em dataclass com `slots`.

    A rota convertia os resultados com `vars()`, e o erro ficou escondido enquanto as
    listas estavam vazias — apareceu no primeiro tenant com problema de verdade, que é
    o pior momento possível. `asdict` é o que funciona nos dois casos.
    """
    from dataclasses import asdict

    from app.contexts.feedback.diagnostics import ParDePermissao, PessoaComCarga
    from app.contexts.feedback.schemas import ParDePermissaoOut, PessoaComCargaOut

    par = ParDePermissao(
        permission_id=uuid4(),
        reviewer_id=uuid4(),
        reviewer_nome="Ana",
        reviewee_id=uuid4(),
        reviewee_nome="Bruno",
        permission_type="peer_to_peer",
    )
    pessoa = PessoaComCarga(profile_id=uuid4(), nome="Ana", quantidade=0)

    assert ParDePermissaoOut(**asdict(par)).reviewer_nome == "Ana"
    assert PessoaComCargaOut(**asdict(pessoa)).quantidade == 0

    with pytest.raises(TypeError):
        vars(par)  # é justamente o que a rota fazia antes
