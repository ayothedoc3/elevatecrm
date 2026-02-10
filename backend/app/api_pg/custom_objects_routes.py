from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import CustomObjectDefinition, CustomObjectField, CustomObjectRecord

router = APIRouter(prefix="/custom-objects", tags=["Custom Objects"])


class CreateFieldRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=100)
    field_type: str = "text"
    config: Optional[Dict[str, Any]] = None
    is_required: bool = False
    is_unique: bool = False
    show_in_list: bool = True
    show_in_detail: bool = True
    is_searchable: bool = False
    display_order: int = 0
    placeholder: Optional[str] = None
    help_text: Optional[str] = None


class CreateObjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    plural_name: Optional[str] = None
    description: Optional[str] = None
    icon: str = "Box"
    color: str = "#6366F1"
    label_field: str = "name"
    show_in_nav: bool = True
    fields: List[CreateFieldRequest] = []


class CreateRecordRequest(BaseModel):
    data: Dict[str, Any]


class UpdateRecordRequest(BaseModel):
    data: Dict[str, Any]


def _field_to_dict(f: CustomObjectField) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "label": f.label,
        "field_type": f.field_type,
        "config": f.config or {},
        "is_required": bool(f.is_required),
        "is_unique": bool(f.is_unique),
        "show_in_list": bool(f.show_in_list),
        "show_in_detail": bool(f.show_in_detail),
        "is_searchable": bool(f.is_searchable),
        "display_order": int(f.display_order or 0),
        "placeholder": f.placeholder,
        "help_text": f.help_text,
    }


def _record_to_dict(r: CustomObjectRecord) -> dict:
    return {
        "id": r.id,
        "tenant_id": r.tenant_id,
        "object_id": r.object_id,
        "display_label": r.display_label,
        "data": r.data or {},
        "owner_id": r.owner_id,
        "created_at": dt_to_iso(r.created_at),
        "updated_at": dt_to_iso(r.updated_at),
    }


