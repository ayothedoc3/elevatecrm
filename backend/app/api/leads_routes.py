"""
Leads API Routes

Handles lead management operations:
- Create, read, update, delete leads
- Lead scoring (0-100)
- Lead tier assignment (A-D)
- Lead source tracking
- Lead assignment and conversion
"""

from fastapi import APIRouter, HTTPException, Query, Request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid
import json

from app.db.mongodb import get_database

router = APIRouter(prefix="/leads", tags=["Leads"])


# ==================== SCHEMAS ====================

class LeadCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    source: Optional[str] = None  # web, referral, cold_call, etc.
    score: int = Field(default=0, ge=0, le=100)
    tier: Optional[str] = None  # A, B, C, D
    sales_motion_type: str = "partnership_sales"
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    source: Optional[str] = None
    score: Optional[int] = Field(default=None, ge=0, le=100)
    tier: Optional[str] = None
    sales_motion_type: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None


class LeadAssignRequest(BaseModel):
    owner_id: str


class LeadScoreRequest(BaseModel):
    score: Optional[int] = Field(default=None, ge=0, le=100)
    scoring_data: Optional[Dict[str, Any]] = None


class LeadPushToSalesRequest(BaseModel):
    deal_name: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    next_step_at: str = Field(..., min_length=1)
    next_step_note: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None


class LeadTouchpointRequest(BaseModel):
    activity_type: str = "call"
    notes: Optional[str] = None
    got_response: bool = False


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


def calculate_tier(score: int) -> str:
    """Calculate lead tier based on score"""
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    else:
        return "D"


