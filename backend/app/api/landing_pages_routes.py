"""
Landing Page Builder API Routes

Handles all landing page operations:
- AI-powered page generation
- Page CRUD operations
- Version management
- Publishing/deployment
- Analytics
"""

from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import json

from app.db.mongodb import get_database
from app.services.ai_service import get_ai_service, LandingPageSchema, LandingPageSection, AIModel

router = APIRouter(prefix="/landing-pages", tags=["Landing Pages"])


# ==================== ENUMS ====================

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


# ==================== SCHEMAS ====================

class GeneratePageRequest(BaseModel):
    page_type: PageType = PageType.GENERIC
    page_goal: str = Field(..., min_length=10)
    target_audience: str = Field(..., min_length=10)
    offer_details: str = Field(..., min_length=10)
    cta_type: str = "signup"  # signup, book_demo, checkout, download
    tone: str = "professional"  # professional, bold, friendly, premium
    # Brand
    brand_name: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    brand_voice: Optional[str] = None
    # Context
    affiliate_program_id: Optional[str] = None
    product_id: Optional[str] = None
    product_features: Optional[List[str]] = None
    testimonials: Optional[List[Dict[str, str]]] = None
    additional_context: Optional[str] = None
    # AI
    ai_model: str = "gpt-4o"


class CreatePageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    page_type: PageType = PageType.GENERIC
    page_schema: Dict[str, Any]  # The generated or manually created schema
    affiliate_program_id: Optional[str] = None
    product_id: Optional[str] = None


class UpdatePageRequest(BaseModel):
    name: Optional[str] = None
    page_schema: Optional[Dict[str, Any]] = None
    status: Optional[PageStatus] = None
    custom_slug: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class RewriteSectionRequest(BaseModel):
    section_index: int
    instruction: str = Field(..., min_length=10)
    tone: str = "professional"


# ==================== HELPER FUNCTIONS ====================

