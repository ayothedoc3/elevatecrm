"""
Settings Service - Manages workspace settings and integrations

Handles:
- Workspace configuration
- AI provider management
- Integration key storage
- Audit logging for settings changes
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

from app.db.mongodb import get_database
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ProviderType(str, Enum):
    # AI Providers
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    # Communication Providers
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    # Payment Providers
    STRIPE = "stripe"
    WISE = "wise"
    PAYPAL = "paypal"
    # Future providers
    CUSTOM = "custom"


class AIFeatureType(str, Enum):
    PAGE_BUILDER = "page_builder"
    LEAD_SCORING = "lead_scoring"
    DEAL_ANALYSIS = "deal_analysis"
    CONTACT_ANALYSIS = "contact_analysis"
    WORKFLOW_AI = "workflow_ai"
    GENERAL_ASSISTANT = "general_assistant"
    # Elev8 AI Assistant features (advisory/draft-only)
    SPICED_DRAFTING = "spiced_drafting"
    LEAD_INTELLIGENCE = "lead_intelligence"


class AuditAction(str, Enum):
    ADD_KEY = "add_key"
    UPDATE_KEY = "update_key"
    ROTATE_KEY = "rotate_key"
    REVOKE_KEY = "revoke_key"
    ENABLE_PROVIDER = "enable_provider"
    DISABLE_PROVIDER = "disable_provider"
    UPDATE_CONFIG = "update_config"
    TEST_CONNECTION = "test_connection"


# ==================== SERVICE CLASS ====================

class SettingsService:
    """
    Service for managing workspace settings and integrations.
    Handles secure key storage and retrieval.
    """
    
    def __init__(self):
        self.encryption = get_encryption_service()
    
    # ==================== WORKSPACE SETTINGS ====================
    
    async def get_workspace_settings(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace settings (branding, timezone, etc.)"""
        db = get_database()
        
        settings = await db.workspace_settings.find_one(
            {"workspace_id": workspace_id},
            {"_id": 0}
        )
        
        if not settings:
            # Return defaults
            return {
                "workspace_id": workspace_id,
                "name": "My Workspace",
                "description": "",
                "logo_url": None,
                "primary_color": "#6366F1",
                "timezone": "UTC",
                "currency": "USD",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return settings
    
    async def update_workspace_settings(
        self, workspace_id: str, updates: Dict[str, Any], actor_id: str
    ) -> Dict[str, Any]:
        """Update workspace settings"""
        db = get_database()
        
        # Get existing settings
        existing = await self.get_workspace_settings(workspace_id)
        
        # Filter allowed fields
        allowed_fields = ["name", "description", "logo_url", "primary_color", "timezone", "currency"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Upsert
        await db.workspace_settings.update_one(
            {"workspace_id": workspace_id},
            {
                "$set": filtered_updates,
                "$setOnInsert": {
                    "workspace_id": workspace_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        # Log audit
        await self._log_audit(
            workspace_id, actor_id, AuditAction.UPDATE_CONFIG,
            provider_type=None,
            metadata={"updated_fields": list(filtered_updates.keys())}
        )
        
        return await self.get_workspace_settings(workspace_id)
    
    # ==================== INTEGRATION MANAGEMENT ====================
    
    async def get_integrations(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all integrations for a workspace.
        API keys are NEVER returned - only masked versions.
        """
        db = get_database()
        
        cursor = db.workspace_integrations.find(
            {"workspace_id": workspace_id},
            {"_id": 0}
        )
        integrations = await cursor.to_list(length=100)
        
        # Mask all keys before returning
        for integration in integrations:
            if integration.get("encrypted_api_key"):
                # Decrypt to get last 4 chars for masking
                try:
                    decrypted = self.encryption.decrypt(integration["encrypted_api_key"])
                    integration["key_hint"] = self.encryption.mask_key(decrypted)
                except:
                    integration["key_hint"] = "••••••••"
            else:
                integration["key_hint"] = None
            
            # Never return the encrypted key to frontend
            integration.pop("encrypted_api_key", None)
        
        return integrations
    
    async def get_integration(
        self, workspace_id: str, provider_type: str, include_key: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific integration.
        
        Args:
            workspace_id: The workspace ID
            provider_type: The provider type (e.g., 'openai')
            include_key: If True, returns decrypted key (ONLY for internal backend use)
        """
        db = get_database()
        
        integration = await db.workspace_integrations.find_one(
            {"workspace_id": workspace_id, "provider_type": provider_type},
            {"_id": 0}
        )
        
        if not integration:
            return None
        
        if include_key and integration.get("encrypted_api_key"):
            try:
                integration["api_key"] = self.encryption.decrypt(integration["encrypted_api_key"])
            except:
                integration["api_key"] = None
        
        # Mask key for frontend
        if integration.get("encrypted_api_key"):
            try:
                decrypted = self.encryption.decrypt(integration["encrypted_api_key"])
                integration["key_hint"] = self.encryption.mask_key(decrypted)
            except:
                integration["key_hint"] = "••••••••"
        
        # Remove encrypted key unless internal use
        if not include_key:
            integration.pop("encrypted_api_key", None)
            integration.pop("api_key", None)
        
        return integration
    
    async def add_integration(
        self, workspace_id: str, provider_type: str, api_key: str,
        config: Dict[str, Any] = None, actor_id: str = None
    ) -> Dict[str, Any]:
        """
        Add or update an integration with an API key.
        The key is encrypted immediately upon receipt.
        """
        db = get_database()
        
        # Encrypt the API key immediately
        encrypted_key = self.encryption.encrypt(api_key)
        key_hash = self.encryption.hash_key_for_audit(api_key)
        
        # Check if integration exists
        existing = await db.workspace_integrations.find_one(
            {"workspace_id": workspace_id, "provider_type": provider_type}
        )
        
        now = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update existing
            await db.workspace_integrations.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "encrypted_api_key": encrypted_key,
                    "config": config or existing.get("config", {}),
                    "enabled": True,
                    "updated_at": now,
                    "key_hash": key_hash
                }}
            )
            action = AuditAction.UPDATE_KEY
            integration_id = existing["id"]
        else:
            # Create new
            integration_id = str(uuid.uuid4())
            integration = {
                "id": integration_id,
                "workspace_id": workspace_id,
                "provider_type": provider_type,
                "encrypted_api_key": encrypted_key,
                "config": config or {},
                "enabled": True,
                "last_used_at": None,
                "last_test_at": None,
                "test_status": None,
                "key_hash": key_hash,
                "created_at": now,
                "updated_at": now
            }
            await db.workspace_integrations.insert_one(integration)
            action = AuditAction.ADD_KEY
        
        # Log audit (never log the actual key)
        await self._log_audit(
            workspace_id, actor_id, action,
            provider_type=provider_type,
            metadata={"key_hash": key_hash}
        )
        
        # Return the integration without the key
        return await self.get_integration(workspace_id, provider_type)
    
    async def revoke_integration(
        self, workspace_id: str, provider_type: str, actor_id: str
    ) -> bool:
        """Revoke (delete) an integration key"""
        db = get_database()
        
        # Get existing to log audit
        existing = await db.workspace_integrations.find_one(
            {"workspace_id": workspace_id, "provider_type": provider_type}
        )
        
        if not existing:
            return False
        
        # Delete the integration
        await db.workspace_integrations.delete_one(
            {"workspace_id": workspace_id, "provider_type": provider_type}
        )
        
        # Log audit
        await self._log_audit(
            workspace_id, actor_id, AuditAction.REVOKE_KEY,
            provider_type=provider_type,
            metadata={"key_hash": existing.get("key_hash", "unknown")}
        )
        
        return True
    
    async def toggle_integration(
        self, workspace_id: str, provider_type: str, enabled: bool, actor_id: str
    ) -> Optional[Dict[str, Any]]:
        """Enable or disable an integration without deleting it"""
        db = get_database()
        
        result = await db.workspace_integrations.update_one(
            {"workspace_id": workspace_id, "provider_type": provider_type},
            {"$set": {
                "enabled": enabled,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.matched_count == 0:
            return None
        
        # Log audit
        await self._log_audit(
            workspace_id, actor_id,
            AuditAction.ENABLE_PROVIDER if enabled else AuditAction.DISABLE_PROVIDER,
            provider_type=provider_type
        )
        
        return await self.get_integration(workspace_id, provider_type)
    
    async def update_last_used(
        self, workspace_id: str, provider_type: str
    ):
        """Update the last_used_at timestamp for an integration"""
        db = get_database()
        await db.workspace_integrations.update_one(
            {"workspace_id": workspace_id, "provider_type": provider_type},
            {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    # ==================== AI USAGE CONFIG ====================
    
    async def get_ai_config(self, workspace_id: str) -> Dict[str, Any]:
        """Get AI usage configuration for a workspace"""
        db = get_database()
        
        config = await db.ai_usage_configs.find_one(
            {"workspace_id": workspace_id},
            {"_id": 0}
        )
        
        if not config:
            # Return defaults
            return {
                "workspace_id": workspace_id,
                "default_provider": "openai",
                "default_model": "gpt-4o",
                "provider_overrides": {},  # {feature_type: {provider, model}}
                "usage_limits": {
                    "daily_requests": 1000,
                    "monthly_requests": 25000
                },
                "features_enabled": {
                    "page_builder": True,
                    "lead_scoring": True,
                    "deal_analysis": True,
                    "contact_analysis": True,
                    "workflow_ai": True,
                    "general_assistant": True
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return config
    
    async def update_ai_config(
        self, workspace_id: str, updates: Dict[str, Any], actor_id: str
    ) -> Dict[str, Any]:
        """Update AI configuration"""
        db = get_database()
        
        # Filter allowed fields
        allowed_fields = [
            "default_provider", "default_model", "provider_overrides",
            "usage_limits", "features_enabled"
        ]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Upsert
        await db.ai_usage_configs.update_one(
            {"workspace_id": workspace_id},
            {
                "$set": filtered_updates,
                "$setOnInsert": {
                    "workspace_id": workspace_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        # Log audit
        await self._log_audit(
            workspace_id, actor_id, AuditAction.UPDATE_CONFIG,
            provider_type=None,
            metadata={"updated_fields": list(filtered_updates.keys())}
        )
        
        return await self.get_ai_config(workspace_id)
    
    # ==================== AFFILIATE SETTINGS ====================
    
    async def get_affiliate_settings(self, workspace_id: str) -> Dict[str, Any]:
        """Get affiliate system settings"""
        db = get_database()
        
        settings = await db.affiliate_settings.find_one(
            {"workspace_id": workspace_id},
            {"_id": 0}
        )
        
        if not settings:
            return {
                "workspace_id": workspace_id,
                "enabled": True,
                "default_currency": "USD",
                "default_attribution_window_days": 30,
                "approval_mode": "manual",  # "auto" or "manual"
                "min_payout_threshold": 50,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        
        return settings
    
    async def update_affiliate_settings(
        self, workspace_id: str, updates: Dict[str, Any], actor_id: str
    ) -> Dict[str, Any]:
        """Update affiliate settings"""
        db = get_database()
        
        allowed_fields = [
            "enabled", "default_currency", "default_attribution_window_days",
            "approval_mode", "min_payout_threshold"
        ]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.affiliate_settings.update_one(
            {"workspace_id": workspace_id},
            {
                "$set": filtered_updates,
                "$setOnInsert": {
                    "workspace_id": workspace_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        await self._log_audit(
            workspace_id, actor_id, AuditAction.UPDATE_CONFIG,
            provider_type=None,
            metadata={"type": "affiliate_settings", "updated_fields": list(filtered_updates.keys())}
        )
        
        return await self.get_affiliate_settings(workspace_id)
    
    # ==================== AUDIT LOGGING ====================
    
    async def _log_audit(
        self, workspace_id: str, actor_id: str, action: AuditAction,
        provider_type: str = None, metadata: Dict[str, Any] = None
    ):
        """Log a settings audit event"""
        db = get_database()
        
        log_entry = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "action": action.value,
            "provider_type": provider_type,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.settings_audit_logs.insert_one(log_entry)
    
    async def get_audit_logs(
        self, workspace_id: str, page: int = 1, page_size: int = 50,
        action_filter: str = None, provider_filter: str = None
    ) -> Dict[str, Any]:
        """Get audit logs for a workspace"""
        db = get_database()
        
        query = {"workspace_id": workspace_id}
        if action_filter:
            query["action"] = action_filter
        if provider_filter:
            query["provider_type"] = provider_filter
        
        total = await db.settings_audit_logs.count_documents(query)
        skip = (page - 1) * page_size
        
        cursor = db.settings_audit_logs.find(
            query, {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(page_size)
        
        logs = await cursor.to_list(length=page_size)
        
        # Enrich with actor names
        for log in logs:
            if log.get("actor_id"):
                actor = await db.users.find_one({"id": log["actor_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
                if actor:
                    log["actor_name"] = f"{actor.get('first_name', '')} {actor.get('last_name', '')}".strip()
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "page_size": page_size
        }


# Singleton instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get the singleton settings service instance"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
