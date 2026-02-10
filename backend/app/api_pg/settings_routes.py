from __future__ import annotations

import uuid
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import (
    AIUsageConfig,
    AIUsageLog,
    AffiliateSetting,
    SettingsAuditLog,
    Tenant,
    WorkspaceIntegration,
    WorkspaceSetting,
)
from app.services.encryption_service import get_encryption_service

router = APIRouter(prefix="/settings", tags=["Settings"])


def _require_admin(user: dict) -> None:
    if (user.get("role") or "").lower() not in {"admin", "manager", "owner", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required. Only admins can manage settings.")


async def _log_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor: dict,
    action: str,
    provider_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    log = SettingsAuditLog(
        tenant_id=tenant_id,
        actor_id=actor.get("id"),
        actor_email=actor.get("email"),
        action=action,
        provider_type=provider_type,
        meta=metadata or {},
        created_at=now_utc(),
    )
    db.add(log)


class WorkspaceSettingsUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None


class IntegrationCreate(BaseModel):
    provider_type: str
    api_key: str
    config: Optional[Dict[str, Any]] = None


class IntegrationToggle(BaseModel):
    enabled: bool


class AIConfigUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    provider_overrides: Optional[Dict[str, Dict[str, str]]] = None
    usage_limits: Optional[Dict[str, int]] = None
    features_enabled: Optional[Dict[str, bool]] = None


class AffiliateSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    default_currency: Optional[str] = None
    default_attribution_window_days: Optional[int] = None
    approval_mode: Optional[str] = None
    min_payout_threshold: Optional[float] = None


class TestConnectionRequest(BaseModel):
    provider_type: str
    api_key: Optional[str] = None


@router.get("/workspace")
async def get_workspace_settings(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == user["tenant_id"]))
    tenant = tenant_res.scalar_one_or_none()

    res = await db.execute(select(WorkspaceSetting).where(WorkspaceSetting.tenant_id == user["tenant_id"]))
    settings = res.scalar_one_or_none()
    if not settings:
        return {
            "name": tenant.name if tenant else "My Workspace",
            "description": "",
            "logo_url": None,
            "primary_color": "#6366F1",
            "timezone": "UTC",
            "currency": "USD",
        }
    return {
        "name": settings.name,
        "description": settings.description or "",
        "logo_url": settings.logo_url,
        "primary_color": settings.primary_color,
        "timezone": settings.timezone,
        "currency": settings.currency,
    }


