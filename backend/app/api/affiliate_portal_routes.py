"""
Affiliate Portal API Routes

Secure endpoints for affiliates to:
- Login/authenticate
- View their performance dashboard
- Generate referral links
- Browse/download marketing materials
- Manage their profile
"""

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from jose import jwt
import uuid
import os
import secrets
import hashlib

from app.db.mongodb import get_database
from app.services.storage_service import get_storage

router = APIRouter(prefix="/affiliate-portal", tags=["Affiliate Portal"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
ALGORITHM = "HS256"
AFFILIATE_TOKEN_EXPIRE_HOURS = 24


# ==================== SCHEMAS ====================

class AffiliateLogin(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str = "demo"


class AffiliateRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    company: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    tenant_slug: str = "demo"


class AffiliateProfileUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None


class AffiliateLinkGenerate(BaseModel):
    program_id: str
    landing_page_url: Optional[str] = None
    custom_slug: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_affiliate_token(affiliate_id: str, tenant_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=AFFILIATE_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": affiliate_id,
        "tenant_id": tenant_id,
        "type": "affiliate",
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_affiliate(request: Request):
    """Extract affiliate from portal token"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        affiliate_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not affiliate_id or token_type != "affiliate":
            raise HTTPException(status_code=401, detail="Invalid token")
        
        db = get_database()
        affiliate = await db.affiliates.find_one(
            {"id": affiliate_id},
            {"_id": 0, "password_hash": 0}
        )
        
        if not affiliate:
            raise HTTPException(status_code=401, detail="Affiliate not found")
        
        if affiliate["status"] != "active":
            raise HTTPException(status_code=403, detail="Account not active")
        
        return affiliate
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_referral_code(affiliate_id: str, length: int = 8) -> str:
    """Generate a unique referral code"""
    hash_input = f"{affiliate_id}{secrets.token_hex(4)}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:length].upper()


# ==================== AUTH ENDPOINTS ====================

@router.post("/register", status_code=201)
async def register_affiliate(data: AffiliateRegister):
    """Public affiliate registration"""
    db = get_database()
    
    # Find tenant
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid tenant")
    
    # Check if email already exists
    existing = await db.affiliates.find_one({
        "tenant_id": tenant["id"],
        "email": data.email
    })
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    
    # Create affiliate
    affiliate = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant["id"],
        "name": data.name,
        "email": data.email,
        "password_hash": get_password_hash(data.password),
        "phone": data.phone,
        "company": data.company,
        "website": data.website,
        "status": "pending",  # Requires admin approval
        "payout_method": "manual",
        "payout_details": "{}",
        "notes": None,
        "total_earnings": 0,
        "total_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliates.insert_one(affiliate)
    
    return {
        "success": True,
        "message": "Registration successful! Your account is pending approval. You'll receive an email once approved."
    }


@router.post("/login")
async def login_affiliate(data: AffiliateLogin):
    """Affiliate login"""
    db = get_database()
    
    # Find tenant
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Find affiliate
    affiliate = await db.affiliates.find_one({
        "tenant_id": tenant["id"],
        "email": data.email
    })
    
    if not affiliate or not affiliate.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, affiliate["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if affiliate["status"] == "pending":
        raise HTTPException(status_code=403, detail="Your account is pending approval")
    
    if affiliate["status"] == "banned":
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    
    if affiliate["status"] == "paused":
        raise HTTPException(status_code=403, detail="Your account is paused")
    
    # Create token
    token = create_affiliate_token(affiliate["id"], tenant["id"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "affiliate": {
            "id": affiliate["id"],
            "name": affiliate["name"],
            "email": affiliate["email"],
            "company": affiliate.get("company"),
            "status": affiliate["status"]
        }
    }


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/me")
async def get_affiliate_profile(request: Request):
    """Get current affiliate profile"""
    affiliate = await get_current_affiliate(request)
    return affiliate


@router.put("/me")
async def update_affiliate_profile(
    data: AffiliateProfileUpdate,
    request: Request
):
    """Update affiliate profile"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.affiliates.update_one(
        {"id": affiliate["id"]},
        {"$set": update_data}
    )
    
    return {"success": True}


@router.get("/dashboard")
async def get_affiliate_dashboard(
    days: int = Query(30, ge=1, le=365),
    request: Request = None
):
    """Get affiliate dashboard stats"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    start_str = start_date.isoformat()
    
    # Get links
    links = await db.affiliate_links.find(
        {"affiliate_id": affiliate["id"], "is_active": True},
        {"_id": 0}
    ).to_list(length=100)
    
    # Calculate stats
    total_clicks = sum(l.get("click_count", 0) for l in links)
    total_conversions = sum(l.get("conversion_count", 0) for l in links)
    
    # Commission stats
    commission_pipeline = [
        {"$match": {"affiliate_id": affiliate["id"]}},
        {"$group": {
            "_id": "$status",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    commission_stats = await db.affiliate_commissions.aggregate(commission_pipeline).to_list(length=10)
    commissions_by_status = {s["_id"]: {"total": s["total"], "count": s["count"]} for s in commission_stats}
    
    # Recent clicks (from events)
    recent_clicks_pipeline = [
        {"$match": {
            "affiliate_id": affiliate["id"],
            "event_type": "affiliate_link_clicked",
            "created_at": {"$gte": start_str}
        }},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 30}
    ]
    click_history = await db.affiliate_events.aggregate(recent_clicks_pipeline).to_list(length=30)
    
    # Programs affiliate is part of
    program_ids = list(set(l.get("program_id") for l in links if l.get("program_id")))
    programs = []
    if program_ids:
        cursor = db.affiliate_programs.find(
            {"id": {"$in": program_ids}, "is_active": True},
            {"_id": 0, "id": 1, "name": 1, "commission_type": 1, "commission_value": 1, "journey_type": 1}
        )
        programs = await cursor.to_list(length=20)
    
    return {
        "affiliate": {
            "id": affiliate["id"],
            "name": affiliate["name"],
            "email": affiliate["email"],
            "total_earnings": affiliate.get("total_earnings", 0),
            "total_paid": affiliate.get("total_paid", 0)
        },
        "stats": {
            "total_links": len(links),
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round((total_conversions / total_clicks * 100), 2) if total_clicks > 0 else 0
        },
        "commissions": commissions_by_status,
        "pending_payout": commissions_by_status.get("approved", {}).get("total", 0),
        "click_history": [{"date": c["_id"], "clicks": c["count"]} for c in click_history],
        "programs": programs,
        "period_days": days
    }


# ==================== LINKS ENDPOINTS ====================

@router.get("/links")
async def get_affiliate_links(request: Request):
    """Get affiliate's referral links"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    cursor = db.affiliate_links.find(
        {"affiliate_id": affiliate["id"]},
        {"_id": 0}
    ).sort("created_at", -1)
    links = await cursor.to_list(length=100)
    
    # Enrich with program info
    for link in links:
        program = await db.affiliate_programs.find_one(
            {"id": link["program_id"]},
            {"_id": 0, "name": 1, "commission_type": 1, "commission_value": 1}
        )
        link["program"] = program
        
        # Build full URL
        base_url = link.get("landing_page_url") or f"/ref/{link['referral_code']}"
        link["full_url"] = f"{base_url}?ref={link['referral_code']}"
    
    return {"links": links}


@router.post("/links", status_code=201)
async def generate_affiliate_link(
    data: AffiliateLinkGenerate,
    request: Request
):
    """Generate a new referral link"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    # Verify program exists and is active
    program = await db.affiliate_programs.find_one(
        {"id": data.program_id, "tenant_id": affiliate["tenant_id"], "is_active": True},
        {"_id": 0}
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found or inactive")
    
    # Generate referral code
    referral_code = data.custom_slug or generate_referral_code(affiliate["id"])
    
    # Check if code already exists
    existing = await db.affiliate_links.find_one({"referral_code": referral_code})
    if existing:
        if data.custom_slug:
            raise HTTPException(status_code=400, detail="This slug is already taken")
        referral_code = generate_referral_code(affiliate["id"], 10)
    
    link = {
        "id": str(uuid.uuid4()),
        "tenant_id": affiliate["tenant_id"],
        "affiliate_id": affiliate["id"],
        "program_id": data.program_id,
        "referral_code": referral_code,
        "landing_page_url": data.landing_page_url,
        "utm_source": "affiliate",
        "utm_medium": "referral",
        "utm_campaign": program["name"].lower().replace(" ", "_"),
        "click_count": 0,
        "conversion_count": 0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliate_links.insert_one(link)
    
    # Build full URL
    base_url = data.landing_page_url or f"/ref/{referral_code}"
    link["full_url"] = f"{base_url}?ref={referral_code}"
    link["program"] = {"name": program["name"], "commission_type": program["commission_type"], "commission_value": program["commission_value"]}
    
    return {k: v for k, v in link.items() if k != "_id"}


# ==================== PROGRAMS ENDPOINTS ====================

@router.get("/programs")
async def get_available_programs(request: Request):
    """Get programs available to affiliate"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    cursor = db.affiliate_programs.find(
        {"tenant_id": affiliate["tenant_id"], "is_active": True},
        {"_id": 0}
    ).sort("created_at", -1)
    programs = await cursor.to_list(length=50)
    
    # Check if affiliate has links for each program
    for prog in programs:
        link_count = await db.affiliate_links.count_documents({
            "affiliate_id": affiliate["id"],
            "program_id": prog["id"]
        })
        prog["has_link"] = link_count > 0
    
    return {"programs": programs}


# ==================== COMMISSIONS ENDPOINTS ====================

@router.get("/commissions")
async def get_affiliate_commissions(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """Get affiliate's commissions"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    query = {"affiliate_id": affiliate["id"]}
    if status:
        query["status"] = status
    
    total = await db.affiliate_commissions.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.affiliate_commissions.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    commissions = await cursor.to_list(length=page_size)
    
    # Enrich with program names
    for comm in commissions:
        program = await db.affiliate_programs.find_one(
            {"id": comm["program_id"]},
            {"_id": 0, "name": 1}
        )
        comm["program_name"] = program["name"] if program else "Unknown"
    
    return {
        "commissions": commissions,
        "total": total,
        "page": page,
        "page_size": page_size
    }


# ==================== MATERIALS ENDPOINTS ====================

@router.get("/materials")
async def get_affiliate_materials(
    category: Optional[str] = None,
    program_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """Get marketing materials available to affiliate"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    storage = get_storage()
    
    query = {"tenant_id": affiliate["tenant_id"], "is_active": True}
    if category:
        query["category"] = category
    if program_id:
        query["$or"] = [{"program_id": program_id}, {"program_id": None}]
    
    total = await db.marketing_materials.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.marketing_materials.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    materials = await cursor.to_list(length=page_size)
    
    # Add URLs for files
    for mat in materials:
        if mat.get("file_path"):
            mat["file_url"] = await storage.get_url(mat["file_path"])
        else:
            mat["file_url"] = mat.get("url")
    
    return {
        "materials": materials,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/materials/categories")
async def get_material_categories(request: Request):
    """Get material categories with counts"""
    affiliate = await get_current_affiliate(request)
    db = get_database()
    
    pipeline = [
        {"$match": {"tenant_id": affiliate["tenant_id"], "is_active": True}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.marketing_materials.aggregate(pipeline).to_list(length=20)
    
    return {"categories": [{"category": r["_id"], "count": r["count"]} for r in results]}


# ==================== PUBLIC TRACKING ENDPOINT ====================

@router.get("/ref/{referral_code}")
async def track_and_redirect(
    referral_code: str,
    request: Request,
    response: Response
):
    """Track affiliate link click and redirect (PUBLIC - no auth)"""
    db = get_database()
    
    link = await db.affiliate_links.find_one(
        {"referral_code": referral_code, "is_active": True},
        {"_id": 0}
    )
    
    if not link:
        raise HTTPException(status_code=404, detail="Invalid referral link")
    
    # Get program for cookie duration
    program = await db.affiliate_programs.find_one(
        {"id": link["program_id"]},
        {"_id": 0, "cookie_duration_days": 1, "attribution_model": 1}
    )
    cookie_days = program.get("cookie_duration_days", 30) if program else 30
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Log click event
    event = {
        "id": str(uuid.uuid4()),
        "tenant_id": link["tenant_id"],
        "event_type": "affiliate_link_clicked",
        "affiliate_id": link["affiliate_id"],
        "link_id": link["id"],
        "program_id": link["program_id"],
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": {
            "referral_code": referral_code,
            "referer": request.headers.get("referer", "")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.affiliate_events.insert_one(event)
    
    # Increment click count
    await db.affiliate_links.update_one(
        {"id": link["id"]},
        {"$inc": {"click_count": 1}}
    )
    
    # Set attribution cookie
    redirect_url = link.get("landing_page_url") or "/"
    if "?" in redirect_url:
        redirect_url += f"&ref={referral_code}"
    else:
        redirect_url += f"?ref={referral_code}"
    
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="_aff_ref",
        value=referral_code,
        max_age=cookie_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    
    return response