@router.get("")
async def list_custom_objects(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    defs_res = await db.execute(
        select(CustomObjectDefinition)
        .where(and_(CustomObjectDefinition.tenant_id == user["tenant_id"], CustomObjectDefinition.is_active.is_(True)))
        .order_by(CustomObjectDefinition.display_order.asc())
        .limit(100)
    )
    defs = defs_res.scalars().all()
    if not defs:
        return []

    object_ids = [d.id for d in defs]

    fields_res = await db.execute(
        select(CustomObjectField)
        .where(CustomObjectField.object_id.in_(object_ids))
        .order_by(CustomObjectField.object_id.asc(), CustomObjectField.display_order.asc())
    )
    fields = fields_res.scalars().all()
    fields_by_object: Dict[str, List[CustomObjectField]] = {oid: [] for oid in object_ids}
    for f in fields:
        fields_by_object.setdefault(f.object_id, []).append(f)

    counts_res = await db.execute(
        select(CustomObjectRecord.object_id, func.count(CustomObjectRecord.id))
        .where(CustomObjectRecord.object_id.in_(object_ids))
        .group_by(CustomObjectRecord.object_id)
    )
    counts = {oid: int(cnt or 0) for oid, cnt in counts_res.all()}

    result = []
    for d in defs:
        result.append(
            {
                "id": d.id,
                "tenant_id": d.tenant_id,
                "name": d.name,
                "slug": d.slug,
                "plural_name": d.plural_name,
                "description": d.description,
                "icon": d.icon,
                "color": d.color,
                "label_field": d.label_field,
                "is_system": bool(d.is_system),
                "is_active": bool(d.is_active),
                "show_in_nav": bool(d.show_in_nav),
                "display_order": int(d.display_order or 0),
                "record_count": counts.get(d.id, 0),
                "fields": [_field_to_dict(f) for f in fields_by_object.get(d.id, [])],
                "created_at": dt_to_iso(d.created_at),
            }
        )
    return result


@router.post("", status_code=201)
async def create_custom_object(
    data: CreateObjectRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.tenant_id == user["tenant_id"], CustomObjectDefinition.slug == data.slug)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Object with slug '{data.slug}' already exists")

    max_order_res = await db.execute(
        select(func.coalesce(func.max(CustomObjectDefinition.display_order), 0)).where(CustomObjectDefinition.tenant_id == user["tenant_id"])
    )
    max_order = int(max_order_res.scalar() or 0)

    now = now_utc()
    obj = CustomObjectDefinition(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        slug=data.slug,
        plural_name=data.plural_name or f"{data.name}s",
        description=data.description,
        icon=data.icon,
        color=data.color,
        label_field=data.label_field or "name",
        is_system=False,
        is_active=True,
        show_in_nav=bool(data.show_in_nav),
        display_order=max_order + 1,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(obj)
    await db.flush()

    fields_to_create = data.fields or [
        CreateFieldRequest(name="name", label="Name", field_type="text", is_required=True, display_order=0)
    ]
    created_fields = []
    for i, f in enumerate(fields_to_create):
        field = CustomObjectField(
            id=str(uuid.uuid4()),
            object_id=obj.id,
            name=f.name,
            label=f.label,
            field_type=f.field_type,
            config=f.config or {},
            is_required=bool(f.is_required),
            is_unique=bool(f.is_unique),
            show_in_list=bool(f.show_in_list),
            show_in_detail=bool(f.show_in_detail),
            is_searchable=bool(f.is_searchable),
            display_order=int(f.display_order if f.display_order is not None else i),
            placeholder=f.placeholder,
            help_text=f.help_text,
            created_at=now,
        )
        db.add(field)
        created_fields.append(field)

    await db.flush()

    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "name": obj.name,
        "slug": obj.slug,
        "plural_name": obj.plural_name,
        "description": obj.description,
        "icon": obj.icon,
        "color": obj.color,
        "label_field": obj.label_field,
        "is_system": bool(obj.is_system),
        "is_active": bool(obj.is_active),
        "show_in_nav": bool(obj.show_in_nav),
        "display_order": int(obj.display_order or 0),
        "record_count": 0,
        "fields": [_field_to_dict(f) for f in created_fields],
        "created_at": dt_to_iso(obj.created_at),
    }


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_object(
    object_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.id == object_id, CustomObjectDefinition.tenant_id == user["tenant_id"])
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    if obj.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system object")
    await db.delete(obj)
    return None


@router.get("/{object_id}/records")
async def list_records(
    object_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj_res = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.id == object_id, CustomObjectDefinition.tenant_id == user["tenant_id"])
        )
    )
    obj = obj_res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")

    where = [CustomObjectRecord.tenant_id == user["tenant_id"], CustomObjectRecord.object_id == object_id]
    total_res = await db.execute(select(func.count(CustomObjectRecord.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(CustomObjectRecord)
        .where(and_(*where))
        .order_by(CustomObjectRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = res.scalars().all()
    return {"records": [_record_to_dict(r) for r in records], "total": total, "page": page, "page_size": page_size}


@router.post("/{object_id}/records", status_code=201)
async def create_record(
    object_id: str,
    data: CreateRecordRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj_res = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.id == object_id, CustomObjectDefinition.tenant_id == user["tenant_id"])
        )
    )
    obj = obj_res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")

    now = now_utc()
    display_label = str((data.data or {}).get(obj.label_field or "name", "")) if data.data else ""
    record = CustomObjectRecord(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        object_id=object_id,
        data=data.data or {},
        display_label=display_label,
        owner_id=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    await db.flush()
    return _record_to_dict(record)


@router.put("/{object_id}/records/{record_id}")
async def update_record(
    object_id: str,
    record_id: str,
    data: UpdateRecordRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj_res = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.id == object_id, CustomObjectDefinition.tenant_id == user["tenant_id"])
        )
    )
    obj = obj_res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")

    rec_res = await db.execute(
        select(CustomObjectRecord).where(
            and_(
                CustomObjectRecord.id == record_id,
                CustomObjectRecord.object_id == object_id,
                CustomObjectRecord.tenant_id == user["tenant_id"],
            )
        )
    )
    rec = rec_res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    now = now_utc()
    display_label = str((data.data or {}).get(obj.label_field or "name", "")) if data.data else ""
    await db.execute(
        update(CustomObjectRecord)
        .where(CustomObjectRecord.id == record_id)
        .values(data=data.data or {}, display_label=display_label, updated_at=now)
    )
    return {"success": True}


@router.delete("/{object_id}/records/{record_id}")
async def delete_record(
    object_id: str,
    record_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec_res = await db.execute(
        select(CustomObjectRecord.id).where(
            and_(
                CustomObjectRecord.id == record_id,
                CustomObjectRecord.object_id == object_id,
                CustomObjectRecord.tenant_id == user["tenant_id"],
            )
        )
    )
    if not rec_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Record not found")
    await db.execute(delete(CustomObjectRecord).where(CustomObjectRecord.id == record_id))
    return {"success": True}

