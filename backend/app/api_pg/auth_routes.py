from __future__ import annotations

import uuid
from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import create_access_token, get_current_user, get_password_hash, verify_password
from app.api_pg.utils import now_utc
from app.core.database import get_db
from app.pg_models.models import Tenant, User

ADMIN_ROLES = {"admin", "manager", "owner", "super_admin"}
VALID_USER_ROLES = {"admin", "manager", "sales", "viewer"}


def _require_admin(user: dict) -> None:
    if (user.get("role") or "").lower() not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required. Only admins can manage team members.")

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


@router.get("/health")
async def health_check():
    from app.api_pg.utils import now_utc

    return {"status": "healthy", "timestamp": now_utc().isoformat()}


@router.post("/auth/login")
async def login(
    request: LoginRequest,
    tenant_slug: str = Query(default="demo"),
    db: AsyncSession = Depends(get_db),
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_res = await db.execute(
        select(User).where(and_(User.tenant_id == tenant.id, User.email == request.email))
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.id})
    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "role": user.role,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
        },
    }


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@router.get("/users")
async def list_users(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.tenant_id == user["tenant_id"]).order_by(User.created_at.asc()))
    users = res.scalars().all()
    return {
        "users": [
            {
                "id": u.id,
                "tenant_id": u.tenant_id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": f"{u.first_name} {u.last_name}".strip(),
                "role": u.role,
                "is_active": u.is_active,
                "phone": u.phone,
                "avatar_url": u.avatar_url,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


# --- User management models ---

class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="viewer")
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserToggleActive(BaseModel):
    is_active: bool


def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "tenant_id": u.tenant_id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": f"{u.first_name} {u.last_name}".strip(),
        "role": u.role,
        "is_active": u.is_active,
        "phone": u.phone,
        "avatar_url": u.avatar_url,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


@router.post("/users", status_code=201)
async def create_user(
    data: UserCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    role = (data.role or "viewer").lower()
    if role not in VALID_USER_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_USER_ROLES))}")

    existing = await db.execute(
        select(User).where(and_(User.tenant_id == user["tenant_id"], User.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists in your workspace")

    now = now_utc()
    new_user = User(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        email=data.email.strip().lower(),
        hashed_password=get_password_hash(data.password),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        role=role,
        is_active=True,
        phone=data.phone,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    await db.flush()
    return _user_to_dict(new_user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    res = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == user["tenant_id"]))
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role is not None:
        role = data.role.lower()
        if role not in VALID_USER_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_USER_ROLES))}")
        if user_id == user["id"]:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        target.role = role

    if data.first_name is not None:
        target.first_name = data.first_name.strip()
    if data.last_name is not None:
        target.last_name = data.last_name.strip()
    if data.phone is not None:
        target.phone = data.phone
    if data.avatar_url is not None:
        target.avatar_url = data.avatar_url

    target.updated_at = now_utc()
    await db.flush()
    return _user_to_dict(target)


@router.patch("/users/{user_id}/active")
async def toggle_user_active(
    user_id: str,
    data: UserToggleActive,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    res = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == user["tenant_id"]))
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = data.is_active
    target.updated_at = now_utc()
    await db.flush()
    return _user_to_dict(target)

