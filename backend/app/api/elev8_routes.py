"""
Elev8 CRM Entity Routes

Implements the core entity model per Elev8 CRM specification:
- Lead (early-stage prospects in Qualification Pipeline)
- Partner (for Partner Sales motion)
- Product (linked to Partners)
- Company (organization records)

Plus enhancements to existing entities:
- Deal (with Sales Motion Type, SPICED, etc.)
- Contact (linked to qualified deals)

Follows spec sections:
- Section 3: Entity Model
- Section 4: Sales Motion Identification
- Section 6: Lead Scoring
- Section 7: Required Fields Enforcement
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from app.db.mongodb import get_database

router = APIRouter(prefix="/elev8", tags=["Elev8 CRM"])


# ==================== ENUMS ====================

class SalesMotionType(str, Enum):
    PARTNERSHIP_SALES = "partnership_sales"  # Selling Elev8 services
    PARTNER_SALES = "partner_sales"  # Selling partner products


class LeadTier(str, Enum):
    A = "A"  # 80-100: Priority account, senior ownership
    B = "B"  # 60-79: Strategic SDR or AE motion
    C = "C"  # 40-59: Standard SDR motion
    D = "D"  # 0-39: Low priority, nurture only


class LeadStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    WORKING = "working"
    INFO_COLLECTED = "info_collected"
    UNRESPONSIVE = "unresponsive"
    DISQUALIFIED = "disqualified"
    QUALIFIED = "qualified"


class PartnerType(str, Enum):
    CHANNEL = "channel"
    RESELLER = "reseller"
    TECHNOLOGY = "technology"
    STRATEGIC = "strategic"


class PartnerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"


# ==================== SCHEMAS ====================

# --- Lead Schemas ---
class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    
    # Sales Motion (Required per Section 4)
    sales_motion_type: SalesMotionType = SalesMotionType.PARTNERSHIP_SALES
    partner_id: Optional[str] = None  # Required if partner_sales
    product_id: Optional[str] = None  # Required if partner_sales
    
    # Lead Source
    source: Optional[str] = None
    source_detail: Optional[str] = None
    
    # Scoring Inputs (Section 6.2)
    economic_units: Optional[int] = None  # e.g., locations, sites, licenses
    usage_volume: Optional[int] = None  # e.g., fryers, users, lines
    urgency: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale
    trigger_event: Optional[str] = None
    primary_motivation: Optional[str] = None
    decision_role: Optional[str] = None  # Decision Maker, Influencer, Champion, etc.
    decision_process_clarity: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale
    
    # Assignment
    owner_id: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    sales_motion_type: Optional[SalesMotionType] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    source: Optional[str] = None
    source_detail: Optional[str] = None
    economic_units: Optional[int] = None
    usage_volume: Optional[int] = None
    urgency: Optional[int] = Field(None, ge=1, le=5)
    trigger_event: Optional[str] = None
    primary_motivation: Optional[str] = None
    decision_role: Optional[str] = None
    decision_process_clarity: Optional[int] = Field(None, ge=1, le=5)
    owner_id: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None


# --- Partner Schemas ---
class PartnerCreate(BaseModel):
    name: str
    partner_type: PartnerType = PartnerType.CHANNEL
    status: PartnerStatus = PartnerStatus.PROSPECT
    description: Optional[str] = None
    territory: Optional[str] = None
    
    # Governance
    partner_manager_id: Optional[str] = None
    go_live_date: Optional[str] = None
    contract_term: Optional[str] = None
    renewal_date: Optional[str] = None
    
    # Configuration (Section 12)
    required_fields: List[str] = []  # Extra fields required for this partner
    custom_kpi_metrics: Dict[str, Any] = {}
    compliance_rules: Dict[str, Any] = {}  # e.g., min deal size, approval requirements
    
    # Contact Info
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    partner_type: Optional[PartnerType] = None
    status: Optional[PartnerStatus] = None
    description: Optional[str] = None
    territory: Optional[str] = None
    partner_manager_id: Optional[str] = None
    go_live_date: Optional[str] = None
    contract_term: Optional[str] = None
    renewal_date: Optional[str] = None
    required_fields: Optional[List[str]] = None
    custom_kpi_metrics: Optional[Dict[str, Any]] = None
    compliance_rules: Optional[Dict[str, Any]] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None


# --- Product Schemas ---
class ProductCreate(BaseModel):
    name: str
    partner_id: str  # Required - linked to partner
    description: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    
    # Pricing
    base_price: Optional[float] = None
    currency: str = "USD"
    pricing_model: Optional[str] = None  # one_time, recurring, usage_based
    
    # Scoring Configuration (product-specific fields for lead scoring)
    economic_unit_label: Optional[str] = None  # e.g., "locations", "licenses"
    usage_volume_label: Optional[str] = None  # e.g., "fryers", "users"
    
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    base_price: Optional[float] = None
    currency: Optional[str] = None
    pricing_model: Optional[str] = None
    economic_unit_label: Optional[str] = None
    usage_volume_label: Optional[str] = None
    is_active: Optional[bool] = None


# --- Company Schemas ---
class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "USA"
    
    # Business Info
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    
    # Parent/Hierarchy
    parent_company_id: Optional[str] = None
    
    notes: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    parent_company_id: Optional[str] = None
    notes: Optional[str] = None


# ==================== AUTH HELPER ====================

async def get_current_user(request):
    """Get current user from request (reuse from main server)"""
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== LEAD SCORING LOGIC ====================

def calculate_lead_score(lead: dict) -> tuple[int, str]:
    """
    Calculate lead score (0-100) based on Section 6.1 weights.
    Returns (score, tier).
    
    Categories:
    - Size & Economic Impact: 30%
    - Urgency & Willingness to Act: 20%
    - Lead Source Quality: 15%
    - Strategic Motivation & Vision: 20%
    - Decision Readiness: 15%
    """
    score = 0
    
    # 1. Size & Economic Impact (30 points max)
    economic_units = lead.get("economic_units") or 0
    usage_volume = lead.get("usage_volume") or 0
    
    # Scale economic units (assume 1-10 = low, 11-50 = medium, 51+ = high)
    if economic_units >= 50:
        score += 30
    elif economic_units >= 20:
        score += 22
    elif economic_units >= 10:
        score += 15
    elif economic_units >= 5:
        score += 10
    elif economic_units >= 1:
        score += 5
    
    # Boost for high usage volume
    if usage_volume >= 100:
        score = min(score + 5, 30)
    
    # 2. Urgency & Willingness to Act (20 points max)
    urgency = lead.get("urgency") or 0
    trigger_event = lead.get("trigger_event")
    
    # Urgency score (1-5 scale)
    urgency_score = (urgency / 5) * 15
    score += int(urgency_score)
    
    # Trigger event bonus
    if trigger_event and len(trigger_event) > 5:
        score += 5
    
    # 3. Lead Source Quality (15 points max)
    source = lead.get("source", "").lower()
    source_scores = {
        "referral": 15,
        "partner_referral": 15,
        "inbound_demo": 13,
        "website_demo": 12,
        "trade_show": 10,
        "webinar": 9,
        "content_download": 7,
        "cold_outreach": 5,
        "purchased_list": 3,
        "unknown": 2
    }
    score += source_scores.get(source, 5)
    
    # 4. Strategic Motivation & Vision (20 points max)
    primary_motivation = lead.get("primary_motivation", "")
    motivation_scores = {
        "cost_reduction": 18,
        "revenue_growth": 20,
        "compliance": 15,
        "efficiency": 17,
        "competitive_pressure": 16,
        "modernization": 12,
        "expansion": 14,
        "other": 8
    }
    score += motivation_scores.get(primary_motivation.lower(), 8) if primary_motivation else 5
    
    # 5. Decision Readiness (15 points max)
    decision_role = lead.get("decision_role", "").lower()
    decision_clarity = lead.get("decision_process_clarity") or 0
    
    role_scores = {
        "decision_maker": 8,
        "economic_buyer": 8,
        "champion": 6,
        "influencer": 4,
        "user": 2,
        "unknown": 1
    }
    score += role_scores.get(decision_role, 3)
    
    # Decision process clarity (1-5 scale)
    clarity_score = (decision_clarity / 5) * 7
    score += int(clarity_score)
    
    # Cap score at 100
    score = min(score, 100)
    
    # Determine tier (Section 6.3)
    if score >= 80:
        tier = LeadTier.A.value
    elif score >= 60:
        tier = LeadTier.B.value
    elif score >= 40:
        tier = LeadTier.C.value
    else:
        tier = LeadTier.D.value
    
    return score, tier


def get_tier_probability(tier: str) -> float:
    """Get forecast probability by tier (Section 6.4)"""
    probabilities = {
        "A": 0.70,  # 60-80%
        "B": 0.475,  # 35-60%
        "C": 0.225,  # 15-30%
        "D": 0.0    # 0%
    }
    return probabilities.get(tier, 0.0)


# ==================== LEAD ENDPOINTS ====================

@router.get("/leads")
async def list_leads(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    sales_motion_type: Optional[str] = None,
    partner_id: Optional[str] = None,
    owner_id: Optional[str] = None
):
    """List leads with filtering"""
    user = await get_current_user(request)
    db = get_database()
    
    # Build query
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}}
        ]
    
    if status:
        query["status"] = status
    if tier:
        query["tier"] = tier
    if sales_motion_type:
        query["sales_motion_type"] = sales_motion_type
    if partner_id:
        query["partner_id"] = partner_id
    if owner_id:
        query["owner_id"] = owner_id
    
    # Count and fetch
    total = await db.leads.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.leads.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    leads = await cursor.to_list(length=page_size)
    
    # Enrich with partner/product names
    for lead in leads:
        if lead.get("partner_id"):
            partner = await db.partners.find_one({"id": lead["partner_id"]}, {"_id": 0, "name": 1})
            lead["partner_name"] = partner.get("name") if partner else None
        if lead.get("product_id"):
            product = await db.products.find_one({"id": lead["product_id"]}, {"_id": 0, "name": 1})
            lead["product_name"] = product.get("name") if product else None
        if lead.get("owner_id"):
            owner = await db.users.find_one({"id": lead["owner_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            lead["owner_name"] = f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip() if owner else None
        lead["full_name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    return {
        "leads": leads,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/leads", status_code=201)
async def create_lead(data: LeadCreate, request: Request):
    """Create a new lead"""
    user = await get_current_user(request)
    db = get_database()
    
    # Validate partner sales requirements (Section 4)
    if data.sales_motion_type == SalesMotionType.PARTNER_SALES:
        if not data.partner_id:
            raise HTTPException(
                status_code=400,
                detail="Partner ID is required for Partner Sales motion"
            )
        if not data.product_id:
            raise HTTPException(
                status_code=400,
                detail="Product ID is required for Partner Sales motion"
            )
        
        # Verify partner exists
        partner = await db.partners.find_one({"id": data.partner_id, "tenant_id": user["tenant_id"]})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")
        
        # Verify product exists and belongs to partner
        product = await db.products.find_one({
            "id": data.product_id, 
            "partner_id": data.partner_id,
            "tenant_id": user["tenant_id"]
        })
        if not product:
            raise HTTPException(status_code=404, detail="Product not found or doesn't belong to partner")
    
    now = datetime.now(timezone.utc).isoformat()
    
    lead = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "status": LeadStatus.NEW.value,
        "lead_score": 0,
        "tier": LeadTier.D.value,
        "touchpoint_count": 0,
        "last_touchpoint_at": None,
        "qualified_at": None,
        "converted_deal_id": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    # Calculate initial score
    score, tier = calculate_lead_score(lead)
    lead["lead_score"] = score
    lead["tier"] = tier
    
    await db.leads.insert_one(lead)
    
    # Remove MongoDB _id for response
    lead.pop("_id", None)
    
    return lead


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, request: Request):
    """Get a specific lead"""
    user = await get_current_user(request)
    db = get_database()
    
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Enrich with related data
    if lead.get("partner_id"):
        partner = await db.partners.find_one({"id": lead["partner_id"]}, {"_id": 0, "name": 1})
        lead["partner_name"] = partner.get("name") if partner else None
    if lead.get("product_id"):
        product = await db.products.find_one({"id": lead["product_id"]}, {"_id": 0, "name": 1})
        lead["product_name"] = product.get("name") if product else None
    if lead.get("owner_id"):
        owner = await db.users.find_one({"id": lead["owner_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
        lead["owner_name"] = f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip() if owner else None
    
    lead["full_name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    return lead


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, data: LeadUpdate, request: Request):
    """Update a lead"""
    user = await get_current_user(request)
    db = get_database()
    
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Build update dict
    updates = {k: v for k, v in data.dict().items() if v is not None}
    
    # Validate partner sales requirements if changing sales motion
    if updates.get("sales_motion_type") == SalesMotionType.PARTNER_SALES.value:
        partner_id = updates.get("partner_id") or lead.get("partner_id")
        product_id = updates.get("product_id") or lead.get("product_id")
        
        if not partner_id:
            raise HTTPException(status_code=400, detail="Partner ID is required for Partner Sales motion")
        if not product_id:
            raise HTTPException(status_code=400, detail="Product ID is required for Partner Sales motion")
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate score if scoring fields changed
    scoring_fields = ["economic_units", "usage_volume", "urgency", "trigger_event", 
                      "primary_motivation", "decision_role", "decision_process_clarity", "source"]
    if any(f in updates for f in scoring_fields):
        merged = {**lead, **updates}
        score, tier = calculate_lead_score(merged)
        updates["lead_score"] = score
        updates["tier"] = tier
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": updates}
    )
    
    return await get_lead(lead_id, request)


@router.post("/leads/{lead_id}/qualify")
async def qualify_lead(lead_id: str, request: Request):
    """
    Qualify a lead and push to Sales Pipeline.
    Creates a Deal from the lead per Section 5.1.
    """
    user = await get_current_user(request)
    db = get_database()
    
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.get("status") == LeadStatus.QUALIFIED.value:
        raise HTTPException(status_code=400, detail="Lead is already qualified")
    
    # Validate required fields for qualification (Section 7)
    required_for_qualification = ["economic_units", "usage_volume", "urgency", "decision_role"]
    missing = [f for f in required_for_qualification if not lead.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot qualify lead. Missing required fields: {', '.join(missing)}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get or create default sales pipeline
    sales_pipeline = await db.pipelines.find_one(
        {"tenant_id": user["tenant_id"], "pipeline_type": "sales"},
        {"_id": 0}
    )
    
    if not sales_pipeline:
        raise HTTPException(status_code=400, detail="Sales pipeline not configured")
    
    first_stage = sales_pipeline.get("stages", [{}])[0]
    
    # Create company if needed
    company_id = None
    if lead.get("company_name"):
        existing_company = await db.companies.find_one({
            "tenant_id": user["tenant_id"],
            "name": {"$regex": f"^{lead['company_name']}$", "$options": "i"}
        })
        if existing_company:
            company_id = existing_company["id"]
        else:
            company = {
                "id": str(uuid.uuid4()),
                "tenant_id": user["tenant_id"],
                "name": lead["company_name"],
                "created_at": now,
                "updated_at": now
            }
            await db.companies.insert_one(company)
            company_id = company["id"]
    
    # Create contact from lead
    contact = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "first_name": lead["first_name"],
        "last_name": lead["last_name"],
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "company": lead.get("company_name"),
        "company_id": company_id,
        "title": lead.get("title"),
        "source": lead.get("source"),
        "lifecycle_stage": "opportunity",
        "lead_id": lead_id,
        "tags": [],
        "status": "active",
        "created_at": now,
        "updated_at": now
    }
    await db.contacts.insert_one(contact)
    
    # Create deal from lead
    deal = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": f"{lead.get('company_name', lead['first_name'])} - Deal",
        "amount": 0,
        "currency": "USD",
        "status": "open",
        
        # Sales Motion (Section 4)
        "sales_motion_type": lead.get("sales_motion_type", SalesMotionType.PARTNERSHIP_SALES.value),
        "partner_id": lead.get("partner_id"),
        "product_id": lead.get("product_id"),
        
        # Links
        "contact_id": contact["id"],
        "company_id": company_id,
        "lead_id": lead_id,
        
        # Pipeline
        "pipeline_id": sales_pipeline["id"],
        "stage_id": first_stage.get("id"),
        "stage_name": first_stage.get("name"),
        
        # Scoring
        "lead_score": lead.get("lead_score", 0),
        "tier": lead.get("tier", LeadTier.D.value),
        "forecast_probability": get_tier_probability(lead.get("tier", "D")),
        "weighted_amount": 0,
        
        # Scoring inputs (carry over)
        "economic_units": lead.get("economic_units"),
        "usage_volume": lead.get("usage_volume"),
        "urgency": lead.get("urgency"),
        "trigger_event": lead.get("trigger_event"),
        "primary_motivation": lead.get("primary_motivation"),
        "decision_role": lead.get("decision_role"),
        "decision_process_clarity": lead.get("decision_process_clarity"),
        
        # SPICED (Section 7 - required for Discovery)
        "spiced_summary": None,
        "spiced_situation": None,
        "spiced_pain": None,
        "spiced_impact": None,
        "spiced_critical_event": None,
        "spiced_economic": None,
        "spiced_decision": None,
        
        # Ownership
        "owner_id": lead.get("owner_id") or user["id"],
        
        # Timestamps
        "qualified_at": now,
        "created_at": now,
        "updated_at": now
    }
    await db.deals.insert_one(deal)
    
    # Update lead status
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "status": LeadStatus.QUALIFIED.value,
            "qualified_at": now,
            "converted_deal_id": deal["id"],
            "updated_at": now
        }}
    )
    
    return {
        "message": "Lead qualified successfully",
        "deal_id": deal["id"],
        "contact_id": contact["id"],
        "company_id": company_id
    }


@router.post("/leads/{lead_id}/touchpoint")
async def record_touchpoint(lead_id: str, request: Request):
    """Record a touchpoint/activity for a lead"""
    user = await get_current_user(request)
    db = get_database()
    
    result = await db.leads.update_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {
            "$inc": {"touchpoint_count": 1},
            "$set": {
                "last_touchpoint_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Touchpoint recorded"}


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, request: Request):
    """Delete a lead"""
    user = await get_current_user(request)
    db = get_database()
    
    result = await db.leads.delete_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted"}


# ==================== PARTNER ENDPOINTS ====================

@router.get("/partners")
async def list_partners(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    partner_type: Optional[str] = None
):
    """List partners"""
    user = await get_current_user(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if status:
        query["status"] = status
    if partner_type:
        query["partner_type"] = partner_type
    
    total = await db.partners.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.partners.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    partners = await cursor.to_list(length=page_size)
    
    # Add deal counts
    for partner in partners:
        partner["active_deals"] = await db.deals.count_documents({
            "partner_id": partner["id"],
            "status": "open"
        })
        partner["total_deals"] = await db.deals.count_documents({
            "partner_id": partner["id"]
        })
    
    return {
        "partners": partners,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/partners", status_code=201)
async def create_partner(data: PartnerCreate, request: Request):
    """Create a new partner"""
    user = await get_current_user(request)
    db = get_database()
    
    now = datetime.now(timezone.utc).isoformat()
    
    partner = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.partners.insert_one(partner)
    partner.pop("_id", None)
    
    return partner


@router.get("/partners/{partner_id}")
async def get_partner(partner_id: str, request: Request):
    """Get a specific partner"""
    user = await get_current_user(request)
    db = get_database()
    
    partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Add products
    products = await db.products.find(
        {"partner_id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    ).to_list(length=100)
    partner["products"] = products
    
    # Add deal stats
    partner["active_deals"] = await db.deals.count_documents({
        "partner_id": partner_id, "status": "open"
    })
    partner["won_deals"] = await db.deals.count_documents({
        "partner_id": partner_id, "status": "won"
    })
    
    return partner


@router.put("/partners/{partner_id}")
async def update_partner(partner_id: str, data: PartnerUpdate, request: Request):
    """Update a partner"""
    user = await get_current_user(request)
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.partners.update_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return await get_partner(partner_id, request)


@router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str, request: Request):
    """Delete a partner"""
    user = await get_current_user(request)
    db = get_database()
    
    # Check for active deals
    active_deals = await db.deals.count_documents({
        "partner_id": partner_id, "status": "open"
    })
    if active_deals > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete partner with {active_deals} active deal(s)"
        )
    
    result = await db.partners.delete_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return {"message": "Partner deleted"}


# ==================== PRODUCT ENDPOINTS ====================

@router.get("/products")
async def list_products(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    partner_id: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """List products"""
    user = await get_current_user(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if partner_id:
        query["partner_id"] = partner_id
    if is_active is not None:
        query["is_active"] = is_active
    
    total = await db.products.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.products.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    products = await cursor.to_list(length=page_size)
    
    # Enrich with partner names
    for product in products:
        if product.get("partner_id"):
            partner = await db.partners.find_one({"id": product["partner_id"]}, {"_id": 0, "name": 1})
            product["partner_name"] = partner.get("name") if partner else None
    
    return {
        "products": products,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/products", status_code=201)
async def create_product(data: ProductCreate, request: Request):
    """Create a new product"""
    user = await get_current_user(request)
    db = get_database()
    
    # Verify partner exists
    partner = await db.partners.find_one(
        {"id": data.partner_id, "tenant_id": user["tenant_id"]}
    )
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    product = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.products.insert_one(product)
    product.pop("_id", None)
    
    return product


@router.get("/products/{product_id}")
async def get_product(product_id: str, request: Request):
    """Get a specific product"""
    user = await get_current_user(request)
    db = get_database()
    
    product = await db.products.find_one(
        {"id": product_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Add partner info
    if product.get("partner_id"):
        partner = await db.partners.find_one({"id": product["partner_id"]}, {"_id": 0, "name": 1})
        product["partner_name"] = partner.get("name") if partner else None
    
    return product


@router.put("/products/{product_id}")
async def update_product(product_id: str, data: ProductUpdate, request: Request):
    """Update a product"""
    user = await get_current_user(request)
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.products.update_one(
        {"id": product_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return await get_product(product_id, request)


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request):
    """Delete a product"""
    user = await get_current_user(request)
    db = get_database()
    
    result = await db.products.delete_one(
        {"id": product_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted"}


# ==================== COMPANY ENDPOINTS ====================

@router.get("/companies")
async def list_companies(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    industry: Optional[str] = None
):
    """List companies"""
    user = await get_current_user(request)
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if industry:
        query["industry"] = industry
    
    total = await db.companies.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.companies.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    companies = await cursor.to_list(length=page_size)
    
    # Add contact and deal counts
    for company in companies:
        company["contact_count"] = await db.contacts.count_documents({"company_id": company["id"]})
        company["deal_count"] = await db.deals.count_documents({"company_id": company["id"]})
    
    return {
        "companies": companies,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/companies", status_code=201)
async def create_company(data: CompanyCreate, request: Request):
    """Create a new company"""
    user = await get_current_user(request)
    db = get_database()
    
    now = datetime.now(timezone.utc).isoformat()
    
    company = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.companies.insert_one(company)
    company.pop("_id", None)
    
    return company


@router.get("/companies/{company_id}")
async def get_company(company_id: str, request: Request):
    """Get a specific company"""
    user = await get_current_user(request)
    db = get_database()
    
    company = await db.companies.find_one(
        {"id": company_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Add related contacts and deals
    company["contacts"] = await db.contacts.find(
        {"company_id": company_id},
        {"_id": 0}
    ).to_list(length=100)
    
    company["deals"] = await db.deals.find(
        {"company_id": company_id},
        {"_id": 0}
    ).to_list(length=100)
    
    return company


@router.put("/companies/{company_id}")
async def update_company(company_id: str, data: CompanyUpdate, request: Request):
    """Update a company"""
    user = await get_current_user(request)
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.companies.update_one(
        {"id": company_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return await get_company(company_id, request)


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, request: Request):
    """Delete a company"""
    user = await get_current_user(request)
    db = get_database()
    
    result = await db.companies.delete_one(
        {"id": company_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": "Company deleted"}


# ==================== LEAD SCORING STATS ====================

@router.get("/leads/scoring/stats")
async def get_lead_scoring_stats(request: Request):
    """Get lead scoring statistics and tier distribution"""
    user = await get_current_user(request)
    db = get_database()
    
    # Tier distribution
    pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {
            "_id": "$tier",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$lead_score"}
        }}
    ]
    
    tier_results = await db.leads.aggregate(pipeline).to_list(length=10)
    
    tier_distribution = {
        "A": {"count": 0, "avg_score": 0},
        "B": {"count": 0, "avg_score": 0},
        "C": {"count": 0, "avg_score": 0},
        "D": {"count": 0, "avg_score": 0}
    }
    
    for r in tier_results:
        tier = r["_id"]
        if tier in tier_distribution:
            tier_distribution[tier] = {
                "count": r["count"],
                "avg_score": round(r["avg_score"] or 0, 1)
            }
    
    # Status distribution
    status_pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    
    status_results = await db.leads.aggregate(status_pipeline).to_list(length=10)
    status_distribution = {r["_id"]: r["count"] for r in status_results}
    
    return {
        "tier_distribution": tier_distribution,
        "status_distribution": status_distribution,
        "total_leads": sum(t["count"] for t in tier_distribution.values())
    }


# ==================== PIPELINE SETUP ====================

@router.post("/setup/pipelines")
async def setup_elev8_pipelines(request: Request):
    """
    Create the Elev8 dual pipeline structure (Qualification + Sales).
    This is typically run once during initial setup.
    """
    user = await get_current_user(request)
    db = get_database()
    
    # Check admin role
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.migrations.elev8_pipelines import create_elev8_pipelines
    
    result = await create_elev8_pipelines(db, user["tenant_id"])
    return result


@router.post("/setup/migrate-deals")
async def migrate_deals_to_elev8(request: Request, old_pipeline_id: str = Query(...)):
    """
    Migrate existing deals from an old pipeline to the new Sales Pipeline.
    """
    user = await get_current_user(request)
    db = get_database()
    
    # Check admin role
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get sales pipeline
    sales_pipeline = await db.pipelines.find_one({
        "tenant_id": user["tenant_id"],
        "pipeline_type": "sales"
    })
    
    if not sales_pipeline:
        raise HTTPException(status_code=400, detail="Sales pipeline not found. Run /setup/pipelines first.")
    
    from app.migrations.elev8_pipelines import migrate_existing_deals_to_sales_pipeline
    
    result = await migrate_existing_deals_to_sales_pipeline(
        db, user["tenant_id"], old_pipeline_id, sales_pipeline["id"]
    )
    return result


@router.get("/pipelines/elev8")
async def get_elev8_pipelines(request: Request):
    """Get the Elev8 dual pipeline configuration"""
    user = await get_current_user(request)
    db = get_database()
    
    qual_pipeline = await db.pipelines.find_one(
        {"tenant_id": user["tenant_id"], "pipeline_type": "qualification"},
        {"_id": 0}
    )
    
    sales_pipeline = await db.pipelines.find_one(
        {"tenant_id": user["tenant_id"], "pipeline_type": "sales"},
        {"_id": 0}
    )
    
    result = {"qualification": None, "sales": None}
    
    if qual_pipeline:
        stages = await db.pipeline_stages.find(
            {"pipeline_id": qual_pipeline["id"]},
            {"_id": 0}
        ).sort("display_order", 1).to_list(length=100)
        result["qualification"] = {**qual_pipeline, "stages": stages}
    
    if sales_pipeline:
        stages = await db.pipeline_stages.find(
            {"pipeline_id": sales_pipeline["id"]},
            {"_id": 0}
        ).sort("display_order", 1).to_list(length=100)
        result["sales"] = {**sales_pipeline, "stages": stages}
    
    return result

