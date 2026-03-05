from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import create_timeline_event
from app.api_pg.utils import dt_to_iso, now_utc, parse_iso_datetime
from app.core.database import get_db
from app.pg_models.models import (
    Lead,
    LandingPage,
    LandingPageConversation,
    LandingPageEvent,
    LandingPageGeneration,
    LandingPageVersion,
    Tenant,
    User,
)
from app.services.ai_service import AIModel, get_ai_service

router = APIRouter(prefix="/landing-pages", tags=["Landing Pages"])


class PageType(str, Enum):
    AFFILIATE_RECRUITMENT = "affiliate_recruitment"
    AFFILIATE_PRODUCT = "affiliate_product"
    PRODUCT_SALES = "product_sales"
    DEMO_BOOKING = "demo_booking"
    LEAD_MAGNET = "lead_magnet"
    GENERIC = "generic"


class PageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GeneratePageRequest(BaseModel):
    page_type: PageType = PageType.GENERIC
    page_goal: str = Field(..., min_length=10)
    target_audience: str = Field(..., min_length=10)
    offer_details: str = Field(..., min_length=10)
    cta_type: str = "signup"
    tone: str = "professional"
    brand_name: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    brand_voice: Optional[str] = None
    affiliate_program_id: Optional[str] = None
    product_id: Optional[str] = None
    product_features: Optional[List[str]] = None
    testimonials: Optional[List[Dict[str, str]]] = None
    additional_context: Optional[str] = None
    ai_model: str = AIModel.GPT_4O.value


class CreatePageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    page_type: PageType = PageType.GENERIC
    page_schema: Dict[str, Any]
    affiliate_program_id: Optional[str] = None
    product_id: Optional[str] = None


class UpdatePageRequest(BaseModel):
    name: Optional[str] = None
    page_schema: Optional[Dict[str, Any]] = None
    status: Optional[PageStatus] = None
    custom_slug: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str = Field(..., min_length=1)
    current_schema: Optional[Dict[str, Any]] = None
    selected_section_index: Optional[int] = None
    page_context: Optional[Dict[str, str]] = None
    ai_model: str = AIModel.GPT_4O.value


class ChatMessageResponse(BaseModel):
    conversation_id: str
    response_text: str
    updated_schema: Optional[Dict[str, Any]] = None
    action: str = "message"
    modified_sections: List[int] = []


class PublicFormSubmissionRequest(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    company_name: Optional[str] = None
    country_region: Optional[str] = None
    notes: Optional[str] = None
    affiliate_ref: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return f"{slug}-{uuid.uuid4().hex[:6]}"


def _page_to_dict(page: LandingPage, *, include_schema: bool) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": page.id,
        "tenant_id": page.tenant_id,
        "name": page.name,
        "slug": page.slug,
        "page_type": page.page_type,
        "status": page.status,
        "version": int(page.version or 1),
        "affiliate_program_id": page.affiliate_program_id,
        "product_id": page.product_id,
        "ai_model_used": page.ai_model_used,
        "custom_slug": page.custom_slug,
        "seo_title": page.seo_title,
        "seo_description": page.seo_description,
        "view_count": int(page.view_count or 0),
        "conversion_count": int(page.conversion_count or 0),
        "created_by": page.created_by,
        "created_at": dt_to_iso(page.created_at),
        "updated_at": dt_to_iso(page.updated_at),
        "published_at": dt_to_iso(page.published_at),
    }
    if include_schema:
        data["page_schema"] = page.page_schema or {}
    return data


