"""
Elev8 CRM - Handoff to Delivery Routes

Implements the "Closed Won" handoff process per PRD Section 11.

Required artifacts for handoff:
- SPICED summary
- Gap analysis
- Proposal
- Contract
- Risk notes
- Kickoff readiness checklist

Handoff must:
- Assign delivery owner
- Schedule kickoff
- Lock sales stages
- Timestamp completion
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from app.db.mongodb import get_database
from app.api.elev8.auth import get_current_user

router = APIRouter(tags=["Handoff to Delivery"])


# ==================== SCHEMAS ====================

class HandoffArtifact(BaseModel):
    """Individual handoff artifact"""
    artifact_type: str  # spiced_summary, gap_analysis, proposal, contract, risk_notes, kickoff_checklist
    title: str
    content: Optional[str] = None
    file_url: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None


class HandoffInitiate(BaseModel):
    """Initiate handoff request"""
    delivery_owner_id: str
    kickoff_date: Optional[str] = None
    notes: Optional[str] = None


class HandoffComplete(BaseModel):
    """Complete handoff request"""
    final_notes: Optional[str] = None


class HandoffArtifactUpdate(BaseModel):
    """Update an artifact"""
    title: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    completed: bool = False


# ==================== HANDOFF ENDPOINTS ====================

@router.get("/deals/{deal_id}/handoff-status")
async def get_handoff_status(
    deal_id: str,
    user = Depends(get_current_user)
):
    """
    Get handoff status and artifact completion for a deal.
    """
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get or create handoff record
    handoff = await db.deal_handoffs.find_one(
        {"deal_id": deal_id},
        {"_id": 0}
    )
    
    # Define required artifacts
    required_artifacts = [
        {"type": "spiced_summary", "name": "SPICED Summary", "required": True},
        {"type": "gap_analysis", "name": "Gap Analysis", "required": True},
        {"type": "proposal", "name": "Proposal", "required": True},
        {"type": "contract", "name": "Contract", "required": True},
        {"type": "risk_notes", "name": "Risk Notes", "required": False},
        {"type": "kickoff_checklist", "name": "Kickoff Readiness Checklist", "required": True}
    ]
    
    # Check SPICED from deal
    has_spiced = bool(deal.get("spiced_situation") and deal.get("spiced_pain") and deal.get("spiced_impact"))
    
    # Calculate readiness
    if handoff:
        artifacts = handoff.get("artifacts", [])
        completed_required = sum(
            1 for a in artifacts 
            if a.get("completed") and any(r["type"] == a["artifact_type"] and r["required"] for r in required_artifacts)
        )
        total_required = sum(1 for r in required_artifacts if r["required"])
        
        # SPICED counts as one
        if has_spiced:
            completed_required += 1
        total_required += 1  # Add SPICED to required
        
        readiness_percentage = int((completed_required / max(total_required, 1)) * 100)
    else:
        readiness_percentage = 10 if has_spiced else 0
    
    return {
        "deal_id": deal_id,
        "deal_name": deal.get("name"),
        "deal_status": deal.get("status"),
        "amount": deal.get("amount", 0),
        "handoff_initiated": handoff is not None,
        "handoff_completed": handoff.get("completed") if handoff else False,
        "delivery_owner_id": handoff.get("delivery_owner_id") if handoff else None,
        "kickoff_date": handoff.get("kickoff_date") if handoff else None,
        "artifacts": handoff.get("artifacts", []) if handoff else [],
        "required_artifacts": required_artifacts,
        "has_spiced": has_spiced,
        "readiness_percentage": readiness_percentage,
        "can_complete": readiness_percentage >= 80 and deal.get("status") == "won"
    }


@router.post("/deals/{deal_id}/handoff/initiate")
async def initiate_handoff(
    deal_id: str,
    data: HandoffInitiate,
    user = Depends(get_current_user)
):
    """
    Initiate handoff to delivery for a Closed Won deal.
    Creates handoff record and assigns delivery owner.
    """
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    if deal.get("status") != "won":
        raise HTTPException(
            status_code=400, 
            detail="Handoff can only be initiated for Closed Won deals"
        )
    
    # Check if handoff already exists
    existing = await db.deal_handoffs.find_one({"deal_id": deal_id})
    if existing:
        raise HTTPException(status_code=400, detail="Handoff already initiated for this deal")
    
    # Verify delivery owner exists
    delivery_owner = await db.users.find_one({"id": data.delivery_owner_id}, {"_id": 0})
    if not delivery_owner:
        raise HTTPException(status_code=404, detail="Delivery owner not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create handoff record
    handoff = {
        "id": str(uuid.uuid4()),
        "deal_id": deal_id,
        "tenant_id": user["tenant_id"],
        "delivery_owner_id": data.delivery_owner_id,
        "delivery_owner_name": f"{delivery_owner.get('first_name', '')} {delivery_owner.get('last_name', '')}".strip(),
        "sales_owner_id": deal.get("owner_id"),
        "kickoff_date": data.kickoff_date,
        "notes": data.notes,
        "artifacts": [],
        "status": "initiated",
        "completed": False,
        "initiated_at": now,
        "initiated_by": user["id"],
        "completed_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.deal_handoffs.insert_one(handoff)
    
    # Update deal with handoff info
    await db.deals.update_one(
        {"id": deal_id},
        {"$set": {
            "handoff_initiated": True,
            "handoff_id": handoff["id"],
            "delivery_owner_id": data.delivery_owner_id,
            "updated_at": now
        }}
    )
    
    # Create activity log
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "type": "handoff_initiated",
        "deal_id": deal_id,
        "user_id": user["id"],
        "description": f"Handoff initiated for deal. Delivery owner: {handoff['delivery_owner_name']}",
        "created_at": now
    })
    
    handoff.pop("_id", None)
    return handoff


@router.put("/deals/{deal_id}/handoff/artifact")
async def update_handoff_artifact(
    deal_id: str,
    artifact_type: str = Query(..., description="Type: spiced_summary, gap_analysis, proposal, contract, risk_notes, kickoff_checklist"),
    data: HandoffArtifactUpdate = None,
    user = Depends(get_current_user)
):
    """
    Add or update a handoff artifact.
    """
    db = get_database()
    
    handoff = await db.deal_handoffs.find_one(
        {"deal_id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found. Initiate handoff first.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Find or create artifact
    artifacts = handoff.get("artifacts", [])
    artifact_index = next(
        (i for i, a in enumerate(artifacts) if a["artifact_type"] == artifact_type),
        None
    )
    
    artifact = {
        "artifact_type": artifact_type,
        "title": data.title if data else artifact_type.replace("_", " ").title(),
        "content": data.content if data else None,
        "file_url": data.file_url if data else None,
        "completed": data.completed if data else False,
        "completed_at": now if (data and data.completed) else None,
        "completed_by": user["id"] if (data and data.completed) else None,
        "updated_at": now
    }
    
    if artifact_index is not None:
        artifacts[artifact_index] = artifact
    else:
        artifact["created_at"] = now
        artifacts.append(artifact)
    
    # Update handoff
    await db.deal_handoffs.update_one(
        {"deal_id": deal_id},
        {"$set": {"artifacts": artifacts, "updated_at": now}}
    )
    
    return {"message": "Artifact updated", "artifact": artifact}


@router.post("/deals/{deal_id}/handoff/complete")
async def complete_handoff(
    deal_id: str,
    data: HandoffComplete = None,
    user = Depends(get_current_user)
):
    """
    Complete the handoff to delivery.
    Locks sales stages and timestamps completion.
    """
    db = get_database()
    
    handoff = await db.deal_handoffs.find_one(
        {"deal_id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    if handoff.get("completed"):
        raise HTTPException(status_code=400, detail="Handoff already completed")
    
    # Get deal to check SPICED
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    
    # Check required artifacts
    artifacts = handoff.get("artifacts", [])
    required_types = ["gap_analysis", "proposal", "contract", "kickoff_checklist"]
    
    missing = []
    for req in required_types:
        artifact = next((a for a in artifacts if a["artifact_type"] == req), None)
        if not artifact or not artifact.get("completed"):
            missing.append(req.replace("_", " ").title())
    
    # Check SPICED
    has_spiced = bool(
        deal.get("spiced_situation") and 
        deal.get("spiced_pain") and 
        deal.get("spiced_impact")
    )
    if not has_spiced:
        missing.append("SPICED Summary")
    
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete handoff. Missing required artifacts: {', '.join(missing)}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Complete handoff
    await db.deal_handoffs.update_one(
        {"deal_id": deal_id},
        {"$set": {
            "status": "completed",
            "completed": True,
            "completed_at": now,
            "completed_by": user["id"],
            "final_notes": data.final_notes if data else None,
            "updated_at": now
        }}
    )
    
    # Lock deal - move to "Handoff to Delivery" stage
    await db.deals.update_one(
        {"id": deal_id},
        {"$set": {
            "stage_name": "Handoff to Delivery",
            "handoff_completed": True,
            "handoff_completed_at": now,
            "sales_locked": True,  # Lock sales stages
            "updated_at": now
        }}
    )
    
    # Create activity log
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "type": "handoff_completed",
        "deal_id": deal_id,
        "user_id": user["id"],
        "description": "Handoff to delivery completed. Sales stages locked.",
        "created_at": now
    })
    
    return {
        "message": "Handoff completed successfully",
        "deal_id": deal_id,
        "completed_at": now,
        "sales_locked": True
    }


@router.get("/handoffs")
async def list_handoffs(
    status: Optional[str] = Query(None, description="Filter by status: initiated, completed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user = Depends(get_current_user)
):
    """
    List all handoffs for the tenant.
    """
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status
    
    total = await db.deal_handoffs.count_documents(query)
    skip = (page - 1) * page_size
    
    handoffs = await db.deal_handoffs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)
    
    # Enrich with deal info
    for h in handoffs:
        deal = await db.deals.find_one({"id": h["deal_id"]}, {"_id": 0, "name": 1, "amount": 1})
        if deal:
            h["deal_name"] = deal.get("name")
            h["deal_amount"] = deal.get("amount")
    
    return {
        "handoffs": handoffs,
        "total": total,
        "page": page,
        "page_size": page_size
    }



# ==================== USERS ENDPOINT ====================

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user = Depends(get_current_user)
):
    """
    List users for the tenant (for delivery owner selection).
    """
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"], "is_active": True}
    
    total = await db.users.count_documents(query)
    skip = (page - 1) * page_size
    
    users = await db.users.find(
        query,
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1, "role": 1}
    ).skip(skip).limit(page_size).to_list(length=page_size)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size
    }