def compute_universal_score(scoring_data: Dict[str, Any], lead_source: str) -> int:
    """
    Compute product-agnostic lead score (0–100) using Elev8 weights.

    Required inputs (stored in scoring_data):
    - economic_units (number)
    - usage_volume (number)
    - urgency (1–5)
    - trigger_event (string)
    - primary_motivation (string)
    - decision_role (string)
    - decision_process_clarity (1–5)

    Lead source comes from the Lead.source field.
    """
    def _to_float(value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    def _to_int(value, default=0):
        try:
            if value is None or value == "":
                return default
            return int(value)
        except Exception:
            return default

    economic_units = max(0.0, _to_float(scoring_data.get("economic_units"), 0.0))
    usage_volume = max(0.0, _to_float(scoring_data.get("usage_volume"), 0.0))
    urgency = min(5, max(1, _to_int(scoring_data.get("urgency"), 1)))
    trigger_event = (scoring_data.get("trigger_event") or "").strip()
    primary_motivation = (scoring_data.get("primary_motivation") or "").strip().lower()
    decision_role = (scoring_data.get("decision_role") or "").strip().lower()
    decision_process_clarity = min(5, max(1, _to_int(scoring_data.get("decision_process_clarity"), 1)))

    # Size & Economic Impact (30)
    # Split across economic_units (15) and usage_volume (15)
    if economic_units >= 20:
        econ_points = 15
    elif economic_units >= 10:
        econ_points = 12
    elif economic_units >= 5:
        econ_points = 9
    elif economic_units >= 2:
        econ_points = 6
    elif economic_units >= 1:
        econ_points = 3
    else:
        econ_points = 0

    if usage_volume >= 100:
        usage_points = 15
    elif usage_volume >= 50:
        usage_points = 12
    elif usage_volume >= 20:
        usage_points = 9
    elif usage_volume >= 6:
        usage_points = 6
    elif usage_volume >= 1:
        usage_points = 3
    else:
        usage_points = 0

    size_impact = econ_points + usage_points  # 0–30

    # Urgency & Willingness to Act (20)
    urgency_points = (urgency - 1) * 4  # 0,4,8,12,16
    trigger_points = 4 if trigger_event else 0
    urgency_total = min(20, urgency_points + trigger_points)

    # Lead Source Quality (15)
    source = (lead_source or "").strip().lower()
    source_map = {
        "referral": 15,
        "event": 12,
        "web": 10,
        "social": 8,
        "email": 6,
        "manual": 5,
        "cold_call": 4,
    }
    source_quality = source_map.get(source, 6)

    # Strategic Motivation & Vision (20)
    motivation_points = 12  # default
    if any(k in primary_motivation for k in ["growth", "scale", "expansion"]):
        motivation_points = 18
    elif any(k in primary_motivation for k in ["save", "savings", "cost"]):
        motivation_points = 20
    elif any(k in primary_motivation for k in ["efficien", "process", "automation"]):
        motivation_points = 15
    elif any(k in primary_motivation for k in ["compliance", "risk", "audit"]):
        motivation_points = 15
    elif any(k in primary_motivation for k in ["curious", "learn", "explore"]):
        motivation_points = 6

    # Decision Readiness (15)
    role_points = 3
    if decision_role in ["decision_maker", "dm", "owner", "ceo", "cfo", "founder"]:
        role_points = 8
    elif decision_role in ["influencer", "champion", "manager", "director"]:
        role_points = 5
    elif decision_role in ["researcher", "analyst", "assistant"]:
        role_points = 2

    clarity_points = (decision_process_clarity - 1) * 2  # 0,2,4,6,8
    clarity_points = min(7, clarity_points)  # cap at 7
    decision_readiness = min(15, role_points + clarity_points)

    score = int(round(size_impact + urgency_total + source_quality + motivation_points + decision_readiness))
    return min(100, max(0, score))


def scoring_inputs_complete(scoring_data: Dict[str, Any]) -> bool:
    required_keys = [
        "economic_units",
        "usage_volume",
        "urgency",
        "trigger_event",
        "primary_motivation",
        "decision_role",
        "decision_process_clarity",
    ]
    for key in required_keys:
        value = scoring_data.get(key)
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True


VALID_SALES_MOTION_TYPES = {"partnership_sales", "partner_sales"}
VALID_LEAD_TIERS = {"A", "B", "C", "D"}
MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE = 3

def normalize_lower(value: Optional[str]) -> str:
    return " ".join((value or "").strip().split()).lower()


async def resolve_account(
    db,
    tenant_id: str,
    account_name: str,
    actor_id: str
) -> Dict[str, Optional[str]]:
    name = " ".join((account_name or "").strip().split())
    if not name:
        raise HTTPException(status_code=400, detail="account_name is required")

    now = datetime.now(timezone.utc).isoformat()
    name_lower = normalize_lower(name)

    existing = await db.accounts.find_one(
        {"tenant_id": tenant_id, "name_lower": name_lower},
        {"_id": 0}
    )
    if existing:
        return {"account_id": existing["id"], "account_name": existing.get("name") or name}

    account = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": name,
        "name_lower": name_lower,
        "is_active": True,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now
    }
    await db.accounts.insert_one(account)
    return {"account_id": account["id"], "account_name": account["name"]}


async def upsert_open_next_step_task_for_deal(
    db,
    tenant_id: str,
    deal_id: str,
    due_at: str,
    owner_id: str,
    created_by: str,
    note: Optional[str] = None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.tasks.find_one(
        {
            "tenant_id": tenant_id,
            "related_type": "deal",
            "related_id": deal_id,
            "kind": "next_step",
            "status": "open"
        },
        {"_id": 0}
    )
    if existing:
        await db.tasks.update_one(
            {"id": existing["id"], "tenant_id": tenant_id},
            {"$set": {"due_at": due_at, "owner_id": owner_id, "description": note, "updated_at": now}}
        )
        return

    task = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "title": "Next Step",
        "description": note,
        "status": "open",
        "kind": "next_step",
        "due_at": due_at,
        "completed_at": None,
        "owner_id": owner_id,
        "related_type": "deal",
        "related_id": deal_id,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now
    }
    await db.tasks.insert_one(task)


