"""
Custom Objects API Routes

Handles CRUD operations for custom object definitions, fields, and records.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import json

from app.core.database import get_db
from app.models import User, CustomObjectDefinition, CustomObjectField, CustomObjectRecord

router = APIRouter(prefix="/custom-objects", tags=["Custom Objects"])


# ==================== SCHEMAS ====================

class FieldConfig(BaseModel):
    options: Optional[List[Dict[str, str]]] = None
    default_value: Optional[Any] = None


class CreateFieldRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=100)
    field_type: str
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


class UpdateObjectRequest(BaseModel):
    name: Optional[str] = None
    plural_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    label_field: Optional[str] = None
    show_in_nav: Optional[bool] = None


class ObjectFieldResponse(BaseModel):
    id: str
    name: str
    label: str
    field_type: str
    config: Dict[str, Any]
    is_required: bool
    is_unique: bool
    show_in_list: bool
    show_in_detail: bool
    is_searchable: bool
    display_order: int
    placeholder: Optional[str]
    help_text: Optional[str]


class ObjectDefinitionResponse(BaseModel):
    id: str
    name: str
    slug: str
    plural_name: Optional[str]
    description: Optional[str]
    icon: str
    color: str
    label_field: str
    is_system: bool
    is_active: bool
    show_in_nav: bool
    display_order: int
    record_count: int = 0
    fields: List[ObjectFieldResponse] = []
    created_at: str


class CreateRecordRequest(BaseModel):
    data: Dict[str, Any]


class RecordResponse(BaseModel):
    id: str
    object_id: str
    display_label: Optional[str]
    data: Dict[str, Any]
    owner_id: Optional[str]
    created_at: str
    updated_at: str


# ==================== HELPER FUNCTIONS ====================

async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Get current user from auth context - placeholder"""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def slugify(name: str) -> str:
    """Convert name to slug"""
    return name.lower().replace(' ', '_').replace('-', '_')


# ==================== OBJECT DEFINITION ENDPOINTS ====================

@router.get("", response_model=List[ObjectDefinitionResponse])
async def list_object_definitions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all custom object definitions for the tenant"""
    result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.tenant_id == user.tenant_id,
                CustomObjectDefinition.is_active == True
            )
        )
        .order_by(CustomObjectDefinition.display_order)
    )
    definitions = result.scalars().all()
    
    response = []
    for d in definitions:
        # Get fields
        fields_result = await db.execute(
            select(CustomObjectField)
            .where(CustomObjectField.object_id == d.id)
            .order_by(CustomObjectField.display_order)
        )
        fields = fields_result.scalars().all()
        
        # Get record count
        count_result = await db.execute(
            select(func.count(CustomObjectRecord.id))
            .where(CustomObjectRecord.object_id == d.id)
        )
        record_count = count_result.scalar() or 0
        
        response.append(ObjectDefinitionResponse(
            id=d.id,
            name=d.name,
            slug=d.slug,
            plural_name=d.plural_name,
            description=d.description,
            icon=d.icon,
            color=d.color,
            label_field=d.label_field,
            is_system=d.is_system,
            is_active=d.is_active,
            show_in_nav=d.show_in_nav,
            display_order=d.display_order,
            record_count=record_count,
            fields=[
                ObjectFieldResponse(
                    id=f.id,
                    name=f.name,
                    label=f.label,
                    field_type=f.field_type,
                    config=json.loads(f.config or '{}'),
                    is_required=f.is_required,
                    is_unique=f.is_unique,
                    show_in_list=f.show_in_list,
                    show_in_detail=f.show_in_detail,
                    is_searchable=f.is_searchable,
                    display_order=f.display_order,
                    placeholder=f.placeholder,
                    help_text=f.help_text
                )
                for f in fields
            ],
            created_at=d.created_at.isoformat()
        ))
    
    return response


@router.post("", response_model=ObjectDefinitionResponse, status_code=201)
async def create_object_definition(
    request: CreateObjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom object definition"""
    # Check if slug already exists
    existing = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.tenant_id == user.tenant_id,
                CustomObjectDefinition.slug == request.slug
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Object with slug '{request.slug}' already exists")
    
    # Get max display order
    max_order_result = await db.execute(
        select(func.max(CustomObjectDefinition.display_order))
        .where(CustomObjectDefinition.tenant_id == user.tenant_id)
    )
    max_order = max_order_result.scalar() or 0
    
    # Create object definition
    obj_def = CustomObjectDefinition(
        tenant_id=user.tenant_id,
        name=request.name,
        slug=request.slug,
        plural_name=request.plural_name or f"{request.name}s",
        description=request.description,
        icon=request.icon,
        color=request.color,
        label_field=request.label_field,
        show_in_nav=request.show_in_nav,
        display_order=max_order + 1,
        created_by=user.id
    )
    db.add(obj_def)
    await db.flush()
    
    # Create default fields if none provided
    fields_to_create = request.fields or [
        CreateFieldRequest(
            name="name",
            label="Name",
            field_type="text",
            is_required=True,
            show_in_list=True,
            is_searchable=True,
            display_order=0
        )
    ]
    
    created_fields = []
    for i, field_req in enumerate(fields_to_create):
        field = CustomObjectField(
            object_id=obj_def.id,
            name=field_req.name,
            label=field_req.label,
            field_type=field_req.field_type,
            config=json.dumps(field_req.config or {}),
            is_required=field_req.is_required,
            is_unique=field_req.is_unique,
            show_in_list=field_req.show_in_list,
            show_in_detail=field_req.show_in_detail,
            is_searchable=field_req.is_searchable,
            display_order=field_req.display_order or i,
            placeholder=field_req.placeholder,
            help_text=field_req.help_text
        )
        db.add(field)
        created_fields.append(field)
    
    await db.commit()
    
    return ObjectDefinitionResponse(
        id=obj_def.id,
        name=obj_def.name,
        slug=obj_def.slug,
        plural_name=obj_def.plural_name,
        description=obj_def.description,
        icon=obj_def.icon,
        color=obj_def.color,
        label_field=obj_def.label_field,
        is_system=obj_def.is_system,
        is_active=obj_def.is_active,
        show_in_nav=obj_def.show_in_nav,
        display_order=obj_def.display_order,
        record_count=0,
        fields=[
            ObjectFieldResponse(
                id=f.id,
                name=f.name,
                label=f.label,
                field_type=f.field_type,
                config=json.loads(f.config or '{}'),
                is_required=f.is_required,
                is_unique=f.is_unique,
                show_in_list=f.show_in_list,
                show_in_detail=f.show_in_detail,
                is_searchable=f.is_searchable,
                display_order=f.display_order,
                placeholder=f.placeholder,
                help_text=f.help_text
            )
            for f in created_fields
        ],
        created_at=obj_def.created_at.isoformat()
    )