@router.put("/workspace")
async def update_workspace_settings(
    data: WorkspaceSettingsUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return {"success": True}

    now = now_utc()
    res = await db.execute(select(WorkspaceSetting).where(WorkspaceSetting.tenant_id == user["tenant_id"]))
    settings = res.scalar_one_or_none()
    if not settings:
        settings = WorkspaceSetting(
            tenant_id=user["tenant_id"],
            name=updates.get("name") or "My Workspace",
            description=updates.get("description"),
            logo_url=updates.get("logo_url"),
            primary_color=updates.get("primary_color") or "#6366F1",
            timezone=updates.get("timezone") or "UTC",
            currency=updates.get("currency") or "USD",
            updated_by=user["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(settings)
    else:
        for k, v in updates.items():
            setattr(settings, k, v)
        settings.updated_by = user["id"]
        settings.updated_at = now

    # Keep Tenant.name in sync for Phase 1 UX.
    if "name" in updates:
        await db.execute(update(Tenant).where(Tenant.id == user["tenant_id"]).values(name=updates["name"], updated_at=now))

    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action="update_config",
        provider_type=None,
        metadata={"updated_fields": list(updates.keys())},
    )
    await db.flush()
    return await get_workspace_settings(user=user, db=db)


@router.get("/integrations")
async def list_integrations(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    enc = get_encryption_service()

    res = await db.execute(select(WorkspaceIntegration).where(WorkspaceIntegration.tenant_id == user["tenant_id"]))
    integrations = res.scalars().all()

    out = []
    for i in integrations:
        key_hint = None
        try:
            key_hint = enc.mask_key(enc.decrypt(i.encrypted_api_key))
        except Exception:
            key_hint = "••••••••"

        out.append(
            {
                "id": i.id,
                "tenant_id": i.tenant_id,
                "provider_type": i.provider_type,
                "enabled": bool(i.enabled),
                "config": i.config or {},
                "key_hint": key_hint,
                "last_used_at": dt_to_iso(i.last_used_at),
                "last_test_at": dt_to_iso(i.last_test_at),
                "test_status": i.test_status,
                "created_by": i.created_by,
                "created_at": dt_to_iso(i.created_at),
                "updated_at": dt_to_iso(i.updated_at),
            }
        )

    ai = [x for x in out if x.get("provider_type") in {"openai", "anthropic", "openrouter"}]
    communication = [x for x in out if x.get("provider_type") in {"twilio", "sendgrid", "mailgun"}]
    payment = [x for x in out if x.get("provider_type") in {"stripe", "wise", "paypal"}]

    return {"integrations": out, "by_category": {"ai": ai, "communication": communication, "payment": payment}}


@router.post("/integrations")
async def add_integration(
    data: IntegrationCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    provider_type = (data.provider_type or "").strip().lower()
    valid = {"openai", "anthropic", "openrouter", "twilio", "sendgrid", "mailgun", "stripe", "wise", "paypal"}
    if provider_type not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid provider type. Must be one of: {', '.join(sorted(valid))}")
    if not data.api_key or len(data.api_key.strip()) < 10:
        raise HTTPException(status_code=400, detail="API key is required and must be at least 10 characters")

    enc = get_encryption_service()
    encrypted_key = enc.encrypt(data.api_key.strip())
    key_hash = enc.hash_key_for_audit(data.api_key.strip())
    now = now_utc()

    res = await db.execute(
        select(WorkspaceIntegration).where(and_(WorkspaceIntegration.tenant_id == user["tenant_id"], WorkspaceIntegration.provider_type == provider_type))
    )
    integration = res.scalar_one_or_none()
    action = "add_key"
    if integration:
        integration.encrypted_api_key = encrypted_key
        integration.key_hash = key_hash
        if data.config is not None:
            integration.config = data.config
        integration.enabled = True
        integration.updated_at = now
        action = "update_key"
    else:
        integration = WorkspaceIntegration(
            id=str(uuid.uuid4()),  # type: ignore[name-defined]
            tenant_id=user["tenant_id"],
            provider_type=provider_type,
            encrypted_api_key=encrypted_key,
            key_hash=key_hash,
            config=data.config or {},
            enabled=True,
            last_used_at=None,
            last_test_at=None,
            test_status=None,
            created_by=user["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(integration)

    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action=action,
        provider_type=provider_type,
        metadata={"key_hash": key_hash},
    )
    await db.flush()
    return {"success": True}


@router.patch("/integrations/{provider_type}/toggle")
async def toggle_integration(
    provider_type: str,
    data: IntegrationToggle,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    provider_type = (provider_type or "").strip().lower()
    res = await db.execute(
        select(WorkspaceIntegration).where(and_(WorkspaceIntegration.tenant_id == user["tenant_id"], WorkspaceIntegration.provider_type == provider_type))
    )
    integration = res.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{provider_type}' not found")
    integration.enabled = bool(data.enabled)
    integration.updated_at = now_utc()
    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action="enable_provider" if integration.enabled else "disable_provider",
        provider_type=provider_type,
        metadata={"enabled": integration.enabled},
    )
    await db.flush()
    return {"success": True}


@router.delete("/integrations/{provider_type}")
async def revoke_integration(
    provider_type: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    provider_type = (provider_type or "").strip().lower()
    res = await db.execute(
        select(WorkspaceIntegration).where(and_(WorkspaceIntegration.tenant_id == user["tenant_id"], WorkspaceIntegration.provider_type == provider_type))
    )
    integration = res.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{provider_type}' not found")
    await db.delete(integration)
    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action="revoke_key",
        provider_type=provider_type,
        metadata={},
    )
    await db.flush()
    return {"success": True}


@router.post("/integrations/test")
async def test_connection(
    data: TestConnectionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    provider_type = (data.provider_type or "").strip().lower()
    enc = get_encryption_service()

    api_key = data.api_key
    integration = None
    if not api_key:
        res = await db.execute(
            select(WorkspaceIntegration).where(and_(WorkspaceIntegration.tenant_id == user["tenant_id"], WorkspaceIntegration.provider_type == provider_type))
        )
        integration = res.scalar_one_or_none()
        if not integration:
            return {"success": False, "error": f"No {provider_type} integration configured"}
        try:
            api_key = enc.decrypt(integration.encrypted_api_key)
        except Exception:
            return {"success": False, "error": "Failed to decrypt stored key"}

    if not api_key:
        return {"success": False, "error": "No API key provided"}

    if provider_type not in {"openai", "openrouter", "anthropic"}:
        return {"success": False, "error": f"Connection testing is not implemented for {provider_type}"}

    start = time.time()
    try:
        if provider_type in {"openrouter", "anthropic"}:
            client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            model = "anthropic/claude-sonnet-4.5"
        else:
            client = AsyncOpenAI(api_key=api_key)
            model = "gpt-4o"

        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Respond with only the word 'connected'."},
                {"role": "user", "content": "Test connection"},
            ],
            max_tokens=10,
        )
        _ = completion.choices[0].message.content
        response_time_ms = int((time.time() - start) * 1000)

        if integration:
            integration.last_test_at = now_utc()
            integration.test_status = "success"
            integration.updated_at = now_utc()

        await _log_audit(
            db,
            tenant_id=user["tenant_id"],
            actor=user,
            action="test_connection",
            provider_type=provider_type,
            metadata={"test_result": "success", "response_time_ms": response_time_ms},
        )
        await db.flush()
        return {"success": True, "response_time_ms": response_time_ms}
    except Exception as e:
        response_time_ms = int((time.time() - start) * 1000)
        if integration:
            integration.last_test_at = now_utc()
            integration.test_status = "failure"
            integration.updated_at = now_utc()
        await _log_audit(
            db,
            tenant_id=user["tenant_id"],
            actor=user,
            action="test_connection",
            provider_type=provider_type,
            metadata={"test_result": "failure", "error": str(e), "response_time_ms": response_time_ms},
        )
        await db.flush()
        return {"success": False, "error": str(e), "response_time_ms": response_time_ms}


@router.get("/providers")
async def list_providers(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return {
        "providers": {
            "ai": [
                {"type": "openai", "name": "OpenAI", "description": "GPT models via the OpenAI API"},
                {"type": "openrouter", "name": "OpenRouter", "description": "Claude and other models via OpenRouter"},
                {"type": "anthropic", "name": "Anthropic", "description": "Claude models (stored as OpenRouter key)"},
            ],
            "communication": [
                {"type": "twilio", "name": "Twilio", "description": "SMS and voice messaging"},
                {"type": "sendgrid", "name": "SendGrid", "description": "Email delivery provider"},
                {"type": "mailgun", "name": "Mailgun", "description": "Email delivery provider"},
            ],
            "payment": [
                {"type": "stripe", "name": "Stripe", "description": "Payments and subscriptions"},
                {"type": "wise", "name": "Wise", "description": "International payouts"},
                {"type": "paypal", "name": "PayPal", "description": "Payments and payouts"},
            ],
        }
    }


@router.get("/ai")
async def get_ai_config(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    res = await db.execute(select(AIUsageConfig).where(AIUsageConfig.tenant_id == user["tenant_id"]))
    cfg = res.scalar_one_or_none()
    if not cfg:
        return {
            "default_provider": "openai",
            "default_model": "gpt-4o",
            "features_enabled": {},
            "usage_limits": {"daily_requests": 1000, "monthly_requests": 25000},
        }
    return {
        "default_provider": cfg.default_provider,
        "default_model": cfg.default_model,
        "features_enabled": cfg.features_enabled or {},
        "usage_limits": cfg.usage_limits or {"daily_requests": 1000, "monthly_requests": 25000},
        "provider_overrides": cfg.provider_overrides or {},
    }


@router.put("/ai")
async def update_ai_config(
    data: AIConfigUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return {"success": True}
    now = now_utc()
    res = await db.execute(select(AIUsageConfig).where(AIUsageConfig.tenant_id == user["tenant_id"]))
    cfg = res.scalar_one_or_none()
    if not cfg:
        cfg = AIUsageConfig(
            tenant_id=user["tenant_id"],
            default_provider=updates.get("default_provider") or "openai",
            default_model=updates.get("default_model") or "gpt-4o",
            provider_overrides=updates.get("provider_overrides") or {},
            usage_limits=updates.get("usage_limits") or {"daily_requests": 1000, "monthly_requests": 25000},
            features_enabled=updates.get("features_enabled") or {},
            updated_by=user["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(cfg)
    else:
        for k, v in updates.items():
            setattr(cfg, k, v)
        cfg.updated_by = user["id"]
        cfg.updated_at = now

    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action="update_config",
        provider_type="ai",
        metadata={"updated_fields": list(updates.keys())},
    )
    await db.flush()
    return await get_ai_config(user=user, db=db)


@router.get("/ai/usage")
async def get_ai_usage(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    cfg_res = await db.execute(select(AIUsageConfig).where(AIUsageConfig.tenant_id == user["tenant_id"]))
    cfg = cfg_res.scalar_one_or_none()
    limits = (cfg.usage_limits or {}) if cfg else {"daily_requests": 1000, "monthly_requests": 25000}
    daily_limit = int(limits.get("daily_requests", 1000))
    monthly_limit = int(limits.get("monthly_requests", 25000))

    now = now_utc()
    daily_start = now - timedelta(days=1)
    monthly_start = now - timedelta(days=days)

    daily_res = await db.execute(
        select(func.coalesce(func.sum(AIUsageLog.requests), 0)).where(
            and_(AIUsageLog.tenant_id == user["tenant_id"], AIUsageLog.created_at >= daily_start)
        )
    )
    monthly_res = await db.execute(
        select(func.coalesce(func.sum(AIUsageLog.requests), 0)).where(
            and_(AIUsageLog.tenant_id == user["tenant_id"], AIUsageLog.created_at >= monthly_start)
        )
    )
    daily_used = int(daily_res.scalar() or 0)
    monthly_used = int(monthly_res.scalar() or 0)

    return {
        "period_days": days,
        "current_usage": {
            "daily": {"used": daily_used, "limit": daily_limit, "remaining": max(0, daily_limit - daily_used)},
            "monthly": {"used": monthly_used, "limit": monthly_limit, "remaining": max(0, monthly_limit - monthly_used)},
        },
    }


@router.get("/affiliates")
async def get_affiliate_settings(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    res = await db.execute(select(AffiliateSetting).where(AffiliateSetting.tenant_id == user["tenant_id"]))
    s = res.scalar_one_or_none()
    if not s:
        return {
            "enabled": True,
            "default_currency": "USD",
            "default_attribution_window_days": 30,
            "approval_mode": "manual",
            "min_payout_threshold": 50,
        }
    return {
        "enabled": bool(s.enabled),
        "default_currency": s.default_currency,
        "default_attribution_window_days": int(s.default_attribution_window_days),
        "approval_mode": s.approval_mode,
        "min_payout_threshold": float(s.min_payout_threshold or 0),
    }


@router.put("/affiliates")
async def update_affiliate_settings(
    data: AffiliateSettingsUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    now = now_utc()
    res = await db.execute(select(AffiliateSetting).where(AffiliateSetting.tenant_id == user["tenant_id"]))
    s = res.scalar_one_or_none()
    if not s:
        s = AffiliateSetting(
            tenant_id=user["tenant_id"],
            enabled=bool(updates.get("enabled", True)),
            default_currency=updates.get("default_currency") or "USD",
            default_attribution_window_days=int(updates.get("default_attribution_window_days") or 30),
            approval_mode=updates.get("approval_mode") or "manual",
            min_payout_threshold=float(updates.get("min_payout_threshold") or 50),
            meta={},
            updated_by=user["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(s)
    else:
        for k, v in updates.items():
            setattr(s, k, v)
        s.updated_by = user["id"]
        s.updated_at = now

    await _log_audit(
        db,
        tenant_id=user["tenant_id"],
        actor=user,
        action="update_config",
        provider_type="affiliates",
        metadata={"updated_fields": list(updates.keys())},
    )
    await db.flush()
    return await get_affiliate_settings(user=user, db=db)


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    where = [SettingsAuditLog.tenant_id == user["tenant_id"]]

    total_res = await db.execute(select(func.count(SettingsAuditLog.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)
    offset = (page - 1) * page_size

    res = await db.execute(
        select(SettingsAuditLog)
        .where(and_(*where))
        .order_by(SettingsAuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = res.scalars().all()

    return {
        "logs": [
            {
                "id": l.id,
                "tenant_id": l.tenant_id,
                "actor_id": l.actor_id,
                "actor_email": l.actor_email,
                "action": l.action,
                "provider_type": l.provider_type,
                "metadata": l.meta or {},
                "created_at": dt_to_iso(l.created_at),
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
