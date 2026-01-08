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
        
    except AINotConfiguredError:
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


# ==================== STAGE READINESS ADVISOR ====================

class StageReadinessResponse(BaseModel):
    """Stage readiness analysis - advisory only"""
    deal_id: str
    current_stage: str
    next_stage: Optional[str]
    is_ready: bool
    blockers: list  # Required fields/actions missing
    recommendations: list  # AI suggestions to progress
    required_fields: dict  # Fields needed for next stage
    completion_percentage: int
    disclaimer: str = "Advisory only. CRM enforces actual stage transitions."


@router.get("/deals/{deal_id}/stage-readiness", response_model=StageReadinessResponse)
async def get_stage_readiness(
    deal_id: str,
    user = Depends(get_current_user)
):
    """
    Analyze deal readiness for stage progression.
    
    GOVERNANCE:
    - Read-only analysis
    - AI suggests, CRM enforces
    - Cannot bypass stage rules
    """
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get current stage info
    current_stage = deal.get("stage_name", "Unknown")
    pipeline_id = deal.get("pipeline_id")
    
    # Get next stage in pipeline
    next_stage = None
    if pipeline_id:
        current_stage_doc = await db.pipeline_stages.find_one(
            {"pipeline_id": pipeline_id, "name": current_stage},
            {"_id": 0}
        )
        if current_stage_doc:
            next_stage_doc = await db.pipeline_stages.find_one(
                {"pipeline_id": pipeline_id, "display_order": current_stage_doc.get("display_order", 0) + 1},
                {"_id": 0}
            )
            if next_stage_doc:
                next_stage = next_stage_doc.get("name")
    
    # Define stage requirements based on PRD Section 7
    stage_requirements = {
        "Calculations / Analysis In Progress": {
            "required": ["economic_units", "usage_volume"],
            "recommended": ["trigger_event", "primary_motivation"]
        },
        "Discovery / Demo Scheduled": {
            "required": ["economic_units", "usage_volume", "urgency"],
            "recommended": ["decision_role", "trigger_event"]
        },
        "Discovery / Demo Completed": {
            "required": ["spiced_situation", "spiced_pain", "spiced_impact"],
            "recommended": ["spiced_critical_event", "spiced_economic", "spiced_decision"]
        },
        "Decision Pending": {
            "required": ["spiced_situation", "spiced_pain", "spiced_impact", "spiced_economic", "spiced_decision"],
            "recommended": ["amount"]
        },
        "Verbal Commitment": {
            "required": ["amount", "spiced_summary"],
            "recommended": ["decision_process_clarity"]
        },
        "Closed Won": {
            "required": ["amount", "spiced_summary"],
            "recommended": []
        }
    }
    
    # Get requirements for next stage
    reqs = stage_requirements.get(next_stage, {"required": [], "recommended": []})
    
    # Check blockers
    blockers = []
    for field in reqs.get("required", []):
        value = deal.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            blockers.append({
                "field": field,
                "label": field.replace("_", " ").title(),
                "type": "required"
            })
    
    # Check recommended
    recommendations = []
    for field in reqs.get("recommended", []):
        value = deal.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            recommendations.append(f"Consider adding {field.replace('_', ' ')}")
    
    # Add contextual recommendations
    if not deal.get("amount") or deal.get("amount") == 0:
        recommendations.append("Add deal amount for accurate forecasting")
    if deal.get("tier") == "D":
        recommendations.append("Low tier lead - consider re-qualifying before progressing")
    if not deal.get("contact_id"):
        recommendations.append("Link a primary contact to this deal")
    
    # Calculate completion
    total_fields = len(reqs.get("required", [])) + len(reqs.get("recommended", []))
    completed_fields = total_fields - len(blockers) - len([r for r in recommendations if "Consider adding" in r])
    completion_pct = int((completed_fields / max(total_fields, 1)) * 100)
    
    return StageReadinessResponse(
        deal_id=deal_id,
        current_stage=current_stage,
        next_stage=next_stage,
        is_ready=len(blockers) == 0,
        blockers=blockers,
        recommendations=recommendations,
        required_fields=reqs,
        completion_percentage=min(completion_pct, 100),
        disclaimer="Advisory only. CRM enforces actual stage transitions."
    )


