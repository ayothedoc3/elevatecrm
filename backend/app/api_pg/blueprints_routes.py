from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import WorkflowBlueprint

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])


@router.get("")
async def list_workflow_blueprints(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(WorkflowBlueprint)
        .where(and_(WorkflowBlueprint.tenant_id == user["tenant_id"]))
        .order_by(WorkflowBlueprint.created_at.desc())
        .limit(100)
    )
    blueprints = res.scalars().all()
    return {
        "blueprints": [
            {
                "id": b.id,
                "tenant_id": b.tenant_id,
                "name": b.name,
                "description": b.description,
                "stages": list(b.stages or []),
                "is_active": bool(b.is_active),
                "created_at": dt_to_iso(b.created_at),
                "updated_at": dt_to_iso(b.updated_at),
            }
            for b in blueprints
        ],
        "total": len(blueprints),
    }

