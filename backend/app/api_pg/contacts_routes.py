from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
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


@router.get("/contacts/export")
async def export_contacts_csv(
    format: str = Query("hubspot"),
    limit: int = Query(10000, ge=1, le=50000),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    contacts = (
        await db.execute(select(Contact).where(Contact.tenant_id == tenant_id).order_by(Contact.created_at.desc()).limit(limit))
    ).scalars().all()

    out = io.StringIO()
    writer = csv.writer(out)

    fmt = (format or "hubspot").strip().lower()
    if fmt == "hubspot":
        writer.writerow(["Email", "First Name", "Last Name", "Phone Number", "Company Name", "Lifecycle Stage"])
        for c in contacts:
            writer.writerow(
                [
                    c.email or "",
                    c.first_name or "",
                    c.last_name or "",
                    c.phone or "",
                    c.company_name or "",
                    c.lifecycle_stage or "",
                ]
            )
    else:
        writer.writerow(
            [
                "email",
                "first_name",
                "last_name",
                "phone",
                "company_name",
                "lifecycle_stage",
                "lead_score",
                "lead_tier",
                "created_at",
                "updated_at",
            ]
        )
        for c in contacts:
            writer.writerow(
                [
                    c.email or "",
                    c.first_name or "",
                    c.last_name or "",
                    c.phone or "",
                    c.company_name or "",
                    c.lifecycle_stage or "",
                    int(c.lead_score or 0),
                    c.lead_tier or "",
                    dt_to_iso(c.created_at) or "",
                    dt_to_iso(c.updated_at) or "",
                ]
            )

    filename = f"contacts_{tenant_id}.csv"
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/contacts/import")
async def import_contacts_csv(
    file: UploadFile = File(...),
    max_rows: int = Query(5000, ge=1, le=50000),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    filename = (file.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a header row")

    def norm_header(h: str) -> str:
        return "".join(ch for ch in (h or "").strip().lower() if ch.isalnum())

    header_aliases = {
        "email": "email",
        "emailaddress": "email",
        "emailid": "email",
        "firstname": "first_name",
        "lastname": "last_name",
        "fullname": "full_name",
        "name": "full_name",
        "phone": "phone",
        "phonenumber": "phone",
        "mobilenumber": "phone",
        "company": "company_name",
        "companyname": "company_name",
        "organization": "company_name",
        "lifecyclestage": "lifecycle_stage",
        "lifecycle": "lifecycle_stage",
    }

    header_map: Dict[str, Optional[str]] = {}
    for h in reader.fieldnames:
        header_map[h] = header_aliases.get(norm_header(h))

    created = 0
    updated = 0
    skipped = 0
    errors: list[Dict[str, Any]] = []

    now = now_utc()
    row_count = 0
    for row_index, row in enumerate(reader, start=2):
        row_count += 1
        if row_count > max_rows:
            skipped += 1
            errors.append({"row": row_index, "error": f"Max rows exceeded ({max_rows}). Remaining rows not processed."})
            break

        values: Dict[str, str] = {}
        for k, v in (row or {}).items():
            field = header_map.get(k)
            if not field:
                continue
            val = (v or "").strip()
            if val:
                values[field] = val

        email = (values.get("email") or "").strip()
        if not email:
            skipped += 1
            errors.append({"row": row_index, "error": "Missing email"})
            continue

        first_name = (values.get("first_name") or "").strip()
        last_name = (values.get("last_name") or "").strip()
        full_name = (values.get("full_name") or "").strip()

        if (not first_name or not last_name) and full_name:
            parts = [p for p in full_name.split(" ") if p]
            if not first_name and parts:
                first_name = parts[0]
            if not last_name and len(parts) > 1:
                last_name = " ".join(parts[1:])

        if not first_name and "@" in email:
            first_name = email.split("@", 1)[0]

        company_name = (values.get("company_name") or "").strip() or None
        phone = (values.get("phone") or "").strip() or None
        lifecycle_stage = (values.get("lifecycle_stage") or "").strip() or "lead"

        existing = (
            await db.execute(
                select(Contact)
                .where(and_(Contact.tenant_id == tenant_id, func.lower(Contact.email) == email.lower()))
                .limit(1)
            )
        ).scalar_one_or_none()

        if existing:
            if first_name:
                existing.first_name = first_name
            if last_name:
                existing.last_name = last_name
            if first_name or last_name:
                existing.full_name = f"{existing.first_name or ''} {existing.last_name or ''}".strip() or existing.full_name
            if phone:
                existing.phone = phone
            if company_name:
                existing.company_name = company_name
                resolved = await resolve_account(db, tenant_id, company_name, user["id"])
                existing.account_id = resolved.get("account_id")
                existing.account_name = resolved.get("account_name")
            if lifecycle_stage:
                existing.lifecycle_stage = lifecycle_stage
            existing.updated_at = now
            updated += 1
            continue

        resolved = None
        if company_name:
            resolved = await resolve_account(db, tenant_id, company_name, user["id"])

        contact = Contact(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name=first_name or None,
            last_name=last_name or None,
            full_name=f"{first_name} {last_name}".strip() or full_name or None,
            email=email,
            phone=phone,
            company_name=company_name,
            account_id=(resolved or {}).get("account_id"),
            account_name=(resolved or {}).get("account_name"),
            source="hubspot_import",
            lifecycle_stage=lifecycle_stage,
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
        created += 1

    if created or updated or skipped:
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="contacts_imported",
            title=f"Contacts imported ({created} created, {updated} updated)",
            actor_id=user["id"],
            actor_name=user.get("full_name"),
            metadata={"created": created, "updated": updated, "skipped": skipped, "errors": len(errors)},
        )

    await db.flush()
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:200]}


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

