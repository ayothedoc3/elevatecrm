from __future__ import annotations

from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import create_access_token, get_current_user, verify_password
from app.core.database import get_db
from app.pg_models.models import Tenant, User

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

