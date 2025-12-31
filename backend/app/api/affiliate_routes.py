"""
Affiliate System API Routes

Handles all affiliate-related operations:
- Affiliate management
- Program configuration
- Link generation & tracking
- Commission ledger
- Attribution engine
- Event logging
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid
import json
import hashlib
import secrets

from app.db.mongodb import get_database

router = APIRouter(prefix="/affiliates", tags=["Affiliates"])


# ==================== ENUMS ====================

class AffiliateStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    BANNED = "banned"


class PayoutMethod(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    WISE = "wise"
    MANUAL = "manual"


class ProductType(str, Enum):
    SERVICE = "service"
    PRODUCT = "product"
    HYBRID = "hybrid"


class JourneyType(str, Enum):
    DEMO_FIRST = "demo_first"
    DIRECT_CHECKOUT = "direct_checkout"


class AttributionType(str, Enum):
    LEAD = "lead"
    DEAL = "deal"
    PAYMENT = "payment"


class CommissionType(str, Enum):
    FLAT = "flat"
    PERCENTAGE = "percentage"


class CommissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    REVERSED = "reversed"


class AffiliateEventType(str, Enum):
    LINK_CLICKED = "affiliate_link_clicked"
    LEAD_CREATED = "affiliate_lead_created"
    DEMO_BOOKED = "affiliate_demo_booked"
    DEAL_CREATED = "affiliate_deal_created"
    DEAL_STAGE_CHANGED = "affiliate_deal_stage_changed"
    PAYMENT_COMPLETED = "affiliate_payment_completed"
    COMMISSION_EARNED = "affiliate_commission_earned"
    COMMISSION_APPROVED = "affiliate_commission_approved"
    COMMISSION_PAID = "affiliate_commission_paid"
    COMMISSION_REVERSED = "affiliate_commission_reversed"


class AttributionModel(str, Enum):
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"


# ==================== SCHEMAS ====================

class AffiliateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    payout_method: PayoutMethod = PayoutMethod.MANUAL
    payout_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class AffiliateUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    status: Optional[AffiliateStatus] = None
    payout_method: Optional[PayoutMethod] = None
    payout_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class AffiliateProgramCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    product_type: ProductType = ProductType.SERVICE
    journey_type: JourneyType = JourneyType.DEMO_FIRST
    attribution_type: AttributionType = AttributionType.DEAL
    attribution_model: AttributionModel = AttributionModel.FIRST_TOUCH
    attribution_window_days: int = Field(default=30, ge=1, le=365)
    commission_type: CommissionType = CommissionType.PERCENTAGE
    commission_value: float = Field(..., ge=0)
    min_payout_threshold: float = Field(default=50, ge=0)
    cookie_duration_days: int = Field(default=30, ge=1, le=365)
    pipeline_scope: Optional[str] = None  # Pipeline ID if scoped
    qualifying_stage_id: Optional[str] = None  # Stage that triggers commission
    auto_approve: bool = False
    is_active: bool = True


class AffiliateLinkCreate(BaseModel):
    program_id: str
    landing_page_url: Optional[str] = None
    custom_slug: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class CommissionCreate(BaseModel):
    affiliate_id: str
    program_id: str
    deal_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount: float
    notes: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def generate_referral_code(affiliate_id: str, length: int = 8) -> str:
    """Generate a unique referral code"""
    hash_input = f"{affiliate_id}{secrets.token_hex(4)}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:length].upper()


async def get_current_user_from_token(request: Request):
    """Extract user from request - simplified for affiliate system"""
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


async def log_affiliate_event(
    db, tenant_id: str, event_type: AffiliateEventType, 
    affiliate_id: str = None, link_id: str = None,
    program_id: str = None, deal_id: str = None,
    contact_id: str = None, commission_id: str = None,
    payment_id: str = None, metadata: dict = None,
    ip_address: str = None, user_agent: str = None
):
    """Log an affiliate event for tracking and attribution"""
    event = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "event_type": event_type.value,
        "affiliate_id": affiliate_id,
        "link_id": link_id,
        "program_id": program_id,
        "deal_id": deal_id,
        "contact_id": contact_id,
        "commission_id": commission_id,
        "payment_id": payment_id,
        "metadata": metadata or {},
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.affiliate_events.insert_one(event)
    return event


async def calculate_commission(
    db, program: dict, deal: dict = None, payment_amount: float = None
) -> float:
    """Calculate commission amount based on program rules"""
    if program["commission_type"] == CommissionType.FLAT.value:
        return program["commission_value"]
    
    # Percentage-based
    if payment_amount is not None:
        base_amount = payment_amount
    elif deal and deal.get("amount"):
        base_amount = deal["amount"]
    else:
        return 0
    
    return round(base_amount * (program["commission_value"] / 100), 2)


async def check_attribution(
    db, tenant_id: str, contact_id: str = None, 
    email: str = None, ip_address: str = None
) -> dict:
    """Check if a contact/visitor has affiliate attribution"""
    # Look for recent click events within attribution window
    window_start = datetime.now(timezone.utc) - timedelta(days=30)
    
    query = {
        "tenant_id": tenant_id,
        "event_type": AffiliateEventType.LINK_CLICKED.value,
        "created_at": {"$gte": window_start.isoformat()}
    }
    
    # Try to match by contact_id first, then email, then IP
    if contact_id:
        query["contact_id"] = contact_id
    elif email:
        query["metadata.email"] = email
    elif ip_address:
        query["ip_address"] = ip_address
    else:
        return None
    
    # Get the attribution event (first or last touch based on program)
    event = await db.affiliate_events.find_one(
        query, {"_id": 0}, sort=[("created_at", 1)]  # First touch
    )
    
    return event


# ==================== AFFILIATE ENDPOINTS ====================

@router.get("")
async def list_affiliates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AffiliateStatus] = None,
    program_id: Optional[str] = None,
    search: Optional[str] = None,
    request: Request = None
):
    """List all affiliates (admin only)"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status.value
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.affiliates.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.affiliates.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    affiliates = await cursor.to_list(length=page_size)
    
    # Enrich with stats
    for aff in affiliates:
        # Get link count
        aff["link_count"] = await db.affiliate_links.count_documents({"affiliate_id": aff["id"]})
        
        # Get commission stats
        pipeline = [
            {"$match": {"affiliate_id": aff["id"]}},
            {"$group": {
                "_id": "$status",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }}
        ]
        stats = await db.affiliate_commissions.aggregate(pipeline).to_list(length=10)
        aff["commission_stats"] = {s["_id"]: {"total": s["total"], "count": s["count"]} for s in stats}
        
        # Get click count
        aff["total_clicks"] = await db.affiliate_events.count_documents({
            "affiliate_id": aff["id"],
            "event_type": AffiliateEventType.LINK_CLICKED.value
        })
    
    return {
        "affiliates": affiliates,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", status_code=201)
async def create_affiliate(
    data: AffiliateCreate,
    request: Request
):
    """Create a new affiliate"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Check if email already exists
    existing = await db.affiliates.find_one({
        "tenant_id": user["tenant_id"],
        "email": data.email
    })
    if existing:
        raise HTTPException(status_code=400, detail="Affiliate with this email already exists")
    
    affiliate = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "company": data.company,
        "website": data.website,
        "status": AffiliateStatus.PENDING.value,
        "payout_method": data.payout_method.value,
        "payout_details": json.dumps(data.payout_details or {}),
        "notes": data.notes,
        "total_earnings": 0,
        "total_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliates.insert_one(affiliate)
    
    # Return clean response without _id and payout_details
    return {
        "id": affiliate["id"],
        "tenant_id": affiliate["tenant_id"],
        "name": affiliate["name"],
        "email": affiliate["email"],
        "phone": affiliate["phone"],
        "company": affiliate["company"],
        "website": affiliate["website"],
        "status": affiliate["status"],
        "payout_method": affiliate["payout_method"],
        "notes": affiliate["notes"],
        "total_earnings": affiliate["total_earnings"],
        "total_paid": affiliate["total_paid"],
        "created_at": affiliate["created_at"],
        "updated_at": affiliate["updated_at"]
    }


# ==================== PROGRAM ENDPOINTS ====================
# NOTE: These routes MUST come before /{affiliate_id} routes to avoid path parameter conflicts

@router.get("/programs")
async def list_programs(
    is_active: Optional[bool] = None,
    journey_type: Optional[JourneyType] = None,
    request: Request = None
):
    """List affiliate programs"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if is_active is not None:
        query["is_active"] = is_active
    if journey_type:
        query["journey_type"] = journey_type.value
    
    cursor = db.affiliate_programs.find(query, {"_id": 0}).sort("created_at", -1)
    programs = await cursor.to_list(length=100)
    
    # Get affiliate count per program
    for prog in programs:
        prog["affiliate_count"] = await db.affiliate_links.distinct(
            "affiliate_id", {"program_id": prog["id"]}
        )
        prog["affiliate_count"] = len(prog["affiliate_count"])
    
    return {"programs": programs}


@router.post("/programs", status_code=201)
async def create_program(
    data: AffiliateProgramCreate,
    request: Request
):
    """Create an affiliate program"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    program = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "description": data.description,
        "product_type": data.product_type.value,
        "journey_type": data.journey_type.value,
        "attribution_type": data.attribution_type.value,
        "attribution_model": data.attribution_model.value,
        "attribution_window_days": data.attribution_window_days,
        "commission_type": data.commission_type.value,
        "commission_value": data.commission_value,
        "min_payout_threshold": data.min_payout_threshold,
        "cookie_duration_days": data.cookie_duration_days,
        "pipeline_scope": data.pipeline_scope,
        "qualifying_stage_id": data.qualifying_stage_id,
        "auto_approve": data.auto_approve,
        "is_active": data.is_active,
        "total_commissions_earned": 0,
        "total_commissions_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliate_programs.insert_one(program)
    
    # Return clean response without MongoDB _id
    program_response = {k: v for k, v in program.items() if k != "_id"}
    return program_response


@router.get("/programs/{program_id}")
async def get_program(
    program_id: str,
    request: Request
):
    """Get program details"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    program = await db.affiliate_programs.find_one(
        {"id": program_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    return program


@router.put("/programs/{program_id}")
async def update_program(
    program_id: str,
    data: dict,
    request: Request
):
    """Update program"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Remove fields that shouldn't be updated
    data.pop("id", None)
    data.pop("tenant_id", None)
    data.pop("created_at", None)
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.affiliate_programs.update_one(
        {"id": program_id, "tenant_id": user["tenant_id"]},
        {"$set": data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    
    return {"success": True}


# ==================== LINK ENDPOINTS ====================

@router.post("/links", status_code=201)
async def create_link(
    data: AffiliateLinkCreate,
    affiliate_id: str = Query(...),
    request: Request = None
):
    """Create an affiliate link"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Verify affiliate exists
    affiliate = await db.affiliates.find_one(
        {"id": affiliate_id, "tenant_id": user["tenant_id"]}
    )
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    # Verify program exists
    program = await db.affiliate_programs.find_one(
        {"id": data.program_id, "tenant_id": user["tenant_id"]}
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Generate referral code
    referral_code = data.custom_slug or generate_referral_code(affiliate_id)
    
    # Check if code already exists
    existing = await db.affiliate_links.find_one({"referral_code": referral_code})
    if existing:
        referral_code = generate_referral_code(affiliate_id, 10)
    
    link = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "affiliate_id": affiliate_id,
        "program_id": data.program_id,
        "referral_code": referral_code,
        "landing_page_url": data.landing_page_url,
        "utm_source": data.utm_source or "affiliate",
        "utm_medium": data.utm_medium or "referral",
        "utm_campaign": data.utm_campaign or program["name"].lower().replace(" ", "_"),
        "click_count": 0,
        "conversion_count": 0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliate_links.insert_one(link)
    
    # Build the full URL
    base_url = data.landing_page_url or f"/ref/{referral_code}"
    link["full_url"] = f"{base_url}?ref={referral_code}&utm_source={link['utm_source']}&utm_medium={link['utm_medium']}&utm_campaign={link['utm_campaign']}"
    
    return link


@router.get("/links")
async def list_links(
    affiliate_id: Optional[str] = None,
    program_id: Optional[str] = None,
    request: Request = None
):
    """List affiliate links"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if affiliate_id:
        query["affiliate_id"] = affiliate_id
    if program_id:
        query["program_id"] = program_id
    
    cursor = db.affiliate_links.find(query, {"_id": 0}).sort("created_at", -1)
    links = await cursor.to_list(length=100)
    
    return {"links": links}


@router.get("/links/track/{referral_code}")
async def track_link_click(
    referral_code: str,
    request: Request
):
    """Track a link click (public endpoint)"""
    db = get_database()
    
    link = await db.affiliate_links.find_one(
        {"referral_code": referral_code, "is_active": True},
        {"_id": 0}
    )
    if not link:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Increment click count
    await db.affiliate_links.update_one(
        {"id": link["id"]},
        {"$inc": {"click_count": 1}}
    )
    
    # Log event
    await log_affiliate_event(
        db, link["tenant_id"], AffiliateEventType.LINK_CLICKED,
        affiliate_id=link["affiliate_id"],
        link_id=link["id"],
        program_id=link["program_id"],
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"referral_code": referral_code}
    )
    
    # Return redirect URL
    return {
        "success": True,
        "redirect_url": link.get("landing_page_url", "/"),
        "referral_code": referral_code
    }


# ==================== COMMISSION ENDPOINTS ====================

@router.get("/commissions")
async def list_commissions(
    affiliate_id: Optional[str] = None,
    program_id: Optional[str] = None,
    status: Optional[CommissionStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """List commissions"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if affiliate_id:
        query["affiliate_id"] = affiliate_id
    if program_id:
        query["program_id"] = program_id
    if status:
        query["status"] = status.value
    
    total = await db.affiliate_commissions.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.affiliate_commissions.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    commissions = await cursor.to_list(length=page_size)
    
    # Enrich with affiliate names
    for comm in commissions:
        affiliate = await db.affiliates.find_one({"id": comm["affiliate_id"]}, {"name": 1})
        comm["affiliate_name"] = affiliate["name"] if affiliate else "Unknown"
    
    # Calculate totals
    totals_pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {
            "_id": "$status",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    totals = await db.affiliate_commissions.aggregate(totals_pipeline).to_list(length=10)
    totals_dict = {t["_id"]: {"total": t["total"], "count": t["count"]} for t in totals}
    
    return {
        "commissions": commissions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "totals": totals_dict
    }


@router.post("/commissions", status_code=201)
async def create_commission(
    data: CommissionCreate,
    request: Request
):
    """Create a commission (manual or from attribution)"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Verify affiliate and program
    affiliate = await db.affiliates.find_one({"id": data.affiliate_id})
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    program = await db.affiliate_programs.find_one({"id": data.program_id})
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    commission = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "affiliate_id": data.affiliate_id,
        "program_id": data.program_id,
        "deal_id": data.deal_id,
        "payment_id": data.payment_id,
        "amount": data.amount,
        "status": CommissionStatus.PENDING.value if not program.get("auto_approve") else CommissionStatus.APPROVED.value,
        "notes": data.notes,
        "earned_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": datetime.now(timezone.utc).isoformat() if program.get("auto_approve") else None,
        "paid_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliate_commissions.insert_one(commission)
    
    # Update affiliate total earnings
    await db.affiliates.update_one(
        {"id": data.affiliate_id},
        {"$inc": {"total_earnings": data.amount}}
    )
    
    # Log event
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.COMMISSION_EARNED,
        affiliate_id=data.affiliate_id,
        program_id=data.program_id,
        commission_id=commission["id"],
        deal_id=data.deal_id,
        metadata={"amount": data.amount}
    )
    
    return commission


@router.post("/commissions/{commission_id}/approve")
async def approve_commission(
    commission_id: str,
    request: Request
):
    """Approve a pending commission"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    commission = await db.affiliate_commissions.find_one(
        {"id": commission_id, "tenant_id": user["tenant_id"]}
    )
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    if commission["status"] != CommissionStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Commission is not pending")
    
    await db.affiliate_commissions.update_one(
        {"id": commission_id},
        {"$set": {
            "status": CommissionStatus.APPROVED.value,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.COMMISSION_APPROVED,
        affiliate_id=commission["affiliate_id"],
        commission_id=commission_id,
        metadata={"amount": commission["amount"]}
    )
    
    return {"success": True, "status": "approved"}


@router.post("/commissions/{commission_id}/pay")
async def mark_commission_paid(
    commission_id: str,
    request: Request
):
    """Mark commission as paid"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    commission = await db.affiliate_commissions.find_one(
        {"id": commission_id, "tenant_id": user["tenant_id"]}
    )
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    if commission["status"] != CommissionStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Commission must be approved first")
    
    await db.affiliate_commissions.update_one(
        {"id": commission_id},
        {"$set": {
            "status": CommissionStatus.PAID.value,
            "paid_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update affiliate total paid
    await db.affiliates.update_one(
        {"id": commission["affiliate_id"]},
        {"$inc": {"total_paid": commission["amount"]}}
    )
    
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.COMMISSION_PAID,
        affiliate_id=commission["affiliate_id"],
        commission_id=commission_id,
        metadata={"amount": commission["amount"]}
    )
    
    return {"success": True, "status": "paid"}


@router.post("/commissions/{commission_id}/reverse")
async def reverse_commission(
    commission_id: str,
    reason: str = Query(...),
    request: Request = None
):
    """Reverse a commission"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    commission = await db.affiliate_commissions.find_one(
        {"id": commission_id, "tenant_id": user["tenant_id"]}
    )
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    if commission["status"] == CommissionStatus.PAID.value:
        raise HTTPException(status_code=400, detail="Cannot reverse paid commission")
    
    await db.affiliate_commissions.update_one(
        {"id": commission_id},
        {"$set": {
            "status": CommissionStatus.REVERSED.value,
            "reversal_reason": reason,
            "reversed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update affiliate total earnings
    await db.affiliates.update_one(
        {"id": commission["affiliate_id"]},
        {"$inc": {"total_earnings": -commission["amount"]}}
    )
    
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.COMMISSION_REVERSED,
        affiliate_id=commission["affiliate_id"],
        commission_id=commission_id,
        metadata={"amount": commission["amount"], "reason": reason}
    )
    
    return {"success": True, "status": "reversed"}


# ==================== ATTRIBUTION ENGINE ====================

@router.post("/attribution/check")
async def check_attribution_endpoint(
    contact_id: Optional[str] = None,
    email: Optional[str] = None,
    request: Request = None
):
    """Check attribution for a contact"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    ip_address = request.client.host if request.client else None
    
    attribution = await check_attribution(
        db, user["tenant_id"],
        contact_id=contact_id,
        email=email,
        ip_address=ip_address
    )
    
    if not attribution:
        return {"has_attribution": False}
    
    # Get affiliate and program details
    affiliate = await db.affiliates.find_one({"id": attribution["affiliate_id"]}, {"_id": 0, "name": 1})
    program = await db.affiliate_programs.find_one({"id": attribution["program_id"]}, {"_id": 0, "name": 1})
    
    return {
        "has_attribution": True,
        "affiliate_id": attribution["affiliate_id"],
        "affiliate_name": affiliate["name"] if affiliate else None,
        "program_id": attribution["program_id"],
        "program_name": program["name"] if program else None,
        "link_id": attribution.get("link_id"),
        "attributed_at": attribution["created_at"]
    }


@router.post("/attribution/attribute-deal")
async def attribute_deal(
    deal_id: str,
    request: Request
):
    """Attribute a deal to an affiliate and create commission"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    # Get deal
    deal = await db.deals.find_one({"id": deal_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Check if deal already has attribution
    existing_commission = await db.affiliate_commissions.find_one({"deal_id": deal_id})
    if existing_commission:
        return {"success": False, "message": "Deal already attributed", "commission_id": existing_commission["id"]}
    
    # Get contact email for attribution check
    contact = await db.contacts.find_one({"id": deal.get("contact_id")}, {"_id": 0, "email": 1})
    email = contact.get("email") if contact else None
    
    # Check attribution
    attribution = await check_attribution(db, user["tenant_id"], email=email)
    if not attribution:
        return {"success": False, "message": "No affiliate attribution found"}
    
    # Get program
    program = await db.affiliate_programs.find_one({"id": attribution["program_id"]}, {"_id": 0})
    if not program or not program.get("is_active"):
        return {"success": False, "message": "Affiliate program not active"}
    
    # Calculate commission
    commission_amount = await calculate_commission(db, program, deal=deal)
    
    # Create commission
    commission = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "affiliate_id": attribution["affiliate_id"],
        "program_id": attribution["program_id"],
        "deal_id": deal_id,
        "amount": commission_amount,
        "status": CommissionStatus.APPROVED.value if program.get("auto_approve") else CommissionStatus.PENDING.value,
        "earned_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": datetime.now(timezone.utc).isoformat() if program.get("auto_approve") else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliate_commissions.insert_one(commission)
    
    # Update affiliate and link stats
    await db.affiliates.update_one(
        {"id": attribution["affiliate_id"]},
        {"$inc": {"total_earnings": commission_amount}}
    )
    
    if attribution.get("link_id"):
        await db.affiliate_links.update_one(
            {"id": attribution["link_id"]},
            {"$inc": {"conversion_count": 1}}
        )
    
    # Log events
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.DEAL_CREATED,
        affiliate_id=attribution["affiliate_id"],
        program_id=attribution["program_id"],
        deal_id=deal_id,
        commission_id=commission["id"],
        metadata={"deal_name": deal.get("name"), "deal_amount": deal.get("amount")}
    )
    
    await log_affiliate_event(
        db, user["tenant_id"], AffiliateEventType.COMMISSION_EARNED,
        affiliate_id=attribution["affiliate_id"],
        program_id=attribution["program_id"],
        commission_id=commission["id"],
        deal_id=deal_id,
        metadata={"amount": commission_amount}
    )
    
    return {
        "success": True,
        "commission_id": commission["id"],
        "commission_amount": commission_amount,
        "affiliate_id": attribution["affiliate_id"]
    }


# ==================== EVENTS & ANALYTICS ====================

@router.get("/events")
async def list_events(
    affiliate_id: Optional[str] = None,
    event_type: Optional[AffiliateEventType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    request: Request = None
):
    """List affiliate events"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if affiliate_id:
        query["affiliate_id"] = affiliate_id
    if event_type:
        query["event_type"] = event_type.value
    
    total = await db.affiliate_events.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.affiliate_events.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    events = await cursor.to_list(length=page_size)
    
    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/analytics/dashboard")
async def get_affiliate_dashboard(
    days: int = Query(30, ge=1, le=365),
    request: Request = None
):
    """Get affiliate analytics dashboard data"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    start_str = start_date.isoformat()
    
    # Total affiliates
    total_affiliates = await db.affiliates.count_documents({"tenant_id": user["tenant_id"]})
    active_affiliates = await db.affiliates.count_documents({
        "tenant_id": user["tenant_id"],
        "status": AffiliateStatus.ACTIVE.value
    })
    
    # Click stats
    total_clicks = await db.affiliate_events.count_documents({
        "tenant_id": user["tenant_id"],
        "event_type": AffiliateEventType.LINK_CLICKED.value,
        "created_at": {"$gte": start_str}
    })
    
    # Commission stats
    commission_pipeline = [
        {"$match": {
            "tenant_id": user["tenant_id"],
            "created_at": {"$gte": start_str}
        }},
        {"$group": {
            "_id": "$status",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    commission_stats = await db.affiliate_commissions.aggregate(commission_pipeline).to_list(length=10)
    commission_by_status = {s["_id"]: {"total": s["total"], "count": s["count"]} for s in commission_stats}
    
    # Top affiliates
    top_affiliates_pipeline = [
        {"$match": {
            "tenant_id": user["tenant_id"],
            "created_at": {"$gte": start_str}
        }},
        {"$group": {
            "_id": "$affiliate_id",
            "total_commissions": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total_commissions": -1}},
        {"$limit": 5}
    ]
    top_affiliates_raw = await db.affiliate_commissions.aggregate(top_affiliates_pipeline).to_list(length=5)
    
    top_affiliates = []
    for ta in top_affiliates_raw:
        affiliate = await db.affiliates.find_one({"id": ta["_id"]}, {"_id": 0, "name": 1, "email": 1})
        if affiliate:
            top_affiliates.append({
                "id": ta["_id"],
                "name": affiliate["name"],
                "email": affiliate["email"],
                "total_commissions": ta["total_commissions"],
                "conversion_count": ta["count"]
            })
    
    # Program stats
    program_stats_pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {
            "_id": "$program_id",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    program_stats_raw = await db.affiliate_commissions.aggregate(program_stats_pipeline).to_list(length=20)
    
    program_stats = []
    for ps in program_stats_raw:
        program = await db.affiliate_programs.find_one({"id": ps["_id"]}, {"_id": 0, "name": 1})
        if program:
            program_stats.append({
                "id": ps["_id"],
                "name": program["name"],
                "total_commissions": ps["total"],
                "conversion_count": ps["count"]
            })
    
    return {
        "period_days": days,
        "affiliates": {
            "total": total_affiliates,
            "active": active_affiliates
        },
        "clicks": total_clicks,
        "commissions": commission_by_status,
        "total_commission_value": sum(s.get("total", 0) for s in commission_by_status.values()),
        "top_affiliates": top_affiliates,
        "program_stats": program_stats
    }


# ==================== PUBLIC SIGNUP ====================

@router.post("/signup", status_code=201)
async def affiliate_signup(
    data: AffiliateCreate,
    program_id: Optional[str] = None,
    tenant_slug: str = Query(default="demo")
):
    """Public affiliate signup endpoint"""
    db = get_database()
    
    # Find tenant
    tenant = await db.tenants.find_one({"slug": tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid tenant")
    
    # Check if email already exists
    existing = await db.affiliates.find_one({
        "tenant_id": tenant["id"],
        "email": data.email
    })
    if existing:
        raise HTTPException(status_code=400, detail="An affiliate with this email already exists")
    
    affiliate = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant["id"],
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "company": data.company,
        "website": data.website,
        "status": AffiliateStatus.PENDING.value,
        "payout_method": data.payout_method.value,
        "payout_details": json.dumps(data.payout_details or {}),
        "notes": data.notes,
        "total_earnings": 0,
        "total_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.affiliates.insert_one(affiliate)
    
    return {
        "id": affiliate["id"],
        "name": affiliate["name"],
        "email": affiliate["email"],
        "status": affiliate["status"],
        "message": "Your affiliate application has been submitted. You will be notified once approved."
    }


# ==================== SINGLE AFFILIATE ENDPOINTS ====================
# NOTE: These routes MUST come LAST to avoid path parameter conflicts with specific routes like /programs, /links, etc.

@router.get("/{affiliate_id}")
async def get_affiliate(
    affiliate_id: str,
    request: Request
):
    """Get affiliate details"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    affiliate = await db.affiliates.find_one(
        {"id": affiliate_id, "tenant_id": user["tenant_id"]},
        {"_id": 0, "payout_details": 0}
    )
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    # Get links
    links_cursor = db.affiliate_links.find({"affiliate_id": affiliate_id}, {"_id": 0})
    affiliate["links"] = await links_cursor.to_list(length=100)
    
    # Get recent commissions
    commissions_cursor = db.affiliate_commissions.find(
        {"affiliate_id": affiliate_id}, {"_id": 0}
    ).sort("created_at", -1).limit(10)
    affiliate["recent_commissions"] = await commissions_cursor.to_list(length=10)
    
    return affiliate


@router.put("/{affiliate_id}")
async def update_affiliate(
    affiliate_id: str,
    data: AffiliateUpdate,
    request: Request
):
    """Update affiliate"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    affiliate = await db.affiliates.find_one(
        {"id": affiliate_id, "tenant_id": user["tenant_id"]}
    )
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
    if "payout_method" in update_data:
        update_data["payout_method"] = update_data["payout_method"].value
    if "payout_details" in update_data:
        update_data["payout_details"] = json.dumps(update_data["payout_details"])
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.affiliates.update_one(
        {"id": affiliate_id},
        {"$set": update_data}
    )
    
    return {"success": True}


@router.post("/{affiliate_id}/approve")
async def approve_affiliate(
    affiliate_id: str,
    request: Request
):
    """Approve a pending affiliate"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    result = await db.affiliates.update_one(
        {"id": affiliate_id, "tenant_id": user["tenant_id"], "status": AffiliateStatus.PENDING.value},
        {"$set": {"status": AffiliateStatus.ACTIVE.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Affiliate not found or already approved")
    
    return {"success": True, "status": "active"}
