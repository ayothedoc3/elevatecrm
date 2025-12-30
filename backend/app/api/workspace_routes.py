"""
Workspace and Blueprint API Routes

Handles multi-CRM workspace management, blueprint operations, and provisioning.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import json
import re

from app.core.database import get_db
from app.models import (
    User, CRMBlueprint, CRMWorkspace, WorkspaceUser, ProvisioningJob,
    WorkspaceStatus, ProvisioningStatus, WorkspaceRole
)
from app.services.provisioning_service import ProvisioningService, seed_system_blueprints
from app.blueprints.frylow_blueprint import get_all_blueprints

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ==================== SCHEMAS ====================

class BlueprintSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon: str
    color: str
    is_default: bool
    is_system: bool


class BlueprintListResponse(BaseModel):
    blueprints: List[BlueprintSummary]


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    status: str
    blueprint_name: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    role: str
    created_at: str


class WorkspaceListResponse(BaseModel):
    workspaces: List[WorkspaceSummary]
    current_workspace_id: Optional[str]


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = None
    description: Optional[str] = None
    blueprint_slug: str = "frylow-sales"
    include_demo_data: bool = False


class CreateWorkspaceResponse(BaseModel):
    workspace_id: str
    job_id: str
    status: str


class ProvisioningStatusResponse(BaseModel):
    id: str
    workspace_id: str
    status: str
    progress: int
    current_step: Optional[str]
    completed_steps: List[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]


class WorkspaceDetailResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    status: str
    blueprint_id: Optional[str]
    blueprint_name: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    plan: str
    max_users: int
    max_contacts: int
    created_at: str
    tenant_id: Optional[str]


# ==================== HELPER FUNCTIONS ====================

def generate_slug(name: str) -> str:
    """Generate URL-safe slug from name"""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def get_current_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Placeholder - will be replaced with actual auth"""
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get('sub')
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ==================== BLUEPRINT ENDPOINTS ====================

@router.get("/blueprints", response_model=BlueprintListResponse)
async def list_blueprints(db: AsyncSession = Depends(get_db)):
    """List all available CRM blueprints"""
    # Ensure blueprints are seeded
    await seed_system_blueprints(db)
    
    result = await db.execute(
        select(CRMBlueprint).where(CRMBlueprint.is_active == True).order_by(CRMBlueprint.is_default.desc())
    )
    blueprints = result.scalars().all()
    
    return BlueprintListResponse(
        blueprints=[
            BlueprintSummary(
                id=bp.id,
                name=bp.name,
                slug=bp.slug,
                description=bp.description,
                icon=bp.icon,
                color=bp.color,
                is_default=bp.is_default,
                is_system=bp.is_system
            )
            for bp in blueprints
        ]
    )


@router.get("/blueprints/{slug}")
async def get_blueprint(slug: str, db: AsyncSession = Depends(get_db)):
    """Get blueprint details including full config"""
    result = await db.execute(
        select(CRMBlueprint).where(CRMBlueprint.slug == slug)
    )
    blueprint = result.scalar_one_or_none()
    
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    
    return {
        "id": blueprint.id,
        "name": blueprint.name,
        "slug": blueprint.slug,
        "description": blueprint.description,
        "version": blueprint.version,
        "icon": blueprint.icon,
        "color": blueprint.color,
        "is_default": blueprint.is_default,
        "is_system": blueprint.is_system,
        "config": json.loads(blueprint.config or '{}'),
        "created_at": blueprint.created_at.isoformat()
    }


# ==================== WORKSPACE ENDPOINTS ====================

