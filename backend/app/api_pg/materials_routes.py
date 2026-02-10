from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import MarketingMaterial
from app.services.storage_service import (
    ALLOWED_DOC_TYPES,
    ALLOWED_IMAGE_TYPES,
    get_content_type,
    get_storage,
    validate_file,
)

router = APIRouter(prefix="/materials", tags=["Marketing Materials"])


class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = "other"
    material_type: str = "url"
    url: Optional[str] = None
    program_id: Optional[str] = None
    tags: Optional[List[str]] = []


def _require_admin(user: dict) -> None:
    if (user.get("role") or "").lower() not in {"admin", "manager", "owner", "super_admin"}:
        raise HTTPException(status_code=403, detail="Not authorized")


async def _material_to_dict(mat: MarketingMaterial) -> dict:
    storage = get_storage()
    if mat.file_path:
        file_url = await storage.get_url(mat.file_path)
    else:
        file_url = mat.url
    return {
        "id": mat.id,
        "tenant_id": mat.tenant_id,
        "name": mat.name,
        "description": mat.description,
        "category": mat.category,
        "material_type": mat.material_type,
        "file_path": mat.file_path,
        "file_name": mat.file_name,
        "file_size": int(mat.file_size or 0),
        "content_type": mat.content_type,
        "storage_provider": mat.storage_provider,
        "url": mat.url,
        "file_url": file_url,
        "program_id": mat.program_id,
        "tags": list(mat.tags or []),
        "download_count": int(mat.download_count or 0),
        "is_active": bool(mat.is_active),
        "created_by": mat.created_by,
        "created_at": dt_to_iso(mat.created_at),
        "updated_at": dt_to_iso(mat.updated_at),
    }


@router.post("/upload", status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    category: str = Form(default="other"),
    program_id: str = Form(default=None),
    tags: str = Form(default=""),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    storage = get_storage()
    content = await file.read()
    content_type = file.content_type or get_content_type(file.filename)

    allowed_types = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES
    is_valid, message = validate_file(file.filename, content_type, len(content), allowed_types)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    if content_type in ALLOWED_IMAGE_TYPES:
        material_type = "image"
    elif content_type == "application/pdf":
        material_type = "pdf"
    else:
        material_type = "image"

    folder = f"materials/{user['tenant_id']}/{category}"
    upload_result = await storage.upload(content, file.filename, content_type, folder)

    now = now_utc()
    mat = MarketingMaterial(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=name,
        description=description,
        category=category,
        material_type=material_type,
        file_path=upload_result["file_path"],
        file_name=upload_result["original_name"],
        file_size=int(upload_result["size_bytes"]),
        content_type=upload_result["content_type"],
        storage_provider=upload_result["provider"],
        url=None,
        program_id=program_id if program_id else None,
        tags=[t.strip() for t in (tags or "").split(",") if t.strip()],
        download_count=0,
        is_active=True,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(mat)
    await db.flush()

    return await _material_to_dict(mat)


@router.post("/url", status_code=201)
async def create_url_material(
    data: MaterialCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    if (data.material_type or "").lower() != "url" or not data.url:
        raise HTTPException(status_code=400, detail="URL is required for URL type materials")

    now = now_utc()
    mat = MarketingMaterial(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        description=data.description,
        category=data.category,
        material_type="url",
        file_path=None,
        file_name=None,
        file_size=0,
        content_type=None,
        storage_provider=None,
        url=data.url,
        program_id=data.program_id,
        tags=list(data.tags or []),
        download_count=0,
        is_active=True,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(mat)
    await db.flush()
    return await _material_to_dict(mat)


@router.get("")
async def list_materials(
    category: Optional[str] = None,
    material_type: Optional[str] = None,
    program_id: Optional[str] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = [MarketingMaterial.tenant_id == user["tenant_id"], MarketingMaterial.is_active.is_(bool(is_active))]
    if category:
        where.append(MarketingMaterial.category == category)
    if material_type:
        where.append(MarketingMaterial.material_type == material_type)
    if program_id:
        where.append(MarketingMaterial.program_id == program_id)
    if search:
        like = f"%{search.strip()}%"
        where.append(
            or_(
                MarketingMaterial.name.ilike(like),
                MarketingMaterial.description.ilike(like),
            )
        )

    total_res = await db.execute(select(func.count(MarketingMaterial.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(MarketingMaterial)
        .where(and_(*where))
        .order_by(MarketingMaterial.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    materials = res.scalars().all()

    return {
        "materials": [await _material_to_dict(m) for m in materials],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    # Keep shape compatible with the Mongo routes.
    return {
        "categories": [
            {"value": "banners", "label": "Banners"},
            {"value": "social_posts", "label": "Social Posts"},
            {"value": "email_templates", "label": "Email Templates"},
            {"value": "logos", "label": "Logos"},
            {"value": "product_images", "label": "Product Images"},
            {"value": "sales_sheets", "label": "Sales Sheets"},
            {"value": "videos", "label": "Videos"},
            {"value": "other", "label": "Other"},
        ]
    }


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    res = await db.execute(
        select(MarketingMaterial).where(
            and_(MarketingMaterial.id == material_id, MarketingMaterial.tenant_id == user["tenant_id"])
        )
    )
    mat = res.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    await db.delete(mat)
    return {"success": True}

