"""Comandos administrativos do contexto `identity`.

Completa os comandos que o `target_domain_model.md` prevê para os aggregates `Profile`
e `TeamScope` e que a fundação tinha deixado de fora — ela cobria só a fatia de sessão.

O comando que carrega mais peso aqui é `soft_delete`: BR-MIGRAR-018 diz "histórico
preservado, acesso revogado", e as duas metades têm mecanismos diferentes. Preservar é
não apagar linha (só mudar `status`); revogar é derrubar as sessões **agora**, e não
esperar o access token expirar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.contexts.engagement.service import AuditService
from app.contexts.identity.models import (
    CAPABILITY_FLAGS,
    ROLES,
    CoordinatorMember,
    Department,
    Profile,
    TeamRequest,
    User,
)
from app.contexts.identity.repository import (
    AuthRepository,
    CoordinatorMemberRepository,
    DepartmentRepository,
    ProfileDepartmentRepository,
    ProfileRepository,
    TeamRequestRepository,
    UserRepository,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import PasswordHasher
from app.core.tenancy import TenantContext

# Transições confirmadas de `team_requests` (AMB-004). Cancelamento e expiração
# apareciam nas telas do legado mas ninguém achou o gatilho: modelar seria inventar.
TRANSICOES_TEAM_REQUEST: dict[str, frozenset[str]] = {
    "pending": frozenset({"approved", "rejected"}),
    "approved": frozenset(),
    "rejected": frozenset(),
}


class ProfileService:
    """Ciclo de vida das pessoas dentro do tenant."""

    def __init__(
        self,
        profiles: ProfileRepository,
        users: UserRepository,
        auth: AuthRepository,
        hasher: PasswordHasher,
        departments: ProfileDepartmentRepository,
        audit: AuditService | None = None,
    ) -> None:
        self._profiles = profiles
        self._users = users
        self._auth = auth
        self._hasher = hasher
        self._profile_departments = departments
        self._audit = audit

    async def register(
        self,
        tenant: TenantContext,
        *,
        email: str,
        senha: str,
        full_name: str,
        role: str,
        job_title: str | None = None,
        department_id: UUID | None = None,
        manager_id: UUID | None = None,
    ) -> Profile:
        """Cria usuário e perfil juntos — um sem o outro não entra no sistema.

        O login exige os dois (papel e capacidades vivem no `Profile`), então criar
        só o `User` produziria uma conta que autentica e é recusada em seguida. Os
        dois nascem na mesma transação, com o mesmo id (invariante do banco).
        """
        _exige_papel(role)
        if await self._auth.get_user_by_email(tenant.tenant_id, email) is not None:
            raise ConflictError("Já existe usuário com este e-mail", details={"email": email})

        user = User(
            id=uuid4(),
            tenant_id=tenant.tenant_id,
            email=email,
            password_hash=self._hasher.hash(senha),
            status="active",
        )
        self._users.add_user(user)
        # Flush explícito: `profiles.user_id` referencia `users.id`, e o perfil é
        # inserido logo abaixo. Deixar os dois pendentes faz o INSERT do perfil chegar
        # antes em um autoflush disparado por qualquer consulta no meio — que foi
        # exatamente o que aconteceu quando a auditoria entrou na jogada.
        await self._users.flush()

        perfil = Profile.for_user(
            user,
            full_name=full_name,
            role=role,
            job_title=job_title,
            department_id=department_id,
            manager_id=manager_id,
            status="active",
        )
        self._profiles.add(perfil)

        await self._registrar(tenant, "user.registered", perfil.id, {"role": role})
        return perfil

    async def update_profile(
        self,
        tenant: TenantContext,
        profile_id: UUID,
        *,
        full_name: str | None = None,
        job_title: str | None = None,
        whatsapp: str | None = None,
        department_id: UUID | None = None,
    ) -> Profile:
        perfil = await self._exige_perfil(profile_id)
        if full_name is not None:
            perfil.full_name = full_name
        if job_title is not None:
            perfil.job_title = job_title
        if whatsapp is not None:
            perfil.whatsapp = whatsapp
        if department_id is not None:
            perfil.department_id = department_id
        return perfil

    async def change_role(
        self, tenant: TenantContext, profile_id: UUID, *, role: str
    ) -> Profile:
        """Muda o papel e audita — é a mudança de poder mais óbvia do sistema."""
        _exige_papel(role)
        perfil = await self._exige_perfil(profile_id)
        if perfil.role == role:
            return perfil

        anterior = perfil.role
        perfil.role = role
        await self._registrar(
            tenant, "profile.role_changed", perfil.id, {"de": anterior, "para": role}
        )
        return perfil

    async def set_flags(
        self, tenant: TenantContext, profile_id: UUID, *, flags: dict[str, bool]
    ) -> Profile:
        """Concede ou revoga capacidades (BR-MIGRAR-013/015).

        Só as chaves enviadas mudam: um PATCH que omite uma flag não a desliga por
        acidente. Chave desconhecida é erro, não silêncio — flag com nome errado
        "aplicada" com sucesso é a maneira mais rápida de alguém achar que concedeu
        um acesso que não concedeu.
        """
        desconhecidas = sorted(set(flags) - set(CAPABILITY_FLAGS))
        if desconhecidas:
            raise ValidationError(
                "Capacidade desconhecida",
                details={"flags": desconhecidas, "catalogo": list(CAPABILITY_FLAGS)},
            )

        perfil = await self._exige_perfil(profile_id)
        for nome, valor in flags.items():
            setattr(perfil, nome, valor)

        await self._registrar(tenant, "profile.flags_changed", perfil.id, dict(flags))
        return perfil

    async def set_coordinator(
        self, tenant: TenantContext, profile_id: UUID, *, is_coordinator: bool
    ) -> Profile:
        """Coordenação é atributo, não papel (BR-MIGRAR-015) — foi aqui que o legado
        se enrolou, tratando "coordenador" como papel e duplicando telas."""
        perfil = await self._exige_perfil(profile_id)
        perfil.is_coordinator = is_coordinator
        return perfil

    async def assign_manager(
        self, tenant: TenantContext, profile_id: UUID, *, manager_id: UUID | None
    ) -> Profile:
        """Define o gestor, recusando ciclo na hierarquia.

        Sem esta checagem, A→B→A faria a resolução de equipe girar para sempre — e o
        legado não tinha nada impedindo.
        """
        perfil = await self._exige_perfil(profile_id)
        if manager_id is not None:
            if manager_id == profile_id:
                raise ValidationError("Uma pessoa não pode ser gestora de si mesma")
            if await self._cria_ciclo(profile_id, manager_id):
                raise ValidationError(
                    "Este vínculo criaria um ciclo na hierarquia",
                    details={"profile_id": str(profile_id), "manager_id": str(manager_id)},
                )
        perfil.manager_id = manager_id
        return perfil

    async def _cria_ciclo(self, profile_id: UUID, manager_id: UUID) -> bool:
        """Sobe a cadeia a partir do gestor pretendido procurando a própria pessoa."""
        visitados: set[UUID] = set()
        atual: UUID | None = manager_id
        while atual is not None and atual not in visitados:
            if atual == profile_id:
                return True
            visitados.add(atual)
            acima = await self._profiles.get(atual)
            atual = acima.manager_id if acima else None
        return False

    async def set_departments(
        self, tenant: TenantContext, profile_id: UUID, *, department_ids: list[UUID]
    ) -> None:
        """Substitui os departamentos adicionais do perfil (N:N)."""
        await self._exige_perfil(profile_id)
        await self._profile_departments.substituir(profile_id, department_ids)

    async def soft_delete(self, tenant: TenantContext, profile_id: UUID) -> Profile:
        """Remoção com histórico preservado e acesso revogado (BR-MIGRAR-018 / PAR-08).

        As duas metades da regra têm mecanismos diferentes, e as duas importam:

        - **Preservar**: nada é apagado. `status='deleted'` mantém as FKs válidas, então
          feedbacks enviados e recebidos continuam consultáveis, como o cenário de
          PAR-08 exige.
        - **Revogar**: as sessões caem **agora**, em transação própria. Só marcar o
          status já bloquearia a próxima requisição (`assert_session_active`), mas
          deixaria o refresh token vivo na mão de quem saiu.

        Quem se remove sozinho, ou remove a última conta admin, é recusado: o primeiro
        é acidente, o segundo tranca todo mundo para fora do sistema.
        """
        if profile_id == tenant.user_id:
            raise ValidationError("Não é possível remover a própria conta")

        perfil = await self._exige_perfil(profile_id)
        if perfil.status == "deleted":
            return perfil

        if perfil.role == "admin" and await self._profiles.contar_admins_ativos() <= 1:
            raise ConflictError("Este é o último administrador ativo do tenant")

        perfil.status = "deleted"
        usuario = await self._auth.get_user(tenant.tenant_id, perfil.user_id)
        if usuario is not None:
            usuario.status = "deleted"

        await self._auth.revoke_all_for_user(tenant.tenant_id, perfil.user_id)
        await self._registrar(tenant, "profile.soft_deleted", perfil.id, None)
        return perfil

    async def reactivate(self, tenant: TenantContext, profile_id: UUID) -> Profile:
        perfil = await self._exige_perfil(profile_id)
        perfil.status = "active"
        usuario = await self._auth.get_user(tenant.tenant_id, perfil.user_id)
        if usuario is not None:
            usuario.status = "active"
        await self._registrar(tenant, "profile.reactivated", perfil.id, None)
        return perfil

    async def reset_password(
        self, tenant: TenantContext, profile_id: UUID, *, nova_senha: str
    ) -> None:
        """Redefine a senha e derruba as sessões abertas.

        Redefinir senha sem revogar sessão não resolve o caso que motiva a redefinição:
        se a conta estava comprometida, o invasor continua com o token dele.
        """
        perfil = await self._exige_perfil(profile_id)
        usuario = await self._auth.get_user(tenant.tenant_id, perfil.user_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")

        usuario.password_hash = self._hasher.hash(nova_senha)
        await self._auth.revoke_all_for_user(tenant.tenant_id, perfil.user_id)
        await self._registrar(tenant, "user.password_reset", perfil.id, None)

    async def _exige_perfil(self, profile_id: UUID) -> Profile:
        perfil = await self._profiles.get(profile_id)
        if perfil is None:
            raise NotFoundError("Perfil não encontrado")
        return perfil

    async def _registrar(
        self, tenant: TenantContext, acao: str, record_id: UUID, detalhes: dict | None
    ) -> None:
        if self._audit is not None:
            await self._audit.record(
                tenant,
                action=acao,
                table_name="profiles",
                record_id=record_id,
                details=detalhes,
            )


class DepartmentService:
    def __init__(self, departments: DepartmentRepository) -> None:
        self._departments = departments

    async def create(self, *, name: str) -> Department:
        if await self._departments.get_por_nome(name) is not None:
            raise ConflictError("Já existe departamento com este nome", details={"name": name})
        return self._departments.add(Department(name=name))

    async def rename(self, department_id: UUID, *, name: str) -> Department:
        departamento = await self._departments.get(department_id)
        if departamento is None:
            raise NotFoundError("Departamento não encontrado")
        existente = await self._departments.get_por_nome(name)
        if existente is not None and existente.id != department_id:
            raise ConflictError("Já existe departamento com este nome")
        departamento.name = name
        return departamento


class CoordinatorService:
    """Vínculos de coordenação — a outra metade do escopo de equipe (BR-MIGRAR-017)."""

    def __init__(
        self,
        coordinators: CoordinatorMemberRepository,
        profiles: ProfileRepository,
        audit: AuditService | None = None,
    ) -> None:
        self._coordinators = coordinators
        self._profiles = profiles
        self._audit = audit

    async def add_member(
        self, tenant: TenantContext, *, coordinator_id: UUID, member_id: UUID
    ) -> CoordinatorMember:
        if coordinator_id == member_id:
            raise ValidationError("Ninguém coordena a si mesmo")

        coordenador = await self._profiles.get(coordinator_id)
        membro = await self._profiles.get(member_id)
        if coordenador is None or membro is None:
            raise NotFoundError("Perfil não encontrado")
        if not coordenador.is_coordinator:
            # Vínculo com quem não coordena não amplia escopo nenhum — só suja o banco
            # e engana quem lê a tela de equipe.
            raise ConflictError(
                "O perfil indicado não está marcado como coordenador",
                details={"coordinator_id": str(coordinator_id)},
            )

        existente = await self._coordinators.get_vinculo(coordinator_id, member_id)
        if existente is not None:
            return existente

        return self._coordinators.add(
            CoordinatorMember(coordinator_id=coordinator_id, member_id=member_id)
        )

    async def remove_member(
        self, tenant: TenantContext, *, coordinator_id: UUID, member_id: UUID
    ) -> None:
        """Remoção de membro audita e tenta notificar (BR-MIGRAR-026)."""
        vinculo = await self._coordinators.get_vinculo(coordinator_id, member_id)
        if vinculo is None:
            raise NotFoundError("Vínculo não encontrado")

        await self._coordinators.remove(vinculo)
        if self._audit is not None:
            await self._audit.record(
                tenant,
                action="team.member_removed",
                table_name="coordinator_members",
                record_id=vinculo.id,
                details={"coordinator_id": str(coordinator_id), "member_id": str(member_id)},
                notificar=[member_id, coordinator_id],
            )


class TeamRequestService:
    """Pedidos de inclusão em equipe.

    Só aprovação e rejeição existem (AMB-004): cancelamento e expiração apareciam nas
    telas do legado, mas ninguém achou o gatilho, e o Curator decidiu não migrar o que
    não foi confirmado. Qualquer outra transição recusa com 409, em vez de o modelo
    inventar um estado.
    """

    def __init__(
        self,
        requests: TeamRequestRepository,
        profiles: ProfileRepository,
        audit: AuditService | None = None,
    ) -> None:
        self._requests = requests
        self._profiles = profiles
        self._audit = audit

    async def create(
        self, tenant: TenantContext, *, requested_member_id: UUID
    ) -> TeamRequest:
        if requested_member_id == tenant.user_id:
            raise ValidationError("Não é possível pedir a si mesmo")
        if await self._profiles.get(requested_member_id) is None:
            raise NotFoundError("Perfil não encontrado")

        pendente = await self._requests.get_pendente(tenant.user_id, requested_member_id)
        if pendente is not None:
            return pendente

        return self._requests.add(
            TeamRequest(requester_id=tenant.user_id, requested_member_id=requested_member_id)
        )

    async def approve(self, tenant: TenantContext, request_id: UUID) -> TeamRequest:
        pedido = await self._transicionar(request_id, "approved")
        pedido.approved_by = tenant.user_id

        # Aprovar é o que efetivamente move a pessoa para a equipe de quem pediu.
        membro = await self._profiles.get(pedido.requested_member_id)
        if membro is not None:
            membro.manager_id = pedido.requester_id

        if self._audit is not None:
            await self._audit.record(
                tenant,
                action="team.request_approved",
                table_name="team_requests",
                record_id=pedido.id,
                details={"member_id": str(pedido.requested_member_id)},
                notificar=[pedido.requester_id, pedido.requested_member_id],
            )
        return pedido

    async def reject(
        self, tenant: TenantContext, request_id: UUID, *, motivo: str | None = None
    ) -> TeamRequest:
        pedido = await self._transicionar(request_id, "rejected")
        pedido.rejection_reason = motivo
        if self._audit is not None:
            await self._audit.record(
                tenant,
                action="team.request_rejected",
                table_name="team_requests",
                record_id=pedido.id,
                details={"motivo": motivo},
                notificar=[pedido.requester_id],
            )
        return pedido

    async def _transicionar(self, request_id: UUID, destino: str) -> TeamRequest:
        pedido = await self._requests.get(request_id)
        if pedido is None:
            raise NotFoundError("Pedido não encontrado")

        permitidas = TRANSICOES_TEAM_REQUEST.get(pedido.status, frozenset())
        if destino not in permitidas:
            raise ConflictError(
                "Transição de pedido não permitida",
                details={
                    "de": pedido.status,
                    "para": destino,
                    "permitidas": sorted(permitidas),
                },
            )

        pedido.status = destino
        pedido.resolved_at = datetime.now(UTC)
        return pedido


def _exige_papel(role: str) -> None:
    if role not in ROLES:
        raise ValidationError("Papel inválido", details={"papeis": list(ROLES)})
