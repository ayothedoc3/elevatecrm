"""
Elevate CRM - Legacy Server (MongoDB Version)
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
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    company_name: Optional[str] = None
    company: Optional[str] = None  # backward compat
    title: Optional[str] = None
    source: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    tags: List[str] = []


class ContactResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    company_name: Optional[str]
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    title: Optional[str]
    source: Optional[str]
    lifecycle_stage: Optional[str] = None
    tags: List[str]
    status: str
    created_at: str


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    domain: Optional[str] = None


class DealCreate(BaseModel):
    name: str
    amount: float = 0
    contact_id: Optional[str] = None
    pipeline_id: str
    stage_id: str
    next_step_at: Optional[str] = None
    next_step_note: Optional[str] = None
    lead_score: Optional[int] = Field(default=None, ge=0, le=100)
    lead_tier: Optional[str] = None  # A, B, C, D
    sales_motion_type: str = "partnership_sales"
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None


class DealUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    contact_id: Optional[str] = None
    next_step_at: Optional[str] = None
    next_step_note: Optional[str] = None
    lead_score: Optional[int] = Field(default=None, ge=0, le=100)
    lead_tier: Optional[str] = None
    sales_motion_type: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_at: str = Field(..., min_length=1)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    related_type: Optional[str] = None  # deal | lead | contact | account
    related_id: Optional[str] = None
    kind: str = "manual"  # manual | next_step


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    due_at: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # open | completed | canceled


class DealHandoffUpdate(BaseModel):
    delivery_owner_id: Optional[str] = None
    kickoff_at: Optional[str] = None
    checklist: Optional[Dict[str, bool]] = None
    notes: Optional[str] = None


class DealResponse(BaseModel):
    id: str
    name: str
    amount: float
    currency: str
    status: str
    contact_id: Optional[str]
    contact_name: Optional[str]
    lead_score: Optional[int] = None
    lead_tier: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
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


class MoveDealStageRequest(BaseModel):
    stage_id: str
    override: bool = False
    override_reason: Optional[str] = None


class UpdateCalculationRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)


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


VALID_SALES_MOTION_TYPES = {"partnership_sales", "partner_sales"}
VALID_LEAD_TIERS = {"A", "B", "C", "D"}

# Midpoint probabilities from the spec's tier bands:
# A: 0.60-0.80, B: 0.35-0.60, C: 0.15-0.30, D: 0.00
TIER_PROBABILITY = {"A": 0.70, "B": 0.475, "C": 0.225, "D": 0.00}


def calculate_tier(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def tier_probability(tier: Optional[str]) -> float:
    if not tier:
        return 0.0
    return float(TIER_PROBABILITY.get(str(tier).upper(), 0.0))


def normalize_lower(value: Optional[str]) -> str:
    return " ".join((value or "").strip().split()).lower()


async def resolve_account(
    db,
    tenant_id: str,
    account_name: str,
    actor_id: str
) -> Dict[str, Optional[str]]:
    """
    Upsert an Account by name (case-insensitive) and return its id + canonical name.
    """
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


VALID_TASK_STATUSES = {"open", "completed", "canceled"}
VALID_TASK_KINDS = {"manual", "next_step"}
VALID_TASK_RELATED_TYPES = {"deal", "lead", "contact", "account"}

HANDOFF_CHECKLIST_KEYS = [
    "spiced_summary",
    "gap_analysis",
    "proposal",
    "contract",
    "risk_notes",
    "kickoff_readiness_checklist",
]


async def create_task(
    db,
    tenant_id: str,
    title: str,
    due_at: str,
    owner_id: str,
    created_by: str,
    kind: str = "manual",
    related_type: Optional[str] = None,
    related_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    kind_norm = (kind or "manual").strip().lower()
    if kind_norm not in VALID_TASK_KINDS:
        raise HTTPException(status_code=400, detail="Invalid task kind")

    related_type_norm = (related_type or "").strip().lower() if related_type else None
    if related_type_norm and related_type_norm not in VALID_TASK_RELATED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid related_type")

    task = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "title": title,
        "description": description,
        "status": "open",
        "kind": kind_norm,
        "due_at": due_at,
        "completed_at": None,
        "owner_id": owner_id,
        "related_type": related_type_norm,
        "related_id": related_id,
        "metadata": metadata or {},
        "created_by": created_by,
        "created_at": now,
        "updated_at": now
    }
    await db.tasks.insert_one(task)
    task.pop("_id", None)
    return task


async def complete_open_next_step_tasks_for_deal(
    db,
    tenant_id: str,
    deal_id: str,
    actor_id: str
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    result = await db.tasks.update_many(
        {
            "tenant_id": tenant_id,
            "related_type": "deal",
            "related_id": deal_id,
            "kind": "next_step",
            "status": "open"
        },
        {"$set": {
            "status": "completed",
            "completed_at": now,
            "completed_by": actor_id,
            "updated_at": now
        }}
    )
    return int(getattr(result, "modified_count", 0))


async def upsert_open_next_step_task_for_deal(
    db,
    tenant_id: str,
    deal_id: str,
    due_at: str,
    owner_id: str,
    created_by: str,
    note: Optional[str] = None
) -> dict:
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
            {"$set": {
                "due_at": due_at,
                "owner_id": owner_id,
                "description": note if note is not None else existing.get("description"),
                "updated_at": now
            }}
        )
        updated = await db.tasks.find_one({"id": existing["id"], "tenant_id": tenant_id}, {"_id": 0})
        return updated or existing

    task = await create_task(
        db=db,
        tenant_id=tenant_id,
        title="Next Step",
        due_at=due_at,
        owner_id=owner_id,
        created_by=created_by,
        kind="next_step",
        related_type="deal",
        related_id=deal_id,
        description=note
    )
    return task


async def resolve_partner_and_product(
    db,
    tenant_id: str,
    sales_motion_type: str,
    partner_id: Optional[str],
    product_id: Optional[str],
    partner_name: Optional[str],
    product_name: Optional[str],
    actor: dict
) -> Dict[str, Optional[str]]:
    """
    Resolve partner/product requirements for Partner Sales.

    - For `partnership_sales`: always clears partner/product fields.
    - For `partner_sales`: requires partner+product, allowing either IDs or names.
      If names are provided, partner/product are upserted and IDs returned.
    """
    if sales_motion_type not in VALID_SALES_MOTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sales_motion_type. Must be one of: {', '.join(sorted(VALID_SALES_MOTION_TYPES))}"
        )

    if sales_motion_type == "partnership_sales":
        return {"partner_id": None, "partner_name": None, "product_id": None, "product_name": None}

    # partner_sales
    now = datetime.now(timezone.utc).isoformat()

    # Resolve partner
    partner = None
    if partner_id:
        partner = await db.partners.find_one(
            {"id": partner_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not partner:
            raise HTTPException(status_code=400, detail="Partner not found")
        partner_name = partner.get("name")
    else:
        name = (partner_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="partner_name is required for partner_sales")
        name_lower = name.lower()
        partner = await db.partners.find_one(
            {"tenant_id": tenant_id, "name_lower": name_lower},
            {"_id": 0}
        )
        if not partner:
            partner = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "name": name,
                "name_lower": name_lower,
                "is_active": True,
                "created_by": actor.get("id"),
                "created_at": now,
                "updated_at": now
            }
            await db.partners.insert_one(partner)
        partner_id = partner["id"]
        partner_name = partner["name"]

    # Resolve product
    product = None
    if product_id:
        product = await db.products.find_one(
            {"id": product_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
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
                "created_by": actor.get("id"),
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


@api_router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    """List users for the current tenant (for assignment, etc.)"""
    db = get_database()

    cursor = db.users.find(
        {"tenant_id": user["tenant_id"]},
        {"_id": 0, "hashed_password": 0}
    ).sort("created_at", 1)
    users = await cursor.to_list(length=500)

    for u in users:
        u["full_name"] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()

    return {"users": users}


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
                "company_name": c.get("company_name") or c.get("company"),
                "company": c.get("company_name") or c.get("company"),
                "account_id": c.get("account_id"),
                "account_name": c.get("account_name") or c.get("company_name") or c.get("company"),
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

    company_name = (data.company_name or data.company)
    account_name_input = company_name or f"{data.first_name} {data.last_name}".strip()
    resolved_account = await resolve_account(
        db=db,
        tenant_id=user["tenant_id"],
        account_name=account_name_input,
        actor_id=user["id"]
    )
    
    contact = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "phone": data.phone,
        "company_name": company_name,
        "company": company_name,
        "account_id": resolved_account.get("account_id"),
        "account_name": resolved_account.get("account_name"),
        "title": data.title,
        "source": data.source,
        "lifecycle_stage": data.lifecycle_stage or "lead",
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
        "company_name": contact.get("company_name") or contact.get("company"),
        "company": contact.get("company_name") or contact.get("company"),
        "account_id": contact.get("account_id"),
        "account_name": contact.get("account_name") or contact.get("company_name") or contact.get("company"),
        "full_name": f"{contact['first_name']} {contact['last_name']}"
    }


# ==================== ACCOUNTS ====================

@api_router.get("/accounts")
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List accounts/companies for the tenant"""
    db = get_database()

    query: Dict[str, Any] = {"tenant_id": user["tenant_id"]}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    total = await db.accounts.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.accounts.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    accounts = await cursor.to_list(length=page_size)

    return {"accounts": accounts, "total": total, "page": page, "page_size": page_size}


