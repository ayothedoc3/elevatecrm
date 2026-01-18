"""
Email Campaigns API Routes

Handles all email campaign operations:
- Campaign CRUD operations
- Campaign scheduling and sending
- Analytics and tracking
"""

from fastapi import APIRouter, HTTPException, Query, Request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env')

from app.db.mongodb import get_database

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


# ==================== ENUMS ====================

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class CampaignType(str, Enum):
    EMAIL = "email"
    SMS = "sms"


# ==================== SCHEMAS ====================

class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject: Optional[str] = None
    content: str = Field(default="")
    campaign_type: CampaignType = CampaignType.EMAIL
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    status: Optional[CampaignStatus] = None
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


class SendTestEmailRequest(BaseModel):
    email: EmailStr


# ==================== HELPER FUNCTIONS ====================

async def get_current_user_from_token(request: Request):
    """Extract user from request"""
    from jose import jwt

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


# ==================== CRUD ENDPOINTS ====================

@router.get("")
async def list_campaigns(
    campaign_type: Optional[CampaignType] = None,
    status: Optional[CampaignStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """List all campaigns"""
    user = await get_current_user_from_token(request)
    db = get_database()

    query = {"tenant_id": user["tenant_id"]}

    if campaign_type:
        query["campaign_type"] = campaign_type.value
    if status:
        query["status"] = status.value
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"subject": {"$regex": search, "$options": "i"}}
        ]

    total = await db.campaigns.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.campaigns.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    campaigns = await cursor.to_list(length=page_size)

    return {
        "campaigns": campaigns,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", status_code=201)
async def create_campaign(
    data: CreateCampaignRequest,
    request: Request
):
    """Create a new campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "subject": data.subject,
        "content": data.content,
        "campaign_type": data.campaign_type.value,
        "status": CampaignStatus.DRAFT.value,
        "list_id": data.list_id,
        "scheduled_at": data.scheduled_at,
        "sent_at": None,
        "sent_count": 0,
        "delivered_count": 0,
        "open_count": 0,
        "click_count": 0,
        "bounce_count": 0,
        "unsubscribe_count": 0,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.campaigns.insert_one(campaign)

    return {k: v for k, v in campaign.items() if k != "_id"}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    request: Request
):
    """Get a specific campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: UpdateCampaignRequest,
    request: Request
):
    """Update a campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if "status" in update_data:
        update_data["status"] = update_data["status"].value

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": update_data}
    )

    return {"success": True}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    request: Request
):
    """Delete a campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    result = await db.campaigns.delete_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {"success": True}


# ==================== CAMPAIGN ACTIONS ====================

