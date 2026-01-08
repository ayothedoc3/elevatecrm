"""
Elev8 AI Assistant Routes

API endpoints for the AI Assistant (advisory/draft-only).

GOVERNANCE RULES:
1. NO mutation endpoints - all operations are read or draft
2. All responses clearly marked as "AI suggestion" or "draft"
3. User must explicitly save any drafts via separate CRM endpoints
4. All requests include workspace context for audit

Per Elev8 AI PRD:
- AI is advisory and preparatory only
- CRM is the source of truth
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.db.mongodb import get_database
from app.api.elev8.auth import get_current_user
from app.services.ai_assistant_service import (
    get_ai_assistant,
    SpicedDraftRequest,
    SpicedDraftResponse,
    LeadIntelligenceResponse,
    OutreachDraftRequest,
    OutreachDraftResponse
)
from app.services.unified_ai_service import AIServiceError, AINotConfiguredError

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# ==================== SPICED DRAFTING ====================

@router.post("/spiced/draft", response_model=SpicedDraftResponse)
async def draft_spiced_summary(
    request: SpicedDraftRequest,
    user = Depends(get_current_user)
):
    """
    Generate a SPICED summary draft for a deal.
    
    GOVERNANCE:
    - Returns DRAFT only - not saved automatically
    - User must review and save via PUT /deals/{id}
    - CRM validates all fields on save
    """
    try:
        assistant = get_ai_assistant(
            workspace_id=user.get("workspace_id") or user["tenant_id"],
            user_id=user["id"],
            user_role=user.get("role", "user")
        )
        
        return await assistant.draft_spiced(request)
        
    except AINotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ai_not_configured",
                "message": str(e),
                "action": "Configure AI provider in Settings > AI & Intelligence"
            }
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ai_service_error",
                "message": str(e)
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== LEAD INTELLIGENCE ====================

@router.get("/leads/{lead_id}/score-explanation", response_model=LeadIntelligenceResponse)
async def explain_lead_score(
    lead_id: str,
    user = Depends(get_current_user)
):
    """
    Get AI explanation of how a lead's score was calculated.
    
    GOVERNANCE:
    - Read-only operation
    - Score is calculated by CRM, AI explains it
    - AI analysis is advisory only
    """
    try:
        assistant = get_ai_assistant(
            workspace_id=user.get("workspace_id") or user["tenant_id"],
            user_id=user["id"],
            user_role=user.get("role", "user")
        )
        
        return await assistant.explain_lead_score(lead_id)
        
    except AINotConfiguredError as e:
        # Fall back to score breakdown without AI
        from app.api.elev8.scoring import get_score_breakdown
        db = get_database()
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        breakdown = get_score_breakdown(lead)
        return LeadIntelligenceResponse(
            lead_id=lead_id,
            query_type="score_breakdown",
            explanation=f"Score: {breakdown['total_score']}/100 (Tier {breakdown['tier']}). AI explanation unavailable - configure AI in Settings.",
            data=breakdown,
            disclaimer="AI not configured. Showing score breakdown only."
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/leads/{lead_id}/tier-explanation", response_model=LeadIntelligenceResponse)
async def explain_lead_tier(
    lead_id: str,
    user = Depends(get_current_user)
):
    """
    Get explanation of what a lead's tier means and recommended actions.
    
    GOVERNANCE:
    - Read-only operation
    - Tier is determined by CRM scoring
    - Recommendations are guidelines only
    """
    try:
        assistant = get_ai_assistant(
            workspace_id=user.get("workspace_id") or user["tenant_id"],
            user_id=user["id"],
            user_role=user.get("role", "user")
        )
        
        return await assistant.explain_tier(lead_id)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/leads/{lead_id}/outreach-draft", response_model=OutreachDraftResponse)
async def draft_outreach_message(
    lead_id: str,
    message_type: str = Query(..., description="Type: first_touch, follow_up, discovery_prep, demo_agenda"),
    additional_context: Optional[str] = Query(None, description="Additional context for personalization"),
    user = Depends(get_current_user)
):
    """
    Generate an outreach message draft for a lead.
    
    GOVERNANCE:
    - Returns DRAFT only
    - User must edit and send manually
    - Not connected to any email sending system
    """
    try:
        assistant = get_ai_assistant(
            workspace_id=user.get("workspace_id") or user["tenant_id"],
            user_id=user["id"],
            user_role=user.get("role", "user")
        )
        
        request = OutreachDraftRequest(
            lead_id=lead_id,
            message_type=message_type,
            additional_context=additional_context
        )
        
        return await assistant.suggest_outreach(request)
        
    except AINotConfiguredError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ai_not_configured",
                "message": str(e),
                "action": "Configure AI provider in Settings > AI & Intelligence"
            }
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ai_service_error",
                "message": str(e)
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== AI STATUS CHECK ====================

@router.get("/status")
async def get_ai_assistant_status(user = Depends(get_current_user)):
    """
    Check if AI Assistant is configured and available for this workspace.
    """
    from app.services.settings_service import get_settings_service
    
    settings = get_settings_service()
    workspace_id = user.get("workspace_id") or user["tenant_id"]
    
    # Get AI config
    config = await settings.get_ai_config(workspace_id)
    
    # Get configured providers
    integrations = await settings.get_integrations_list(workspace_id)
    ai_integrations = [i for i in integrations if i.get("category") == "ai"]
    
    enabled_providers = [
        i["provider_type"] for i in ai_integrations 
        if i.get("enabled", False)
    ]
    
    # Check if at least one AI provider is available
    import os
    has_fallback = bool(os.environ.get("EMERGENT_LLM_KEY"))
    
    is_configured = len(enabled_providers) > 0 or has_fallback
    
    return {
        "is_configured": is_configured,
        "enabled_providers": enabled_providers,
        "default_provider": config.get("default_provider"),
        "default_model": config.get("default_model"),
        "has_fallback_key": has_fallback,
        "features": {
            "spiced_drafting": is_configured,
            "lead_intelligence": True,  # Score breakdown works without AI
            "outreach_drafting": is_configured
        },
        "governance": {
            "ai_role": "advisory_only",
            "mutations_allowed": False,
            "auto_save": False,
            "crm_is_source_of_truth": True
        }
    }


# ==================== GOVERNANCE INFO ====================

@router.get("/governance")
async def get_ai_governance_rules():
    """
    Get AI Assistant governance rules and boundaries.
    For transparency and user education.
    """
    return {
        "core_principle": "AI may suggest, draft, explain, and prepare. AI may NEVER decide, bypass, or commit.",
        "crm_authority": {
            "scoring": "CRM calculates, AI explains",
            "stages": "CRM enforces, AI guides",
            "spiced": "AI drafts, CRM validates",
            "tasks": "AI suggests, CRM enforces",
            "forecast": "CRM calculates, AI analyzes",
            "handoff": "AI prepares, CRM triggers"
        },
        "ai_boundaries": {
            "allowed": [
                "Explain lead score breakdown",
                "Draft SPICED summaries",
                "Suggest outreach messages",
                "Analyze deal risks (read-only)",
                "Provide coaching suggestions"
            ],
            "never_allowed": [
                "Change lead score",
                "Move pipeline stages",
                "Modify ownership",
                "Change tier assignment",
                "Auto-save any data",
                "Bypass validation rules"
            ]
        },
        "data_handling": {
            "prompts_logged": False,
            "responses_logged": False,
            "usage_metadata_logged": True,
            "cross_tenant_access": False
        }
    }