async def resolve_partner_and_product(
    db,
    tenant_id: str,
    sales_motion_type: str,
    partner_id: Optional[str],
    product_id: Optional[str],
    partner_name: Optional[str],
    product_name: Optional[str],
    actor_id: str
) -> Dict[str, Optional[str]]:
    if sales_motion_type not in VALID_SALES_MOTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sales_motion_type. Must be one of: {', '.join(sorted(VALID_SALES_MOTION_TYPES))}"
        )

    if sales_motion_type == "partnership_sales":
        return {"partner_id": None, "partner_name": None, "product_id": None, "product_name": None}

    now = datetime.now(timezone.utc).isoformat()

    # Partner
    if partner_id:
        partner = await db.partners.find_one({"id": partner_id, "tenant_id": tenant_id}, {"_id": 0})
        if not partner:
            raise HTTPException(status_code=400, detail="Partner not found")
        partner_name = partner.get("name")
    else:
        name = (partner_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="partner_name is required for partner_sales")
        name_lower = name.lower()
        partner = await db.partners.find_one({"tenant_id": tenant_id, "name_lower": name_lower}, {"_id": 0})
        if not partner:
            partner = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "name": name,
                "name_lower": name_lower,
                "is_active": True,
                "created_by": actor_id,
                "created_at": now,
                "updated_at": now
            }
            await db.partners.insert_one(partner)
        partner_id = partner["id"]
        partner_name = partner["name"]

    # Product
    if product_id:
        product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id}, {"_id": 0})
        if not product or product.get("partner_id") != partner_id:
            raise HTTPException(status_code=400, detail="Product not found for partner")
        product_name = product.get("name")
    else:
        name = (product_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="product_name is required for partner_sales")
        name_lower = name.lower()
        product = await db.products.find_one(
            {"tenant_id": tenant_id, "partner_id": partner_id, "name_lower": name_lower},
            {"_id": 0}
        )
        if not product:
            product = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "partner_id": partner_id,
                "name": name,
                "name_lower": name_lower,
                "is_active": True,
                "created_by": actor_id,
                "created_at": now,
                "updated_at": now
            }
            await db.products.insert_one(product)
        product_id = product["id"]
        product_name = product["name"]

    return {
        "partner_id": partner_id,
        "partner_name": partner_name,
        "product_id": product_id,
        "product_name": product_name
    }


# ==================== LEAD ENDPOINTS ====================

@router.get("")
async def get_leads(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    tier: Optional[str] = None,
    source: Optional[str] = None,
    owner_id: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100)
):
    """Get all leads for the tenant with filtering and pagination"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Build query
    query = {"tenant_id": tenant_id}

    if status:
        query["status"] = status

    if tier:
        query["tier"] = tier

    if source:
        query["source"] = source

    if owner_id:
        query["owner_id"] = owner_id

    if min_score is not None:
        query["score"] = query.get("score", {})
        query["score"]["$gte"] = min_score

    if max_score is not None:
        query["score"] = query.get("score", {})
        query["score"]["$lte"] = max_score

    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}}
        ]

    # Get total count
    total = await db.leads.count_documents(query)

    # Get paginated leads
    skip = (page - 1) * page_size
    leads_cursor = db.leads.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    leads = await leads_cursor.to_list(length=page_size)

    # Enrich with owner names
    for lead in leads:
        if lead.get("owner_id"):
            owner = await db.users.find_one(
                {"id": lead["owner_id"], "tenant_id": tenant_id},
                {"_id": 0, "first_name": 1, "last_name": 1}
            )
            if owner:
                lead["owner_name"] = f"{owner['first_name']} {owner['last_name']}"
        lead["full_name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

    return {
        "leads": leads,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", status_code=201)
async def create_lead(
    request: Request,
    data: LeadCreate
):
    """Create a new lead"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()
    now = datetime.now(timezone.utc).isoformat()

    lead_id = str(uuid.uuid4())

    # Calculate tier based on score
    tier = data.tier or calculate_tier(data.score)

    sales_motion_type = (data.sales_motion_type or "partnership_sales").strip()
    resolved = await resolve_partner_and_product(
        db=db,
        tenant_id=tenant_id,
        sales_motion_type=sales_motion_type,
        partner_id=data.partner_id,
        product_id=data.product_id,
        partner_name=data.partner_name,
        product_name=data.product_name,
        actor_id=user["id"]
    )

    new_lead = {
        "id": lead_id,
        "tenant_id": tenant_id,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "full_name": f"{data.first_name} {data.last_name}",
        "email": data.email,
        "phone": data.phone,
        "company_name": data.company_name,
        "source": data.source or "manual",
        "score": data.score,
        "tier": tier,
        "sales_motion_type": sales_motion_type,
        "partner_id": resolved.get("partner_id"),
        "product_id": resolved.get("product_id"),
        "partner_name": resolved.get("partner_name"),
        "product_name": resolved.get("product_name"),
        "status": "new",
        "notes": data.notes,
        "tags": data.tags,
        "owner_id": None,
        "assigned_at": None,
        "converted_at": None,
        "contact_id": None,  # Set when converted to contact
        "touchpoints_count": 0,
        "last_touchpoint_at": None,
        "scoring_data": {},
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }

    await db.leads.insert_one(new_lead)

    # Remove _id from response
    new_lead.pop("_id", None)

    return new_lead