@api_router.post("/accounts", status_code=201)
async def create_account(
    data: AccountCreate,
    user: dict = Depends(get_current_user)
):
    """Create an account (company)"""
    db = get_database()

    resolved = await resolve_account(
        db=db,
        tenant_id=user["tenant_id"],
        account_name=data.name,
        actor_id=user["id"]
    )

    account = await db.accounts.find_one(
        {"id": resolved.get("account_id"), "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not account:
        raise HTTPException(status_code=500, detail="Failed to create account")

    if data.domain and not account.get("domain"):
        now = datetime.now(timezone.utc).isoformat()
        await db.accounts.update_one(
            {"id": account["id"], "tenant_id": user["tenant_id"]},
            {"$set": {"domain": data.domain, "updated_at": now}}
        )
        account["domain"] = data.domain
        account["updated_at"] = now

    return account


@api_router.get("/partners")
async def list_partners(user: dict = Depends(get_current_user)):
    """List partners for the tenant (Partner Sales)"""
    db = get_database()

    cursor = db.partners.find(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    ).sort("name", 1)
    partners = await cursor.to_list(length=500)
    return {"partners": partners}


@api_router.get("/products")
async def list_products(
    partner_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List products for the tenant (optionally filtered by partner)"""
    db = get_database()

    query: Dict[str, Any] = {"tenant_id": user["tenant_id"]}
    if partner_id:
        query["partner_id"] = partner_id

    cursor = db.products.find(query, {"_id": 0}).sort("name", 1)
    products = await cursor.to_list(length=1000)
    return {"products": products}


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
        contacts_cursor = db.contacts.find(
            {"id": {"$in": contact_ids}, "tenant_id": user["tenant_id"]},
            {"_id": 0}
        )
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
    contact_id: Optional[str] = None,
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
    if contact_id:
        query["contact_id"] = contact_id
    
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
            contact = await db.contacts.find_one(
                {"id": deal["contact_id"], "tenant_id": user["tenant_id"]},
                {"_id": 0}
            )
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

    pipeline = await db.pipelines.find_one(
        {"id": data.pipeline_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stage = await db.pipeline_stages.find_one(
        {"id": data.stage_id, "pipeline_id": data.pipeline_id},
        {"_id": 0}
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    contact = None
    if data.contact_id:
        contact = await db.contacts.find_one(
            {"id": data.contact_id, "tenant_id": user["tenant_id"]},
            {"_id": 0}
        )
        if not contact:
            raise HTTPException(status_code=400, detail="Contact not found")

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

    sales_motion_type = (data.sales_motion_type or "partnership_sales").strip()
    resolved = await resolve_partner_and_product(
        db=db,
        tenant_id=user["tenant_id"],
        sales_motion_type=sales_motion_type,
        partner_id=data.partner_id,
        product_id=data.product_id,
        partner_name=data.partner_name,
        product_name=data.product_name,
        actor=user
    )

    # Resolve account from contact (required for deal-level Company/Account linkage)
    resolved_account = {"account_id": None, "account_name": None}
    if contact:
        contact_full_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        account_name_input = (
            contact.get("account_name")
            or contact.get("company_name")
            or contact.get("company")
            or contact_full_name
        )
        if account_name_input:
            resolved_account = await resolve_account(
                db=db,
                tenant_id=user["tenant_id"],
                account_name=account_name_input,
                actor_id=user["id"]
            )
            if not contact.get("account_id"):
                now = datetime.now(timezone.utc).isoformat()
                await db.contacts.update_one(
                    {"id": contact["id"], "tenant_id": user["tenant_id"]},
                    {"$set": {
                        "account_id": resolved_account.get("account_id"),
                        "account_name": resolved_account.get("account_name"),
                        "updated_at": now
                    }}
                )
                contact["account_id"] = resolved_account.get("account_id")
                contact["account_name"] = resolved_account.get("account_name")

    # Deal scoring fields (required for forecasting)
    lead_score = data.lead_score
    lead_tier = (data.lead_tier or "").strip().upper() if data.lead_tier else None
    if lead_score is None and contact and contact.get("lead_score") is not None:
        lead_score = int(contact.get("lead_score"))
    if not lead_tier and contact and contact.get("lead_tier"):
        lead_tier = str(contact.get("lead_tier")).strip().upper()

    if lead_score is not None:
        lead_score = int(max(0, min(100, lead_score)))
    if lead_tier and lead_tier not in VALID_LEAD_TIERS:
        raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")

    if lead_score is not None and not lead_tier:
        lead_tier = calculate_tier(lead_score)
    if lead_tier and lead_score is None:
        lead_score = {"A": 80, "B": 60, "C": 40, "D": 0}.get(lead_tier, 0)
    if lead_score is None:
        lead_score = 0
    if not lead_tier:
        lead_tier = "D"
    
    deal = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "amount": data.amount,
        "currency": "USD",
        "status": "open",
        "contact_id": data.contact_id,
        "account_id": resolved_account.get("account_id"),
        "account_name": resolved_account.get("account_name"),
        "pipeline_id": data.pipeline_id,
        "stage_id": data.stage_id,
        "next_step_at": data.next_step_at,
        "next_step_note": data.next_step_note,
        "lead_score": lead_score,
        "lead_tier": lead_tier,
        "sales_motion_type": sales_motion_type,
        "partner_id": resolved.get("partner_id"),
        "product_id": resolved.get("product_id"),
        "partner_name": resolved.get("partner_name"),
        "product_name": resolved.get("product_name"),
        "owner_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    required_fields = stage.get("required_fields") or []
    missing = [field for field in required_fields if not is_non_empty(deal.get(field))]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for stage '{stage.get('name', 'Unknown')}': {', '.join(missing)}"
        )
    
    await db.deals.insert_one(deal)
    
    # Create timeline event
    await create_timeline_event(
        db, user["tenant_id"], "deal_created",
        f"Deal created: {data.name}",
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=deal["id"]
    )

    # Create/Sync Next Step task (discipline)
    if deal.get("next_step_at"):
        await upsert_open_next_step_task_for_deal(
            db=db,
            tenant_id=user["tenant_id"],
            deal_id=deal["id"],
            due_at=deal.get("next_step_at"),
            owner_id=deal.get("owner_id") or user["id"],
            created_by=user["id"],
            note=deal.get("next_step_note")
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
        contact = await db.contacts.find_one(
            {"id": deal["contact_id"], "tenant_id": user["tenant_id"]},
            {"_id": 0}
        )
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


@api_router.put("/deals/{deal_id}")
async def update_deal(
    deal_id: str,
    data: DealUpdate,
    user: dict = Depends(get_current_user)
):
    """Update mutable deal fields (phase 1: next step + basic edits)"""
    db = get_database()

    existing = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Deal not found")

    current_stage = None
    if existing.get("stage_id"):
        current_stage = await db.pipeline_stages.find_one(
            {"id": existing.get("stage_id")},
            {"_id": 0}
        )
    current_required = set((current_stage or {}).get("required_fields") or [])

    update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if data.name is not None:
        update_data["name"] = data.name
    if data.amount is not None:
        update_data["amount"] = data.amount
    if data.contact_id is not None:
        if not data.contact_id:
            if "contact_id" in current_required:
                raise HTTPException(status_code=400, detail="contact_id is required for the current stage")
            update_data["contact_id"] = None
            update_data["account_id"] = None
            update_data["account_name"] = None
        else:
            contact = await db.contacts.find_one(
                {"id": data.contact_id, "tenant_id": user["tenant_id"]},
                {"_id": 0}
            )
            if not contact:
                raise HTTPException(status_code=400, detail="Contact not found")
            update_data["contact_id"] = data.contact_id

            contact_full_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
            account_name_input = (
                contact.get("account_name")
                or contact.get("company_name")
                or contact.get("company")
                or contact_full_name
            )
            if account_name_input:
                resolved_account = await resolve_account(
                    db=db,
                    tenant_id=user["tenant_id"],
                    account_name=account_name_input,
                    actor_id=user["id"]
                )
                update_data["account_id"] = resolved_account.get("account_id")
                update_data["account_name"] = resolved_account.get("account_name")
                if not contact.get("account_id"):
                    await db.contacts.update_one(
                        {"id": contact["id"], "tenant_id": user["tenant_id"]},
                        {"$set": {
                            "account_id": resolved_account.get("account_id"),
                            "account_name": resolved_account.get("account_name"),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )

            # If caller didn't specify scoring, inherit from contact when available
            if data.lead_score is None and data.lead_tier is None:
                if contact.get("lead_score") is not None:
                    update_data["lead_score"] = int(contact.get("lead_score"))
                if contact.get("lead_tier"):
                    update_data["lead_tier"] = str(contact.get("lead_tier")).strip().upper()
    if data.next_step_at is not None:
        value = (data.next_step_at or "").strip()
        if value == "":
            if "next_step_at" in current_required:
                raise HTTPException(status_code=400, detail="next_step_at is required for the current stage")
            update_data["next_step_at"] = None
        else:
            update_data["next_step_at"] = data.next_step_at
    if data.next_step_note is not None:
        update_data["next_step_note"] = data.next_step_note

    if data.lead_score is not None or data.lead_tier is not None:
        lead_score = data.lead_score
        lead_tier = (data.lead_tier or "").strip().upper() if data.lead_tier is not None else None

        if lead_score is not None:
            lead_score = int(max(0, min(100, lead_score)))
        if lead_tier and lead_tier not in VALID_LEAD_TIERS:
            raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")

        if lead_score is not None and not lead_tier:
            lead_tier = calculate_tier(lead_score)
        if lead_tier and lead_score is None:
            lead_score = {"A": 80, "B": 60, "C": 40, "D": 0}.get(lead_tier, 0)

        if lead_score is not None:
            update_data["lead_score"] = lead_score
        if lead_tier is not None:
            update_data["lead_tier"] = lead_tier

    motion_update_requested = any([
        data.sales_motion_type is not None,
        data.partner_id is not None,
        data.product_id is not None,
        data.partner_name is not None,
        data.product_name is not None,
    ])

    if motion_update_requested:
        sales_motion_type = (data.sales_motion_type or existing.get("sales_motion_type") or "partnership_sales").strip()
        resolved = await resolve_partner_and_product(
            db=db,
            tenant_id=user["tenant_id"],
            sales_motion_type=sales_motion_type,
            partner_id=data.partner_id if data.partner_id is not None else existing.get("partner_id"),
            product_id=data.product_id if data.product_id is not None else existing.get("product_id"),
            partner_name=data.partner_name if data.partner_name is not None else existing.get("partner_name"),
            product_name=data.product_name if data.product_name is not None else existing.get("product_name"),
            actor=user
        )
        update_data["sales_motion_type"] = sales_motion_type
        update_data["partner_id"] = resolved.get("partner_id")
        update_data["product_id"] = resolved.get("product_id")
        update_data["partner_name"] = resolved.get("partner_name")
        update_data["product_name"] = resolved.get("product_name")

    await db.deals.update_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"$set": update_data}
    )

    updated = await db.deals.find_one({"id": deal_id, "tenant_id": user["tenant_id"]}, {"_id": 0})

    # Keep Next Step task in sync
    if updated and ("next_step_at" in update_data or "next_step_note" in update_data or "owner_id" in update_data):
        if updated.get("next_step_at"):
            await upsert_open_next_step_task_for_deal(
                db=db,
                tenant_id=user["tenant_id"],
                deal_id=deal_id,
                due_at=updated.get("next_step_at"),
                owner_id=updated.get("owner_id") or user["id"],
                created_by=user["id"],
                note=updated.get("next_step_note")
            )
        else:
            now = datetime.now(timezone.utc).isoformat()
            await db.tasks.update_many(
                {
                    "tenant_id": user["tenant_id"],
                    "related_type": "deal",
                    "related_id": deal_id,
                    "kind": "next_step",
                    "status": "open"
                },
                {"$set": {"status": "canceled", "updated_at": now}}
            )
    return updated


# ==================== DEAL HANDOFF (Delivery) ====================

async def get_or_create_deal_handoff(db, tenant_id: str, deal_id: str, actor_id: str) -> dict:
    existing = await db.deal_handoffs.find_one(
        {"tenant_id": tenant_id, "deal_id": deal_id},
        {"_id": 0}
    )
    if existing:
        return existing

    now = datetime.now(timezone.utc).isoformat()
    handoff = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "deal_id": deal_id,
        "status": "pending",
        "delivery_owner_id": None,
        "kickoff_at": None,
        "checklist": {k: False for k in HANDOFF_CHECKLIST_KEYS},
        "notes": None,
        "completed_at": None,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now
    }
    await db.deal_handoffs.insert_one(handoff)
    handoff.pop("_id", None)
    return handoff


def is_handoff_complete(handoff: dict) -> bool:
    if not handoff:
        return False
    if not handoff.get("delivery_owner_id"):
        return False
    if not handoff.get("kickoff_at"):
        return False
    checklist = handoff.get("checklist") or {}
    return all(bool(checklist.get(k)) for k in HANDOFF_CHECKLIST_KEYS)


@api_router.get("/deals/{deal_id}/handoff")
async def get_deal_handoff(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """Get (or create) the delivery handoff packet for a deal"""
    db = get_database()

    deal = await db.deals.find_one({"id": deal_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    handoff = await get_or_create_deal_handoff(db, user["tenant_id"], deal_id, user["id"])
    handoff["is_complete"] = is_handoff_complete(handoff)
    return handoff


@api_router.put("/deals/{deal_id}/handoff")
async def update_deal_handoff(
    deal_id: str,
    data: DealHandoffUpdate,
    user: dict = Depends(get_current_user)
):
    """Update the delivery handoff packet for a deal"""
    db = get_database()

    deal = await db.deals.find_one({"id": deal_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    handoff = await get_or_create_deal_handoff(db, user["tenant_id"], deal_id, user["id"])

    update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if data.delivery_owner_id is not None:
        if data.delivery_owner_id:
            owner = await db.users.find_one(
                {"id": data.delivery_owner_id, "tenant_id": user["tenant_id"]},
                {"_id": 0}
            )
            if not owner:
                raise HTTPException(status_code=400, detail="Delivery owner not found")
            update_data["delivery_owner_id"] = data.delivery_owner_id
        else:
            update_data["delivery_owner_id"] = None

    if data.kickoff_at is not None:
        value = (data.kickoff_at or "").strip()
        update_data["kickoff_at"] = value if value else None

    if data.notes is not None:
        update_data["notes"] = data.notes

    if data.checklist is not None:
        incoming = data.checklist or {}
        invalid_keys = [k for k in incoming.keys() if k not in HANDOFF_CHECKLIST_KEYS]
        if invalid_keys:
            raise HTTPException(status_code=400, detail=f"Invalid checklist keys: {', '.join(invalid_keys)}")

        merged = {k: bool((handoff.get('checklist') or {}).get(k)) for k in HANDOFF_CHECKLIST_KEYS}
        for k, v in incoming.items():
            merged[k] = bool(v)
        update_data["checklist"] = merged

    await db.deal_handoffs.update_one(
        {"id": handoff["id"], "tenant_id": user["tenant_id"]},
        {"$set": update_data}
    )

    updated = await db.deal_handoffs.find_one(
        {"id": handoff["id"], "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update handoff")

    complete = is_handoff_complete(updated)
    if complete and updated.get("status") != "completed":
        now = datetime.now(timezone.utc).isoformat()
        await db.deal_handoffs.update_one(
            {"id": updated["id"], "tenant_id": user["tenant_id"]},
            {"$set": {"status": "completed", "completed_at": now, "updated_at": now}}
        )
        updated["status"] = "completed"
        updated["completed_at"] = now

        await db.deals.update_one(
            {"id": deal_id, "tenant_id": user["tenant_id"]},
            {"$set": {"handoff_status": "completed", "handoff_completed_at": now, "updated_at": now}}
        )

        await create_timeline_event(
            db, user["tenant_id"], "handoff_completed",
            "Delivery handoff completed",
            actor_id=user["id"],
            actor_name=f"{user['first_name']} {user['last_name']}",
            deal_id=deal_id,
            metadata={"handoff_id": updated.get("id")}
        )
    elif not complete and updated.get("status") == "completed":
        # Allow reopening if required data is removed
        now = datetime.now(timezone.utc).isoformat()
        await db.deal_handoffs.update_one(
            {"id": updated["id"], "tenant_id": user["tenant_id"]},
            {"$set": {"status": "pending", "completed_at": None, "updated_at": now}}
        )
        updated["status"] = "pending"
        updated["completed_at"] = None

        await db.deals.update_one(
            {"id": deal_id, "tenant_id": user["tenant_id"]},
            {"$set": {"handoff_status": "pending", "handoff_completed_at": None, "updated_at": now}}
        )

    updated["is_complete"] = complete
    return updated


@api_router.post("/deals/{deal_id}/move-stage")
async def move_deal_stage(
    deal_id: str,
    payload: Optional[MoveDealStageRequest] = None,
    new_stage_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user)
):
    """Move a deal to a new stage"""
    db = get_database()

    if payload and payload.stage_id:
        new_stage_id = payload.stage_id
    if not new_stage_id:
        raise HTTPException(status_code=422, detail="stage_id is required")

    override = bool(payload.override) if payload else False
    override_reason = (payload.override_reason or "").strip() if payload else ""

    if override:
        if user.get("role") not in ["admin", "manager"]:
            raise HTTPException(status_code=403, detail="Admin access required to override stage rules")
        if len(override_reason) < 3:
            raise HTTPException(status_code=400, detail="override_reason is required when override=true")
    
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

    new_stage_name = (new_stage.get("name") or "").strip()
    new_stage_name_lower = new_stage_name.lower()
    moving_to_closed_won = "closed won" in new_stage_name_lower
    moving_to_closed_lost = "closed lost" in new_stage_name_lower
    moving_to_handoff = "handoff" in new_stage_name_lower

    def _is_non_empty(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, tuple, set)):
            return len(value) > 0
        if isinstance(value, dict):
            return len(value) > 0
        return True

    def _get_by_path(obj: Any, path: str):
        current = obj
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _stage_requires_calculation(stage_doc: dict) -> bool:
        if stage_doc.get("requires_calculation_complete") is True:
            return True
        name = (stage_doc.get("name") or "").lower()
        return ("demo" in name and ("schedule" in name or "scheduled" in name)) or ("discovery" in name and "scheduled" in name)

    if not override:
        # Closed deals are locked by default
        if (deal.get("status") or "open") in ["won", "lost"]:
            if not (moving_to_closed_won or moving_to_closed_lost or moving_to_handoff):
                raise HTTPException(status_code=400, detail="Deal is closed. Stage changes require an admin override")

        # Stage required fields (deal-level)
        required_fields = new_stage.get("required_fields") or []
        missing = [field for field in required_fields if not _is_non_empty(_get_by_path(deal, field))]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields for stage '{new_stage.get('name', 'Unknown')}': {', '.join(missing)}"
            )

        # Calculations requirement (server-side enforcement)
        if _stage_requires_calculation(new_stage):
            calc_def = await db.calculation_definitions.find_one(
                {"tenant_id": user["tenant_id"], "is_active": True},
                {"_id": 0}
            )
            if calc_def:
                calc_result = await db.calculation_results.find_one(
                    {"deal_id": deal_id, "definition_id": calc_def["id"]},
                    {"_id": 0}
                )
                if not calc_result or not calc_result.get("is_complete"):
                    raise HTTPException(
                        status_code=400,
                        detail="Calculation must be complete before moving to this stage"
                    )

        # Handoff enforcement
        if moving_to_handoff:
            handoff = await db.deal_handoffs.find_one(
                {"tenant_id": user["tenant_id"], "deal_id": deal_id},
                {"_id": 0}
            )
            if not handoff or not is_handoff_complete(handoff):
                raise HTTPException(
                    status_code=400,
                    detail="Delivery handoff must be completed before moving to Handoff to Delivery"
                )
    
    # Update deal
    now = datetime.now(timezone.utc).isoformat()
    previous_status = (deal.get("status") or "open").lower()

    set_payload: Dict[str, Any] = {
        "stage_id": new_stage_id,
        "updated_at": now,
    }

    if moving_to_closed_won:
        set_payload["status"] = "won"
        set_payload["closed_won_at"] = now
        set_payload["closed_at"] = now
    elif moving_to_closed_lost:
        set_payload["status"] = "lost"
        set_payload["closed_lost_at"] = now
        set_payload["closed_at"] = now
    elif previous_status in ["won", "lost"] and not moving_to_handoff:
        # Reopening requires override (enforced above)
        set_payload["status"] = "open"
        set_payload["reopened_at"] = now

    if override:
        set_payload["last_override"] = {
            "from_stage_id": deal.get("stage_id"),
            "to_stage_id": new_stage_id,
            "reason": override_reason,
            "actor_id": user.get("id"),
            "actor_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "created_at": now
        }

    await db.deals.update_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"$set": set_payload}
    )

    # If deal is now closed, close out Next Step tasks
    if set_payload.get("status") in ["won", "lost"]:
        await complete_open_next_step_tasks_for_deal(db, user["tenant_id"], deal_id, user["id"])
    
    # Create timeline event
    await create_timeline_event(
        db, user["tenant_id"], "stage_changed",
        f"Stage changed: {old_stage['name'] if old_stage else 'Unknown'} → {new_stage['name']}",
        actor_id=user["id"],
        actor_name=f"{user['first_name']} {user['last_name']}",
        deal_id=deal_id,
        metadata={
            "from_stage": old_stage["name"] if old_stage else None,
            "to_stage": new_stage["name"],
            "override": override,
            **({"override_reason": override_reason} if override else {})
        }
    )

    # Dedicated close events + handoff creation
    if moving_to_closed_won and previous_status != "won":
        await create_timeline_event(
            db, user["tenant_id"], "deal_won",
            "Deal marked Closed Won",
            actor_id=user["id"],
            actor_name=f"{user['first_name']} {user['last_name']}",
            deal_id=deal_id
        )
        handoff = await get_or_create_deal_handoff(db, user["tenant_id"], deal_id, user["id"])
        await db.deals.update_one(
            {"id": deal_id, "tenant_id": user["tenant_id"]},
            {"$set": {"handoff_status": handoff.get("status"), "updated_at": now}}
        )

    if moving_to_closed_lost and previous_status != "lost":
        await create_timeline_event(
            db, user["tenant_id"], "deal_lost",
            "Deal marked Closed Lost",
            actor_id=user["id"],
            actor_name=f"{user['first_name']} {user['last_name']}",
            deal_id=deal_id
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
    result = await update_deal_calculation(
        deal_id=deal_id,
        data=UpdateCalculationRequest(inputs=inputs),
        user=user
    )

    # Backwards-compatible response shape
    return {"success": True, "is_complete": result["is_complete"], "outputs": result["outputs"]}


@api_router.put("/calculations/deal/{deal_id}")
async def update_deal_calculation(
    deal_id: str,
    data: UpdateCalculationRequest,
    user: dict = Depends(get_current_user)
):
    """Update calculation inputs for a deal and compute outputs"""
    db = get_database()

    calc_def = await db.calculation_definitions.find_one(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    )

    if not calc_def:
        raise HTTPException(status_code=404, detail="No calculation defined")

    input_schema = json.loads(calc_def.get("input_schema", "[]"))

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

    missing_fields = []
    for field in input_schema:
        if field.get("required") and not is_non_empty(data.inputs.get(field.get("name"))):
            missing_fields.append(field.get("name"))

    is_complete = len(missing_fields) == 0

    # Simple Frylow ROI calculation (only meaningful if required inputs exist)
    outputs = {}
    try:
        quantity = float(data.inputs.get("quantity_per_month", 0) or 0)
        cost = float(data.inputs.get("cost_per_unit", 0) or 0)

        monthly_spend = quantity * cost
        yearly_spend = monthly_spend * 12

        outputs = {
            "monthly_oil_spend": monthly_spend,
            "yearly_oil_spend": yearly_spend,
            "estimated_savings_low": yearly_spend * 0.3,
            "estimated_savings_high": yearly_spend * 0.5,
            "recommended_device_quantity": max(1, int(data.inputs.get("number_of_fryers", 1) or 1)),
            "recommended_device_size": "Standard"
        }
    except Exception as e:
        logger.error(f"Calculation error: {e}")

    now = datetime.now(timezone.utc).isoformat()
    result_doc = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "definition_id": calc_def["id"],
        "deal_id": deal_id,
        "inputs": json.dumps(data.inputs),
        "outputs": json.dumps(outputs),
        "is_complete": is_complete,
        "calculated_at": now if is_complete else None,
        "updated_at": now
    }

    await db.calculation_results.update_one(
        {"deal_id": deal_id, "definition_id": calc_def["id"]},
        {"$set": result_doc},
        upsert=True
    )

    return {
        "id": result_doc["id"],
        "inputs": data.inputs,
        "outputs": outputs,
        "is_complete": is_complete,
        "status": "complete" if is_complete else "missing_inputs",
        "missing_fields": missing_fields,
        "validation_errors": [f"Missing required field: {f}" for f in missing_fields],
        "inputs_changed": True,
        "stage_returned": False
    }


@api_router.get("/calculations/deal/{deal_id}/check")
async def check_deal_calculation(
    deal_id: str,
    user: dict = Depends(get_current_user)
):
    """Check whether required calculation inputs have been collected for a deal"""
    db = get_database()

    calc_def = await db.calculation_definitions.find_one(
        {"tenant_id": user["tenant_id"], "is_active": True},
        {"_id": 0}
    )

    if not calc_def:
        return {"is_complete": True, "error_message": None, "missing_fields": []}

    input_schema = json.loads(calc_def.get("input_schema", "[]"))

    result = await db.calculation_results.find_one(
        {"deal_id": deal_id, "definition_id": calc_def["id"]},
        {"_id": 0}
    )

    inputs = json.loads(result.get("inputs", "{}")) if result else {}

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

    missing_fields = []
    for field in input_schema:
        if field.get("required") and not is_non_empty(inputs.get(field.get("name"))):
            missing_fields.append(field.get("name"))

    is_complete = len(missing_fields) == 0
    return {
        "is_complete": is_complete,
        "error_message": None if is_complete else "Missing required calculation inputs",
        "missing_fields": missing_fields
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

    # Discipline: after every interaction, complete the current Next Step task and create a new one.
    deal = await db.deals.find_one({"id": deal_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if deal and deal.get("status") == "open":
        await complete_open_next_step_tasks_for_deal(db, user["tenant_id"], deal_id, user["id"])
        if deal.get("next_step_at"):
            await upsert_open_next_step_task_for_deal(
                db=db,
                tenant_id=user["tenant_id"],
                deal_id=deal_id,
                due_at=deal.get("next_step_at"),
                owner_id=deal.get("owner_id") or user["id"],
                created_by=user["id"],
                note=deal.get("next_step_note")
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


# ==================== TASKS ====================

@api_router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str = "open",
    owner_id: Optional[str] = None,
    related_type: Optional[str] = None,
    related_id: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List tasks for the tenant (supports filtering)"""
    db = get_database()

    query: Dict[str, Any] = {"tenant_id": user["tenant_id"]}

    status_norm = (status or "open").strip().lower()
    if status_norm != "all":
        if status_norm not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status. Use open|completed|canceled|all")
        query["status"] = status_norm

    if owner_id:
        query["owner_id"] = owner_id

    if related_type:
        rt = related_type.strip().lower()
        if rt not in VALID_TASK_RELATED_TYPES:
            raise HTTPException(status_code=400, detail="Invalid related_type")
        query["related_type"] = rt
    if related_id:
        query["related_id"] = related_id

    if due_before or due_after:
        query["due_at"] = {}
        if due_after:
            query["due_at"]["$gte"] = due_after
        if due_before:
            query["due_at"]["$lte"] = due_before

    total = await db.tasks.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.tasks.find(query, {"_id": 0}).sort("due_at", 1).skip(skip).limit(page_size)
    tasks = await cursor.to_list(length=page_size)

    # Enrich owner names
    owner_ids = list({t.get("owner_id") for t in tasks if t.get("owner_id")})
    owners_map = {}
    if owner_ids:
        owners_cursor = db.users.find(
            {"tenant_id": user["tenant_id"], "id": {"$in": owner_ids}},
            {"_id": 0, "first_name": 1, "last_name": 1, "email": 1}
        )
        owners = await owners_cursor.to_list(length=500)
        owners_map = {o["id"]: o for o in owners}

    for t in tasks:
        owner = owners_map.get(t.get("owner_id"))
        if owner:
            t["owner_name"] = f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip() or owner.get("email")

    return {"tasks": tasks, "total": total, "page": page, "page_size": page_size}


@api_router.post("/tasks", status_code=201)
async def create_task_endpoint(
    data: TaskCreate,
    user: dict = Depends(get_current_user)
):
    """Create a task"""
    db = get_database()

    owner_id = data.owner_id or user["id"]
    owner = await db.users.find_one({"id": owner_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not owner:
        raise HTTPException(status_code=400, detail="Owner not found")

    related_type = (data.related_type or "").strip().lower() if data.related_type else None
    if related_type and related_type not in VALID_TASK_RELATED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid related_type")

    if related_type and not data.related_id:
        raise HTTPException(status_code=400, detail="related_id is required when related_type is provided")

    # Optionally validate related object exists
    if related_type == "deal":
        deal = await db.deals.find_one({"id": data.related_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
        if not deal:
            raise HTTPException(status_code=400, detail="Related deal not found")
    if related_type == "contact":
        contact = await db.contacts.find_one({"id": data.related_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
        if not contact:
            raise HTTPException(status_code=400, detail="Related contact not found")
    if related_type == "account":
        account = await db.accounts.find_one({"id": data.related_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
        if not account:
            raise HTTPException(status_code=400, detail="Related account not found")
    if related_type == "lead":
        lead = await db.leads.find_one({"id": data.related_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=400, detail="Related lead not found")

    task = await create_task(
        db=db,
        tenant_id=user["tenant_id"],
        title=data.title,
        due_at=data.due_at,
        owner_id=owner_id,
        created_by=user["id"],
        kind=data.kind,
        related_type=related_type,
        related_id=data.related_id,
        description=data.description
    )

    # Create timeline event for deal/contact-linked tasks
    if related_type in ["deal", "contact"] and data.related_id:
        await create_timeline_event(
            db, user["tenant_id"], "task",
            f"Task created: {task.get('title')}",
            actor_id=user["id"],
            actor_name=f"{user['first_name']} {user['last_name']}",
            deal_id=data.related_id if related_type == "deal" else None,
            contact_id=data.related_id if related_type == "contact" else None,
            description=task.get("description"),
            metadata={"task_id": task["id"], "due_at": task.get("due_at"), "status": task.get("status")}
        )

    return task


@api_router.put("/tasks/{task_id}")
async def update_task_endpoint(
    task_id: str,
    data: TaskUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a task (including marking complete)"""
    db = get_database()

    task = await db.tasks.find_one({"id": task_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.due_at is not None:
        update_data["due_at"] = data.due_at
    if data.status is not None:
        status_norm = data.status.strip().lower()
        if status_norm not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        update_data["status"] = status_norm
        if status_norm == "completed":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            update_data["completed_by"] = user["id"]
        elif status_norm == "open":
            update_data["completed_at"] = None
            update_data["completed_by"] = None

    await db.tasks.update_one(
        {"id": task_id, "tenant_id": user["tenant_id"]},
        {"$set": update_data}
    )

    updated = await db.tasks.find_one({"id": task_id, "tenant_id": user["tenant_id"]}, {"_id": 0})

    # Timeline event for completion (deal/contact)
    if updated and data.status is not None and updated.get("related_type") in ["deal", "contact"]:
        await create_timeline_event(
            db, user["tenant_id"], "task",
            f"Task {updated.get('status')}: {updated.get('title')}",
            actor_id=user["id"],
            actor_name=f"{user['first_name']} {user['last_name']}",
            deal_id=updated.get("related_id") if updated.get("related_type") == "deal" else None,
            contact_id=updated.get("related_id") if updated.get("related_type") == "contact" else None,
            description=updated.get("description"),
            metadata={"task_id": updated.get("id"), "due_at": updated.get("due_at"), "status": updated.get("status")}
        )

    return updated


# ==================== FORECASTING & KPI (Phase 1) ====================

@api_router.get("/forecast/summary")
async def get_forecast_summary(
    sales_motion_type: Optional[str] = None,
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    lead_tier: Optional[str] = None,
    owner_id: Optional[str] = None,
    include_closed: bool = False,
    stale_days: int = Query(3, ge=1, le=90),
    user: dict = Depends(get_current_user)
):
    """Weighted forecast summary using tier probability (filterable)."""
    db = get_database()

    query: Dict[str, Any] = {"tenant_id": user["tenant_id"]}
    if not include_closed:
        query["status"] = "open"
    if sales_motion_type:
        query["sales_motion_type"] = sales_motion_type
    if partner_id:
        query["partner_id"] = partner_id
    if product_id:
        query["product_id"] = product_id
    if owner_id:
        query["owner_id"] = owner_id
    if lead_tier:
        tier_norm = lead_tier.strip().upper()
        if tier_norm not in VALID_LEAD_TIERS:
            raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")
        query["lead_tier"] = tier_norm

    cursor = db.deals.find(query, {"_id": 0})
    deals = await cursor.to_list(length=5000)

    deal_ids = [d.get("id") for d in deals if d.get("id")]

    # Last activity per deal (outreach)
    last_activity_map: Dict[str, str] = {}
    if deal_ids:
        pipeline = [
            {"$match": {"tenant_id": user["tenant_id"], "deal_id": {"$in": deal_ids}}},
            {"$group": {"_id": "$deal_id", "last_activity_at": {"$max": "$created_at"}}}
        ]
        rows = await db.outreach_activities.aggregate(pipeline).to_list(length=5000)
        last_activity_map = {r["_id"]: r.get("last_activity_at") for r in rows if r.get("_id")}

    def parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    now_dt = datetime.now(timezone.utc)
    totals = {
        "deal_count": 0,
        "pipeline_value": 0.0,
        "weighted_value": 0.0,
        "overdue_next_steps": 0,
        "missing_next_steps": 0,
        "stale_no_activity": 0,
    }

    by_tier: Dict[str, Dict[str, Any]] = {
        t: {"deal_count": 0, "pipeline_value": 0.0, "weighted_value": 0.0, "probability": tier_probability(t)}
        for t in VALID_LEAD_TIERS
    }

    for d in deals:
        status_val = (d.get("status") or "open").lower()
        if not include_closed and status_val != "open":
            continue

        amount = float(d.get("amount") or 0)

        tier = (d.get("lead_tier") or "").strip().upper()
        if tier not in VALID_LEAD_TIERS:
            score = int(d.get("lead_score") or 0)
            tier = calculate_tier(score)

        prob = tier_probability(tier)
        weighted = amount * prob

        totals["deal_count"] += 1
        totals["pipeline_value"] += amount
        totals["weighted_value"] += weighted

        by_tier[tier]["deal_count"] += 1
        by_tier[tier]["pipeline_value"] += amount
        by_tier[tier]["weighted_value"] += weighted

        # SLA checks (next step + activity freshness)
        next_step_at = parse_iso(d.get("next_step_at"))
        if status_val == "open":
            if not next_step_at:
                totals["missing_next_steps"] += 1
            elif next_step_at <= now_dt:
                totals["overdue_next_steps"] += 1

        last_activity_at = parse_iso(last_activity_map.get(d.get("id")))
        baseline = last_activity_at or parse_iso(d.get("updated_at")) or parse_iso(d.get("created_at"))
        if baseline:
            days_since = (now_dt - baseline).days
            if days_since >= stale_days:
                totals["stale_no_activity"] += 1

    return {
        "filters": {
            "sales_motion_type": sales_motion_type,
            "partner_id": partner_id,
            "product_id": product_id,
            "lead_tier": lead_tier,
            "owner_id": owner_id,
            "include_closed": include_closed,
            "stale_days": stale_days,
        },
        "totals": {
            **totals,
            "pipeline_value": round(totals["pipeline_value"], 2),
            "weighted_value": round(totals["weighted_value"], 2),
        },
        "by_tier": {
            t: {
                **by_tier[t],
                "pipeline_value": round(by_tier[t]["pipeline_value"], 2),
                "weighted_value": round(by_tier[t]["weighted_value"], 2),
            }
            for t in sorted(by_tier.keys())
        }
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

    # Create manager user
    manager_id = str(uuid.uuid4())
    manager = {
        "id": manager_id,
        "tenant_id": tenant_id,
        "email": "manager@demo.com",
        "hashed_password": get_password_hash("manager123"),
        "first_name": "Manager",
        "last_name": "User",
        "role": "manager",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(manager)

    # Create sales rep user
    sales_id = str(uuid.uuid4())
    sales = {
        "id": sales_id,
        "tenant_id": tenant_id,
        "email": "sales@demo.com",
        "hashed_password": get_password_hash("sales123"),
        "first_name": "Sales",
        "last_name": "Rep",
        "role": "sales",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(sales)
    
    # Create pipeline
    pipeline_id = str(uuid.uuid4())
    pipeline = {
        "id": pipeline_id,
        "tenant_id": tenant_id,
        "name": "Elev8 Sales Pipeline",
        "description": "Playbook-aligned sales pipeline (Phase 1)",
        "is_default": True,
        "display_order": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.pipelines.insert_one(pipeline)
    
    # Create stages (Phase 1 baseline)
    stages_data = [
        {"name": "Calculations / Analysis In Progress", "color": "#6366F1", "probability": 15, "required_fields": ["next_step_at", "contact_id"]},
        {"name": "Discovery / Demo Scheduled", "color": "#8B5CF6", "probability": 25, "required_fields": ["next_step_at", "contact_id"], "requires_calculation_complete": True},
        {"name": "Discovery / Demo Completed", "color": "#A855F7", "probability": 35, "required_fields": ["next_step_at", "contact_id"]},
        {"name": "Decision Pending", "color": "#C084FC", "probability": 45, "required_fields": ["next_step_at", "contact_id"]},
        {"name": "Trial / Pilot", "color": "#D946EF", "probability": 55, "required_fields": ["next_step_at", "contact_id"]},
        {"name": "Verbal Commitment", "color": "#EC4899", "probability": 65, "required_fields": ["next_step_at", "contact_id"]},
        {"name": "Closed Won", "color": "#10B981", "probability": 100},
        {"name": "Closed Lost", "color": "#EF4444", "probability": 0},
        {"name": "Handoff to Delivery", "color": "#F97316", "probability": 100}
    ]
    
    stage_ids = []
    stage_id_by_name = {}
    for i, cfg in enumerate(stages_data):
        stage_id = str(uuid.uuid4())
        stage = {
            "id": stage_id,
            "pipeline_id": pipeline_id,
            "name": cfg["name"],
            "color": cfg.get("color", "#6366F1"),
            "probability": cfg.get("probability", 0),
            "display_order": i,
            "required_fields": cfg.get("required_fields", []),
            "requires_calculation_complete": cfg.get("requires_calculation_complete", False),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if not stage.get("required_fields"):
            stage.pop("required_fields", None)
        if not stage.get("requires_calculation_complete"):
            stage.pop("requires_calculation_complete", None)
        await db.pipeline_stages.insert_one(stage)
        stage_ids.append(stage_id)
        stage_id_by_name[cfg["name"]] = stage_id
    
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
        resolved_account = await resolve_account(
            db=db,
            tenant_id=tenant_id,
            account_name=company,
            actor_id=admin_id
        )
        contact = {
            "id": contact_id,
            "tenant_id": tenant_id,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "company_name": company,
            "company": company,
            "account_id": resolved_account.get("account_id"),
            "account_name": resolved_account.get("account_name"),
            "lifecycle_stage": "lead",
            "status": "active",
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.contacts.insert_one(contact)
        contact_ids.append(contact_id)
    
    # Create deals
    deals_data = [
        ("Smith's Diner - ROI Analysis", 4500, "Calculations / Analysis In Progress"),
        ("Big Burger Chain - Demo Scheduled", 12500, "Discovery / Demo Scheduled"),
        ("Tasty Foods - Demo Completed", 3200, "Discovery / Demo Completed"),
        ("Food Court Express - Decision Pending", 5800, "Decision Pending"),
        ("Fries King - Verbal Commitment", 7200, "Verbal Commitment")
    ]
    
    for i, (name, amount, stage_name) in enumerate(deals_data):
        contact_doc = await db.contacts.find_one(
            {"id": contact_ids[i], "tenant_id": tenant_id},
            {"_id": 0}
        )
        lead_score = 55 + (i * 5)
        lead_score = int(max(0, min(100, lead_score)))
        lead_tier = calculate_tier(lead_score)
        deal = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id,
            "stage_id": stage_id_by_name.get(stage_name) or stage_ids[0],
            "contact_id": contact_ids[i],
            "account_id": (contact_doc or {}).get("account_id"),
            "account_name": (contact_doc or {}).get("account_name"),
            "owner_id": admin_id,
            "name": name,
            "amount": amount,
            "currency": "USD",
            "status": "open",
            "sales_motion_type": "partnership_sales",
            "next_step_at": (datetime.now(timezone.utc) + timedelta(days=2 + i)).isoformat(),
            "next_step_note": "Follow up scheduled",
            "lead_score": lead_score,
            "lead_tier": lead_tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.deals.insert_one(deal)

        # Seed Next Step task
        await upsert_open_next_step_task_for_deal(
            db=db,
            tenant_id=tenant_id,
            deal_id=deal["id"],
            due_at=deal.get("next_step_at"),
            owner_id=deal.get("owner_id"),
            created_by=admin_id,
            note=deal.get("next_step_note")
        )
        
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
        "qualifying_stage_id": stage_id_by_name.get("Closed Won"),  # Closed Won stage
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


# ==================== INBOX / CONVERSATIONS ====================

@api_router.get("/inbox")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List conversations in inbox"""
    db = get_database()

    # Build query
    query = {"tenant_id": user["tenant_id"]}
    if channel:
        query["channel"] = channel

    # Count total
    total = await db.conversations.count_documents(query)

    # Get conversations
    skip = (page - 1) * page_size
    cursor = db.conversations.find(query, {"_id": 0}).sort("last_message_at", -1).skip(skip).limit(page_size)
    conversations = await cursor.to_list(length=page_size)

    # Enrich with contact info
    conv_responses = []
    for conv in conversations:
        # Get contact info
        contact = await db.contacts.find_one({"id": conv.get("contact_id")}, {"_id": 0})
        conv_responses.append({
            **conv,
            "contact_name": f"{contact['first_name']} {contact['last_name']}" if contact else "Unknown",
            "contact_email": contact.get("email") if contact else None,
            "contact_phone": contact.get("phone") if contact else None
        })

    return {
        "conversations": conv_responses,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@api_router.get("/inbox/stats")
async def get_inbox_stats(user: dict = Depends(get_current_user)):
    """Get inbox statistics"""
    db = get_database()
    tenant_id = user["tenant_id"]

    total = await db.conversations.count_documents({"tenant_id": tenant_id})
    unread = await db.conversations.count_documents({"tenant_id": tenant_id, "is_read": False})
    email_count = await db.conversations.count_documents({"tenant_id": tenant_id, "channel": "email"})
    sms_count = await db.conversations.count_documents({"tenant_id": tenant_id, "channel": "sms"})

    return {
        "total_conversations": total,
        "unread_conversations": unread,
        "email_count": email_count,
        "sms_count": sms_count
    }


@api_router.get("/inbox/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a conversation with all messages"""
    db = get_database()

    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Mark as read
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"is_read": True, "unread_count": 0}}
    )

    # Get messages
    cursor = db.messages.find({"conversation_id": conversation_id}, {"_id": 0}).sort("created_at", 1)
    messages = await cursor.to_list(length=1000)

    # Get contact info
    contact = await db.contacts.find_one({"id": conv.get("contact_id")}, {"_id": 0})

    return {
        **conv,
        "contact_name": f"{contact['first_name']} {contact['last_name']}" if contact else "Unknown",
        "contact_email": contact.get("email") if contact else None,
        "contact_phone": contact.get("phone") if contact else None,
        "messages": messages
    }


class SendMessageRequest(BaseModel):
    contact_id: str
    channel: str = "email"
    to_address: str
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None


@api_router.post("/inbox/send", status_code=201)
async def send_message(
    data: SendMessageRequest,
    user: dict = Depends(get_current_user)
):
    """Send a new message (email or SMS)"""
    db = get_database()
    tenant_id = user["tenant_id"]

    # Verify contact exists
    contact = await db.contacts.find_one(
        {"id": data.contact_id, "tenant_id": tenant_id},
        {"_id": 0}
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Find or create conversation
    conv = await db.conversations.find_one({
        "tenant_id": tenant_id,
        "contact_id": data.contact_id,
        "channel": data.channel
    }, {"_id": 0})

    if not conv:
        conv_id = str(uuid.uuid4())
        conv = {
            "id": conv_id,
            "tenant_id": tenant_id,
            "contact_id": data.contact_id,
            "channel": data.channel,
            "subject": data.subject,
            "is_open": True,
            "is_read": True,
            "message_count": 0,
            "unread_count": 0,
            "last_message_preview": None,
            "last_message_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv)
    else:
        conv_id = conv["id"]

    # Create message
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    message = {
        "id": message_id,
        "tenant_id": tenant_id,
        "conversation_id": conv_id,
        "channel": data.channel,
        "direction": "outbound",
        "status": "sent",  # In production, would be pending until actually sent
        "from_address": user.get("email"),
        "to_address": data.to_address,
        "subject": data.subject,
        "body": data.body,
        "body_html": data.body_html,
        "sent_by_user_id": user["id"],
        "sent_by_name": f"{user['first_name']} {user['last_name']}",
        "sent_at": now,
        "created_at": now
    }
    await db.messages.insert_one(message)

    # Update conversation
    preview = data.body[:100] + "..." if len(data.body) > 100 else data.body
    await db.conversations.update_one(
        {"id": conv_id},
        {
            "$set": {
                "last_message_preview": preview,
                "last_message_at": now,
                "updated_at": now
            },
            "$inc": {"message_count": 1}
        }
    )

    # Log message sending (simulated - in production would use SendGrid/Twilio)
    logger.info(f"[SIMULATED] Sending {data.channel} to {data.to_address}: {data.body[:50]}...")

    return {
        "id": message_id,
        "tenant_id": tenant_id,
        "conversation_id": conv_id,
        "channel": data.channel,
        "direction": "outbound",
        "status": "sent",
        "from_address": user.get("email"),
        "to_address": data.to_address,
        "subject": data.subject,
        "body": data.body,
        "sent_by_user_id": user["id"],
        "sent_by_name": f"{user['first_name']} {user['last_name']}",
        "sent_at": now,
        "created_at": now
    }


# ==================== CAMPAIGNS API ====================

class CampaignCreate(BaseModel):
    name: str
    subject: Optional[str] = None
    content: str = ""
    campaign_type: str = "email"
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


@api_router.get("/campaigns")
async def list_campaigns(
    campaign_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """List all campaigns"""
    db = get_database()
    tenant_id = user["tenant_id"]

    query = {"tenant_id": tenant_id}

    if campaign_type:
        query["campaign_type"] = campaign_type
    if status:
        query["status"] = status
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


@api_router.post("/campaigns", status_code=201)
async def create_campaign(
    data: CampaignCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new campaign"""
    db = get_database()

    campaign = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "subject": data.subject,
        "content": data.content,
        "campaign_type": data.campaign_type,
        "status": "draft",
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


@api_router.get("/campaigns/stats/overview")
async def get_campaigns_stats(
    user: dict = Depends(get_current_user)
):
    """Get overall campaign statistics"""
    db = get_database()
    tenant_id = user["tenant_id"]

    query = {"tenant_id": tenant_id}

    total = await db.campaigns.count_documents(query)
    draft = await db.campaigns.count_documents({**query, "status": "draft"})
    scheduled = await db.campaigns.count_documents({**query, "status": "scheduled"})
    sent = await db.campaigns.count_documents({**query, "status": "sent"})

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


@api_router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific campaign"""
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@api_router.put("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a campaign"""
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": update_data}
    )

    return {"success": True}


@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a campaign"""
    db = get_database()

    result = await db.campaigns.delete_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {"success": True}


@api_router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user)
):
    """Send a campaign immediately"""
    db = get_database()

    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": user["tenant_id"]}
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign["status"] == "sent":
        raise HTTPException(status_code=400, detail="Campaign already sent")

    now = datetime.now(timezone.utc).isoformat()

    # Simulate sending - count contacts in list
    sent_count = 0
    if campaign.get("list_id"):
        sent_count = await db.list_members.count_documents({"list_id": campaign["list_id"]})

    # Mark as sent
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": "sent",
            "sent_at": now,
            "sent_count": sent_count,
            "updated_at": now
        }}
    )

    logger.info(f"[SIMULATED] Campaign '{campaign['name']}' sent to {sent_count} recipients")

    return {
        "success": True,
        "message": f"Campaign sent to {sent_count} recipients"
    }


@api_router.post("/campaigns/{campaign_id}/duplicate")
async def duplicate_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user)
):
    """Duplicate a campaign"""
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
        "status": "draft",
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

# Import and include lists routes
from app.api.lists_routes import router as lists_router
api_router.include_router(lists_router)

# Import and include campaigns routes
from app.api.campaigns_routes import router as campaigns_router
api_router.include_router(campaigns_router)

# Import and include leads routes
from app.api.leads_routes import router as leads_router
api_router.include_router(leads_router)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
