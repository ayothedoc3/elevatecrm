"""
Elev8 CRM - SLA & Task Management Routes

Per PRD Section 8, mandatory rules:
- Task created after every sales interaction
- Follow-up SLAs enforced per stage
- Speed-to-lead SLA configurable per source
- No deal may remain without activity beyond defined SLA

Task completion and SLA compliance must be tracked as KPIs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
import uuid

from app.db.mongodb import get_database
from app.api.elev8.auth import get_current_user

router = APIRouter(tags=["Tasks & SLAs"])


# ==================== ENUMS ====================

class TaskType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    DEMO = "demo"
    PROPOSAL = "proposal"
    CONTRACT = "contract"
    REVIEW = "review"
    OTHER = "other"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# ==================== SCHEMAS ====================

class TaskCreate(BaseModel):
    """Create a new task"""
    title: str
    description: Optional[str] = None
    task_type: TaskType = TaskType.FOLLOW_UP
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: str  # ISO format
    deal_id: Optional[str] = None
    lead_id: Optional[str] = None
    contact_id: Optional[str] = None
    assigned_to: Optional[str] = None  # User ID


class TaskUpdate(BaseModel):
    """Update a task"""
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[str] = None
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    completion_notes: Optional[str] = None


class SLAConfig(BaseModel):
    """SLA configuration"""
    name: str
    stage: Optional[str] = None  # Apply to specific stage
    source: Optional[str] = None  # Apply to specific lead source
    max_hours: int  # Maximum hours before SLA breach
    escalation_hours: Optional[int] = None  # Hours before escalation
    applies_to: str = "deals"  # deals, leads, or both


# ==================== TASK ENDPOINTS ====================

@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    deal_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    due_before: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user = Depends(get_current_user)
):
    """
    List tasks with filtering.
    """
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if assigned_to:
        query["assigned_to"] = assigned_to
    if deal_id:
        query["deal_id"] = deal_id
    if lead_id:
        query["lead_id"] = lead_id
    if due_before:
        query["due_date"] = {"$lte": due_before}
    
    total = await db.tasks.count_documents(query)
    skip = (page - 1) * page_size
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).skip(skip).limit(page_size).to_list(length=page_size)
    
    # Check for overdue tasks and update status
    now = datetime.now(timezone.utc).isoformat()
    for task in tasks:
        if task.get("status") == "pending" and task.get("due_date") < now:
            task["status"] = "overdue"
            task["is_overdue"] = True
        else:
            task["is_overdue"] = False
    
    # Enrich with related info
    for task in tasks:
        if task.get("deal_id"):
            deal = await db.deals.find_one({"id": task["deal_id"]}, {"_id": 0, "name": 1})
            task["deal_name"] = deal.get("name") if deal else None
        if task.get("lead_id"):
            lead = await db.leads.find_one({"id": task["lead_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            task["lead_name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() if lead else None
        if task.get("assigned_to"):
            assignee = await db.users.find_one({"id": task["assigned_to"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            task["assigned_to_name"] = f"{assignee.get('first_name', '')} {assignee.get('last_name', '')}".strip() if assignee else None
    
    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/tasks")
async def create_task(
    data: TaskCreate,
    user = Depends(get_current_user)
):
    """
    Create a new task.
    """
    db = get_database()
    
    now = datetime.now(timezone.utc).isoformat()
    
    task = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "status": TaskStatus.PENDING.value,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
        "completed_at": None
    }
    
    await db.tasks.insert_one(task)
    task.pop("_id", None)
    
    return task


@router.get("/tasks/my-tasks")
async def get_my_tasks(
    include_overdue: bool = True,
    user = Depends(get_current_user)
):
    """
    Get tasks assigned to the current user.
    """
    db = get_database()
    
    query = {
        "tenant_id": user["tenant_id"],
        "assigned_to": user["id"],
        "status": {"$in": ["pending", "in_progress"]}
    }
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).to_list(length=100)
    
    # Categorize
    overdue = []
    due_today = []
    upcoming = []
    
    today = datetime.now(timezone.utc).date()
    
    for task in tasks:
        due_date_str = task.get("due_date", "")
        try:
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
            
            if due_date < today:
                task["status"] = "overdue"
                overdue.append(task)
            elif due_date == today:
                due_today.append(task)
            else:
                upcoming.append(task)
        except (ValueError, TypeError):
            upcoming.append(task)
    
    return {
        "overdue": overdue,
        "due_today": due_today,
        "upcoming": upcoming[:10],
        "total_pending": len(overdue) + len(due_today) + len(upcoming)
    }


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user = Depends(get_current_user)
):
    """
    Get a specific task.
    """
    db = get_database()
    
    task = await db.tasks.find_one(
        {"id": task_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user = Depends(get_current_user)
):
    """
    Update a task.
    """
    db = get_database()
    
    task = await db.tasks.find_one(
        {"id": task_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = now
    
    # If completing task, set completed_at
    if updates.get("status") == TaskStatus.COMPLETED.value:
        updates["completed_at"] = now
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": updates}
    )
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return updated_task


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user = Depends(get_current_user)
):
    """
    Delete a task.
    """
    db = get_database()
    
    result = await db.tasks.delete_one(
        {"id": task_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted"}


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    notes: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    Mark a task as completed.
    """
    db = get_database()
    
    task = await db.tasks.find_one(
        {"id": task_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": now,
            "completed_by": user["id"],
            "completion_notes": notes,
            "updated_at": now
        }}
    )
    
    # Create activity log
    activity_data = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "type": "task_completed",
        "user_id": user["id"],
        "description": f"Task completed: {task.get('title')}",
        "created_at": now
    }
    
    if task.get("deal_id"):
        activity_data["deal_id"] = task["deal_id"]
    if task.get("lead_id"):
        activity_data["lead_id"] = task["lead_id"]
    
    await db.activities.insert_one(activity_data)
    
    return {"message": "Task completed", "task_id": task_id, "completed_at": now}