@router.get("/{lead_id}")
async def get_lead(
    request: Request,
    lead_id: str
):
    """Get a single lead by ID"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"_id": 0}
    )

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Enrich with owner name
    if lead.get("owner_id"):
        owner = await db.users.find_one(
            {"id": lead["owner_id"], "tenant_id": tenant_id},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if owner:
            lead["owner_name"] = f"{owner['first_name']} {owner['last_name']}"

    lead["full_name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

    return lead


@router.put("/{lead_id}")
async def update_lead(
    request: Request,
    lead_id: str,
    data: LeadUpdate
):
    """Update a lead"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check lead exists
    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.get("status") in ["disqualified", "converted"]:
        raise HTTPException(status_code=400, detail="Cannot assign a disqualified or converted lead")

    # Build update
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if data.first_name is not None:
        update_data["first_name"] = data.first_name
    if data.last_name is not None:
        update_data["last_name"] = data.last_name
    if data.email is not None:
        update_data["email"] = data.email
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.company_name is not None:
        update_data["company_name"] = data.company_name
    if data.source is not None:
        update_data["source"] = data.source
    if data.score is not None:
        update_data["score"] = data.score
        # Recalculate tier if score changed
        update_data["tier"] = data.tier or calculate_tier(data.score)
    if data.tier is not None:
        update_data["tier"] = data.tier
    if data.status is not None:
        allowed_statuses = {
            "new",
            "assigned",
            "working",
            "info_collected",
            "unresponsive",
            "disqualified",
            "qualified",
            "converted",
        }
        if data.status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(sorted(allowed_statuses))}")

        if data.status in ["info_collected", "qualified"]:
            scoring_data = lead.get("scoring_data", {}) or {}
            if not scoring_inputs_complete(scoring_data):
                raise HTTPException(
                    status_code=400,
                    detail="Scoring inputs must be completed before moving to Info Collected or Qualified"
                )
        if data.status == "unresponsive":
            touchpoints = int(lead.get("touchpoints_count") or 0)
            if touchpoints < MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"At least {MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE} touchpoints are required before marking Unresponsive"
                )
        update_data["status"] = data.status
    if data.notes is not None:
        update_data["notes"] = data.notes
    if data.owner_id is not None:
        update_data["owner_id"] = data.owner_id
        if not lead.get("assigned_at"):
            update_data["assigned_at"] = datetime.now(timezone.utc).isoformat()
    if data.tags is not None:
        update_data["tags"] = data.tags

    motion_update_requested = any([
        data.sales_motion_type is not None,
        data.partner_id is not None,
        data.product_id is not None,
        data.partner_name is not None,
        data.product_name is not None,
    ])

    if motion_update_requested:
        sales_motion_type = (data.sales_motion_type or lead.get("sales_motion_type") or "partnership_sales").strip()
        resolved = await resolve_partner_and_product(
            db=db,
            tenant_id=tenant_id,
            sales_motion_type=sales_motion_type,
            partner_id=data.partner_id if data.partner_id is not None else lead.get("partner_id"),
            product_id=data.product_id if data.product_id is not None else lead.get("product_id"),
            partner_name=data.partner_name if data.partner_name is not None else lead.get("partner_name"),
            product_name=data.product_name if data.product_name is not None else lead.get("product_name"),
            actor_id=user["id"]
        )
        update_data["sales_motion_type"] = sales_motion_type
        update_data["partner_id"] = resolved.get("partner_id")
        update_data["product_id"] = resolved.get("product_id")
        update_data["partner_name"] = resolved.get("partner_name")
        update_data["product_name"] = resolved.get("product_name")

    # Update full_name if name changed
    first_name = update_data.get("first_name", lead.get("first_name", ""))
    last_name = update_data.get("last_name", lead.get("last_name", ""))
    update_data["full_name"] = f"{first_name} {last_name}".strip()

    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    # Return updated lead
    updated = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id}, {"_id": 0})
    if updated and updated.get("owner_id"):
        owner = await db.users.find_one(
            {"id": updated["owner_id"], "tenant_id": tenant_id},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if owner:
            updated["owner_name"] = f"{owner['first_name']} {owner['last_name']}"
    if updated:
        updated["full_name"] = f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip()
    return updated


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    request: Request,
    lead_id: str
):
    """Delete a lead"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    result = await db.leads.delete_one({"id": lead_id, "tenant_id": tenant_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")

    return None


@router.post("/{lead_id}/assign")
async def assign_lead(
    request: Request,
    lead_id: str,
    data: LeadAssignRequest
):
    """Assign a lead to a user"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check lead exists
    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Verify owner exists
    owner = await db.users.find_one({"id": data.owner_id, "tenant_id": tenant_id})
    if not owner:
        raise HTTPException(status_code=400, detail="Assigned user not found")

    now = datetime.now(timezone.utc).isoformat()

    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": {
            "owner_id": data.owner_id,
            "assigned_at": now,
            "status": "working",
            "updated_at": now
        }}
    )

    updated = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id}, {"_id": 0})
    updated["owner_name"] = f"{owner['first_name']} {owner['last_name']}"

    return updated


