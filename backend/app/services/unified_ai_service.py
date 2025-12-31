"""
Unified AI Service Layer

Centralized AI service that:
- Resolves provider + key based on workspace_id and feature_type
- Handles provider fallback
- Logs usage metadata (never prompts/keys)
- Enforces rate limits

ALL AI usage across the platform MUST go through this service.
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum

from app.db.mongodb import get_database
from app.services.settings_service import get_settings_service, ProviderType, AIFeatureType

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass


class AINotConfiguredError(AIServiceError):
    """Raised when AI is not configured for a workspace"""
    pass


class AIRateLimitError(AIServiceError):
    """Raised when rate limit is exceeded"""
    pass


class UnifiedAIService:
    """
    Unified AI service layer for all AI operations.
    
    Usage:
        service = UnifiedAIService(workspace_id="abc123")
        response = await service.generate(
            feature_type=AIFeatureType.PAGE_BUILDER,
            prompt="Generate a landing page...",
            system_message="You are a copywriter..."
        )
    """
    
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.settings_service = get_settings_service()
        self._config_cache = None
        self._integrations_cache = None
    
    async def _get_config(self) -> Dict[str, Any]:
        """Get cached AI config"""
        if self._config_cache is None:
            self._config_cache = await self.settings_service.get_ai_config(self.workspace_id)
        return self._config_cache
    
    async def _get_integration(self, provider_type: str) -> Optional[Dict[str, Any]]:
        """Get integration with decrypted key (internal use only)"""
        return await self.settings_service.get_integration(
            self.workspace_id, provider_type, include_key=True
        )
    
    async def resolve_provider(
        self, feature_type: AIFeatureType
    ) -> tuple[str, str, str]:
        """
        Resolve which provider, model, and key to use for a feature.
        
        Returns:
            Tuple of (provider, model, api_key)
        """
        config = await self._get_config()
        
        # Check if feature is enabled
        if not config.get("features_enabled", {}).get(feature_type.value, True):
            raise AINotConfiguredError(f"AI feature '{feature_type.value}' is disabled for this workspace")
        
        # Check for feature-specific override
        overrides = config.get("provider_overrides", {})
        if feature_type.value in overrides:
            override = overrides[feature_type.value]
            provider = override.get("provider", config.get("default_provider", "openai"))
            model = override.get("model", config.get("default_model", "gpt-4o"))
        else:
            provider = config.get("default_provider", "openai")
            model = config.get("default_model", "gpt-4o")
        
        # Get the integration and key
        integration = await self._get_integration(provider)
        
        if not integration or not integration.get("enabled", True):
            # Try fallback to environment key
            env_key = os.environ.get("EMERGENT_LLM_KEY")
            if env_key:
                logger.info(f"Using environment EMERGENT_LLM_KEY for workspace {self.workspace_id}")
                return provider, model, env_key
            
            raise AINotConfiguredError(
                f"AI provider '{provider}' is not configured for this workspace. "
                "Please configure your API keys in Settings > AI & Intelligence."
            )
        
        api_key = integration.get("api_key")
        if not api_key:
            raise AINotConfiguredError(
                f"API key for '{provider}' is missing or invalid. "
                "Please update your API key in Settings > AI & Intelligence."
            )
        
        return provider, model, api_key
    
    async def check_rate_limit(self, feature_type: AIFeatureType) -> bool:
        """
        Check if the workspace is within rate limits.
        Returns True if request is allowed, raises AIRateLimitError otherwise.
        """
        config = await self._get_config()
        limits = config.get("usage_limits", {})
        
        daily_limit = limits.get("daily_requests", 1000)
        monthly_limit = limits.get("monthly_requests", 25000)
        
        db = get_database()
        
        # Get today's start
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get month's start
        month_start = today.replace(day=1)
        
        # Count daily usage
        daily_count = await db.ai_usage_logs.count_documents({
            "workspace_id": self.workspace_id,
            "timestamp": {"$gte": today.isoformat()}
        })
        
        if daily_count >= daily_limit:
            raise AIRateLimitError(
                f"Daily AI request limit ({daily_limit}) exceeded. "
                "Please try again tomorrow or upgrade your plan."
            )
        
        # Count monthly usage
        monthly_count = await db.ai_usage_logs.count_documents({
            "workspace_id": self.workspace_id,
            "timestamp": {"$gte": month_start.isoformat()}
        })
        
        if monthly_count >= monthly_limit:
            raise AIRateLimitError(
                f"Monthly AI request limit ({monthly_limit}) exceeded. "
                "Please upgrade your plan or wait until next month."
            )
        
        return True
    
    async def log_usage(
        self, feature_type: AIFeatureType, provider: str, model: str,
        success: bool, error_message: str = None,
        tokens_used: int = None, response_time_ms: int = None
    ):
        """
        Log AI usage metadata (never prompts or keys).
        """
        db = get_database()
        
        log_entry = {
            "id": str(uuid.uuid4()),
            "workspace_id": self.workspace_id,
            "feature_type": feature_type.value,
            "provider": provider,
            "model": model,
            "success": success,
            "error_message": error_message,
            "tokens_used": tokens_used,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.ai_usage_logs.insert_one(log_entry)
        
        # Update last_used_at on the integration
        await self.settings_service.update_last_used(self.workspace_id, provider)
    
    async def generate(
        self, feature_type: AIFeatureType, prompt: str,
        system_message: str = None, temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate AI content using the resolved provider.
        
        Args:
            feature_type: The type of AI feature being used
            prompt: The user prompt
            system_message: Optional system message
            temperature: Model temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            The AI-generated response text
        """
        import time
        start_time = time.time()
        
        # Check rate limit
        await self.check_rate_limit(feature_type)
        
        # Resolve provider
        provider, model, api_key = await self.resolve_provider(feature_type)
        
        try:
            # Import and use emergentintegrations
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            session_id = f"{feature_type.value}-{uuid.uuid4().hex[:8]}"
            
            # Map provider to emergentintegrations format
            provider_map = {
                "openai": "openai",
                "anthropic": "anthropic",
                "openrouter": "openrouter"
            }
            
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=system_message or "You are a helpful assistant."
            ).with_model(provider_map.get(provider, "openai"), model)
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log successful usage
            await self.log_usage(
                feature_type, provider, model,
                success=True,
                response_time_ms=response_time_ms
            )
            
            return response
            
        except Exception as e:
            # Log failed usage
            response_time_ms = int((time.time() - start_time) * 1000)
            await self.log_usage(
                feature_type, provider, model,
                success=False,
                error_message=str(e)[:500],
                response_time_ms=response_time_ms
            )
            
            logger.error(f"AI generation failed: {e}")
            raise AIServiceError(f"AI generation failed: {str(e)}")
    
    async def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get AI usage statistics for the workspace.
        """
        db = get_database()
        
        start_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        start_date = start_date - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "workspace_id": self.workspace_id,
                "timestamp": {"$gte": start_date.isoformat()}
            }},
            {"$group": {
                "_id": {
                    "feature": "$feature_type",
                    "provider": "$provider"
                },
                "total_requests": {"$sum": 1},
                "successful_requests": {
                    "$sum": {"$cond": ["$success", 1, 0]}
                },
                "total_tokens": {"$sum": {"$ifNull": ["$tokens_used", 0]}},
                "avg_response_time": {"$avg": "$response_time_ms"}
            }}
        ]
        
        results = await db.ai_usage_logs.aggregate(pipeline).to_list(length=100)
        
        # Get today's and this month's totals
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today.replace(day=1)
        
        daily_count = await db.ai_usage_logs.count_documents({
            "workspace_id": self.workspace_id,
            "timestamp": {"$gte": today.isoformat()}
        })
        
        monthly_count = await db.ai_usage_logs.count_documents({
            "workspace_id": self.workspace_id,
            "timestamp": {"$gte": month_start.isoformat()}
        })
        
        config = await self._get_config()
        limits = config.get("usage_limits", {})
        
        return {
            "period_days": days,
            "by_feature_provider": [
                {
                    "feature": r["_id"]["feature"],
                    "provider": r["_id"]["provider"],
                    "total_requests": r["total_requests"],
                    "successful_requests": r["successful_requests"],
                    "success_rate": round(r["successful_requests"] / r["total_requests"] * 100, 1) if r["total_requests"] > 0 else 0,
                    "total_tokens": r["total_tokens"],
                    "avg_response_time_ms": round(r["avg_response_time"] or 0, 0)
                }
                for r in results
            ],
            "current_usage": {
                "daily": {
                    "used": daily_count,
                    "limit": limits.get("daily_requests", 1000),
                    "remaining": max(0, limits.get("daily_requests", 1000) - daily_count)
                },
                "monthly": {
                    "used": monthly_count,
                    "limit": limits.get("monthly_requests", 25000),
                    "remaining": max(0, limits.get("monthly_requests", 25000) - monthly_count)
                }
            }
        }


async def test_provider_connection(
    workspace_id: str, provider_type: str, api_key: str = None
) -> Dict[str, Any]:
    """
    Test connection to an AI provider.
    This is called during setup to verify keys work.
    
    Args:
        workspace_id: The workspace ID
        provider_type: The provider to test (openai, anthropic, etc.)
        api_key: Optional key to test (if not provided, uses stored key)
    """
    import time
    start_time = time.time()
    
    settings_service = get_settings_service()
    
    # Get the key to test
    if not api_key:
        integration = await settings_service.get_integration(
            workspace_id, provider_type, include_key=True
        )
        if not integration:
            return {
                "success": False,
                "error": f"No {provider_type} integration configured"
            }
        api_key = integration.get("api_key")
    
    if not api_key:
        return {
            "success": False,
            "error": "No API key provided"
        }
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Simple test message
        chat = LlmChat(
            api_key=api_key,
            session_id=f"test-{uuid.uuid4().hex[:8]}",
            system_message="Respond with only the word 'connected' to confirm the connection."
        ).with_model(provider_type, "gpt-4o" if provider_type == "openai" else "claude-sonnet-4-20250514")
        
        response = await chat.send_message(UserMessage(text="Test connection"))
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Update test status
        db = get_database()
        await db.workspace_integrations.update_one(
            {"workspace_id": workspace_id, "provider_type": provider_type},
            {"$set": {
                "last_test_at": datetime.now(timezone.utc).isoformat(),
                "test_status": "success"
            }}
        )
        
        # Log the test
        await settings_service._log_audit(
            workspace_id, None, settings_service.settings_service if hasattr(settings_service, 'settings_service') else None,
            provider_type=provider_type,
            metadata={"test_result": "success", "response_time_ms": response_time_ms}
        )
        
        return {
            "success": True,
            "response_time_ms": response_time_ms,
            "message": "Connection successful"
        }
        
    except Exception as e:
        error_msg = str(e)[:200]
        
        # Update test status
        db = get_database()
        await db.workspace_integrations.update_one(
            {"workspace_id": workspace_id, "provider_type": provider_type},
            {"$set": {
                "last_test_at": datetime.now(timezone.utc).isoformat(),
                "test_status": "failed",
                "test_error": error_msg
            }}
        )
        
        return {
            "success": False,
            "error": error_msg
        }


def get_ai_service(workspace_id: str) -> UnifiedAIService:
    """Factory function to get an AI service instance for a workspace"""
    return UnifiedAIService(workspace_id)