# ==================== DEAL RISK ANALYSIS ====================

class DealRiskResponse(BaseModel):
    """Deal risk analysis - advisory only"""
    deal_id: str
    risk_score: int  # 0-100, higher = more risk
    risk_level: str  # low, medium, high, critical
    risk_factors: list  # Identified risks
    recommendations: list  # Actions to reduce risk
    forecast_impact: str  # Impact on forecast
    disclaimer: str = "Risk analysis is advisory. Does not affect CRM calculations."


@router.get("/deals/{deal_id}/risk-analysis", response_model=DealRiskResponse)
async def get_deal_risk_analysis(
    deal_id: str,
    user = Depends(get_current_user)
):
    """
    Analyze deal risk factors.
    
    GOVERNANCE:
    - Read-only analysis
    - Does not modify forecast or probability
    - AI insights only
    """
    db = get_database()
    
    deal = await db.deals.find_one(
        {"id": deal_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    risk_score = 0
    risk_factors = []
    recommendations = []
    
    # Risk Factor 1: Low tier
    tier = deal.get("tier", "D")
    if tier == "D":
        risk_score += 30
        risk_factors.append({
            "factor": "Low Lead Tier",
            "severity": "high",
            "description": "Tier D leads have 0% forecast probability"
        })
        recommendations.append("Re-qualify lead or move to nurture")
    elif tier == "C":
        risk_score += 15
        risk_factors.append({
            "factor": "Standard Lead Tier",
            "severity": "medium",
            "description": "Tier C has 15-30% probability"
        })
    
    # Risk Factor 2: Missing SPICED
    has_spiced = any([
        deal.get("spiced_situation"),
        deal.get("spiced_pain"),
        deal.get("spiced_impact")
    ])
    if not has_spiced:
        risk_score += 20
        risk_factors.append({
            "factor": "Missing SPICED Summary",
            "severity": "high",
            "description": "No discovery information captured"
        })
        recommendations.append("Complete SPICED discovery summary")
    
    # Risk Factor 3: No amount
    if not deal.get("amount") or deal.get("amount") == 0:
        risk_score += 15
        risk_factors.append({
            "factor": "No Deal Amount",
            "severity": "medium",
            "description": "Cannot forecast without deal value"
        })
        recommendations.append("Add estimated deal amount")
    
    # Risk Factor 4: Low urgency
    urgency = deal.get("urgency", 0)
    if urgency and urgency < 3:
        risk_score += 10
        risk_factors.append({
            "factor": "Low Urgency",
            "severity": "medium",
            "description": f"Urgency rated {urgency}/5"
        })
        recommendations.append("Identify trigger events to increase urgency")
    
    # Risk Factor 5: Missing decision clarity
    decision_clarity = deal.get("decision_process_clarity", 0)
    if not decision_clarity or decision_clarity < 3:
        risk_score += 15
        risk_factors.append({
            "factor": "Unclear Decision Process",
            "severity": "medium",
            "description": "Decision process not well understood"
        })
        recommendations.append("Map out decision makers and process")
    
    # Risk Factor 6: Stale deal (no recent activity)
    from datetime import datetime, timezone, timedelta
    updated_at = deal.get("updated_at")
    if updated_at:
        try:
            if isinstance(updated_at, str):
                last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            else:
                last_update = updated_at
            days_stale = (datetime.now(timezone.utc) - last_update).days
            if days_stale > 14:
                risk_score += 20
                risk_factors.append({
                    "factor": "Stale Deal",
                    "severity": "high",
                    "description": f"No activity in {days_stale} days"
                })
                recommendations.append("Schedule follow-up activity immediately")
            elif days_stale > 7:
                risk_score += 10
                risk_factors.append({
                    "factor": "Aging Deal",
                    "severity": "medium",
                    "description": f"No activity in {days_stale} days"
                })
        except (ValueError, TypeError, AttributeError):
            pass
    
    # Determine risk level
    risk_score = min(risk_score, 100)
    if risk_score >= 70:
        risk_level = "critical"
        forecast_impact = "Deal unlikely to close - excluded from reliable forecast"
    elif risk_score >= 50:
        risk_level = "high"
        forecast_impact = "Significant forecast risk - apply conservative weighting"
    elif risk_score >= 30:
        risk_level = "medium"
        forecast_impact = "Moderate risk - monitor closely"
    else:
        risk_level = "low"
        forecast_impact = "On track - included in forecast"
    
    return DealRiskResponse(
        deal_id=deal_id,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        recommendations=recommendations,
        forecast_impact=forecast_impact,
        disclaimer="Risk analysis is advisory. Does not affect CRM calculations."
    )


# ==================== PIPELINE HEALTH SUMMARY ====================

@router.get("/pipeline/health-summary")
async def get_pipeline_health_summary(
    pipeline_type: str = Query("sales", description="Pipeline type: qualification or sales"),
    user = Depends(get_current_user)
):
    """
    Get overall pipeline health metrics.
    
    GOVERNANCE:
    - Read-only aggregation
    - Does not modify any data
    """
    db = get_database()
    tenant_id = user["tenant_id"]
    
    # Get pipeline
    pipeline = await db.pipelines.find_one(
        {"tenant_id": tenant_id, "pipeline_type": pipeline_type},
        {"_id": 0}
    )
    
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_type}' not found")
    
    # Get all deals in pipeline
    deals = await db.deals.find(
        {"tenant_id": tenant_id, "pipeline_id": pipeline["id"], "status": "open"},
        {"_id": 0}
    ).to_list(length=1000)
    
    # Calculate metrics
    total_deals = len(deals)
    total_value = sum(d.get("amount", 0) for d in deals)
    weighted_value = sum(
        (d.get("amount", 0) * d.get("forecast_probability", 0)) 
        for d in deals
    )
    
    # Tier distribution
    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for deal in deals:
        tier = deal.get("tier", "D")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    # Risk distribution
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    at_risk_deals = []
    
    for deal in deals:
        # Simple risk calculation
        risk_score = 0
        if deal.get("tier") == "D":
            risk_score += 30
        elif deal.get("tier") == "C":
            risk_score += 15
        if not deal.get("spiced_situation"):
            risk_score += 20
        if not deal.get("amount"):
            risk_score += 15
        
        if risk_score >= 70:
            risk_counts["critical"] += 1
            at_risk_deals.append({"id": deal["id"], "name": deal.get("name"), "risk_score": risk_score})
        elif risk_score >= 50:
            risk_counts["high"] += 1
            at_risk_deals.append({"id": deal["id"], "name": deal.get("name"), "risk_score": risk_score})
        elif risk_score >= 30:
            risk_counts["medium"] += 1
        else:
            risk_counts["low"] += 1
    
    # Stage distribution
    stage_counts = {}
    for deal in deals:
        stage = deal.get("stage_name", "Unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    
    # SPICED completion rate
    spiced_complete = sum(
        1 for d in deals 
        if d.get("spiced_situation") and d.get("spiced_pain") and d.get("spiced_impact")
    )
    spiced_rate = (spiced_complete / max(total_deals, 1)) * 100
    
    return {
        "pipeline_id": pipeline["id"],
        "pipeline_name": pipeline.get("name"),
        "pipeline_type": pipeline_type,
        "summary": {
            "total_deals": total_deals,
            "total_value": total_value,
            "weighted_value": weighted_value,
            "avg_deal_size": total_value / max(total_deals, 1)
        },
        "tier_distribution": tier_counts,
        "risk_distribution": risk_counts,
        "at_risk_deals": at_risk_deals[:10],  # Top 10 at-risk
        "stage_distribution": stage_counts,
        "health_metrics": {
            "spiced_completion_rate": round(spiced_rate, 1),
            "tier_a_percentage": round((tier_counts["A"] / max(total_deals, 1)) * 100, 1),
            "at_risk_percentage": round(((risk_counts["high"] + risk_counts["critical"]) / max(total_deals, 1)) * 100, 1)
        },
        "disclaimer": "Metrics are calculated from current data. Does not predict future outcomes."
    }


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
    integrations = await settings.get_integrations(workspace_id)
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
