"""
Elev8 CRM - Lead Routes

Lead management endpoints including:
- CRUD operations
- Lead scoring
- Qualification flow to Sales Pipeline
- Touchpoint tracking

Per Elev8 specification sections 5.1, 6, and 7.
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.db.mongodb import get_database
from .auth import get_current_user
from .models import (
    LeadCreate, LeadUpdate, LeadStatus, LeadTier, SalesMotionType
)
from .scoring import calculate_lead_score, get_tier_probability, get_score_breakdown

router = APIRouter(tags=["Leads"])


@router.get("/leads")
async def list_leads(
    user = Depends(get_current_user),
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


@router.post("/leads", status_code=http_status.HTTP_201_CREATED)
async def create_lead(data: LeadCreate, user = Depends(get_current_user)):
    """Create a new lead"""
    
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


@router.get("/leads/scoring/stats")
async def get_lead_scoring_stats(user = Depends(get_current_user)):
    """Get lead scoring statistics and tier distribution"""
    
    db = get_database()
    
    # Aggregate tier distribution
    pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {
            "_id": "$tier",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$lead_score"},
            "total_value": {"$sum": {"$ifNull": ["$estimated_value", 0]}}
        }}
    ]
    
    tier_results = await db.leads.aggregate(pipeline).to_list(length=10)
    
    tier_distribution = {
        "A": {"count": 0, "avg_score": 0, "total_value": 0},
        "B": {"count": 0, "avg_score": 0, "total_value": 0},
        "C": {"count": 0, "avg_score": 0, "total_value": 0},
        "D": {"count": 0, "avg_score": 0, "total_value": 0}
    }
    
    for result in tier_results:
        tier = result["_id"]
        if tier in tier_distribution:
            tier_distribution[tier] = {
                "count": result["count"],
                "avg_score": round(result["avg_score"], 1) if result["avg_score"] else 0,
                "total_value": result["total_value"]
            }
    
    # Status distribution
    status_pipeline = [
        {"$match": {"tenant_id": user["tenant_id"]}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    status_results = await db.leads.aggregate(status_pipeline).to_list(length=20)
    status_distribution = {r["_id"]: r["count"] for r in status_results}
    
    return {
        "tier_distribution": tier_distribution,
        "status_distribution": status_distribution,
        "total_leads": sum(t["count"] for t in tier_distribution.values())
    }


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, user = Depends(get_current_user)):
    """Get a specific lead"""
    
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


@router.get("/leads/{lead_id}/score-breakdown")
async def get_lead_score_breakdown(lead_id: str, user = Depends(get_current_user)):
    """
    Get detailed score breakdown for a lead.
    Used by AI Assistant to explain scores (read-only).
    """
    db = get_database()
    
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return get_score_breakdown(lead)


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, data: LeadUpdate, user = Depends(get_current_user)):
    """Update a lead"""
    
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
    
    # Return updated lead
    updated_lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    return updated_lead


@router.post("/leads/{lead_id}/qualify")
async def qualify_lead(lead_id: str, user = Depends(get_current_user)):
    """
    Qualify a lead and push to Sales Pipeline.
    Creates a Deal from the lead per Section 5.1.
    """
    
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
    
    # Get first stage of sales pipeline
    first_stage = await db.pipeline_stages.find_one(
        {"pipeline_id": sales_pipeline["id"]},
        {"_id": 0},
        sort=[("display_order", 1)]
    )
    
    if not first_stage:
        raise HTTPException(status_code=400, detail="Sales pipeline has no stages")
    
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
async def record_touchpoint(lead_id: str, user = Depends(get_current_user)):
    """Record a touchpoint/activity for a lead"""
    
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
async def delete_lead(lead_id: str, user = Depends(get_current_user)):
    """Delete a lead"""
    
    db = get_database()
    
    result = await db.leads.delete_one(
        {"id": lead_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted"}
