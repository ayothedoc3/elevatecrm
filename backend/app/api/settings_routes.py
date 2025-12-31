"""
Settings API Routes

Handles all settings-related endpoints:
- Workspace settings
- AI & Intelligence configuration
- Integration management
- Affiliate settings
- Audit logs

Security:
- All endpoints require authentication
- Most endpoints require admin role
- API keys are NEVER returned in responses
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from app.db.mongodb import get_database
from app.services.settings_service import (
    get_settings_service, ProviderType, AIFeatureType, AuditAction
)
from app.services.unified_ai_service import test_provider_connection, get_ai_service

router = APIRouter(prefix="/settings", tags=["Settings"])


# ==================== SCHEMAS ====================

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
    api_key: Optional[str] = None  # If not provided, use stored key


# ==================== AUTH HELPER ====================

async def get_current_user_admin(request: Request):
    """Get current user and verify admin role"""
    from jose import jwt
    import os
    
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
        
        # Check admin role
        if user.get("role") not in ["admin", "owner", "super_admin"]:
            raise HTTPException(
                status_code=403, 
                detail="Admin access required. Only admins can manage settings."
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request):
    """Get current user (any role)"""
    from jose import jwt
    import os
    
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== WORKSPACE SETTINGS ====================

@router.get("/workspace")
async def get_workspace_settings(request: Request):
    """Get workspace settings (any authenticated user)"""
    user = await get_current_user(request)
    settings_service = get_settings_service()
    
    return await settings_service.get_workspace_settings(user["tenant_id"])


@router.put("/workspace")
async def update_workspace_settings(
    data: WorkspaceSettingsUpdate,
    request: Request
):
    """Update workspace settings (admin only)"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    
    return await settings_service.update_workspace_settings(
        user["tenant_id"], updates, user["id"]
    )


# ==================== INTEGRATIONS ====================

@router.get("/integrations")
async def list_integrations(request: Request):
    """
    List all integrations for the workspace.
    API keys are NEVER returned - only masked hints.
    """
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    integrations = await settings_service.get_integrations(user["tenant_id"])
    
    # Group by category
    ai_providers = []
    communication_providers = []
    payment_providers = []
    
    for integration in integrations:
        provider = integration.get("provider_type", "")
        if provider in ["openai", "anthropic", "openrouter"]:
            ai_providers.append(integration)
        elif provider in ["twilio", "sendgrid", "mailgun"]:
            communication_providers.append(integration)
        elif provider in ["stripe", "wise", "paypal"]:
            payment_providers.append(integration)
    
    return {
        "integrations": integrations,
        "by_category": {
            "ai": ai_providers,
            "communication": communication_providers,
            "payment": payment_providers
        }
    }


@router.get("/integrations/{provider_type}")
async def get_integration(
    provider_type: str,
    request: Request
):
    """
    Get a specific integration.
    API key is NEVER returned - only masked hint.
    """
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    integration = await settings_service.get_integration(user["tenant_id"], provider_type)
    
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{provider_type}' not found")
    
    return integration


@router.post("/integrations")
async def add_integration(
    data: IntegrationCreate,
    request: Request
):
    """
    Add or update an integration with an API key.
    The key is encrypted immediately and NEVER returned.
    """
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    # Validate provider type
    valid_providers = [p.value for p in ProviderType]
    if data.provider_type not in valid_providers:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid provider type. Must be one of: {', '.join(valid_providers)}"
        )
    
    # Validate API key is not empty
    if not data.api_key or len(data.api_key.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="API key is required and must be at least 10 characters"
        )
    
    result = await settings_service.add_integration(
        workspace_id=user["tenant_id"],
        provider_type=data.provider_type,
        api_key=data.api_key.strip(),
        config=data.config,
        actor_id=user["id"]
    )
    
    return {
        "success": True,
        "message": f"Integration '{data.provider_type}' configured successfully",
        "integration": result
    }


