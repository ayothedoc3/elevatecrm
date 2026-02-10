from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import create_timeline_event, resolve_account
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Contact

router = APIRouter(tags=["Contacts"])


class ContactCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    company: Optional[str] = None
    lifecycle_stage: str = "lead"


def _contact_to_dict(c: Contact) -> Dict[str, Any]:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "full_name": (c.full_name or f"{c.first_name or ''} {c.last_name or ''}").strip(),
        "email": c.email,
        "phone": c.phone,
        "company_name": c.company_name,
        "company": c.company_name,
        "account_id": c.account_id,
        "account_name": c.account_name or c.company_name,
        "source": c.source,
        "lifecycle_stage": c.lifecycle_stage,
        "lead_score": c.lead_score,
        "lead_tier": c.lead_tier,
        "owner_id": c.owner_id,
        "tags": c.tags or [],
        "status": c.status,
        "created_at": dt_to_iso(c.created_at),
        "updated_at": dt_to_iso(c.updated_at),
    }


@router.get("/contacts")
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    filters = [Contact.tenant_id == tenant_id]
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Contact.first_name.ilike(pattern),
                Contact.last_name.ilike(pattern),
                Contact.email.ilike(pattern),
            )
        )

    total_res = await db.execute(select(func.count()).select_from(Contact).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Contact)
        .where(and_(*filters))
        .order_by(Contact.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    contacts = (await db.execute(stmt)).scalars().all()

    return {"contacts": [_contact_to_dict(c) for c in contacts], "total": total, "page": page, "page_size": page_size}


@router.post("/contacts", status_code=201)
async def create_contact(
    data: ContactCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    now = now_utc()

    company_name = data.company_name or data.company
    account_name_input = company_name or f"{data.first_name} {data.last_name}".strip()
    resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])

    contact = Contact(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name=data.first_name,
        last_name=data.last_name,
        full_name=f"{data.first_name} {data.last_name}".strip(),
        email=data.email,
        phone=data.phone,
        company_name=company_name,
        account_id=resolved_account.get("account_id"),
        account_name=resolved_account.get("account_name"),
        source="manual",
        lifecycle_stage=data.lifecycle_stage or "lead",
        lead_score=0,
        lead_tier="D",
        owner_id=user["id"],
        tags=[],
        status="active",
        converted_from_lead_id=None,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(contact)

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="contact_created",
        title=f"Contact created: {contact.full_name}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        contact_id=contact.id,
    )

    await db.flush()
    return _contact_to_dict(contact)


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    res = await db.execute(select(Contact).where(and_(Contact.id == contact_id, Contact.tenant_id == tenant_id)))
    contact = res.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _contact_to_dict(contact)

