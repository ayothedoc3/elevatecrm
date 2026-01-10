"""
External API Module for Labyrinth OS Integration

Provides:
- Pull API endpoints for bulk data retrieval
- Push webhooks for real-time events
- API Key authentication
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import hashlib
import hmac
import httpx
import json

router = APIRouter(prefix="/external", tags=["External API"])

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

def get_database():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


# ==================== API KEY AUTHENTICATION ====================

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key and return associated tenant"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    db = get_database()
    
    # Hash the provided key to compare
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    api_key = await db.api_keys.find_one({
        "key_hash": key_hash,
        "is_active": True
    })
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    # Update last used
    await db.api_keys.update_one(
        {"_id": api_key["_id"]},
        {"$set": {"last_used": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "tenant_id": api_key["tenant_id"],
        "key_id": api_key["id"],
        "permissions": api_key.get("permissions", ["read"])
    }


# ==================== MODELS ====================

class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Friendly name for the API key")
    permissions: List[str] = Field(default=["read"], description="Permissions: read, write, webhook")
    expires_in_days: Optional[int] = Field(default=None, description="Days until expiration (null = never)")

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # Only returned on creation
    permissions: List[str]
    created_at: str
    expires_at: Optional[str]

class WebhookConfig(BaseModel):
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(default=None, description="Secret for signature verification")
    is_active: bool = Field(default=True)
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers to send")

class WebhookEvent(BaseModel):
    event_type: str
    timestamp: str
    tenant_id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


# ==================== API KEY MANAGEMENT ====================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    data: APIKeyCreate,
    tenant_id: str = Query(..., description="Tenant ID to create key for")
):
    """
    Create a new API key for external access.
    The key is only shown once - store it securely!
    """
    db = get_database()
    
    # Generate secure random key
    raw_key = f"elk_{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}"  # elk = elevate labyrinth key
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    now = datetime.now(timezone.utc)
    expires_at = None
    if data.expires_in_days:
        expires_at = (now + timedelta(days=data.expires_in_days)).isoformat()
    
    api_key = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "key_hash": key_hash,
        "key_prefix": raw_key[:12],  # Store prefix for identification
        "tenant_id": tenant_id,
        "permissions": data.permissions,
        "is_active": True,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "last_used": None
    }
    
    await db.api_keys.insert_one(api_key)
    
    return APIKeyResponse(
        id=api_key["id"],
        name=api_key["name"],
        key=raw_key,  # Only time we return the full key
        permissions=api_key["permissions"],
        created_at=api_key["created_at"],
        expires_at=api_key["expires_at"]
    )


@router.get("/api-keys")
async def list_api_keys(tenant_id: str = Query(...)):
    """List all API keys for a tenant (without the actual keys)"""
    db = get_database()
    
    keys = await db.api_keys.find(
        {"tenant_id": tenant_id},
        {"_id": 0, "key_hash": 0}
    ).to_list(100)
    
    return {"api_keys": keys}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, tenant_id: str = Query(...)):
    """Revoke an API key"""
    db = get_database()
    
    result = await db.api_keys.update_one(
        {"id": key_id, "tenant_id": tenant_id},
        {"$set": {"is_active": False, "revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked"}


# ==================== PULL API - BULK DATA ENDPOINTS ====================

@router.get("/deals")
async def get_deals(
    api_key: dict = Depends(verify_api_key),
    status: Optional[str] = Query(None, description="Filter by status: open, won, lost"),
    stage: Optional[str] = Query(None, description="Filter by stage name"),
    since: Optional[str] = Query(None, description="ISO timestamp - get deals updated since"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Get all deals for the tenant.
    Supports filtering by status, stage, and last update time.
    """
    db = get_database()
    
    query = {"tenant_id": api_key["tenant_id"]}
    if status:
        query["status"] = status
    if stage:
        query["stage_name"] = stage
    if since:
        query["updated_at"] = {"$gte": since}
    
    total = await db.deals.count_documents(query)
    skip = (page - 1) * page_size
    
    deals = await db.deals.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "deals": deals,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(deals) < total
    }