@router.get("/{object_id}", response_model=ObjectDefinitionResponse)
async def get_object_definition(
    object_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific custom object definition"""
    result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.id == object_id,
                CustomObjectDefinition.tenant_id == user.tenant_id
            )
        )
    )
    obj_def = result.scalar_one_or_none()
    
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    # Get fields
    fields_result = await db.execute(
        select(CustomObjectField)
        .where(CustomObjectField.object_id == obj_def.id)
        .order_by(CustomObjectField.display_order)
    )
    fields = fields_result.scalars().all()
    
    # Get record count
    count_result = await db.execute(
        select(func.count(CustomObjectRecord.id))
        .where(CustomObjectRecord.object_id == obj_def.id)
    )
    record_count = count_result.scalar() or 0
    
    return ObjectDefinitionResponse(
        id=obj_def.id,
        name=obj_def.name,
        slug=obj_def.slug,
        plural_name=obj_def.plural_name,
        description=obj_def.description,
        icon=obj_def.icon,
        color=obj_def.color,
        label_field=obj_def.label_field,
        is_system=obj_def.is_system,
        is_active=obj_def.is_active,
        show_in_nav=obj_def.show_in_nav,
        display_order=obj_def.display_order,
        record_count=record_count,
        fields=[
            ObjectFieldResponse(
                id=f.id,
                name=f.name,
                label=f.label,
                field_type=f.field_type,
                config=json.loads(f.config or '{}'),
                is_required=f.is_required,
                is_unique=f.is_unique,
                show_in_list=f.show_in_list,
                show_in_detail=f.show_in_detail,
                is_searchable=f.is_searchable,
                display_order=f.display_order,
                placeholder=f.placeholder,
                help_text=f.help_text
            )
            for f in fields
        ],
        created_at=obj_def.created_at.isoformat()
    )


@router.delete("/{object_id}", status_code=204)
async def delete_object_definition(
    object_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a custom object definition"""
    result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.id == object_id,
                CustomObjectDefinition.tenant_id == user.tenant_id
            )
        )
    )
    obj_def = result.scalar_one_or_none()
    
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    if obj_def.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system object")
    
    await db.delete(obj_def)
    await db.commit()


# ==================== RECORD ENDPOINTS ====================