@router.post("/{lead_id}/touchpoint")
async def log_lead_touchpoint(
    request: Request,
    lead_id: str,
    data: LeadTouchpointRequest
):
    """Log a touchpoint for a lead (used to enforce Unresponsive minimum touchpoints)."""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.get("status") in ["disqualified", "converted"]:
        raise HTTPException(status_code=400, detail="Cannot log touchpoints for a disqualified or converted lead")

    now = datetime.now(timezone.utc).isoformat()

    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {
            "$inc": {"touchpoints_count": 1},
            "$set": {"last_touchpoint_at": now, "updated_at": now}
        }
    )

    # Timeline event
    event = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "event_type": "lead_touchpoint",
        "title": f"Lead touchpoint: {data.activity_type}",
        "description": data.notes,
        "actor_id": user["id"],
        "actor_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "deal_id": None,
        "contact_id": None,
        "visibility": "internal_only",
        "metadata": {
            "lead_id": lead_id,
            "activity_type": data.activity_type,
            "got_response": bool(data.got_response),
        },
        "created_at": now
    }
    await db.timeline_events.insert_one(event)

    updated = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id}, {"_id": 0})
    if updated and updated.get("owner_id"):
        owner = await db.users.find_one(
            {"id": updated["owner_id"], "tenant_id": tenant_id},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if owner:
            updated["owner_name"] = f"{owner['first_name']} {owner['last_name']}"
    if updated:
        updated["full_name"] = f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip()
    return updated


@router.post("/{lead_id}/score")
async def score_lead(
    request: Request,
    lead_id: str,
    data: LeadScoreRequest
):
    """Update lead score and recalculate tier"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check lead exists
    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now(timezone.utc).isoformat()

    scoring_data = data.scoring_data if data.scoring_data is not None else lead.get("scoring_data", {})

    if data.scoring_data is not None:
        score = compute_universal_score(scoring_data, lead.get("source") or "manual")
    elif data.score is not None:
        score = data.score
    else:
        raise HTTPException(status_code=400, detail="Provide scoring_data to compute score or score to set manually")

    tier = calculate_tier(score)

    update_data = {"updated_at": now, "score": score, "tier": tier}
    if data.scoring_data is not None:
        update_data["scoring_data"] = scoring_data

    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    updated = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id}, {"_id": 0})
    if updated and updated.get("owner_id"):
        owner = await db.users.find_one(
            {"id": updated["owner_id"], "tenant_id": tenant_id},
            {"_id": 0, "first_name": 1, "last_name": 1}
        )
        if owner:
            updated["owner_name"] = f"{owner['first_name']} {owner['last_name']}"
    if updated:
        updated["full_name"] = f"{updated.get('first_name', '')} {updated.get('last_name', '')}".strip()
    return updated


@router.post("/{lead_id}/convert")
async def convert_lead_to_contact(
    request: Request,
    lead_id: str
):
    """Convert a lead to a contact"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check lead exists
    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.get("converted_at"):
        raise HTTPException(status_code=400, detail="Lead already converted")

    now = datetime.now(timezone.utc).isoformat()
    contact_id = str(uuid.uuid4())

    # Create contact from lead
    company_name = lead.get("company_name") or lead.get("company")
    account_name_input = company_name or (lead.get("full_name") or "").strip()
    resolved_account = None
    if account_name_input:
        resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
    new_contact = {
        "id": contact_id,
        "tenant_id": tenant_id,
        "first_name": lead.get("first_name"),
        "last_name": lead.get("last_name"),
        "full_name": lead.get("full_name"),
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "company_name": company_name,
        "company": company_name,
        "account_id": (resolved_account or {}).get("account_id"),
        "account_name": (resolved_account or {}).get("account_name"),
        "source": lead.get("source"),
        "lifecycle_stage": "lead",
        "lead_score": lead.get("score"),
        "lead_tier": lead.get("tier"),
        "owner_id": lead.get("owner_id"),
        "tags": lead.get("tags", []),
        "status": "active",
        "converted_from_lead_id": lead_id,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }

    await db.contacts.insert_one(new_contact)

    # Update lead status
    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": {
            "status": "converted",
            "converted_at": now,
            "contact_id": contact_id,
            "updated_at": now
        }}
    )

    new_contact.pop("_id", None)

    return {
        "lead_id": lead_id,
        "contact_id": contact_id,
        "contact": new_contact,
        "message": "Lead successfully converted to contact"
    }


