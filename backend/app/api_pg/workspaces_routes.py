from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import CRMBlueprint, Tenant

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("/blueprints")
async def list_crm_blueprints(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Keep response shape compatible with existing frontend expectations.
    res = await db.execute(
        select(CRMBlueprint)
        .where(and_(CRMBlueprint.tenant_id == user["tenant_id"], CRMBlueprint.is_active.is_(True)))
        .order_by(CRMBlueprint.is_default.desc(), CRMBlueprint.created_at.desc())
        .limit(100)
    )
    blueprints = res.scalars().all()

    if not blueprints:
        # Fallback to code-defined blueprints until seed data is applied.
        from app.blueprints.registry import get_all_blueprints

        blueprints = []
        for b in get_all_blueprints():
            cfg = b.get("config") or {}
            blueprints.append(
                CRMBlueprint(
                    id=b["slug"],
                    tenant_id=user["tenant_id"],
                    name=b["name"],
                    slug=b["slug"],
                    description=cfg.get("description", ""),
                    version=int(cfg.get("version") or 1),
                    icon=cfg.get("icon", "building"),
                    color=cfg.get("color", "#6366F1"),
                    is_default=bool(b.get("is_default")),
                    is_system=True,
                    is_active=True,
                    config=cfg,
                    created_at=cfg.get("created_at") or None,  # not persisted
                    updated_at=cfg.get("created_at") or None,  # not persisted
                )
            )

    return {
        "blueprints": [
            {
                "id": bp.id,
                "name": bp.name,
                "slug": bp.slug,
                "description": bp.description,
                "icon": bp.icon,
                "color": bp.color,
                "is_default": bool(bp.is_default),
                "is_system": bool(bp.is_system),
            }
            for bp in blueprints
        ]
    }


@router.get("/blueprints/{slug}")
async def get_crm_blueprint(
    slug: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(CRMBlueprint).where(and_(CRMBlueprint.tenant_id == user["tenant_id"], CRMBlueprint.slug == slug))
    )
    bp = res.scalar_one_or_none()
    if not bp:
        from app.blueprints.registry import get_blueprint_json, get_all_blueprints

        cfg = get_blueprint_json(slug)
        meta = next((b for b in get_all_blueprints() if b.get("slug") == slug), None) or {}
        if not cfg:
            raise HTTPException(status_code=404, detail="Blueprint not found")
        return {
            "id": slug,
            "name": meta.get("name") or cfg.get("name") or slug,
            "slug": slug,
            "description": cfg.get("description"),
            "version": int(cfg.get("version") or 1),
            "icon": cfg.get("icon", "building"),
            "color": cfg.get("color", "#6366F1"),
            "is_default": bool(meta.get("is_default")),
            "is_system": True,
            "config": cfg,
            "created_at": None,
        }

    return {
        "id": bp.id,
        "name": bp.name,
        "slug": bp.slug,
        "description": bp.description,
        "version": int(bp.version or 1),
        "icon": bp.icon,
        "color": bp.color,
        "is_default": bool(bp.is_default),
        "is_system": bool(bp.is_system),
        "config": bp.config or {},
        "created_at": dt_to_iso(bp.created_at),
    }


@router.get("")
async def list_workspaces(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Phase 1 simplification: treat Tenants as Workspaces.
    # Security: only return workspaces the current user belongs to (single-tenant for Phase 1).
    res = await db.execute(
        select(Tenant).where(Tenant.id == user["tenant_id"], Tenant.is_active.is_(True)).limit(1)
    )
    tenants = [t for t in [res.scalar_one_or_none()] if t]
    workspaces = [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "description": None,
            "status": "active",
            "blueprint_name": None,
            "logo_url": None,
            "primary_color": "#6366F1",
            "role": "owner",
            "created_at": dt_to_iso(t.created_at),
        }
        for t in tenants
    ]
    return {"workspaces": workspaces, "current_workspace_id": workspaces[0]["id"] if workspaces else None}


@router.post("/{workspace_id}/switch")
async def switch_workspace(
    workspace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    res = await db.execute(select(Tenant).where(Tenant.id == workspace_id, Tenant.is_active.is_(True)))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"tenant_id": tenant.id, "workspace_slug": tenant.slug}


@router.get("/{workspace_id}/provisioning")
async def get_provisioning_status(
    workspace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    res = await db.execute(select(Tenant).where(Tenant.id == workspace_id, Tenant.is_active.is_(True)))
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {
        "id": workspace_id,
        "workspace_id": workspace_id,
        "status": "completed",
        "progress": 100,
        "current_step": None,
        "completed_steps": ["created"],
        "error_message": None,
        "started_at": dt_to_iso(tenant.created_at),
        "completed_at": dt_to_iso(tenant.created_at),
    }