@router.get("/{object_id}/records")
async def list_records(
    object_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List records for a custom object"""
    # Verify object exists
    obj_result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.id == object_id,
                CustomObjectDefinition.tenant_id == user.tenant_id
            )
        )
    )
    obj_def = obj_result.scalar_one_or_none()
    
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    # Build query
    query = select(CustomObjectRecord).where(
        and_(
            CustomObjectRecord.object_id == object_id,
            CustomObjectRecord.tenant_id == user.tenant_id
        )
    )
    count_query = select(func.count(CustomObjectRecord.id)).where(
        and_(
            CustomObjectRecord.object_id == object_id,
            CustomObjectRecord.tenant_id == user.tenant_id
        )
    )
    
    # Note: Full-text search would require more complex implementation
    # For now, we filter by display_label if search is provided
    if search:
        query = query.where(CustomObjectRecord.display_label.ilike(f"%{search}%"))
        count_query = count_query.where(CustomObjectRecord.display_label.ilike(f"%{search}%"))
    
    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(CustomObjectRecord.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return {
        "records": [
            RecordResponse(
                id=r.id,
                object_id=r.object_id,
                display_label=r.display_label,
                data=json.loads(r.data or '{}'),
                owner_id=r.owner_id,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat()
            )
            for r in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/{object_id}/records", response_model=RecordResponse, status_code=201)
async def create_record(
    object_id: str,
    request: CreateRecordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new record for a custom object"""
    # Verify object exists
    obj_result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.id == object_id,
                CustomObjectDefinition.tenant_id == user.tenant_id
            )
        )
    )
    obj_def = obj_result.scalar_one_or_none()
    
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    # Get fields for validation
    fields_result = await db.execute(
        select(CustomObjectField).where(CustomObjectField.object_id == object_id)
    )
    fields = {f.name: f for f in fields_result.scalars().all()}
    
    # Validate required fields
    for field_name, field in fields.items():
        if field.is_required and field_name not in request.data:
            raise HTTPException(status_code=400, detail=f"Field '{field.label}' is required")
    
    # Compute display label
    display_label = str(request.data.get(obj_def.label_field, ''))
    
    record = CustomObjectRecord(
        tenant_id=user.tenant_id,
        object_id=object_id,
        data=json.dumps(request.data),
        display_label=display_label,
        owner_id=user.id,
        created_by=user.id
    )
    db.add(record)
    await db.commit()
    
    return RecordResponse(
        id=record.id,
        object_id=record.object_id,
        display_label=record.display_label,
        data=request.data,
        owner_id=record.owner_id,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat()
    )


@router.get("/{object_id}/records/{record_id}", response_model=RecordResponse)
async def get_record(
    object_id: str,
    record_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific record"""
    result = await db.execute(
        select(CustomObjectRecord)
        .where(
            and_(
                CustomObjectRecord.id == record_id,
                CustomObjectRecord.object_id == object_id,
                CustomObjectRecord.tenant_id == user.tenant_id
            )
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return RecordResponse(
        id=record.id,
        object_id=record.object_id,
        display_label=record.display_label,
        data=json.loads(record.data or '{}'),
        owner_id=record.owner_id,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat()
    )


@router.put("/{object_id}/records/{record_id}", response_model=RecordResponse)
async def update_record(
    object_id: str,
    record_id: str,
    request: CreateRecordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a record"""
    # Get object definition
    obj_result = await db.execute(
        select(CustomObjectDefinition)
        .where(
            and_(
                CustomObjectDefinition.id == object_id,
                CustomObjectDefinition.tenant_id == user.tenant_id
            )
        )
    )
    obj_def = obj_result.scalar_one_or_none()
    
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    result = await db.execute(
        select(CustomObjectRecord)
        .where(
            and_(
                CustomObjectRecord.id == record_id,
                CustomObjectRecord.object_id == object_id,
                CustomObjectRecord.tenant_id == user.tenant_id
            )
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Update record
    record.data = json.dumps(request.data)
    record.display_label = str(request.data.get(obj_def.label_field, ''))
    record.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return RecordResponse(
        id=record.id,
        object_id=record.object_id,
        display_label=record.display_label,
        data=request.data,
        owner_id=record.owner_id,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat()
    )


@router.delete("/{object_id}/records/{record_id}", status_code=204)
async def delete_record(
    object_id: str,
    record_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a record"""
    result = await db.execute(
        select(CustomObjectRecord)
        .where(
            and_(
                CustomObjectRecord.id == record_id,
                CustomObjectRecord.object_id == object_id,
                CustomObjectRecord.tenant_id == user.tenant_id
            )
        )
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.delete(record)
    await db.commit()