async def get_current_user_from_token(request: Request):
    """Extract user from request"""
    from jose import jwt
    import os
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    try:
        SECRET_KEY = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        db = get_database()
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug"""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return f"{slug}-{uuid.uuid4().hex[:6]}"


# ==================== AI GENERATION ENDPOINTS ====================

@router.post("/generate")
async def generate_landing_page(
    data: GeneratePageRequest,
    request: Request
):
    """Generate a landing page using AI"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Get affiliate program details if provided
    affiliate_program = None
    if data.affiliate_program_id:
        affiliate_program = await db.affiliate_programs.find_one(
            {"id": data.affiliate_program_id, "tenant_id": user["tenant_id"]},
            {"_id": 0}
        )
    
    # Get AI service
    ai_service = get_ai_service(provider="openai", model=data.ai_model)
    
    try:
        # Generate page
        page_schema = await ai_service.generate_landing_page(
            page_goal=data.page_goal,
            target_audience=data.target_audience,
            offer_details=data.offer_details,
            cta_type=data.cta_type,
            tone=data.tone,
            brand_name=data.brand_name,
            brand_colors=data.brand_colors,
            brand_voice=data.brand_voice,
            affiliate_program=affiliate_program,
            product_features=data.product_features,
            testimonials=data.testimonials,
            additional_context=data.additional_context
        )
        
        # Log generation
        generation_log = {
            "id": str(uuid.uuid4()),
            "tenant_id": user["tenant_id"],
            "user_id": user["id"],
            "ai_model": data.ai_model,
            "prompt_data": data.dict(),
            "success": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.landing_page_generations.insert_one(generation_log)
        
        return {
            "success": True,
            "page_schema": page_schema.dict(),
            "ai_model": data.ai_model
        }
        
    except Exception as e:
        # Log error
        generation_log = {
            "id": str(uuid.uuid4()),
            "tenant_id": user["tenant_id"],
            "user_id": user["id"],
            "ai_model": data.ai_model,
            "prompt_data": data.dict(),
            "success": False,
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.landing_page_generations.insert_one(generation_log)
        
        raise HTTPException(status_code=500, detail=f"Failed to generate page: {str(e)}")


@router.post("/{page_id}/rewrite-section")
async def rewrite_page_section(
    page_id: str,
    data: RewriteSectionRequest,
    request: Request
):
    """Rewrite a specific section using Claude"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    sections = page.get("page_schema", {}).get("sections", [])
    if data.section_index >= len(sections):
        raise HTTPException(status_code=400, detail="Invalid section index")
    
    original_section = LandingPageSection(**sections[data.section_index])
    
    ai_service = get_ai_service(provider="anthropic", model=AIModel.CLAUDE_SONNET_4.value)
    
    try:
        new_section = await ai_service.rewrite_section(
            section=original_section,
            instruction=data.instruction,
            tone=data.tone
        )
        
        return {
            "success": True,
            "original_section": original_section.dict(),
            "new_section": new_section.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rewrite section: {str(e)}")


@router.post("/{page_id}/generate-variants")
async def generate_page_variants(
    page_id: str,
    num_variants: int = Query(3, ge=1, le=5),
    request: Request = None
):
    """Generate A/B test variants for hero section"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    page_schema = LandingPageSchema(**page.get("page_schema", {}))
    
    ai_service = get_ai_service(provider="anthropic", model=AIModel.CLAUDE_SONNET_4.value)
    
    try:
        variants = await ai_service.generate_variants(page_schema, num_variants)
        return {
            "success": True,
            "variants": [v.dict() for v in variants]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate variants: {str(e)}")


# ==================== CRUD ENDPOINTS ====================

@router.post("", status_code=201)
async def create_landing_page(
    data: CreatePageRequest,
    request: Request
):
    """Create a new landing page from generated or custom schema"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "slug": generate_slug(data.name),
        "page_type": data.page_type.value,
        "page_schema": data.page_schema,
        "status": PageStatus.DRAFT.value,
        "version": 1,
        "affiliate_program_id": data.affiliate_program_id,
        "product_id": data.product_id,
        "ai_model_used": data.page_schema.get("ai_model"),
        "seo_title": data.page_schema.get("page_title"),
        "seo_description": data.page_schema.get("meta_description"),
        "view_count": 0,
        "conversion_count": 0,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "published_at": None
    }
    
    await db.landing_pages.insert_one(page)
    
    # Create initial version
    version = {
        "id": str(uuid.uuid4()),
        "landing_page_id": page["id"],
        "version_number": 1,
        "page_schema": data.page_schema,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.landing_page_versions.insert_one(version)
    
    return {k: v for k, v in page.items() if k != "_id"}


@router.get("")
async def list_landing_pages(
    page_type: Optional[PageType] = None,
    status: Optional[PageStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """List all landing pages"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if page_type:
        query["page_type"] = page_type.value
    if status:
        query["status"] = status.value
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"slug": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.landing_pages.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.landing_pages.find(query, {"_id": 0, "page_schema": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    pages = await cursor.to_list(length=page_size)
    
    return {
        "pages": pages,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{page_id}")
async def get_landing_page(
    page_id: str,
    request: Request
):
    """Get a specific landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return page


@router.put("/{page_id}")
async def update_landing_page(
    page_id: str,
    data: UpdatePageRequest,
    request: Request
):
    """Update a landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
        if update_data["status"] == PageStatus.PUBLISHED.value:
            update_data["published_at"] = datetime.now(timezone.utc).isoformat()
    
    # If schema is being updated, create new version
    if "page_schema" in update_data:
        new_version = page.get("version", 1) + 1
        update_data["version"] = new_version
        
        version = {
            "id": str(uuid.uuid4()),
            "landing_page_id": page_id,
            "version_number": new_version,
            "page_schema": update_data["page_schema"],
            "created_by": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.landing_page_versions.insert_one(version)
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.landing_pages.update_one(
        {"id": page_id},
        {"$set": update_data}
    )
    
    return {"success": True}


@router.delete("/{page_id}")
async def delete_landing_page(
    page_id: str,
    request: Request
):
    """Delete a landing page (soft delete)"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    result = await db.landing_pages.update_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "status": PageStatus.ARCHIVED.value,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {"success": True}


# ==================== PUBLISHING ENDPOINTS ====================

@router.post("/{page_id}/publish")
async def publish_landing_page(
    page_id: str,
    request: Request
):
    """Publish a landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    result = await db.landing_pages.update_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "status": PageStatus.PUBLISHED.value,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Get updated page
    page = await db.landing_pages.find_one({"id": page_id}, {"_id": 0})
    
    return {
        "success": True,
        "slug": page["slug"],
        "url": f"/pages/{page['slug']}"
    }


@router.post("/{page_id}/unpublish")
async def unpublish_landing_page(
    page_id: str,
    request: Request
):
    """Unpublish a landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    result = await db.landing_pages.update_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "status": PageStatus.DRAFT.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {"success": True}


# ==================== VERSION ENDPOINTS ====================

@router.get("/{page_id}/versions")
async def list_page_versions(
    page_id: str,
    request: Request
):
    """List all versions of a landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Verify page exists and belongs to user
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"_id": 0, "id": 1}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    cursor = db.landing_page_versions.find(
        {"landing_page_id": page_id},
        {"_id": 0, "page_schema": 0}
    ).sort("version_number", -1)
    versions = await cursor.to_list(length=50)
    
    return {"versions": versions}


@router.post("/{page_id}/rollback/{version_number}")
async def rollback_to_version(
    page_id: str,
    version_number: int,
    request: Request
):
    """Rollback to a previous version"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Get version
    version = await db.landing_page_versions.find_one(
        {"landing_page_id": page_id, "version_number": version_number},
        {"_id": 0}
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Update page with version schema
    result = await db.landing_pages.update_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "page_schema": version["page_schema"],
            "version": version_number,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {"success": True, "rolled_back_to_version": version_number}


# ==================== ANALYTICS ENDPOINTS ====================

@router.get("/{page_id}/analytics")
async def get_page_analytics(
    page_id: str,
    days: int = Query(30, ge=1, le=365),
    request: Request = None
):
    """Get analytics for a landing page"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"id": page_id, "tenant_id": user["tenant_id"]},
        {"_id": 0, "id": 1, "name": 1, "view_count": 1, "conversion_count": 1}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Get view events
    from datetime import timedelta
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    views_pipeline = [
        {"$match": {
            "landing_page_id": page_id,
            "event_type": "page_view",
            "created_at": {"$gte": start_date.isoformat()}
        }},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "views": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    views_data = await db.landing_page_events.aggregate(views_pipeline).to_list(length=days)
    
    conversion_rate = 0
    if page.get("view_count", 0) > 0:
        conversion_rate = round(page.get("conversion_count", 0) / page["view_count"] * 100, 2)
    
    return {
        "page_id": page_id,
        "name": page["name"],
        "total_views": page.get("view_count", 0),
        "total_conversions": page.get("conversion_count", 0),
        "conversion_rate": conversion_rate,
        "views_by_day": [{"date": v["_id"], "views": v["views"]} for v in views_data],
        "period_days": days
    }


# ==================== PUBLIC PAGE RENDERING ====================

@router.get("/public/{slug}")
async def get_public_page(
    slug: str,
    ref: Optional[str] = None,  # Affiliate referral code
    request: Request = None
):
    """Get a public landing page by slug (no auth required)"""
    db = get_database()
    
    page = await db.landing_pages.find_one(
        {"slug": slug, "status": PageStatus.PUBLISHED.value},
        {"_id": 0}
    )
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Log view event
    event = {
        "id": str(uuid.uuid4()),
        "landing_page_id": page["id"],
        "tenant_id": page["tenant_id"],
        "event_type": "page_view",
        "affiliate_ref": ref,
        "ip_address": request.client.host if request and request.client else None,
        "user_agent": request.headers.get("user-agent", "") if request else "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.landing_page_events.insert_one(event)
    
    # Increment view count
    await db.landing_pages.update_one(
        {"id": page["id"]},
        {"$inc": {"view_count": 1}}
    )
    
    return {
        "page": page,
        "affiliate_ref": ref
    }
