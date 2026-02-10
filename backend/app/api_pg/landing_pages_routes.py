from __future__ import annotations

import re
import uuid
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc, parse_iso_datetime
from app.core.database import get_db
from app.pg_models.models import (
    LandingPage,
    LandingPageConversation,
    LandingPageEvent,
    LandingPageGeneration,
    LandingPageVersion,
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
        "pages": [_page_to_dict(p, include_schema=False) for p in pages],
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
        metadata={},
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

    return {"page": _page_to_dict(page, include_schema=True), "affiliate_ref": ref}