@router.delete("/integrations/{provider_type}")
async def revoke_integration(
    provider_type: str,
    request: Request
):
    """
    Revoke (delete) an integration.
    This permanently removes the API key.
    """
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    success = await settings_service.revoke_integration(
        user["tenant_id"], provider_type, user["id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Integration '{provider_type}' not found")
    
    return {
        "success": True,
        "message": f"Integration '{provider_type}' revoked successfully"
    }


@router.patch("/integrations/{provider_type}/toggle")
async def toggle_integration(
    provider_type: str,
    data: IntegrationToggle,
    request: Request
):
    """Enable or disable an integration without deleting it"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    result = await settings_service.toggle_integration(
        user["tenant_id"], provider_type, data.enabled, user["id"]
    )
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Integration '{provider_type}' not found")
    
    return {
        "success": True,
        "message": f"Integration '{provider_type}' {'enabled' if data.enabled else 'disabled'}",
        "integration": result
    }


@router.post("/integrations/test")
async def test_integration_connection(
    data: TestConnectionRequest,
    request: Request
):
    """
    Test connection to a provider.
    Can test with a new key (before saving) or existing stored key.
    """
    user = await get_current_user_admin(request)
    
    result = await test_provider_connection(
        workspace_id=user["tenant_id"],
        provider_type=data.provider_type,
        api_key=data.api_key
    )
    
    return result


# ==================== AI CONFIGURATION ====================

@router.get("/ai")
async def get_ai_config(request: Request):
    """Get AI configuration for the workspace"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    config = await settings_service.get_ai_config(user["tenant_id"])
    
    # Add available providers info
    integrations = await settings_service.get_integrations(user["tenant_id"])
    ai_integrations = [i for i in integrations if i.get("provider_type") in ["openai", "anthropic", "openrouter"]]
    
    return {
        **config,
        "configured_providers": ai_integrations,
        "available_models": {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-5.2", "gpt-4.1-mini"],
            "anthropic": ["claude-4-sonnet-20250514", "claude-sonnet-4-5-20250929"],
            "openrouter": ["auto"]
        }
    }


@router.put("/ai")
async def update_ai_config(
    data: AIConfigUpdate,
    request: Request
):
    """Update AI configuration"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    
    return await settings_service.update_ai_config(
        user["tenant_id"], updates, user["id"]
    )


@router.get("/ai/usage")
async def get_ai_usage_stats(
    days: int = Query(30, ge=1, le=365),
    request: Request = None
):
    """Get AI usage statistics"""
    user = await get_current_user_admin(request)
    
    ai_service = get_ai_service(user["tenant_id"])
    return await ai_service.get_usage_stats(days)


@router.get("/ai/status")
async def get_ai_status(request: Request):
    """
    Get AI configuration status for the workspace.
    Returns whether AI is properly configured and usable.
    """
    user = await get_current_user(request)
    settings_service = get_settings_service()
    
    config = await settings_service.get_ai_config(user["tenant_id"])
    integrations = await settings_service.get_integrations(user["tenant_id"])
    
    # Check if any AI provider is configured and enabled
    ai_providers = ["openai", "anthropic", "openrouter"]
    configured_ai = [
        i for i in integrations 
        if i.get("provider_type") in ai_providers and i.get("enabled", True)
    ]
    
    # Check for fallback to environment key
    import os
    has_env_key = bool(os.environ.get("EMERGENT_LLM_KEY"))
    
    is_configured = len(configured_ai) > 0 or has_env_key
    
    return {
        "is_configured": is_configured,
        "configured_providers": [i.get("provider_type") for i in configured_ai],
        "default_provider": config.get("default_provider", "openai"),
        "has_fallback_key": has_env_key,
        "features_enabled": config.get("features_enabled", {}),
        "message": (
            "AI is ready to use" if is_configured 
            else "Please configure an AI provider in Settings > AI & Intelligence"
        )
    }


# ==================== AFFILIATE SETTINGS ====================

@router.get("/affiliates")
async def get_affiliate_settings(request: Request):
    """Get affiliate system settings"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    return await settings_service.get_affiliate_settings(user["tenant_id"])


@router.put("/affiliates")
async def update_affiliate_settings(
    data: AffiliateSettingsUpdate,
    request: Request
):
    """Update affiliate settings"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    
    return await settings_service.update_affiliate_settings(
        user["tenant_id"], updates, user["id"]
    )


# ==================== AUDIT LOGS ====================

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    provider: Optional[str] = None,
    request: Request = None
):
    """Get settings audit logs"""
    user = await get_current_user_admin(request)
    settings_service = get_settings_service()
    
    return await settings_service.get_audit_logs(
        workspace_id=user["tenant_id"],
        page=page,
        page_size=page_size,
        action_filter=action,
        provider_filter=provider
    )


# ==================== PROVIDER INFO ====================

@router.get("/providers")
async def list_available_providers():
    """List all available provider types and their categories"""
    return {
        "providers": {
            "ai": [
                {
                    "type": "openai",
                    "name": "OpenAI",
                    "description": "GPT-4o and other OpenAI models",
                    "models": ["gpt-4o", "gpt-4o-mini", "gpt-5.2"],
                    "key_url": "https://platform.openai.com/api-keys"
                },
                {
                    "type": "anthropic",
                    "name": "Anthropic (Claude)",
                    "description": "Claude Sonnet and other Anthropic models",
                    "models": ["claude-4-sonnet-20250514", "claude-sonnet-4-5-20250929"],
                    "key_url": "https://console.anthropic.com/settings/keys"
                },
                {
                    "type": "openrouter",
                    "name": "OpenRouter",
                    "description": "Access multiple AI providers through one API",
                    "models": ["auto"],
                    "key_url": "https://openrouter.ai/keys"
                }
            ],
            "communication": [
                {
                    "type": "twilio",
                    "name": "Twilio",
                    "description": "SMS and voice communications",
                    "key_url": "https://console.twilio.com/",
                    "config_fields": ["account_sid", "auth_token", "from_number"]
                },
                {
                    "type": "sendgrid",
                    "name": "SendGrid",
                    "description": "Email delivery service",
                    "key_url": "https://app.sendgrid.com/settings/api_keys",
                    "config_fields": ["from_email", "from_name"]
                },
                {
                    "type": "mailgun",
                    "name": "Mailgun",
                    "description": "Email delivery service",
                    "key_url": "https://app.mailgun.com/app/account/security/api_keys",
                    "config_fields": ["domain", "from_email"]
                }
            ],
            "payment": [
                {
                    "type": "stripe",
                    "name": "Stripe",
                    "description": "Payment processing",
                    "key_url": "https://dashboard.stripe.com/apikeys",
                    "config_fields": ["webhook_secret"]
                },
                {
                    "type": "wise",
                    "name": "Wise (TransferWise)",
                    "description": "International payouts",
                    "key_url": "https://wise.com/",
                    "config_fields": ["profile_id"]
                },
                {
                    "type": "paypal",
                    "name": "PayPal",
                    "description": "PayPal payments",
                    "key_url": "https://developer.paypal.com/",
                    "config_fields": ["client_id", "client_secret"]
                }
            ]
        },
        "ai_features": [
            {"type": "page_builder", "name": "AI Page Builder", "description": "Generate landing pages with AI"},
            {"type": "lead_scoring", "name": "Lead Scoring", "description": "AI-powered lead qualification"},
            {"type": "deal_analysis", "name": "Deal Analysis", "description": "Analyze deal potential and risks"},
            {"type": "contact_analysis", "name": "Contact Analysis", "description": "Analyze contact profiles"},
            {"type": "workflow_ai", "name": "Workflow AI", "description": "AI-assisted workflow automation"},
            {"type": "general_assistant", "name": "General Assistant", "description": "AI assistant for general tasks"}
        ]
    }