@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    current_user: User = Depends(lambda: None),  # Will be injected properly
    db: AsyncSession = Depends(get_db)
):
    """List workspaces the current user has access to"""
    # For now, return all workspaces (will be filtered by user membership later)
    result = await db.execute(
        select(CRMWorkspace, CRMBlueprint)
        .outerjoin(CRMBlueprint, CRMWorkspace.blueprint_id == CRMBlueprint.id)
        .where(CRMWorkspace.status != WorkspaceStatus.ARCHIVED)
        .order_by(CRMWorkspace.created_at.desc())
    )
    rows = result.all()
    
    workspaces = []
    for workspace, blueprint in rows:
        workspaces.append(WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            description=workspace.description,
            status=workspace.status.value,
            blueprint_name=blueprint.name if blueprint else None,
            logo_url=workspace.logo_url,
            primary_color=workspace.primary_color,
            role="owner",  # Will be determined by membership
            created_at=workspace.created_at.isoformat()
        ))
    
    return WorkspaceListResponse(
        workspaces=workspaces,
        current_workspace_id=workspaces[0].id if workspaces else None
    )


@router.post("", response_model=CreateWorkspaceResponse)
async def create_workspace(
    request: CreateWorkspaceRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new CRM workspace"""
    # Generate slug if not provided
    slug = request.slug or generate_slug(request.name)
    
    # Check if slug is unique
    result = await db.execute(
        select(CRMWorkspace).where(CRMWorkspace.slug == slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Workspace with slug '{slug}' already exists"
        )
    
    # Create workspace via provisioning service
    service = ProvisioningService(db)
    
    # For now, use a placeholder user ID (will be from auth context)
    user_id = None
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user:
        user_id = user.id
    
    try:
        result = await service.create_workspace(
            name=request.name,
            slug=slug,
            blueprint_slug=request.blueprint_slug,
            created_by_user_id=user_id,
            include_demo_data=request.include_demo_data,
            description=request.description
        )
        
        # Run provisioning in background
        background_tasks.add_task(run_provisioning_task, result['job_id'], db)
        
        return CreateWorkspaceResponse(
            workspace_id=result['workspace_id'],
            job_id=result['job_id'],
            status="provisioning"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """Get workspace details"""
    result = await db.execute(
        select(CRMWorkspace, CRMBlueprint)
        .outerjoin(CRMBlueprint, CRMWorkspace.blueprint_id == CRMBlueprint.id)
        .where(CRMWorkspace.id == workspace_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace, blueprint = row
    settings = json.loads(workspace.settings or '{}')
    
    return WorkspaceDetailResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        status=workspace.status.value,
        blueprint_id=workspace.blueprint_id,
        blueprint_name=blueprint.name if blueprint else None,
        logo_url=workspace.logo_url,
        primary_color=workspace.primary_color,
        plan=workspace.plan,
        max_users=workspace.max_users,
        max_contacts=workspace.max_contacts,
        created_at=workspace.created_at.isoformat(),
        tenant_id=settings.get('tenant_id')
    )


@router.get("/{workspace_id}/provisioning", response_model=ProvisioningStatusResponse)
async def get_provisioning_status(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """Get provisioning status for a workspace"""
    result = await db.execute(
        select(ProvisioningJob)
        .where(ProvisioningJob.workspace_id == workspace_id)
        .order_by(ProvisioningJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Provisioning job not found")
    
    return ProvisioningStatusResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status.value,
        progress=job.progress,
        current_step=job.current_step,
        completed_steps=json.loads(job.completed_steps or '[]'),
        error_message=job.error_message,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


@router.post("/{workspace_id}/switch")
async def switch_workspace(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """Switch to a different workspace (returns tenant_id for auth context)"""
    result = await db.execute(
        select(CRMWorkspace).where(
            and_(
                CRMWorkspace.id == workspace_id,
                CRMWorkspace.status == WorkspaceStatus.ACTIVE
            )
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or not active")
    
    settings = json.loads(workspace.settings or '{}')
    tenant_id = settings.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Workspace not fully provisioned")
    
    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "workspace_slug": workspace.slug,
        "tenant_id": tenant_id
    }


# ==================== BACKGROUND TASK ====================

async def run_provisioning_task(job_id: str, db: AsyncSession):
    """Background task to run workspace provisioning"""
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        service = ProvisioningService(session)
        await service.run_provisioning(job_id)
