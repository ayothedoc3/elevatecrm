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
    status: Optional[str] = None
    notes: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None


class LeadAssignRequest(BaseModel):
    owner_id: str


class LeadScoreRequest(BaseModel):
    score: int = Field(..., ge=0, le=100)
    scoring_data: Optional[Dict[str, Any]] = None


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
            owner = await db.users.find_one({"id": lead["owner_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
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
        "status": "new",
        "notes": data.notes,
        "tags": data.tags,
        "owner_id": None,
        "assigned_at": None,
        "converted_at": None,
        "contact_id": None,  # Set when converted to contact
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
        owner = await db.users.find_one({"id": lead["owner_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
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
        update_data["status"] = data.status
    if data.notes is not None:
        update_data["notes"] = data.notes
    if data.owner_id is not None:
        update_data["owner_id"] = data.owner_id
        if not lead.get("assigned_at"):
            update_data["assigned_at"] = datetime.now(timezone.utc).isoformat()
    if data.tags is not None:
        update_data["tags"] = data.tags

    # Update full_name if name changed
    first_name = update_data.get("first_name", lead.get("first_name", ""))
    last_name = update_data.get("last_name", lead.get("last_name", ""))
    update_data["full_name"] = f"{first_name} {last_name}".strip()

    await db.leads.update_one(
        {"id": lead_id},
        {"$set": update_data}
    )

    # Return updated lead
    updated = await db.leads.find_one({"id": lead_id}, {"_id": 0})
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
        {"id": lead_id},
        {"$set": {
            "owner_id": data.owner_id,
            "assigned_at": now,
            "status": "assigned" if lead.get("status") == "new" else lead.get("status"),
            "updated_at": now
        }}
    )

    updated = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    updated["owner_name"] = f"{owner['first_name']} {owner['last_name']}"

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

    tier = calculate_tier(data.score)
    now = datetime.now(timezone.utc).isoformat()

    update_data = {
        "score": data.score,
        "tier": tier,
        "updated_at": now
    }

    if data.scoring_data:
        update_data["scoring_data"] = data.scoring_data

    await db.leads.update_one(
        {"id": lead_id},
        {"$set": update_data}
    )

    updated = await db.leads.find_one({"id": lead_id}, {"_id": 0})
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
    new_contact = {
        "id": contact_id,
        "tenant_id": tenant_id,
        "first_name": lead.get("first_name"),
        "last_name": lead.get("last_name"),
        "full_name": lead.get("full_name"),
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "company_name": lead.get("company_name"),
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
        {"id": lead_id},
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