@router.post("/{lead_id}/push-to-sales")
async def push_lead_to_sales(
    request: Request,
    lead_id: str,
    data: LeadPushToSalesRequest
):
    """Push a qualified lead into the Sales pipeline by creating a Contact (if needed) and a Deal."""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    lead = await db.leads.find_one({"id": lead_id, "tenant_id": tenant_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.get("status") != "qualified":
        raise HTTPException(status_code=400, detail="Lead must be Qualified before pushing to Sales Pipeline")

    scoring_data = lead.get("scoring_data", {}) or {}
    if not scoring_inputs_complete(scoring_data):
        raise HTTPException(status_code=400, detail="Scoring inputs must be completed before pushing to Sales Pipeline")

    now = datetime.now(timezone.utc).isoformat()

    # Ensure contact exists (reuse if already converted)
    contact = None
    contact_id = lead.get("contact_id")
    if contact_id:
        contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant_id}, {"_id": 0})

    if not contact:
        contact_id = str(uuid.uuid4())
        company_name = lead.get("company_name") or lead.get("company")
        account_name_input = company_name or (lead.get("full_name") or "").strip()
        resolved_account = None
        if account_name_input:
            resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
        contact = {
            "id": contact_id,
            "tenant_id": tenant_id,
            "first_name": lead.get("first_name"),
            "last_name": lead.get("last_name"),
            "full_name": lead.get("full_name"),
            "email": lead.get("email"),
            "phone": lead.get("phone"),
            "company_name": company_name,
            "company": company_name,
            "account_id": (resolved_account or {}).get("account_id"),
            "account_name": (resolved_account or {}).get("account_name"),
            "source": lead.get("source"),
            "lifecycle_stage": "lead",
            "lead_score": lead.get("score"),
            "lead_tier": lead.get("tier"),
            "owner_id": lead.get("owner_id"),
            "tags": lead.get("tags", []),
            "status": "active",
            "converted_from_lead_id": lead_id,
            "created_by": user["id"],
            "created_at": now,
            "updated_at": now
        }
        await db.contacts.insert_one(contact)
    else:
        # Ensure contact has an account link
        account_name_input = (
            contact.get("account_name")
            or contact.get("company_name")
            or contact.get("company")
            or (contact.get("full_name") or "").strip()
            or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        )
        if account_name_input and not contact.get("account_id"):
            resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
            await db.contacts.update_one(
                {"id": contact_id, "tenant_id": tenant_id},
                {"$set": {
                    "account_id": resolved_account.get("account_id"),
                    "account_name": resolved_account.get("account_name"),
                    "updated_at": now
                }}
            )
            contact["account_id"] = resolved_account.get("account_id")
            contact["account_name"] = resolved_account.get("account_name")

    # Determine pipeline (default if not specified)
    pipeline = None
    if data.pipeline_id:
        pipeline = await db.pipelines.find_one(
            {"id": data.pipeline_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    else:
        pipeline = await db.pipelines.find_one(
            {"tenant_id": tenant_id, "is_default": True},
            {"_id": 0}
        )
        if not pipeline:
            pipeline = await db.pipelines.find_one({"tenant_id": tenant_id}, {"_id": 0})
        if not pipeline:
            raise HTTPException(status_code=400, detail="No pipelines configured for tenant")

    pipeline_id = pipeline["id"]

    # Determine stage (first stage if not specified)
    stage = None
    if data.stage_id:
        stage = await db.pipeline_stages.find_one(
            {"id": data.stage_id, "pipeline_id": pipeline_id},
            {"_id": 0}
        )
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
    else:
        stage_cursor = db.pipeline_stages.find(
            {"pipeline_id": pipeline_id},
            {"_id": 0}
        ).sort("display_order", 1).limit(1)
        stages = await stage_cursor.to_list(length=1)
        stage = stages[0] if stages else None
        if not stage:
            raise HTTPException(status_code=400, detail="Pipeline has no stages configured")

    def is_non_empty(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, tuple, set)):
            return len(value) > 0
        if isinstance(value, dict):
            return len(value) > 0
        return True

    deal_name = (data.deal_name or "").strip()
    if not deal_name:
        deal_name = (lead.get("company_name") or lead.get("full_name") or "New Deal").strip()

    amount = float(data.amount) if data.amount is not None else 0.0
    lead_score = int(lead.get("score") or 0)
    lead_tier = (lead.get("tier") or calculate_tier(lead_score)).strip().upper()
    if lead_tier not in VALID_LEAD_TIERS:
        lead_tier = calculate_tier(lead_score)

    deal = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": deal_name,
        "amount": amount,
        "currency": "USD",
        "status": "open",
        "contact_id": contact_id,
        "account_id": contact.get("account_id"),
        "account_name": contact.get("account_name"),
        "pipeline_id": pipeline_id,
        "stage_id": stage["id"],
        "next_step_at": data.next_step_at,
        "next_step_note": data.next_step_note,
        "lead_score": lead_score,
        "lead_tier": lead_tier,
        "sales_motion_type": lead.get("sales_motion_type") or "partnership_sales",
        "partner_id": lead.get("partner_id"),
        "product_id": lead.get("product_id"),
        "partner_name": lead.get("partner_name"),
        "product_name": lead.get("product_name"),
        "owner_id": lead.get("owner_id") or user["id"],
        "converted_from_lead_id": lead_id,
        "created_at": now,
        "updated_at": now
    }

    required_fields = stage.get("required_fields") or []
    missing = [field for field in required_fields if not is_non_empty(deal.get(field))]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for stage '{stage.get('name', 'Unknown')}': {', '.join(missing)}"
        )

    await db.deals.insert_one(deal)

    # Create/Sync Next Step task (discipline)
    if deal.get("next_step_at"):
        await upsert_open_next_step_task_for_deal(
            db=db,
            tenant_id=tenant_id,
            deal_id=deal["id"],
            due_at=deal.get("next_step_at"),
            owner_id=deal.get("owner_id") or user["id"],
            created_by=user["id"],
            note=deal.get("next_step_note")
        )

    # Timeline event (Deal created)
    await db.timeline_events.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "event_type": "deal_created",
        "title": f"Deal created: {deal_name}",
        "description": None,
        "actor_id": user["id"],
        "actor_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "deal_id": deal["id"],
        "contact_id": contact_id,
        "visibility": "internal_only",
        "metadata": {"converted_from_lead_id": lead_id},
        "created_at": now
    })

    # Update lead status + link records
    await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": {
            "status": "converted",
            "converted_at": now,
            "contact_id": contact_id,
            "deal_id": deal["id"],
            "updated_at": now
        }}
    )

    contact.pop("_id", None)
    deal.pop("_id", None)

    return {
        "lead_id": lead_id,
        "contact_id": contact_id,
        "deal_id": deal["id"],
        "contact": contact,
        "deal": deal,
        "message": "Lead pushed to Sales Pipeline"
    }