@router.get("/leads")
async def get_leads(
    api_key: dict = Depends(verify_api_key),
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by tier: A, B, C, D"),
    since: Optional[str] = Query(None, description="ISO timestamp - get leads updated since"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Get all leads for the tenant.
    Supports filtering by status, tier, and last update time.
    """
    db = get_database()
    
    query = {"tenant_id": api_key["tenant_id"]}
    if status:
        query["status"] = status
    if tier:
        query["tier"] = tier
    if since:
        query["updated_at"] = {"$gte": since}
    
    total = await db.leads.count_documents(query)
    skip = (page - 1) * page_size
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "leads": leads,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(leads) < total
    }


@router.get("/tasks")
async def get_tasks(
    api_key: dict = Depends(verify_api_key),
    status: Optional[str] = Query(None, description="Filter by status: pending, completed, overdue"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    since: Optional[str] = Query(None, description="ISO timestamp - get tasks updated since"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Get all tasks for the tenant.
    """
    db = get_database()
    
    query = {"tenant_id": api_key["tenant_id"]}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if since:
        query["updated_at"] = {"$gte": since}
    
    total = await db.tasks.count_documents(query)
    skip = (page - 1) * page_size
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(tasks) < total
    }


@router.get("/kpis")
async def get_kpis(
    api_key: dict = Depends(verify_api_key),
    period: str = Query("month", description="Period: week, month, quarter, year")
):
    """
    Get KPI metrics for the tenant.
    Includes pipeline value, win rate, conversion rates, etc.
    """
    db = get_database()
    tenant_id = api_key["tenant_id"]
    now = datetime.now(timezone.utc)
    
    # Calculate period start
    if period == "week":
        period_start = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        period_start = (now - timedelta(days=30)).isoformat()
    elif period == "quarter":
        period_start = (now - timedelta(days=90)).isoformat()
    else:  # year
        period_start = (now - timedelta(days=365)).isoformat()
    
    # Aggregate metrics
    total_leads = await db.leads.count_documents({"tenant_id": tenant_id})
    qualified_leads = await db.leads.count_documents({"tenant_id": tenant_id, "status": "qualified"})
    
    total_deals = await db.deals.count_documents({"tenant_id": tenant_id})
    open_deals = await db.deals.count_documents({"tenant_id": tenant_id, "status": "open"})
    won_deals = await db.deals.count_documents({"tenant_id": tenant_id, "status": "won"})
    lost_deals = await db.deals.count_documents({"tenant_id": tenant_id, "status": "lost"})
    
    # Pipeline value
    pipeline = await db.deals.aggregate([
        {"$match": {"tenant_id": tenant_id, "status": "open"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    pipeline_value = pipeline[0]["total"] if pipeline else 0
    
    # Won value
    won = await db.deals.aggregate([
        {"$match": {"tenant_id": tenant_id, "status": "won"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    won_value = won[0]["total"] if won else 0
    
    # Tasks metrics
    total_tasks = await db.tasks.count_documents({"tenant_id": tenant_id})
    overdue_tasks = await db.tasks.count_documents({
        "tenant_id": tenant_id,
        "status": {"$in": ["pending", "in_progress"]},
        "due_date": {"$lt": now.isoformat()}
    })
    
    # Calculate rates
    win_rate = (won_deals / (won_deals + lost_deals) * 100) if (won_deals + lost_deals) > 0 else 0
    qualification_rate = (qualified_leads / total_leads * 100) if total_leads > 0 else 0
    
    return {
        "period": period,
        "period_start": period_start,
        "generated_at": now.isoformat(),
        "leads": {
            "total": total_leads,
            "qualified": qualified_leads,
            "qualification_rate": round(qualification_rate, 1)
        },
        "deals": {
            "total": total_deals,
            "open": open_deals,
            "won": won_deals,
            "lost": lost_deals,
            "win_rate": round(win_rate, 1)
        },
        "pipeline": {
            "value": pipeline_value,
            "won_value": won_value
        },
        "tasks": {
            "total": total_tasks,
            "overdue": overdue_tasks
        }
    }


@router.get("/pipeline")
async def get_pipeline_data(
    api_key: dict = Depends(verify_api_key),
    pipeline_type: Optional[str] = Query(None, description="Filter: qualification, sales")
):
    """
    Get pipeline/funnel data with stage breakdown.
    """
    db = get_database()
    tenant_id = api_key["tenant_id"]
    
    # Get pipelines
    pipeline_query = {"tenant_id": tenant_id}
    if pipeline_type:
        pipeline_query["pipeline_type"] = pipeline_type
    
    pipelines = await db.pipelines.find(pipeline_query, {"_id": 0}).to_list(10)
    
    # Get deals by stage
    stage_data = await db.deals.aggregate([
        {"$match": {"tenant_id": tenant_id, "status": "open"}},
        {"$group": {
            "_id": "$stage_name",
            "count": {"$sum": 1},
            "value": {"$sum": "$amount"},
            "avg_value": {"$avg": "$amount"}
        }}
    ]).to_list(50)
    
    stage_map = {s["_id"]: s for s in stage_data}
    
    # Enrich pipelines with deal counts
    for pipeline in pipelines:
        if pipeline.get("stages"):
            for stage in pipeline["stages"]:
                stage_info = stage_map.get(stage.get("name"), {})
                stage["deal_count"] = stage_info.get("count", 0)
                stage["deal_value"] = stage_info.get("value", 0)
                stage["avg_deal_value"] = stage_info.get("avg_value", 0)
    
    return {
        "pipelines": pipelines,
        "stage_summary": stage_data
    }


@router.get("/activity")
async def get_activity_log(
    api_key: dict = Depends(verify_api_key),
    entity_type: Optional[str] = Query(None, description="Filter: deal, lead, task"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    since: Optional[str] = Query(None, description="ISO timestamp"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """
    Get activity/audit log for the tenant.
    """
    db = get_database()
    
    query = {"tenant_id": api_key["tenant_id"]}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if since:
        query["created_at"] = {"$gte": since}
    
    total = await db.activity_log.count_documents(query)
    skip = (page - 1) * page_size
    
    activities = await db.activity_log.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "activities": activities,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(activities) < total
    }


@router.get("/partners")
async def get_partners(
    api_key: dict = Depends(verify_api_key),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    """
    Get all partners for the tenant.
    """
    db = get_database()
    
    query = {"tenant_id": api_key["tenant_id"]}
    if status:
        query["status"] = status
    
    total = await db.partners.count_documents(query)
    skip = (page - 1) * page_size
    
    partners = await db.partners.find(query, {"_id": 0}).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "partners": partners,
        "total": total,
        "page": page,
        "page_size": page_size
    }


# ==================== WEBHOOK CONFIGURATION ====================

@router.post("/webhooks")
async def create_webhook(
    config: WebhookConfig,
    api_key: dict = Depends(verify_api_key)
):
    """
    Register a webhook endpoint for real-time events.
    
    Available events:
    - deal.created, deal.updated, deal.stage_changed, deal.won, deal.lost
    - lead.created, lead.updated, lead.qualified, lead.disqualified
    - task.created, task.completed, task.overdue
    - sla.breach, sla.warning
    - handoff.initiated, handoff.completed
    """
    db = get_database()
    
    # Generate webhook secret if not provided
    secret = config.secret or f"whsec_{uuid.uuid4().hex}"
    
    webhook = {
        "id": str(uuid.uuid4()),
        "tenant_id": api_key["tenant_id"],
        "url": config.url,
        "events": config.events,
        "secret": secret,
        "is_active": config.is_active,
        "headers": config.headers,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failure_count": 0,
        "last_triggered": None
    }
    
    await db.webhooks.insert_one(webhook)
    
    return {
        "id": webhook["id"],
        "url": webhook["url"],
        "events": webhook["events"],
        "secret": secret,  # Return secret for signature verification
        "is_active": webhook["is_active"],
        "created_at": webhook["created_at"]
    }


@router.get("/webhooks")
async def list_webhooks(api_key: dict = Depends(verify_api_key)):
    """List all webhooks for the tenant"""
    db = get_database()
    
    webhooks = await db.webhooks.find(
        {"tenant_id": api_key["tenant_id"]},
        {"_id": 0, "secret": 0}  # Don't expose secrets
    ).to_list(50)
    
    return {"webhooks": webhooks}


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    config: WebhookConfig,
    api_key: dict = Depends(verify_api_key)
):
    """Update a webhook configuration"""
    db = get_database()
    
    update_data = {
        "url": config.url,
        "events": config.events,
        "is_active": config.is_active,
        "headers": config.headers,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if config.secret:
        update_data["secret"] = config.secret
    
    result = await db.webhooks.update_one(
        {"id": webhook_id, "tenant_id": api_key["tenant_id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"message": "Webhook updated"}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, api_key: dict = Depends(verify_api_key)):
    """Delete a webhook"""
    db = get_database()
    
    result = await db.webhooks.delete_one({
        "id": webhook_id,
        "tenant_id": api_key["tenant_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"message": "Webhook deleted"}


# ==================== WEBHOOK DELIVERY SERVICE ====================

async def trigger_webhook(tenant_id: str, event_type: str, data: dict, metadata: dict = None):
    """
    Trigger webhooks for an event.
    Called internally when CRM events occur.
    """
    db = get_database()
    
    # Find active webhooks subscribed to this event
    webhooks = await db.webhooks.find({
        "tenant_id": tenant_id,
        "is_active": True,
        "events": {"$in": [event_type, "*"]}  # Support wildcard
    }).to_list(50)
    
    if not webhooks:
        return
    
    now = datetime.now(timezone.utc)
    
    payload = WebhookEvent(
        event_type=event_type,
        timestamp=now.isoformat(),
        tenant_id=tenant_id,
        data=data,
        metadata=metadata
    ).dict()
    
    # Deliver to each webhook
    async with httpx.AsyncClient(timeout=10.0) as client:
        for webhook in webhooks:
            try:
                # Create signature
                payload_bytes = json.dumps(payload, default=str).encode()
                signature = hmac.new(
                    webhook["secret"].encode(),
                    payload_bytes,
                    hashlib.sha256
                ).hexdigest()
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": f"sha256={signature}",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Timestamp": now.isoformat()
                }
                
                # Add custom headers if configured
                if webhook.get("headers"):
                    headers.update(webhook["headers"])
                
                response = await client.post(
                    webhook["url"],
                    json=payload,
                    headers=headers
                )
                
                # Log delivery
                await db.webhook_logs.insert_one({
                    "webhook_id": webhook["id"],
                    "event_type": event_type,
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "timestamp": now.isoformat()
                })
                
                # Reset failure count on success
                if response.status_code < 400:
                    await db.webhooks.update_one(
                        {"id": webhook["id"]},
                        {"$set": {"failure_count": 0, "last_triggered": now.isoformat()}}
                    )
                else:
                    # Increment failure count
                    await db.webhooks.update_one(
                        {"id": webhook["id"]},
                        {"$inc": {"failure_count": 1}, "$set": {"last_triggered": now.isoformat()}}
                    )
                    
            except Exception as e:
                # Log failure
                await db.webhook_logs.insert_one({
                    "webhook_id": webhook["id"],
                    "event_type": event_type,
                    "error": str(e),
                    "success": False,
                    "timestamp": now.isoformat()
                })
                
                # Increment failure count
                await db.webhooks.update_one(
                    {"id": webhook["id"]},
                    {"$inc": {"failure_count": 1}}
                )


@router.post("/webhooks/test/{webhook_id}")
async def test_webhook(
    webhook_id: str,
    background_tasks: BackgroundTasks,
    api_key: dict = Depends(verify_api_key)
):
    """Send a test event to a webhook"""
    db = get_database()
    
    webhook = await db.webhooks.find_one({
        "id": webhook_id,
        "tenant_id": api_key["tenant_id"]
    })
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Queue test delivery
    background_tasks.add_task(
        trigger_webhook,
        api_key["tenant_id"],
        "test.ping",
        {"message": "Test webhook delivery", "webhook_id": webhook_id},
        {"test": True}
    )
    
    return {"message": "Test webhook queued for delivery"}


# ==================== WEBHOOK EVENT TRIGGERS ====================
# These functions should be called from other parts of the application

async def on_deal_created(tenant_id: str, deal: dict):
    await trigger_webhook(tenant_id, "deal.created", deal)

async def on_deal_updated(tenant_id: str, deal: dict, changes: dict = None):
    await trigger_webhook(tenant_id, "deal.updated", deal, {"changes": changes})

async def on_deal_stage_changed(tenant_id: str, deal: dict, old_stage: str, new_stage: str):
    await trigger_webhook(tenant_id, "deal.stage_changed", deal, {
        "old_stage": old_stage,
        "new_stage": new_stage
    })

async def on_deal_won(tenant_id: str, deal: dict):
    await trigger_webhook(tenant_id, "deal.won", deal)

async def on_deal_lost(tenant_id: str, deal: dict, reason: str = None):
    await trigger_webhook(tenant_id, "deal.lost", deal, {"reason": reason})

async def on_lead_created(tenant_id: str, lead: dict):
    await trigger_webhook(tenant_id, "lead.created", lead)

async def on_lead_qualified(tenant_id: str, lead: dict):
    await trigger_webhook(tenant_id, "lead.qualified", lead)

async def on_task_completed(tenant_id: str, task: dict):
    await trigger_webhook(tenant_id, "task.completed", task)

async def on_sla_breach(tenant_id: str, entity: dict, breach_details: dict):
    await trigger_webhook(tenant_id, "sla.breach", entity, breach_details)

async def on_handoff_completed(tenant_id: str, deal: dict, handoff: dict):
    await trigger_webhook(tenant_id, "handoff.completed", {
        "deal": deal,
        "handoff": handoff
    })
