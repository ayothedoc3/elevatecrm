"""
Elev8 CRM - Partner Routes

Partner management endpoints for Partner Sales motion.
Per Elev8 specification section 12.
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.db.mongodb import get_database
from .auth import get_current_user
from .models import PartnerCreate, PartnerUpdate

router = APIRouter(tags=["Partners"])


@router.get("/partners")
async def list_partners(
    user = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    partner_type: Optional[str] = None
):
    """List partners"""
    
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


@router.post("/partners", status_code=http_status.HTTP_201_CREATED)
async def create_partner(data: PartnerCreate, user = Depends(get_current_user)):
    """Create a new partner"""
    
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
async def get_partner(partner_id: str, user = Depends(get_current_user)):
    """Get a specific partner"""
    
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
async def update_partner(partner_id: str, data: PartnerUpdate, user = Depends(get_current_user)):
    """Update a partner"""
    
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.partners.update_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Return updated partner
    updated_partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    return updated_partner


@router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str, user = Depends(get_current_user)):
    """Delete a partner"""
    
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
