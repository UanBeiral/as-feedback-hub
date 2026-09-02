"""Rotas administrativas do contexto `identity`.

Ficam fora do router de `/auth` de propósito: administrar pessoas não é autenticação.
`/auth` é o que a sessão faz consigo mesma (entrar, renovar, sair, trocar de contexto);
aqui é o que o escritório faz com as pessoas — criar, mudar papel, conceder capacidade,
remover. Misturar os dois deixaria `POST /auth/profiles`, que descreve errado quem faz
o quê.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.contexts.engagement.repository import AuditLogRepository, OutboxRepository
from app.contexts.engagement.service import AuditService, OutboxService
from app.contexts.identity.admin_service import (
    CoordinatorService,
    DepartmentService,
    ProfileService,
    TeamRequestService,
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
from app.contexts.identity.schemas import (
    CoordinatorIn,
    CoordinatorMemberIn,
    DepartmentIn,
    DepartmentOut,
    DepartmentsIn,
    FlagsIn,
    ManagerIn,
    PasswordResetIn,
    ProfileSummary,
    ProfileUpdateIn,
    RegisterUserIn,
    RoleIn,
    TeamRequestIn,
    TeamRequestOut,
    TeamRequestRejectIn,
)
from app.core.di import PasswordHasherDep, SessionDep, TenantDep, require_role
from app.core.tenancy import TenantContext

router = APIRouter(tags=["identity-admin"])


# ------------------------------------------------------- pessoas

def get_profile_service(
    session: SessionDep, tenant: TenantDep, hasher: PasswordHasherDep
) -> ProfileService:
    outbox = OutboxService(OutboxRepository(session, tenant))
    return ProfileService(
        profiles=ProfileRepository(session, tenant),
        users=UserRepository(session, tenant),
        auth=AuthRepository(session),
        hasher=hasher,
        departments=ProfileDepartmentRepository(session, tenant),
        audit=AuditService(AuditLogRepository(session, tenant), outbox),
    )


def get_team_request_service(session: SessionDep, tenant: TenantDep) -> TeamRequestService:
    outbox = OutboxService(OutboxRepository(session, tenant))
    return TeamRequestService(
        requests=TeamRequestRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
        audit=AuditService(AuditLogRepository(session, tenant), outbox),
    )


def get_coordinator_service(session: SessionDep, tenant: TenantDep) -> CoordinatorService:
    outbox = OutboxService(OutboxRepository(session, tenant))
    return CoordinatorService(
        coordinators=CoordinatorMemberRepository(session, tenant),
        profiles=ProfileRepository(session, tenant),
        audit=AuditService(AuditLogRepository(session, tenant), outbox),
    )


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
TeamRequestServiceDep = Annotated[TeamRequestService, Depends(get_team_request_service)]
CoordinatorServiceDep = Annotated[CoordinatorService, Depends(get_coordinator_service)]

AdminDep = Annotated[TenantContext, Depends(require_role("admin", "rh"))]
GestaoDep = Annotated[TenantContext, Depends(require_role("admin", "rh", "gestor"))]


@router.get("/profiles", response_model=list[ProfileSummary])
async def list_profiles(tenant: AdminDep, session: SessionDep) -> list[ProfileSummary]:
    repo = ProfileRepository(session, tenant)
    return [ProfileSummary.model_validate(p) for p in await repo.list_active()]


@router.post("/profiles", response_model=ProfileSummary, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterUserIn,
    tenant: AdminDep,
    session: SessionDep,
    service: ProfileServiceDep,
) -> ProfileSummary:
    """Cria credencial e perfil juntos: um sem o outro não entra no sistema."""
    perfil = await service.register(
        tenant,
        email=payload.email,
        senha=payload.senha,
        full_name=payload.full_name,
        role=payload.role,
        job_title=payload.job_title,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
    )
    await session.flush()
    await session.refresh(perfil)
    return ProfileSummary.model_validate(perfil)


@router.patch("/profiles/{profile_id}", response_model=ProfileSummary)
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdateIn,
    tenant: AdminDep,
    service: ProfileServiceDep,
) -> ProfileSummary:
    perfil = await service.update_profile(
        tenant,
        profile_id,
        full_name=payload.full_name,
        job_title=payload.job_title,
        whatsapp=payload.whatsapp,
        department_id=payload.department_id,
    )
    return ProfileSummary.model_validate(perfil)


@router.put("/profiles/{profile_id}/role", response_model=ProfileSummary)
async def change_role(
    profile_id: UUID, payload: RoleIn, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    return ProfileSummary.model_validate(
        await service.change_role(tenant, profile_id, role=payload.role)
    )


@router.patch("/profiles/{profile_id}/flags", response_model=ProfileSummary)
async def set_flags(
    profile_id: UUID, payload: FlagsIn, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    """Capacidades individuais (BR-MIGRAR-013/015). Chave desconhecida é 422."""
    return ProfileSummary.model_validate(
        await service.set_flags(tenant, profile_id, flags=payload.flags)
    )


@router.put("/profiles/{profile_id}/coordinator", response_model=ProfileSummary)
async def set_coordinator(
    profile_id: UUID, payload: CoordinatorIn, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    return ProfileSummary.model_validate(
        await service.set_coordinator(
            tenant, profile_id, is_coordinator=payload.is_coordinator
        )
    )


@router.put("/profiles/{profile_id}/manager", response_model=ProfileSummary)
async def assign_manager(
    profile_id: UUID, payload: ManagerIn, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    """Recusa ciclo na hierarquia — A→B→A faria a resolução de equipe girar sem fim."""
    return ProfileSummary.model_validate(
        await service.assign_manager(tenant, profile_id, manager_id=payload.manager_id)
    )


@router.put("/profiles/{profile_id}/departments", status_code=status.HTTP_204_NO_CONTENT)
async def set_departments(
    profile_id: UUID, payload: DepartmentsIn, tenant: AdminDep, service: ProfileServiceDep
) -> None:
    await service.set_departments(tenant, profile_id, department_ids=payload.department_ids)


@router.delete("/profiles/{profile_id}", response_model=ProfileSummary)
async def soft_delete_profile(
    profile_id: UUID, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    """Soft-delete: histórico preservado, sessões derrubadas na hora (BR-MIGRAR-018)."""
    return ProfileSummary.model_validate(await service.soft_delete(tenant, profile_id))


@router.post("/profiles/{profile_id}/reactivate", response_model=ProfileSummary)
async def reactivate_profile(
    profile_id: UUID, tenant: AdminDep, service: ProfileServiceDep
) -> ProfileSummary:
    return ProfileSummary.model_validate(await service.reactivate(tenant, profile_id))


@router.post("/profiles/{profile_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    profile_id: UUID,
    payload: PasswordResetIn,
    tenant: AdminDep,
    service: ProfileServiceDep,
) -> None:
    """Redefinir senha derruba as sessões abertas: se a conta estava comprometida, o
    token do invasor continuaria valendo."""
    await service.reset_password(tenant, profile_id, nova_senha=payload.nova_senha)


# ---------------------------------------------------------------- departamentos

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(tenant: TenantDep, session: SessionDep) -> list[DepartmentOut]:
    repo = DepartmentRepository(session, tenant)
    return [DepartmentOut.model_validate(d) for d in await repo.list_all_ordenado()]


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentIn, tenant: AdminDep, session: SessionDep
) -> DepartmentOut:
    service = DepartmentService(DepartmentRepository(session, tenant))
    departamento = await service.create(name=payload.name)
    await session.flush()
    await session.refresh(departamento)
    return DepartmentOut.model_validate(departamento)


@router.put("/departments/{department_id}", response_model=DepartmentOut)
async def rename_department(
    department_id: UUID, payload: DepartmentIn, tenant: AdminDep, session: SessionDep
) -> DepartmentOut:
    service = DepartmentService(DepartmentRepository(session, tenant))
    return DepartmentOut.model_validate(await service.rename(department_id, name=payload.name))


# ---------------------------------------------------------------- equipe

@router.post("/coordinator-members", status_code=status.HTTP_201_CREATED)
async def add_coordinator_member(
    payload: CoordinatorMemberIn,
    tenant: AdminDep,
    session: SessionDep,
    service: CoordinatorServiceDep,
) -> dict[str, str]:
    vinculo = await service.add_member(
        tenant, coordinator_id=payload.coordinator_id, member_id=payload.member_id
    )
    await session.flush()
    return {"id": str(vinculo.id)}


@router.delete("/coordinator-members", status_code=status.HTTP_204_NO_CONTENT)
async def remove_coordinator_member(
    coordinator_id: UUID,
    member_id: UUID,
    tenant: AdminDep,
    service: CoordinatorServiceDep,
) -> None:
    """Remoção de membro audita com `actor_id` e tenta notificar (BR-MIGRAR-026)."""
    await service.remove_member(tenant, coordinator_id=coordinator_id, member_id=member_id)


@router.post(
    "/team-requests", response_model=TeamRequestOut, status_code=status.HTTP_201_CREATED
)
async def create_team_request(
    payload: TeamRequestIn,
    tenant: GestaoDep,
    session: SessionDep,
    service: TeamRequestServiceDep,
) -> TeamRequestOut:
    pedido = await service.create(tenant, requested_member_id=payload.requested_member_id)
    await session.flush()
    await session.refresh(pedido)
    return TeamRequestOut.model_validate(pedido)


@router.get("/team-requests", response_model=list[TeamRequestOut])
async def list_team_requests(tenant: GestaoDep, session: SessionDep) -> list[TeamRequestOut]:
    repo = TeamRequestRepository(session, tenant)
    return [
        TeamRequestOut.model_validate(p) for p in await repo.list_pendentes_para(tenant.user_id)
    ]


@router.post("/team-requests/{request_id}/approve", response_model=TeamRequestOut)
async def approve_team_request(
    request_id: UUID, tenant: GestaoDep, service: TeamRequestServiceDep
) -> TeamRequestOut:
    return TeamRequestOut.model_validate(await service.approve(tenant, request_id))


@router.post("/team-requests/{request_id}/reject", response_model=TeamRequestOut)
async def reject_team_request(
    request_id: UUID,
    payload: TeamRequestRejectIn,
    tenant: GestaoDep,
    service: TeamRequestServiceDep,
) -> TeamRequestOut:
    """Só aprovação e rejeição existem (AMB-004): o resto não foi confirmado no legado."""
    return TeamRequestOut.model_validate(
        await service.reject(tenant, request_id, motivo=payload.motivo)
    )