# ==================== STATS ENDPOINT ====================

@router.get("/stats/summary")
async def get_lead_stats(
    request: Request
):
    """Get lead statistics summary"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Total leads
    total = await db.leads.count_documents({"tenant_id": tenant_id})

    # By status
    new_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "new"})
    assigned_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "assigned"})
    working_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "working"})
    info_collected_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "info_collected"})
    unresponsive_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "unresponsive"})
    disqualified_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "disqualified"})
    qualified_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "qualified"})
    converted_count = await db.leads.count_documents({"tenant_id": tenant_id, "status": "converted"})

    # By tier
    tier_a = await db.leads.count_documents({"tenant_id": tenant_id, "tier": "A", "status": {"$ne": "converted"}})
    tier_b = await db.leads.count_documents({"tenant_id": tenant_id, "tier": "B", "status": {"$ne": "converted"}})
    tier_c = await db.leads.count_documents({"tenant_id": tenant_id, "tier": "C", "status": {"$ne": "converted"}})
    tier_d = await db.leads.count_documents({"tenant_id": tenant_id, "tier": "D", "status": {"$ne": "converted"}})

    # Average score (active leads only)
    pipeline = [
        {"$match": {"tenant_id": tenant_id, "status": {"$ne": "converted"}}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}}
    ]
    avg_result = await db.leads.aggregate(pipeline).to_list(length=1)
    avg_score = avg_result[0]["avg_score"] if avg_result else 0

    return {
        "total": total,
        "by_status": {
            "new": new_count,
            "assigned": assigned_count,
            "working": working_count,
            "info_collected": info_collected_count,
            "unresponsive": unresponsive_count,
            "disqualified": disqualified_count,
            "qualified": qualified_count,
            "converted": converted_count
        },
        "by_tier": {
            "A": tier_a,
            "B": tier_b,
            "C": tier_c,
            "D": tier_d
        },
        "average_score": round(avg_score, 1) if avg_score else 0
    }
