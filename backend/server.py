"""
Elevate CRM - Main Server (MongoDB Version)
Multi-CRM Platform API Server
"""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import uuid
import logging
import json

# MongoDB imports
from app.db.mongodb import init_db, close_db, get_database, serialize_doc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# ==================== PYDANTIC MODELS ====================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    is_active: bool
    tenant_id: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = []


class ContactResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    title: Optional[str]
    source: Optional[str]
    tags: List[str]
    status: str
    created_at: str


class DealCreate(BaseModel):
    name: str
    amount: float = 0
    contact_id: Optional[str] = None
    pipeline_id: str
    stage_id: str


class DealResponse(BaseModel):
    id: str
    name: str
    amount: float
    currency: str
    status: str
    contact_id: Optional[str]
    contact_name: Optional[str]
    pipeline_id: str
    stage_id: str
    stage_name: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str]
    created_at: str


class PipelineResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_default: bool
    stages: List[dict]


class TimelineEventCreate(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    deal_id: Optional[str] = None
    contact_id: Optional[str] = None
    visibility: str = "internal_only"


class TimelineEventResponse(BaseModel):
    id: str
    event_type: str
    title: str
    description: Optional[str]
    actor_id: Optional[str]
    actor_name: Optional[str]
    deal_id: Optional[str]
    contact_id: Optional[str]
    visibility: str
    metadata: dict
    created_at: str


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Elevate CRM server...")
    await init_db()
    await seed_demo_data()
    logger.info("Server started successfully!")
    yield
    # Shutdown
    await close_db()
    logger.info("Server shutdown complete")


# ==================== APP SETUP ====================

app = FastAPI(
    title="Elevate CRM API",
    description="Multi-CRM Platform API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")


# ==================== AUTH HELPERS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_database()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# ==================== HEALTH CHECK ====================

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, tenant_slug: str = Query(default="demo")):
    """Login with email and password"""
    db = get_database()
    
    # Find tenant
    tenant = await db.tenants.find_one({"slug": tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Find user
    user = await db.users.find_one(
        {"email": request.email, "tenant_id": tenant["id"]},
        {"_id": 0}
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    access_token = create_access_token(data={"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "full_name": f"{user['first_name']} {user['last_name']}",
            "role": user["role"],
            "is_active": user["is_active"],
            "tenant_id": user["tenant_id"],
            "phone": user.get("phone"),
            "avatar_url": user.get("avatar_url")
        }
    )


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        full_name=f"{user['first_name']} {user['last_name']}",
        role=user["role"],
        is_active=user["is_active"],
        tenant_id=user["tenant_id"],
        phone=user.get("phone"),
        avatar_url=user.get("avatar_url")
    )


# ==================== CONTACTS ====================

@api_router.get("/contacts")
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List contacts for the tenant"""
    db = get_database()
    
    # Build query
    query = {"tenant_id": user["tenant_id"]}
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    # Count total
    total = await db.contacts.count_documents(query)
    
    # Get contacts
    skip = (page - 1) * page_size
    cursor = db.contacts.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    contacts = await cursor.to_list(length=page_size)
    
    return {
        "contacts": [
            {
                **c,
                "full_name": f"{c['first_name']} {c['last_name']}"
            }
            for c in contacts
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@api_router.post("/contacts", status_code=201)
async def create_contact(
    data: ContactCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new contact"""
    db = get_database()
    
    contact = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "phone": data.phone,
        "company": data.company,
        "title": data.title,
        "source": data.source,
        "tags": data.tags,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.contacts.insert_one(contact)
    
    return {
        **contact,
        "full_name": f"{contact['first_name']} {contact['last_name']}"
    }


@api_router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific contact"""
    db = get_database()
    
    contact = await db.contacts.find_one(
        {"id": contact_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {
        **contact,
        "full_name": f"{contact['first_name']} {contact['last_name']}"
    }


# ==================== PIPELINES ====================

@api_router.get("/pipelines")
async def list_pipelines(user: dict = Depends(get_current_user)):
    """List pipelines for the tenant"""
    db = get_database()
    
    cursor = db.pipelines.find({"tenant_id": user["tenant_id"]}, {"_id": 0}).sort("display_order", 1)
    pipelines = await cursor.to_list(length=100)
    
    # Get stages for each pipeline
    result = []
    for p in pipelines:
        stages_cursor = db.pipeline_stages.find({"pipeline_id": p["id"]}, {"_id": 0}).sort("display_order", 1)
        stages = await stages_cursor.to_list(length=100)
        result.append({
            **p,
            "stages": stages
        })
    
    return {"pipelines": result}


@api_router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific pipeline with stages"""
    db = get_database()
    
    pipeline = await db.pipelines.find_one(
        {"id": pipeline_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    stages_cursor = db.pipeline_stages.find({"pipeline_id": pipeline_id}, {"_id": 0}).sort("display_order", 1)
    stages = await stages_cursor.to_list(length=100)
    
    return {**pipeline, "stages": stages}


@api_router.get("/pipelines/{pipeline_id}/kanban")
async def get_pipeline_kanban(
    pipeline_id: str,
    user: dict = Depends(get_current_user)
):
    """Get pipeline in Kanban format with deals in each stage"""
    db = get_database()
    
    pipeline = await db.pipelines.find_one(
        {"id": pipeline_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Get stages
    stages_cursor = db.pipeline_stages.find({"pipeline_id": pipeline_id}, {"_id": 0}).sort("display_order", 1)
    stages = await stages_cursor.to_list(length=100)
    
    # Get all deals for this pipeline
    deals_cursor = db.deals.find(
        {"pipeline_id": pipeline_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    deals = await deals_cursor.to_list(length=1000)
    
    # Get contacts for deals
    contact_ids = [d["contact_id"] for d in deals if d.get("contact_id")]
    contacts_map = {}
    if contact_ids:
        contacts_cursor = db.contacts.find({"id": {"$in": contact_ids}}, {"_id": 0})
        contacts = await contacts_cursor.to_list(length=1000)
        contacts_map = {c["id"]: c for c in contacts}
    
    # Group deals by stage
    columns = []
    for stage in stages:
        stage_deals = [d for d in deals if d.get("stage_id") == stage["id"]]
        column_deals = []
        for deal in stage_deals:
            contact = contacts_map.get(deal.get("contact_id"), {})
            column_deals.append({
                **deal,
                "contact_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or None,
                "contact_email": contact.get("email"),
                "stage_name": stage["name"]
            })
        
        columns.append({
            "id": stage["id"],
            "name": stage["name"],
            "color": stage.get("color", "#6366F1"),
            "display_order": stage.get("display_order", 0),
            "deals": column_deals,
            "total_value": sum(d.get("amount", 0) for d in column_deals),
            "deal_count": len(column_deals)
        })
    
    return {
        "pipeline": pipeline,
        "columns": columns
    }


# ==================== DEALS ====================

@api_router.get("/deals")
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List deals for the tenant"""
    db = get_database()
    
    # Build query
    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status
    if pipeline_id:
        query["pipeline_id"] = pipeline_id
    
    # Count total
    total = await db.deals.count_documents(query)
    
    # Get deals
    skip = (page - 1) * page_size
    cursor = db.deals.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    deals = await cursor.to_list(length=page_size)
    
    # Enrich with contact and stage names
    result = []
    for deal in deals:
        # Get contact name
        contact_name = None
        if deal.get("contact_id"):
            contact = await db.contacts.find_one({"id": deal["contact_id"]}, {"_id": 0})
            if contact:
                contact_name = f"{contact['first_name']} {contact['last_name']}"
        
        # Get stage name
        stage_name = None
        if deal.get("stage_id"):
            stage = await db.pipeline_stages.find_one({"id": deal["stage_id"]}, {"_id": 0})
            if stage:
                stage_name = stage["name"]
        
        result.append({
            **deal,
            "contact_name": contact_name,
            "stage_name": stage_name
        })
    
    return {
        "deals": result,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@api_router.post("/deals", status_code=201)
async def create_deal(
    data: DealCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new deal"""
    db = get_database()
    
    deal = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "amount": data.amount,
        "currency": "USD",
        "status": "open",
        "contact_id": data.contact_id,
        "pipeline_id": data.pipeline_id,
        "stage_id": data.stage_id,
        "owner_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.deals.insert_one(deal)
    
    # Create timeline event
    await create_timeline_event(
        db, user["tenant_id"], "deal_created",
        f"Deal created: {data.name}",
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=deal["id"]
    )
    
    return deal


@api_router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific deal"""
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get contact name
    contact_name = None
    if deal.get("contact_id"):
        contact = await db.contacts.find_one({"id": deal["contact_id"]}, {"_id": 0})
        if contact:
            contact_name = f"{contact['first_name']} {contact['last_name']}"
    
    # Get stage name
    stage_name = None
    if deal.get("stage_id"):
        stage = await db.pipeline_stages.find_one({"id": deal["stage_id"]}, {"_id": 0})
        if stage:
            stage_name = stage["name"]
    
    return {
        **deal,
        "contact_name": contact_name,
        "stage_name": stage_name
    }


@api_router.post("/deals/{deal_id}/move-stage")
async def move_deal_stage(
    deal_id: str,
    new_stage_id: str = Query(...),
    user: dict = Depends(get_current_user)
):
    """Move a deal to a new stage"""
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get old and new stage names
    old_stage = await db.pipeline_stages.find_one({"id": deal["stage_id"]}, {"_id": 0})
    new_stage = await db.pipeline_stages.find_one({"id": new_stage_id}, {"_id": 0})
    
    if not new_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # Update deal
    await db.deals.update_one(
        {"id": deal_id},
        {
            "$set": {
                "stage_id": new_stage_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create timeline event
    await create_timeline_event(
        db, user["tenant_id"], "stage_changed",
        f"Stage changed: {old_stage['name'] if old_stage else 'Unknown'} → {new_stage['name']}",
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=deal_id,
        metadata={
            "from_stage": old_stage["name"] if old_stage else None,
            "to_stage": new_stage["name"]
        }
    )
    
    return {"success": True, "new_stage_id": new_stage_id}


# ==================== TIMELINE ====================

async def create_timeline_event(
    db, tenant_id: str, event_type: str, title: str,
    actor_id: str = None, actor_name: str = None,
    deal_id: str = None, contact_id: str = None,
    description: str = None, visibility: str = "internal_only",
    metadata: dict = None
):
    """Helper to create timeline events"""
    event = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "title": title,
        "description": description,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "deal_id": deal_id,
        "contact_id": contact_id,
        "visibility": visibility,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.timeline_events.insert_one(event)
    return event


@api_router.get("/timeline")
async def list_timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    deal_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List timeline events"""
    db = get_database()
    
    # Build query
    query = {"tenant_id": user["tenant_id"]}
    if event_type:
        query["event_type"] = event_type
    if deal_id:
        query["deal_id"] = deal_id
    if contact_id:
        query["contact_id"] = contact_id
    
    # Count total
    total = await db.timeline_events.count_documents(query)
    
    # Get events
    skip = (page - 1) * page_size
    cursor = db.timeline_events.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    events = await cursor.to_list(length=page_size)
    
    return {
        "events": events,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@api_router.post("/timeline", status_code=201)
async def create_timeline_event_endpoint(
    data: TimelineEventCreate,
    user: dict = Depends(get_current_user)
):
    """Create a timeline event"""
    db = get_database()
    
    event = await create_timeline_event(
        db, user["tenant_id"], data.event_type, data.title,
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=data.deal_id,
        contact_id=data.contact_id,
        description=data.description,
        visibility=data.visibility
    )
    
    return event


# ==================== BLUEPRINTS ====================

@api_router.get("/workspaces/blueprints")
async def list_crm_blueprints():
    """List available CRM blueprints"""
    from app.blueprints.frylow_blueprint import get_all_blueprints
    
    blueprints = get_all_blueprints()
    return {
        "blueprints": [
            {
                "slug": b["slug"],
                "name": b["name"],
                "description": b["config"].get("description", ""),
                "icon": b["config"].get("icon", "building"),
                "color": b["config"].get("color", "#6366F1"),
                "is_default": b["is_default"]
            }
            for b in blueprints
        ]
    }


# ==================== CALCULATIONS ====================

@api_router.get("/calculations/deal/{deal_id}")
async def get_deal_calculation(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """Get calculation definition and result for a deal"""
    db = get_database()
    
    # Get calculation definition for tenant
    calc_def = await db.calculation_definitions.find_one(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    )
    
    if not calc_def:
        return {"definition": None, "result": None}
    
    # Get existing result for this deal
    result = await db.calculation_results.find_one(
        {"deal_id": deal_id, "definition_id": calc_def["id"]},
        {"_id": 0}
    )
    
    # Parse JSON schemas
    input_schema = json.loads(calc_def.get("input_schema", "[]"))
    output_schema = json.loads(calc_def.get("output_schema", "[]"))
    
    return {
        "definition": {
            "id": calc_def["id"],
            "name": calc_def["name"],
            "description": calc_def.get("description"),
            "inputs": input_schema,
            "outputs": output_schema
        },
        "result": {
            "inputs": json.loads(result.get("inputs", "{}")) if result else {},
            "outputs": json.loads(result.get("outputs", "{}")) if result else {},
            "is_complete": result.get("is_complete", False) if result else False
        } if result else None
    }


@api_router.post("/calculations/deal/{deal_id}/calculate")
async def calculate_deal(
    deal_id: str,
    inputs: dict,
    user: dict = Depends(get_current_user)
):
    """Run calculation for a deal"""
    db = get_database()
    
    # Get calculation definition
    calc_def = await db.calculation_definitions.find_one(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    )
    
    if not calc_def:
        raise HTTPException(status_code=404, detail="No calculation defined")
    
    # Simple Frylow ROI calculation
    outputs = {}
    try:
        quantity = float(inputs.get("quantity_per_month", 0))
        cost = float(inputs.get("cost_per_unit", 0))
        
        monthly_spend = quantity * cost
        yearly_spend = monthly_spend * 12
        
        outputs = {
            "monthly_oil_spend": monthly_spend,
            "yearly_oil_spend": yearly_spend,
            "estimated_savings_low": yearly_spend * 0.3,
            "estimated_savings_high": yearly_spend * 0.5,
            "recommended_device_quantity": max(1, int(inputs.get("number_of_fryers", 1))),
            "recommended_device_size": "Standard"
        }
    except Exception as e:
        logger.error(f"Calculation error: {e}")
    
    # Save result
    result = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "definition_id": calc_def["id"],
        "deal_id": deal_id,
        "inputs": json.dumps(inputs),
        "outputs": json.dumps(outputs),
        "is_complete": True,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert result
    await db.calculation_results.update_one(
        {"deal_id": deal_id, "definition_id": calc_def["id"]},
        {"$set": result},
        upsert=True
    )
    
    return {
        "success": True,
        "is_complete": True,
        "outputs": outputs
    }


# ==================== OUTREACH ====================

@api_router.post("/outreach", status_code=201)
async def create_outreach_activity(
    deal_id: str,
    activity_type: str,
    direction: str = "outbound",
    status: str = "completed",
    subject: Optional[str] = None,
    notes: Optional[str] = None,
    got_response: bool = False,
    user: dict = Depends(get_current_user)
):
    """Log an outreach activity"""
    db = get_database()
    
    activity = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "deal_id": deal_id,
        "user_id": user["id"],
        "activity_type": activity_type,
        "direction": direction,
        "status": status,
        "subject": subject,
        "notes": notes,
        "got_response": got_response,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.outreach_activities.insert_one(activity)
    
    # Create timeline event
    activity_labels = {
        "call": "📞 Call", "email": "📧 Email", "sms": "💬 SMS",
        "meeting": "🤝 Meeting", "demo": "📺 Demo", "note": "📝 Note"
    }
    await create_timeline_event(
        db, user["tenant_id"], "activity",
        f"{activity_labels.get(activity_type, 'Activity')}: {subject or activity_type}",
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=deal_id,
        description=notes
    )
    
    return activity


@api_router.get("/outreach/deal/{deal_id}")
async def list_deal_outreach(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """List outreach activities for a deal"""
    db = get_database()
    
    cursor = db.outreach_activities.find(
        {"deal_id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    ).sort("created_at", -1)
    activities = await cursor.to_list(length=100)
    
    # Count touchpoints
    touchpoint_count = len([a for a in activities if a["status"] in ["completed", "no_answer", "voicemail"]])
    
    return {
        "activities": activities,
        "total": len(activities),
        "touchpoint_count": touchpoint_count
    }


@api_router.get("/outreach/deal/{deal_id}/summary")
async def get_deal_outreach_summary(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """Get outreach summary for a deal"""
    db = get_database()
    
    cursor = db.outreach_activities.find(
        {"deal_id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    activities = await cursor.to_list(length=1000)
    
    # Calculate summary
    calls = len([a for a in activities if a["activity_type"] == "call"])
    emails = len([a for a in activities if a["activity_type"] == "email"])
    sms = len([a for a in activities if a["activity_type"] == "sms"])
    meetings = len([a for a in activities if a["activity_type"] == "meeting"])
    responses = len([a for a in activities if a.get("got_response")])
    
    last_activity = activities[0] if activities else None
    days_since = None
    if last_activity:
        last_date = datetime.fromisoformat(last_activity["created_at"].replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - last_date).days
    
    return {
        "deal_id": deal_id,
        "total_touchpoints": len(activities),
        "calls": calls,
        "emails": emails,
        "sms": sms,
        "meetings": meetings,
        "responses": responses,
        "last_activity_at": last_activity["created_at"] if last_activity else None,
        "days_since_last_contact": days_since
    }


# ==================== CUSTOM OBJECTS ====================

@api_router.get("/custom-objects")
async def list_custom_objects(user: dict = Depends(get_current_user)):
    """List custom object definitions"""
    db = get_database()
    
    cursor = db.custom_object_definitions.find(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    ).sort("display_order", 1)
    definitions = await cursor.to_list(length=100)
    
    result = []
    for d in definitions:
        # Get fields
        fields_cursor = db.custom_object_fields.find({"object_id": d["id"]}, {"_id": 0}).sort("display_order", 1)
        fields = await fields_cursor.to_list(length=100)
        
        # Parse field config JSON
        for f in fields:
            f["config"] = json.loads(f.get("config", "{}"))
        
        # Get record count
        record_count = await db.custom_object_records.count_documents({"object_id": d["id"]})
        
        result.append({
            **d,
            "fields": fields,
            "record_count": record_count
        })
    
    return result


@api_router.post("/custom-objects", status_code=201)
async def create_custom_object(
    name: str,
    slug: str,
    description: Optional[str] = None,
    icon: str = "Box",
    color: str = "#6366F1",
    fields: List[dict] = [],
    user: dict = Depends(get_current_user)
):
    """Create a custom object definition"""
    db = get_database()
    
    # Check if slug exists
    existing = await db.custom_object_definitions.find_one(
        {"tenant_id": user["tenant_id"], "slug": slug}
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Object with slug '{slug}' already exists")
    
    obj_def = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": name,
        "slug": slug,
        "plural_name": f"{name}s",
        "description": description,
        "icon": icon,
        "color": color,
        "label_field": "name",
        "is_system": False,
        "is_active": True,
        "show_in_nav": True,
        "display_order": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.custom_object_definitions.insert_one(obj_def)
    
    # Create fields
    created_fields = []
    default_fields = fields or [{"name": "name", "label": "Name", "field_type": "text", "is_required": True}]
    for i, f in enumerate(default_fields):
        field = {
            "id": str(uuid.uuid4()),
            "object_id": obj_def["id"],
            "name": f.get("name", f"field_{i}"),
            "label": f.get("label", f"Field {i}"),
            "field_type": f.get("field_type", "text"),
            "config": json.dumps(f.get("config", {})),
            "is_required": f.get("is_required", False),
            "is_unique": f.get("is_unique", False),
            "show_in_list": f.get("show_in_list", True),
            "show_in_detail": f.get("show_in_detail", True),
            "is_searchable": f.get("is_searchable", False),
            "display_order": i,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.custom_object_fields.insert_one(field)
        field["config"] = json.loads(field["config"])
        created_fields.append(field)
    
    return {
        **obj_def,
        "fields": created_fields,
        "record_count": 0
    }


@api_router.get("/custom-objects/{object_id}/records")
async def list_custom_object_records(
    object_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """List records for a custom object"""
    db = get_database()
    
    # Verify object exists
    obj_def = await db.custom_object_definitions.find_one(
        {"id": object_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    # Get records
    total = await db.custom_object_records.count_documents({"object_id": object_id})
    skip = (page - 1) * page_size
    cursor = db.custom_object_records.find(
        {"object_id": object_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(page_size)
    records = await cursor.to_list(length=page_size)
    
    # Parse data JSON
    for r in records:
        r["data"] = json.loads(r.get("data", "{}"))
    
    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@api_router.post("/custom-objects/{object_id}/records", status_code=201)
async def create_custom_object_record(
    object_id: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Create a record for a custom object"""
    db = get_database()
    
    # Verify object exists
    obj_def = await db.custom_object_definitions.find_one(
        {"id": object_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    record = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "object_id": object_id,
        "data": json.dumps(data),
        "display_label": str(data.get(obj_def.get("label_field", "name"), "")),
        "owner_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.custom_object_records.insert_one(record)
    record["data"] = data
    
    return record


@api_router.delete("/custom-objects/{object_id}", status_code=204)
async def delete_custom_object(
    object_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a custom object"""
    db = get_database()
    
    obj_def = await db.custom_object_definitions.find_one(
        {"id": object_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not obj_def:
        raise HTTPException(status_code=404, detail="Object not found")
    
    if obj_def.get("is_system"):
        raise HTTPException(status_code=400, detail="Cannot delete system object")
    
    # Delete records, fields, and definition
    await db.custom_object_records.delete_many({"object_id": object_id})
    await db.custom_object_fields.delete_many({"object_id": object_id})
    await db.custom_object_definitions.delete_one({"id": object_id})


# ==================== WORKFLOW BLUEPRINTS ====================

@api_router.get("/blueprints")
async def list_workflow_blueprints(user: dict = Depends(get_current_user)):
    """List workflow blueprints"""
    db = get_database()
    
    cursor = db.workflow_blueprints.find(
        {"tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    blueprints = await cursor.to_list(length=100)
    
    return {"blueprints": blueprints, "total": len(blueprints)}


# ==================== STORAGE FILE SERVING ====================

from fastapi.responses import FileResponse
import aiofiles

@api_router.get("/storage/files/{file_path:path}")
async def serve_storage_file(file_path: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Serve files from local storage (authenticated)"""
    user = await get_current_user(credentials)
    
    # Construct full path
    base_path = "/app/backend/uploads"
    full_path = os.path.join(base_path, file_path)
    
    # Security: Prevent directory traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(full_path)


# ==================== PUBLIC REFERRAL TRACKING ====================

from fastapi.responses import RedirectResponse

@api_router.get("/ref/{referral_code}")
async def public_referral_redirect(referral_code: str, request: Request):
    """Public endpoint to track affiliate link clicks and redirect"""
    db = get_database()
    
    # Find the link
    link = await db.affiliate_links.find_one(
        {"referral_code": referral_code, "is_active": True},
        {"_id": 0}
    )
    
    if not link:
        raise HTTPException(status_code=404, detail="Invalid referral link")
    
    # Get program for cookie duration
    program = await db.affiliate_programs.find_one(
        {"id": link["program_id"]},
        {"_id": 0, "cookie_duration_days": 1}
    )
    cookie_days = program.get("cookie_duration_days", 30) if program else 30
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Log click event
    event = {
        "id": str(uuid.uuid4()),
        "tenant_id": link["tenant_id"],
        "event_type": "affiliate_link_clicked",
        "affiliate_id": link["affiliate_id"],
        "link_id": link["id"],
        "program_id": link["program_id"],
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": {
            "referral_code": referral_code,
            "referer": request.headers.get("referer", "")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.affiliate_events.insert_one(event)
    
    # Increment click count
    await db.affiliate_links.update_one(
        {"id": link["id"]},
        {"$inc": {"click_count": 1}}
    )
    
    # Determine redirect URL
    redirect_url = link.get("landing_page_url") or "/"
    if "?" in redirect_url:
        redirect_url += f"&ref={referral_code}"
    else:
        redirect_url += f"?ref={referral_code}"
    
    # Create response with cookie
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="_aff_ref",
        value=referral_code,
        max_age=cookie_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    
    return response


# ==================== SEED DATA ====================

async def seed_demo_data():
    """Seed demo data if not exists"""
    db = get_database()
    
    # Check if demo tenant exists
    existing_tenant = await db.tenants.find_one({"slug": "demo"})
    if existing_tenant:
        logger.info("Demo data already exists, skipping seed")
        return
    
    logger.info("Seeding demo data...")
    
    # Create tenant
    tenant_id = str(uuid.uuid4())
    tenant = {
        "id": tenant_id,
        "name": "Demo Company",
        "slug": "demo",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tenants.insert_one(tenant)
    
    # Create admin user
    admin_id = str(uuid.uuid4())
    admin = {
        "id": admin_id,
        "tenant_id": tenant_id,
        "email": "admin@demo.com",
        "hashed_password": get_password_hash("admin123"),
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin)
    
    # Create pipeline
    pipeline_id = str(uuid.uuid4())
    pipeline = {
        "id": pipeline_id,
        "tenant_id": tenant_id,
        "name": "Frylow Sales Pipeline",
        "description": "Sales pipeline for Frylow oil savings solutions",
        "is_default": True,
        "display_order": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.pipelines.insert_one(pipeline)
    
    # Create stages
    stages_data = [
        ("New Lead", "#6366F1", 10),
        ("Contacted", "#8B5CF6", 20),
        ("Demo Scheduled", "#A855F7", 30),
        ("Demo Completed", "#C084FC", 40),
        ("Proposal Sent", "#D946EF", 50),
        ("Negotiation", "#EC4899", 60),
        ("Contract Sent", "#F43F5E", 70),
        ("Contract Signed", "#F97316", 80),
        ("Installation Scheduled", "#FB923C", 85),
        ("Installed", "#FBBF24", 90),
        ("Training", "#A3E635", 92),
        ("Active Customer", "#22C55E", 95),
        ("Won", "#10B981", 100),
        ("Lost", "#EF4444", 0),
        ("On Hold", "#6B7280", 0)
    ]
    
    stage_ids = []
    for i, (name, color, prob) in enumerate(stages_data):
        stage_id = str(uuid.uuid4())
        stage = {
            "id": stage_id,
            "pipeline_id": pipeline_id,
            "name": name,
            "color": color,
            "probability": prob,
            "display_order": i,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.pipeline_stages.insert_one(stage)
        stage_ids.append(stage_id)
    
    # Create contacts
    contacts_data = [
        ("John", "Smith", "john.smith@restaurant.com", "555-0101", "Smith's Diner"),
        ("Sarah", "Johnson", "sarah@bigburger.com", "555-0102", "Big Burger Chain"),
        ("Mike", "Williams", "mike@tastyfoods.com", "555-0103", "Tasty Foods Inc"),
        ("Emily", "Brown", "emily@foodcourt.com", "555-0104", "Food Court Express"),
        ("David", "Davis", "david@friesking.com", "555-0105", "Fries King Restaurant")
    ]
    
    contact_ids = []
    for first, last, email, phone, company in contacts_data:
        contact_id = str(uuid.uuid4())
        contact = {
            "id": contact_id,
            "tenant_id": tenant_id,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "company": company,
            "status": "active",
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.contacts.insert_one(contact)
        contact_ids.append(contact_id)
    
    # Create deals
    deals_data = [
        ("Smith's Diner - Frylow Installation", 4500, 0),
        ("Big Burger Chain - Multi-Unit Deal", 12500, 1),
        ("Tasty Foods - Initial Demo", 3200, 2),
        ("Food Court Express - Proposal Review", 5800, 4),
        ("Fries King - Contract Negotiation", 7200, 5)
    ]
    
    for i, (name, amount, stage_idx) in enumerate(deals_data):
        deal = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id,
            "stage_id": stage_ids[stage_idx],
            "contact_id": contact_ids[i],
            "owner_id": admin_id,
            "name": name,
            "amount": amount,
            "currency": "USD",
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.deals.insert_one(deal)
        
        # Create timeline event
        await create_timeline_event(
            db, tenant_id, "deal_created",
            f"Deal created: {name}",
            actor_id=admin_id,
            actor_name="Admin User",
            deal_id=deal["id"]
        )
    
    # Create Frylow ROI Calculator
    calc_def = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Frylow ROI Calculator",
        "slug": "frylow-roi-calculator",
        "description": "Calculate oil savings and recommended Frylow device configuration",
        "version": 1,
        "is_active": True,
        "input_schema": json.dumps([
            {"name": "number_of_fryers", "type": "integer", "label": "Number of Fryers", "required": True, "min": 1, "max": 50},
            {"name": "fryer_capacities", "type": "multi_select", "label": "Fryer Capacities", "required": True,
             "options": [{"value": "16L", "label": "16 Liters"}, {"value": "30L", "label": "30 Liters"}, {"value": "45L", "label": "45 Liters"}]},
            {"name": "oil_units", "type": "select", "label": "Oil Purchase Units", "required": True,
             "options": [{"value": "boxes", "label": "Boxes"}, {"value": "gallons", "label": "Gallons"}]},
            {"name": "quantity_per_month", "type": "integer", "label": "Quantity Per Month", "required": True, "min": 1},
            {"name": "cost_per_unit", "type": "currency", "label": "Cost Per Unit ($)", "required": True, "min": 0}
        ]),
        "output_schema": json.dumps([
            {"name": "monthly_oil_spend", "type": "currency", "label": "Monthly Oil Spend"},
            {"name": "yearly_oil_spend", "type": "currency", "label": "Yearly Oil Spend"},
            {"name": "estimated_savings_low", "type": "currency", "label": "Estimated Savings (Low)"},
            {"name": "estimated_savings_high", "type": "currency", "label": "Estimated Savings (High)"},
            {"name": "recommended_device_quantity", "type": "integer", "label": "Recommended Devices"},
            {"name": "recommended_device_size", "type": "text", "label": "Recommended Size"}
        ]),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.calculation_definitions.insert_one(calc_def)
    
    # Create workflow blueprint
    blueprint = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Frylow Sales Workflow",
        "description": "Sales workflow with required actions",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.workflow_blueprints.insert_one(blueprint)
    
    # ==================== SEED AFFILIATE DATA ====================
    
    # Create Frylow Affiliate Program (Demo-First Journey)
    frylow_program = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Frylow Partner Program",
        "description": "Earn 10% commission on every Frylow sale you refer",
        "product_type": "service",
        "journey_type": "demo_first",
        "attribution_type": "deal",
        "attribution_model": "first_touch",
        "attribution_window_days": 30,
        "commission_type": "percentage",
        "commission_value": 10,
        "min_payout_threshold": 100,
        "cookie_duration_days": 30,
        "pipeline_scope": pipeline_id,
        "qualifying_stage_id": stage_ids[12],  # Won stage
        "auto_approve": False,
        "is_active": True,
        "total_commissions_earned": 0,
        "total_commissions_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.affiliate_programs.insert_one(frylow_program)
    
    # Create Direct Checkout Program (for products)
    direct_program = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Frylow Direct Sales",
        "description": "Flat $50 commission per direct sale",
        "product_type": "product",
        "journey_type": "direct_checkout",
        "attribution_type": "payment",
        "attribution_model": "last_touch",
        "attribution_window_days": 7,
        "commission_type": "flat",
        "commission_value": 50,
        "min_payout_threshold": 50,
        "cookie_duration_days": 7,
        "pipeline_scope": None,
        "qualifying_stage_id": None,
        "auto_approve": True,
        "is_active": True,
        "total_commissions_earned": 0,
        "total_commissions_paid": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.affiliate_programs.insert_one(direct_program)
    
    # Create sample affiliates
    affiliates_data = [
        ("John Partner", "john.partner@email.com", "Partner Marketing Inc", "active"),
        ("Sarah Referrer", "sarah@referrals.com", "Referral Pro", "active"),
        ("Mike Affiliate", "mike@affiliate.net", None, "pending")
    ]
    
    for name, email, company, status in affiliates_data:
        affiliate_id = str(uuid.uuid4())
        affiliate = {
            "id": affiliate_id,
            "tenant_id": tenant_id,
            "name": name,
            "email": email,
            "phone": None,
            "company": company,
            "website": None,
            "status": status,
            "payout_method": "manual",
            "payout_details": "{}",
            "notes": None,
            "total_earnings": 0,
            "total_paid": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.affiliates.insert_one(affiliate)
        
        # Create affiliate link for active affiliates
        if status == "active":
            import hashlib
            import secrets
            ref_code = hashlib.sha256(f"{affiliate_id}{secrets.token_hex(4)}".encode()).hexdigest()[:8].upper()
            
            link = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "affiliate_id": affiliate_id,
                "program_id": frylow_program["id"],
                "referral_code": ref_code,
                "landing_page_url": "/demo",
                "utm_source": "affiliate",
                "utm_medium": "referral",
                "utm_campaign": "frylow_partner",
                "click_count": 0,
                "conversion_count": 0,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.affiliate_links.insert_one(link)
    
    logger.info("Demo data seeded successfully!")


# ==================== INCLUDE ROUTERS ====================

# Import and include affiliate routes
from app.api.affiliate_routes import router as affiliate_router
api_router.include_router(affiliate_router)

# Import and include marketing materials routes
from app.api.materials_routes import router as materials_router
api_router.include_router(materials_router)

# Import and include affiliate portal routes
from app.api.affiliate_portal_routes import router as portal_router
api_router.include_router(portal_router)

# Import and include landing pages routes
from app.api.landing_pages_routes import router as landing_pages_router
api_router.include_router(landing_pages_router)

# Import and include settings routes
from app.api.settings_routes import router as settings_router
api_router.include_router(settings_router)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
