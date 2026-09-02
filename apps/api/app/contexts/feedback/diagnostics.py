"""Diagnóstico de permissões — o que vai dar errado no próximo ciclo.

Esta é a tela mais valiosa do legado e a que menos parece: ela responde "o próximo
ciclo vai sair certo?" **antes** de o ciclo abrir. Sem ela, o administrador descobre
que dezenas de pessoas ficaram sem pedido depois de abrir — e aí já não dá para
consertar sem reabrir a conversa com o time.

Cinco categorias, todas com a mesma lógica: comparar a matriz de permissões com a
realidade (quem está ativo, o que o ciclo gerou) e apontar a diferença.

O cálculo acontece em Python, sobre listas já carregadas, e não em SQL. É deliberado:
um escritório tem ordem de centenas de permissões, o custo é irrelevante, e as regras
aqui são de leitura difícil em SQL — `peer_to_peer` sem recíproca vira um NOT EXISTS
correlacionado que ninguém revisa com confiança seis meses depois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

from app.contexts.feedback.models import FeedbackCycle, FeedbackPermission
from app.contexts.feedback.repository import (
    CycleRepository,
    PermissionRepository,
    RequestRepository,
)
from app.contexts.identity.repository import ProfileRepository

# Abaixo disso, a pessoa avalia (ou é avaliada por) tão pouca gente que o resultado
# dela no ciclo não sustenta conclusão nenhuma. O número vem do legado.
POUCAS_AVALIACOES = 2


@dataclass(frozen=True, slots=True)
class ParDePermissao:
    permission_id: UUID
    reviewer_id: UUID
    reviewer_nome: str
    reviewee_id: UUID
    reviewee_nome: str
    permission_type: str


@dataclass(frozen=True, slots=True)
class PessoaComCarga:
    profile_id: UUID
    nome: str
    quantidade: int


@dataclass(slots=True)
class Diagnostico:
    """O retrato completo. `pontos_de_atencao` é a soma do que pede ação."""

    ciclo_ativo: FeedbackCycle | None
    dias_para_fechar: int | None
    permissoes_ativas: int
    usuarios_ativos: int

    sem_request: list[ParDePermissao] = field(default_factory=list)
    par_reverso_faltando: list[ParDePermissao] = field(default_factory=list)
    sem_cobertura: list[PessoaComCarga] = field(default_factory=list)
    com_usuario_inativo: list[ParDePermissao] = field(default_factory=list)
    poucos_avaliadores: list[PessoaComCarga] = field(default_factory=list)
    poucos_avaliados: list[PessoaComCarga] = field(default_factory=list)

    media_por_avaliador: float = 0.0
    media_por_avaliado: float = 0.0
    requests_a_criar: int = 0

    @property
    def pontos_de_atencao(self) -> int:
        """Só o que pede ação entra na conta.

        Desequilíbrio de carga fica de fora: é informação para calibrar a matriz, não
        um defeito a corrigir. Contá-lo inflaria o número e faria o alerta perder o
        sentido — que é justamente o que acontece quando tudo é urgente.
        """
        return (
            len(self.sem_request)
            + len(self.par_reverso_faltando)
            + len(self.sem_cobertura)
            + len(self.com_usuario_inativo)
        )


class DiagnosticsService:
    def __init__(
        self,
        permissions: PermissionRepository,
        cycles: CycleRepository,
        requests: RequestRepository,
        profiles: ProfileRepository,
    ) -> None:
        self._permissions = permissions
        self._cycles = cycles
        self._requests = requests
        self._profiles = profiles

    async def gerar(self, hoje: date | None = None) -> Diagnostico:
        hoje = hoje or datetime.now(UTC).date()

        abertos = await self._cycles.list_by_status("open")
        ciclo = abertos[0] if abertos else None

        perfis = {p.id: p for p in await self._profiles.list_active()}
        todas = await self._permissions.list_all()
        ativas = [p for p in todas if p.active]

        # Permissão apontando para quem saiu: não dá erro, mas gera pedido que ninguém
        # responde e polui todo relatório do ciclo.
        com_inativo = [
            p for p in ativas if p.reviewer_id not in perfis or p.reviewee_id not in perfis
        ]
        validas = [p for p in ativas if p.reviewer_id in perfis and p.reviewee_id in perfis]

        pares_existentes = {(p.reviewer_id, p.reviewee_id, p.permission_type) for p in ativas}
        reverso_faltando = [
            p
            for p in validas
            if p.permission_type == "peer_to_peer"
            and (p.reviewee_id, p.reviewer_id, p.permission_type) not in pares_existentes
        ]

        sem_request: list[FeedbackPermission] = []
        if ciclo is not None:
            gerados = {
                (r.giver_id, r.receiver_id)
                for r in await self._requests.list_do_ciclo(ciclo.id)
            }
            sem_request = [p for p in validas if (p.reviewer_id, p.reviewee_id) not in gerados]

        # Quem não aparece em lado nenhum está fora do processo: não avalia e não é
        # avaliado, então some do ciclo sem ninguém notar.
        envolvidos = {p.reviewer_id for p in validas} | {p.reviewee_id for p in validas}
        sem_cobertura = [
            PessoaComCarga(profile_id=pid, nome=perfil.full_name, quantidade=0)
            for pid, perfil in perfis.items()
            if pid not in envolvidos
        ]

        como_avaliador: dict[UUID, int] = {}
        como_avaliado: dict[UUID, int] = {}
        for permissao in validas:
            como_avaliador[permissao.reviewer_id] = como_avaliador.get(permissao.reviewer_id, 0) + 1
            como_avaliado[permissao.reviewee_id] = como_avaliado.get(permissao.reviewee_id, 0) + 1

        return Diagnostico(
            ciclo_ativo=ciclo,
            dias_para_fechar=(ciclo.prazo_final - hoje).days if ciclo else None,
            permissoes_ativas=len(ativas),
            usuarios_ativos=len(perfis),
            sem_request=[self._par(p, perfis) for p in sem_request],
            par_reverso_faltando=[self._par(p, perfis) for p in reverso_faltando],
            sem_cobertura=sorted(sem_cobertura, key=lambda p: p.nome),
            com_usuario_inativo=[self._par(p, perfis) for p in com_inativo],
            poucos_avaliadores=self._poucos(como_avaliador, perfis),
            poucos_avaliados=self._poucos(como_avaliado, perfis),
            media_por_avaliador=_media(como_avaliador, len(perfis)),
            media_por_avaliado=_media(como_avaliado, len(perfis)),
            # O que a abertura do próximo ciclo geraria hoje, se nada mudar.
            requests_a_criar=len({(p.reviewer_id, p.reviewee_id) for p in validas}),
        )

    async def desativar_permissoes_com_inativos(self) -> int:
        """Ação em massa: desliga o que aponta para quem saiu.

        Desativa em vez de apagar — a permissão é histórico de como o ciclo passado foi
        montado, e apagá-la reescreveria esse passado.
        """
        perfis = {p.id for p in await self._profiles.list_active()}
        alvo = [
            p
            for p in await self._permissions.list_all()
            if p.active and (p.reviewer_id not in perfis or p.reviewee_id not in perfis)
        ]
        for permissao in alvo:
            permissao.active = False
        return len(alvo)

    @staticmethod
    def _par(permissao: FeedbackPermission, perfis: dict[UUID, object]) -> ParDePermissao:
        def nome(pid: UUID) -> str:
            perfil = perfis.get(pid)
            return getattr(perfil, "full_name", "(removido)")

        return ParDePermissao(
            permission_id=permissao.id,
            reviewer_id=permissao.reviewer_id,
            reviewer_nome=nome(permissao.reviewer_id),
            reviewee_id=permissao.reviewee_id,
            reviewee_nome=nome(permissao.reviewee_id),
            permission_type=permissao.permission_type,
        )

    @staticmethod
    def _poucos(carga: dict[UUID, int], perfis: dict[UUID, object]) -> list[PessoaComCarga]:
        """Inclui quem tem zero: ausência é o caso mais grave, e some de um dicionário
        montado só com quem aparece."""
        return sorted(
            (
                PessoaComCarga(
                    profile_id=pid,
                    nome=getattr(perfil, "full_name", "—"),
                    quantidade=carga.get(pid, 0),
                )
                for pid, perfil in perfis.items()
                if carga.get(pid, 0) <= POUCAS_AVALIACOES
            ),
            key=lambda p: (p.quantidade, p.nome),
        )


def _media(carga: dict[UUID, int], pessoas: int) -> float:
    if not pessoas:
        return 0.0
    return round(sum(carga.values()) / pessoas, 1)