# ==================== SLA ENDPOINTS ====================

@router.get("/sla/config")
async def get_sla_config(
    user = Depends(get_current_user)
):
    """
    Get SLA configuration for the workspace.
    """
    db = get_database()
    
    config = await db.sla_configs.find(
        {"tenant_id": user["tenant_id"]},
        {"_id": 0}
    ).to_list(length=100)
    
    # Return defaults if none configured
    if not config:
        config = [
            {
                "id": "default_lead_response",
                "name": "Lead Response SLA",
                "stage": None,
                "source": None,
                "max_hours": 24,
                "escalation_hours": 12,
                "applies_to": "leads",
                "is_default": True
            },
            {
                "id": "default_deal_activity",
                "name": "Deal Activity SLA",
                "stage": None,
                "source": None,
                "max_hours": 72,
                "escalation_hours": 48,
                "applies_to": "deals",
                "is_default": True
            },
            {
                "id": "referral_response",
                "name": "Referral Response SLA",
                "stage": None,
                "source": "referral",
                "max_hours": 4,
                "escalation_hours": 2,
                "applies_to": "leads",
                "is_default": True
            }
        ]
    
    return {"sla_configs": config}


@router.post("/sla/config")
async def create_sla_config(
    data: SLAConfig,
    user = Depends(get_current_user)
):
    """
    Create a new SLA configuration.
    """
    db = get_database()
    
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    config = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "is_default": False,
        "created_at": now,
        "created_by": user["id"]
    }
    
    await db.sla_configs.insert_one(config)
    config.pop("_id", None)
    
    return config


@router.get("/sla/status")
async def get_sla_status(
    entity_type: str = Query("deals", description="Entity type: deals or leads"),
    user = Depends(get_current_user)
):
    """
    Get SLA status overview - identify breaches and at-risk items.
    """
    db = get_database()
    
    now = datetime.now(timezone.utc)
    
    # Get SLA configs
    configs = await db.sla_configs.find(
        {"tenant_id": user["tenant_id"], "applies_to": {"$in": [entity_type, "both"]}}
    ).to_list(length=100)
    
    # Default SLA if none configured
    default_max_hours = 72 if entity_type == "deals" else 24
    
    results = {
        "entity_type": entity_type,
        "total_count": 0,
        "compliant_count": 0,
        "at_risk_count": 0,
        "breached_count": 0,
        "breached_items": [],
        "at_risk_items": []
    }
    
    if entity_type == "deals":
        items = await db.deals.find(
            {"tenant_id": user["tenant_id"], "status": "open"},
            {"_id": 0}
        ).to_list(length=1000)
    else:
        items = await db.leads.find(
            {"tenant_id": user["tenant_id"], "status": {"$nin": ["qualified", "disqualified"]}},
            {"_id": 0}
        ).to_list(length=1000)
    
    results["total_count"] = len(items)
    
    for item in items:
        # Get last activity time
        last_activity = item.get("updated_at") or item.get("created_at")
        if not last_activity:
            continue
        
        try:
            if isinstance(last_activity, str):
                last_time = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            else:
                last_time = last_activity
            
            hours_since = (now - last_time).total_seconds() / 3600
            
            # Find applicable SLA
            max_hours = default_max_hours
            escalation_hours = default_max_hours * 0.66
            
            for config in configs:
                if config.get("source") and config["source"] == item.get("source"):
                    max_hours = config["max_hours"]
                    escalation_hours = config.get("escalation_hours", max_hours * 0.66)
                    break
                elif config.get("stage") and config["stage"] == item.get("stage_name"):
                    max_hours = config["max_hours"]
                    escalation_hours = config.get("escalation_hours", max_hours * 0.66)
                    break
            
            item_summary = {
                "id": item["id"],
                "name": item.get("name") or f"{item.get('first_name', '')} {item.get('last_name', '')}".strip(),
                "hours_since_activity": round(hours_since, 1),
                "sla_hours": max_hours,
                "owner_id": item.get("owner_id")
            }
            
            if hours_since > max_hours:
                results["breached_count"] += 1
                item_summary["breach_hours"] = round(hours_since - max_hours, 1)
                results["breached_items"].append(item_summary)
            elif hours_since > escalation_hours:
                results["at_risk_count"] += 1
                item_summary["hours_to_breach"] = round(max_hours - hours_since, 1)
                results["at_risk_items"].append(item_summary)
            else:
                results["compliant_count"] += 1
                
        except (ValueError, TypeError):
            continue
    
    # Sort by severity
    results["breached_items"] = sorted(
        results["breached_items"], 
        key=lambda x: x.get("breach_hours", 0), 
        reverse=True
    )[:10]
    
    results["at_risk_items"] = sorted(
        results["at_risk_items"],
        key=lambda x: x.get("hours_to_breach", 999)
    )[:10]
    
    return results


@router.get("/tasks/deal/{deal_id}")
async def get_deal_tasks(
    deal_id: str,
    user = Depends(get_current_user)
):
    """
    Get all tasks for a specific deal.
    """
    db = get_database()
    
    tasks = await db.tasks.find(
        {"deal_id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    ).sort("due_date", 1).to_list(length=100)
    
    # Check for overdue
    now = datetime.now(timezone.utc).isoformat()
    for task in tasks:
        if task.get("status") == "pending" and task.get("due_date") < now:
            task["is_overdue"] = True
        else:
            task["is_overdue"] = False
    
    return {"tasks": tasks, "total": len(tasks)}