def _split_full_name(name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = " ".join((name or "").strip().split())
    if not text:
        return None, None

    parts = text.split(" ")
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


async def _select_round_robin_owner(db: AsyncSession, tenant_id: str) -> Optional[User]:
    users_res = await db.execute(
        select(User)
        .where(
            and_(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                func.lower(User.role).in_(["sales", "manager", "admin", "owner", "super_admin"]),
            )
        )
        .order_by(User.created_at.asc())
    )
    users = users_res.scalars().all()
    if not users:
        return None

    user_ids = [u.id for u in users]
    stats_res = await db.execute(
        select(
            Lead.owner_id,
            func.max(Lead.assigned_at).label("last_assigned_at"),
            func.count(Lead.id).label("assigned_count"),
        )
        .where(
            and_(
                Lead.tenant_id == tenant_id,
                Lead.owner_id.is_not(None),
                Lead.owner_id.in_(user_ids),
            )
        )
        .group_by(Lead.owner_id)
    )
    stats = {
        str(owner_id): {
            "last_assigned_at": last_assigned_at,
            "assigned_count": int(assigned_count or 0),
        }
        for owner_id, last_assigned_at, assigned_count in stats_res.all()
    }

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ranked = sorted(
        users,
        key=lambda u: (
            stats.get(u.id, {}).get("last_assigned_at") or epoch,
            int(stats.get(u.id, {}).get("assigned_count") or 0),
            u.created_at or epoch,
            u.id,
        ),
    )
    return ranked[0] if ranked else None


async def submit_public_landing_form_internal(
    *,
    page: LandingPage,
    slug: str,
    data: PublicFormSubmissionRequest,
    db: AsyncSession,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    email = (data.email or "").strip() or None
    phone = (data.phone or "").strip() or None
    company_name = (data.company_name or data.company or "").strip() or None
    country_region = (data.country_region or "").strip() or None
    if not country_region and isinstance(data.metadata, dict):
        country_region = (str(data.metadata.get("country") or data.metadata.get("country_region") or "").strip() or None)
    provided_first_name = (data.first_name or "").strip() or None
    provided_last_name = (data.last_name or "").strip() or None
    first_name_from_name, last_name_from_name = _split_full_name(data.name)

    first_name = provided_first_name or first_name_from_name
    last_name = provided_last_name or last_name_from_name
    full_name = " ".join([x for x in [first_name, last_name] if x]).strip() or None

    if not email and not phone:
        raise HTTPException(status_code=400, detail="Email or phone is required")
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name is required")
    if not country_region:
        raise HTTPException(status_code=400, detail="Country / region is required")

    now = now_utc()
    owner = await _select_round_robin_owner(db, page.tenant_id)
    owner_id = owner.id if owner else None
    owner_name = (
        f"{(owner.first_name or '').strip()} {(owner.last_name or '').strip()}".strip()
        if owner
        else None
    )

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=page.tenant_id,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name or company_name,
        email=email,
        phone=phone,
        company_name=company_name,
        country_region=country_region,
        source="inbound_form",
        sales_motion_type="partnership_sales",
        partner_id=None,
        product_id=None,
        partner_name=None,
        product_name=None,
        score=0,
        tier="D",
        scoring_data={},
        status="new_assigned" if owner_id else "new",
        owner_id=owner_id,
        assigned_at=now if owner_id else None,
        notes=(data.notes or "").strip() or None,
        touchpoints_count=0,
        last_touchpoint_at=None,
        first_touchpoint_at=None,
        tags=[],
        converted_at=None,
        contact_id=None,
        created_at=now,
        updated_at=now,
    )
    db.add(lead)

    affiliate_ref = (data.affiliate_ref or "").strip() or None
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent", "") if request else ""
    event_meta = {
        "slug": slug,
        "lead_id": lead.id,
        "affiliate_ref": affiliate_ref,
        "utm_source": (data.utm_source or "").strip() or None,
        "utm_medium": (data.utm_medium or "").strip() or None,
        "utm_campaign": (data.utm_campaign or "").strip() or None,
        "utm_content": (data.utm_content or "").strip() or None,
        "utm_term": (data.utm_term or "").strip() or None,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "form_metadata": data.metadata or {},
    }

    lp_event = LandingPageEvent(
        id=str(uuid.uuid4()),
        landing_page_id=page.id,
        tenant_id=page.tenant_id,
        event_type="form_submission",
        affiliate_ref=affiliate_ref,
        ip_address=ip_address,
        user_agent=user_agent,
        meta=event_meta,
        created_at=now,
    )
    db.add(lp_event)

    await db.execute(
        update(LandingPage)
        .where(LandingPage.id == page.id)
        .values(conversion_count=int(page.conversion_count or 0) + 1, updated_at=now)
    )

    lead_label = (
        lead.full_name
        or lead.company_name
        or lead.email
        or lead.phone
        or "Website visitor"
    )
    page_label = page.name or page.slug
    await create_timeline_event(
        db=db,
        tenant_id=page.tenant_id,
        event_type="form_submitted",
        title=f"Form submitted on {page_label}",
        description=f"New lead captured: {lead_label}",
        contact_id=None,
        deal_id=None,
        metadata={
            **event_meta,
            "landing_page_id": page.id,
            "landing_page_name": page.name,
        },
    )
    await create_timeline_event(
        db=db,
        tenant_id=page.tenant_id,
        event_type="landing_page_conversion",
        title=f"Landing page conversion: {page_label}",
        description=f"Lead captured: {lead_label}",
        metadata={
            **event_meta,
            "landing_page_id": page.id,
            "landing_page_name": page.name,
            "lead_id": lead.id,
        },
    )

    if owner_id:
        await create_timeline_event(
            db=db,
            tenant_id=page.tenant_id,
            event_type="lead_assigned",
            title=f"Lead assigned: {lead_label}",
            description=f"Assigned to {owner_name or owner_id}",
            metadata={
                "lead_id": lead.id,
                "source": "landing_page_form",
                "landing_page_id": page.id,
                "assigned_to_user_id": owner_id,
                "assigned_to_user_name": owner_name,
            },
        )

    await db.flush()

    page.conversion_count = int(page.conversion_count or 0) + 1
    page.updated_at = now

    return {
        "success": True,
        "lead_id": lead.id,
        "page_id": page.id,
        "page_slug": page.slug,
        "conversion_count": int(page.conversion_count or 0),
        "assigned_owner_id": owner_id,
        "assigned_owner_name": owner_name,
        "message": "Lead captured successfully",
    }


@router.post("/generate")
async def generate_landing_page(
    data: GeneratePageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ai_service = get_ai_service(model=data.ai_model)
    try:
        page_schema = await ai_service.generate_landing_page(
            page_goal=data.page_goal,
            target_audience=data.target_audience,
            offer_details=data.offer_details,
            cta_type=data.cta_type,
            tone=data.tone,
            brand_name=data.brand_name,
            brand_colors=data.brand_colors,
            brand_voice=data.brand_voice,
            affiliate_program=None,  # optional enrichment not required for frontend compatibility
            product_features=data.product_features,
            testimonials=data.testimonials,
            additional_context=data.additional_context,
        )

        gen_log = LandingPageGeneration(
            id=str(uuid.uuid4()),
            tenant_id=user["tenant_id"],
            user_id=user["id"],
            ai_model=data.ai_model,
            prompt_data=data.model_dump(),
            success=True,
            error=None,
            created_at=now_utc(),
        )
        db.add(gen_log)
        await db.flush()

        return {"success": True, "page_schema": page_schema.model_dump(), "ai_model": data.ai_model}
    except ValueError as e:
        gen_log = LandingPageGeneration(
            id=str(uuid.uuid4()),
            tenant_id=user["tenant_id"],
            user_id=user["id"],
            ai_model=data.ai_model,
            prompt_data=data.model_dump(),
            success=False,
            error=str(e),
            created_at=now_utc(),
        )
        db.add(gen_log)
        await db.flush()
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        gen_log = LandingPageGeneration(
            id=str(uuid.uuid4()),
            tenant_id=user["tenant_id"],
            user_id=user["id"],
            ai_model=data.ai_model,
            prompt_data=data.model_dump(),
            success=False,
            error=str(e),
            created_at=now_utc(),
        )
        db.add(gen_log)
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Failed to generate page: {str(e)}")


@router.post("/chat", response_model=ChatMessageResponse)
async def chat_with_builder(
    data: ChatMessageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ai_service = get_ai_service(model=data.ai_model)

    res = await db.execute(
        select(LandingPageConversation).where(
            and_(
                LandingPageConversation.tenant_id == user["tenant_id"],
                LandingPageConversation.conversation_id == data.conversation_id,
            )
        )
    )
    conversation = res.scalar_one_or_none()
    if not conversation:
        conversation = LandingPageConversation(
            id=str(uuid.uuid4()),
            conversation_id=data.conversation_id,
            tenant_id=user["tenant_id"],
            user_id=user["id"],
            messages=[],
            current_schema=data.current_schema,
            page_context=data.page_context,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        db.add(conversation)
        await db.flush()

    user_msg = {"role": "user", "content": data.message, "timestamp": now_utc().isoformat()}

    try:
        result = await ai_service.chat_with_context(
            conversation_history=list(conversation.messages or []),
            current_schema=data.current_schema,
            user_message=data.message,
            selected_section_index=data.selected_section_index,
            page_context=data.page_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")

    assistant_msg = {
        "role": "assistant",
        "content": result["response_text"],
        "timestamp": now_utc().isoformat(),
        "had_schema_update": result.get("updated_schema") is not None,
    }

    updated_messages = list(conversation.messages or [])
    updated_messages.extend([user_msg, assistant_msg])

    conversation.messages = updated_messages
    conversation.current_schema = result.get("updated_schema") or data.current_schema
    conversation.page_context = data.page_context
    conversation.updated_at = now_utc()

    await db.flush()

    return ChatMessageResponse(
        conversation_id=data.conversation_id,
        response_text=result["response_text"],
        updated_schema=result.get("updated_schema"),
        action=result.get("action") or "message",
        modified_sections=list(result.get("modified_sections") or []),
    )


@router.get("/chat/{conversation_id}/history")
async def get_chat_history(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPageConversation).where(
            and_(
                LandingPageConversation.tenant_id == user["tenant_id"],
                LandingPageConversation.conversation_id == conversation_id,
            )
        )
    )
    conversation = res.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation_id": conversation_id,
        "messages": list(conversation.messages or []),
        "current_schema": conversation.current_schema,
        "page_context": conversation.page_context,
    }


@router.delete("/chat/{conversation_id}")
async def delete_chat(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPageConversation).where(
            and_(
                LandingPageConversation.tenant_id == user["tenant_id"],
                LandingPageConversation.conversation_id == conversation_id,
            )
        )
    )
    conversation = res.scalar_one_or_none()
    if conversation:
        await db.delete(conversation)
    return {"success": True}


@router.post("", status_code=201)
async def create_landing_page(
    data: CreatePageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    slug = _generate_slug(data.name)

    page = LandingPage(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        slug=slug,
        page_type=data.page_type.value,
        page_schema=data.page_schema,
        status=PageStatus.DRAFT.value,
        version=1,
        affiliate_program_id=data.affiliate_program_id,
        product_id=data.product_id,
        ai_model_used=(data.page_schema or {}).get("ai_model"),
        seo_title=(data.page_schema or {}).get("page_title"),
        seo_description=(data.page_schema or {}).get("meta_description"),
        view_count=0,
        conversion_count=0,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
        published_at=None,
        deleted_at=None,
    )
    db.add(page)
    await db.flush()

    version = LandingPageVersion(
        id=str(uuid.uuid4()),
        landing_page_id=page.id,
        version_number=1,
        page_schema=data.page_schema,
        created_by=user["id"],
        created_at=now,
    )
    db.add(version)
    await db.flush()

    return _page_to_dict(page, include_schema=True)


@router.get("")
async def list_landing_pages(
    page_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    include_schema: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = [LandingPage.tenant_id == user["tenant_id"]]
    if page_type:
        where.append(LandingPage.page_type == page_type)
    if status:
        where.append(LandingPage.status == status)
    if search:
        like = f"%{search.strip()}%"
        where.append(or_(LandingPage.name.ilike(like), LandingPage.slug.ilike(like)))

    total_res = await db.execute(select(func.count(LandingPage.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(LandingPage)
        .where(and_(*where))
        .order_by(LandingPage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    pages = res.scalars().all()

    return {
        "pages": [_page_to_dict(p, include_schema=include_schema) for p in pages],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{page_id}")
async def get_landing_page(
    page_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPage).where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
    )
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return _page_to_dict(page, include_schema=True)


@router.put("/{page_id}")
async def update_landing_page(
    page_id: str,
    data: UpdatePageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPage).where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
    )
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    now = now_utc()

    if "status" in update_data:
        update_data["status"] = update_data["status"].value
        if update_data["status"] == PageStatus.PUBLISHED.value:
            update_data["published_at"] = now

    if "page_schema" in update_data:
        new_version = int(page.version or 1) + 1
        update_data["version"] = new_version
        version = LandingPageVersion(
            id=str(uuid.uuid4()),
            landing_page_id=page_id,
            version_number=new_version,
            page_schema=update_data["page_schema"],
            created_by=user["id"],
            created_at=now,
        )
        db.add(version)

    update_data["updated_at"] = now

    await db.execute(
        update(LandingPage)
        .where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
        .values(**update_data)
    )
    return {"success": True}


@router.delete("/{page_id}")
async def delete_landing_page(
    page_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    result = await db.execute(
        update(LandingPage)
        .where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
        .values(status=PageStatus.ARCHIVED.value, deleted_at=now, updated_at=now)
    )
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"success": True}


@router.post("/{page_id}/publish")
async def publish_landing_page(
    page_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    result = await db.execute(
        update(LandingPage)
        .where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
        .values(status=PageStatus.PUBLISHED.value, published_at=now, updated_at=now)
    )
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Page not found")

    res = await db.execute(select(LandingPage).where(LandingPage.id == page_id))
    page = res.scalar_one()
    return {"success": True, "slug": page.slug, "url": f"/pages/{page.slug}"}


@router.post("/{page_id}/unpublish")
async def unpublish_landing_page(
    page_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    result = await db.execute(
        update(LandingPage)
        .where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
        .values(status=PageStatus.DRAFT.value, updated_at=now)
    )
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"success": True}


@router.get("/{page_id}/versions")
async def list_page_versions(
    page_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify page exists for tenant
    res = await db.execute(
        select(LandingPage.id).where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Page not found")

    versions_res = await db.execute(
        select(LandingPageVersion)
        .where(LandingPageVersion.landing_page_id == page_id)
        .order_by(LandingPageVersion.version_number.desc())
        .limit(50)
    )
    versions = versions_res.scalars().all()
    return {
        "versions": [
            {
                "id": v.id,
                "landing_page_id": v.landing_page_id,
                "version_number": int(v.version_number),
                "created_by": v.created_by,
                "created_at": dt_to_iso(v.created_at),
            }
            for v in versions
        ]
    }


@router.post("/{page_id}/rollback/{version_number}")
async def rollback_to_version(
    page_id: str,
    version_number: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ver_res = await db.execute(
        select(LandingPageVersion).where(
            and_(
                LandingPageVersion.landing_page_id == page_id,
                LandingPageVersion.version_number == version_number,
            )
        )
    )
    version = ver_res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    now = now_utc()
    result = await db.execute(
        update(LandingPage)
        .where(and_(LandingPage.id == page_id, LandingPage.tenant_id == user["tenant_id"]))
        .values(page_schema=version.page_schema, version=version_number, updated_at=now)
    )
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"success": True}


@router.post("/public/{slug}/submit", status_code=201)
async def submit_public_page_form(
    slug: str,
    data: PublicFormSubmissionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPage).where(and_(LandingPage.slug == slug, LandingPage.status == PageStatus.PUBLISHED.value))
    )
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    payload = await submit_public_landing_form_internal(
        page=page,
        slug=slug,
        data=data,
        db=db,
        request=request,
    )
    return payload


@router.get("/public/{slug}")
async def get_public_page(
    slug: str,
    ref: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LandingPage).where(and_(LandingPage.slug == slug, LandingPage.status == PageStatus.PUBLISHED.value))
    )
    page = res.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    now = now_utc()
    event = LandingPageEvent(
        id=str(uuid.uuid4()),
        landing_page_id=page.id,
        tenant_id=page.tenant_id,
        event_type="page_view",
        affiliate_ref=ref,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        meta={},
        created_at=now,
    )
    db.add(event)

    await db.execute(
        update(LandingPage).where(LandingPage.id == page.id).values(view_count=(page.view_count or 0) + 1, updated_at=now)
    )
    await db.flush()

    # Refresh view_count for response
    page.view_count = int(page.view_count or 0) + 1
    page.updated_at = now

    await create_timeline_event(
        db=db,
        tenant_id=page.tenant_id,
        event_type="landing_page_view",
        title=f"Landing page viewed: {page.name or page.slug}",
        metadata={
            "landing_page_id": page.id,
            "landing_page_name": page.name,
            "slug": page.slug,
            "affiliate_ref": ref,
            "ip_address": request.client.host if request and request.client else None,
        },
    )

    tenant_slug_res = await db.execute(select(Tenant.slug).where(Tenant.id == page.tenant_id).limit(1))
    tenant_slug = tenant_slug_res.scalar_one_or_none()

    return {"page": _page_to_dict(page, include_schema=True), "affiliate_ref": ref, "tenant_slug": tenant_slug}