@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    request: Request
):
    """Send a campaign immediately"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign["status"] == CampaignStatus.SENT.value:
        raise HTTPException(status_code=400, detail="Campaign already sent")

    # Update campaign status to sending
    now = datetime.now(timezone.utc).isoformat()
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.SENDING.value,
            "updated_at": now
        }}
    )

    # In production, this would queue the campaign for sending
    # For demo, we simulate the send
    sent_count = 0
    if campaign.get("list_id"):
        # Count contacts in list
        list_members = await db.list_members.count_documents({"list_id": campaign["list_id"]})
        sent_count = list_members

    # Mark as sent
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.SENT.value,
            "sent_at": now,
            "sent_count": sent_count,
            "updated_at": now
        }}
    )

    return {
        "success": True,
        "message": f"Campaign sent to {sent_count} recipients"
    }


@router.post("/{campaign_id}/schedule")
async def schedule_campaign(
    campaign_id: str,
    scheduled_at: str,
    request: Request
):
    """Schedule a campaign for later"""
    user = await get_current_user_from_token(request)
    db = get_database()

    result = await db.campaigns.update_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "status": CampaignStatus.SCHEDULED.value,
            "scheduled_at": scheduled_at,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {"success": True, "scheduled_at": scheduled_at}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    request: Request
):
    """Pause a scheduled campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    result = await db.campaigns.update_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"$set": {
            "status": CampaignStatus.PAUSED.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {"success": True}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    request: Request
):
    """Resume a paused campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    new_status = CampaignStatus.SCHEDULED.value if campaign.get("scheduled_at") else CampaignStatus.DRAFT.value

    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"success": True, "status": new_status}


@router.post("/{campaign_id}/duplicate")
async def duplicate_campaign(
    campaign_id: str,
    request: Request
):
    """Duplicate a campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    new_campaign = {
        **campaign,
        "id": str(uuid.uuid4()),
        "name": f"{campaign['name']} (Copy)",
        "status": CampaignStatus.DRAFT.value,
        "scheduled_at": None,
        "sent_at": None,
        "sent_count": 0,
        "delivered_count": 0,
        "open_count": 0,
        "click_count": 0,
        "bounce_count": 0,
        "unsubscribe_count": 0,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.campaigns.insert_one(new_campaign)

    return {k: v for k, v in new_campaign.items() if k != "_id"}


@router.post("/{campaign_id}/test")
async def send_test_email(
    campaign_id: str,
    data: SendTestEmailRequest,
    request: Request
):
    """Send a test email"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # In production, this would send a real test email
    # For demo, we just log it
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[SIMULATED] Sending test email to {data.email}: {campaign['subject']}")

    return {
        "success": True,
        "message": f"Test email sent to {data.email}"
    }


# ==================== ANALYTICS ENDPOINTS ====================

@router.get("/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    request: Request
):
    """Get analytics for a campaign"""
    user = await get_current_user_from_token(request)
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Calculate rates
    sent = campaign.get("sent_count", 0)
    opens = campaign.get("open_count", 0)
    clicks = campaign.get("click_count", 0)
    bounces = campaign.get("bounce_count", 0)
    unsubscribes = campaign.get("unsubscribe_count", 0)

    open_rate = round((opens / sent * 100), 2) if sent > 0 else 0
    click_rate = round((clicks / sent * 100), 2) if sent > 0 else 0
    bounce_rate = round((bounces / sent * 100), 2) if sent > 0 else 0
    unsubscribe_rate = round((unsubscribes / sent * 100), 2) if sent > 0 else 0

    return {
        "campaign_id": campaign_id,
        "name": campaign["name"],
        "status": campaign["status"],
        "sent_count": sent,
        "delivered_count": campaign.get("delivered_count", 0),
        "open_count": opens,
        "click_count": clicks,
        "bounce_count": bounces,
        "unsubscribe_count": unsubscribes,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "bounce_rate": bounce_rate,
        "unsubscribe_rate": unsubscribe_rate,
        "sent_at": campaign.get("sent_at")
    }


@router.get("/stats/overview")
async def get_campaigns_stats(
    request: Request
):
    """Get overall campaign statistics"""
    user = await get_current_user_from_token(request)
    db = get_database()

    query = {"tenant_id": user["tenant_id"]}

    total = await db.campaigns.count_documents(query)
    draft = await db.campaigns.count_documents({**query, "status": CampaignStatus.DRAFT.value})
    scheduled = await db.campaigns.count_documents({**query, "status": CampaignStatus.SCHEDULED.value})
    sent = await db.campaigns.count_documents({**query, "status": CampaignStatus.SENT.value})

    # Aggregate totals
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": None,
            "total_sent": {"$sum": "$sent_count"},
            "total_opens": {"$sum": "$open_count"},
            "total_clicks": {"$sum": "$click_count"}
        }}
    ]
    agg_result = await db.campaigns.aggregate(pipeline).to_list(length=1)
    totals = agg_result[0] if agg_result else {"total_sent": 0, "total_opens": 0, "total_clicks": 0}

    return {
        "total_campaigns": total,
        "draft_count": draft,
        "scheduled_count": scheduled,
        "sent_count": sent,
        "total_emails_sent": totals.get("total_sent", 0),
        "total_opens": totals.get("total_opens", 0),
        "total_clicks": totals.get("total_clicks", 0)
    }
