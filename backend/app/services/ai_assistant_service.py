"""
Elev8 AI Assistant Service

Advisory-only AI service that:
- Drafts SPICED summaries (never auto-saves)
- Explains lead scores (read-only)
- Suggests outreach strategies (draft-only)
- Never modifies CRM state directly

GOVERNANCE RULES (HARD CONSTRAINTS):
1. AI has NO mutation access to: pipeline stage, lead score, tier, owner
2. AI output is DRAFT-ONLY - user must explicitly save
3. CRM server logic ALWAYS re-validates on save
4. All AI calls include workspace context for audit

Per Elev8 AI Assistant PRD:
- AI may suggest, draft, explain, and prepare
- AI may NEVER decide, bypass, or commit
- CRM is the source of truth, AI is advisory only
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel

from app.db.mongodb import get_database
from app.services.unified_ai_service import get_ai_service, AIServiceError, AINotConfiguredError
from app.services.settings_service import AIFeatureType

logger = logging.getLogger(__name__)


# ==================== REQUEST/RESPONSE MODELS ====================

class SpicedDraftRequest(BaseModel):
    """Request for SPICED drafting assistance"""
    deal_id: str
    # Optional context to help draft better content
    notes: Optional[str] = None
    call_summary: Optional[str] = None
    email_thread: Optional[str] = None
    existing_spiced: Optional[Dict[str, str]] = None  # Current SPICED fields if editing


class SpicedDraftResponse(BaseModel):
    """SPICED draft response - clearly marked as AI suggestion"""
    draft: Dict[str, str]  # situation, pain, impact, critical_event, economic, decision
    confidence_notes: Dict[str, str]  # Notes about each field's confidence
    suggestions: List[str]  # Additional discovery questions to ask
    disclaimer: str = "AI-generated draft. Review and save to apply changes."
    is_draft: bool = True  # Always true - never auto-saved


class LeadIntelligenceRequest(BaseModel):
    """Request for lead intelligence/explanation"""
    lead_id: str
    query_type: str  # "score_breakdown", "tier_explanation", "outreach_suggestion"


class LeadIntelligenceResponse(BaseModel):
    """Lead intelligence response - read-only explanation"""
    lead_id: str
    query_type: str
    explanation: str
    data: Optional[Dict[str, Any]] = None  # Supporting data (score breakdown, etc.)
    suggested_actions: List[str] = []  # Non-binding suggestions
    disclaimer: str = "AI analysis is advisory only. CRM scoring is authoritative."


class OutreachDraftRequest(BaseModel):
    """Request for outreach message drafting"""
    lead_id: str
    message_type: str  # "first_touch", "follow_up", "discovery_prep", "demo_agenda"
    additional_context: Optional[str] = None


class OutreachDraftResponse(BaseModel):
    """Outreach draft - clearly marked as suggestion"""
    subject: Optional[str] = None
    body: str
    tone: str  # "formal", "friendly", "urgent"
    personalization_notes: List[str]  # What was personalized
    disclaimer: str = "AI-generated draft. Edit before sending."
    is_draft: bool = True


# ==================== AI ASSISTANT SERVICE ====================

class Elev8AIAssistant:
    """
    Elev8 AI Sales Assistant
    
    Governance-compliant AI assistant that provides:
    - SPICED drafting (never auto-saves)
    - Lead score explanations (read-only)
    - Outreach suggestions (draft-only)
    
    All operations are workspace-scoped and audit-logged.
    """
    
    def __init__(self, workspace_id: str, user_id: str, user_role: str):
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.user_role = user_role
        self.ai_service = get_ai_service(workspace_id)
    
    async def _log_ai_request(
        self, 
        feature_type: str,
        request_type: str,
        entity_id: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Log AI assistant usage for audit trail"""
        db = get_database()
        
        await db.ai_assistant_logs.insert_one({
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "feature_type": feature_type,
            "request_type": request_type,
            "entity_id": entity_id,
            "success": success,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def draft_spiced(self, request: SpicedDraftRequest) -> SpicedDraftResponse:
        """
        Generate SPICED summary draft from provided context.
        
        GOVERNANCE:
        - Output is DRAFT-ONLY
        - User must explicitly save
        - CRM validates on save
        """
        db = get_database()
        
        # Get deal context (read-only)
        deal = await db.deals.find_one(
            {"id": request.deal_id, "tenant_id": self.workspace_id.split("_")[0]},  # Extract tenant from workspace
            {"_id": 0}
        )
        
        if not deal:
            raise ValueError("Deal not found")
        
        # Get contact and company context
        contact = None
        company = None
        if deal.get("contact_id"):
            contact = await db.contacts.find_one({"id": deal["contact_id"]}, {"_id": 0})
        if deal.get("company_id"):
            company = await db.companies.find_one({"id": deal["company_id"]}, {"_id": 0})
        
        # Build context for AI
        context_parts = []
        context_parts.append(f"Deal: {deal.get('name', 'Unknown')}")
        context_parts.append(f"Amount: ${deal.get('amount', 0):,.0f}")
        context_parts.append(f"Sales Motion: {deal.get('sales_motion_type', 'partnership_sales')}")
        context_parts.append(f"Tier: {deal.get('tier', 'Unknown')}")
        
        if contact:
            context_parts.append(f"Contact: {contact.get('first_name', '')} {contact.get('last_name', '')} ({contact.get('title', 'Unknown title')})")
        if company:
            context_parts.append(f"Company: {company.get('name', 'Unknown')} - {company.get('industry', 'Unknown industry')}")
        
        if request.notes:
            context_parts.append(f"\nUser Notes:\n{request.notes}")
        if request.call_summary:
            context_parts.append(f"\nCall Summary:\n{request.call_summary}")
        if request.email_thread:
            context_parts.append(f"\nEmail Context:\n{request.email_thread[:2000]}")  # Limit email context
        
        if request.existing_spiced:
            context_parts.append(f"\nExisting SPICED (for reference):\n{request.existing_spiced}")
        
        context = "\n".join(context_parts)
        
        system_message = """You are an expert B2B sales assistant helping draft SPICED discovery summaries.

SPICED Framework:
- Situation: Company background, current state, context
- Pain: Specific business pain point(s) identified  
- Impact: Quantified impact in $ or operational terms
- Critical Event: Timeline trigger - what makes this urgent?
- Economic: Budget, decision-maker, approval authority, procurement process
- Decision: How do they buy? Decision criteria? Timeline to close?

Guidelines:
- Be concise but thorough
- Use specific details from the context provided
- Flag areas where more discovery is needed
- Suggest follow-up questions

IMPORTANT: This is a DRAFT for human review. The user will edit and save manually."""

        prompt = f"""Based on the following deal context, draft a SPICED summary.

CONTEXT:
{context}

Generate a JSON response with:
1. "draft": Object with fields: situation, pain, impact, critical_event, economic, decision
2. "confidence_notes": Object noting confidence level for each field
3. "suggestions": Array of follow-up discovery questions

Keep each SPICED field to 2-3 sentences maximum. Mark areas needing more discovery with "[NEEDS DISCOVERY]"."""

        try:
            response = await self.ai_service.generate(
                feature_type=AIFeatureType.SPICED_DRAFTING,
                prompt=prompt,
                system_message=system_message,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse AI response
            import json
            try:
                # Try to extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    parsed = json.loads(response[json_start:json_end])
                else:
                    parsed = {"draft": {}, "confidence_notes": {}, "suggestions": []}
            except json.JSONDecodeError:
                # Fallback parsing
                parsed = {
                    "draft": {
                        "situation": response[:500] if response else "",
                        "pain": "",
                        "impact": "",
                        "critical_event": "",
                        "economic": "",
                        "decision": ""
                    },
                    "confidence_notes": {},
                    "suggestions": ["Unable to fully parse AI response - please review and edit"]
                }
            
            await self._log_ai_request(
                "spiced_drafting", "draft", request.deal_id, True
            )
            
            return SpicedDraftResponse(
                draft=parsed.get("draft", {}),
                confidence_notes=parsed.get("confidence_notes", {}),
                suggestions=parsed.get("suggestions", []),
                disclaimer="AI-generated draft. Review carefully and save to apply changes. CRM will validate on save.",
                is_draft=True
            )
            
        except (AIServiceError, AINotConfiguredError) as e:
            await self._log_ai_request(
                "spiced_drafting", "draft", request.deal_id, False, str(e)
            )
            raise
    
    async def explain_lead_score(self, lead_id: str) -> LeadIntelligenceResponse:
        """
        Explain how a lead's score was calculated.
        
        GOVERNANCE:
        - Read-only operation
        - Uses CRM's deterministic scoring data
        - AI provides human-readable explanation
        """
        db = get_database()
        
        # Get lead (read-only)
        lead = await db.leads.find_one(
            {"id": lead_id},
            {"_id": 0}
        )
        
        if not lead:
            raise ValueError("Lead not found")
        
        # Get score breakdown from scoring engine (deterministic)
        from app.api.elev8.scoring import get_score_breakdown
        breakdown = get_score_breakdown(lead)
        
        # Build human-readable explanation
        explanation_parts = []
        explanation_parts.append(f"**Lead Score: {breakdown['total_score']}/100 (Tier {breakdown['tier']})**\n")
        explanation_parts.append(f"*{breakdown['tier_description']}*\n")
        explanation_parts.append(f"Forecast Probability: {breakdown['forecast_probability']*100:.0f}%\n")
        
        explanation_parts.append("\n**Score Breakdown:**\n")
        for cat in breakdown["categories"]:
            explanation_parts.append(f"- **{cat['name']}**: {cat['score']}/{cat['weight']} points")
            explanation_parts.append(f"  - {cat['explanation']}")
        
        # Generate AI interpretation
        system_message = """You are an expert sales analyst providing insights on lead scoring.
Your role is ADVISORY ONLY. The score is calculated by the CRM system - you explain it.
Be concise and actionable. Focus on what the sales rep should know and do."""

        prompt = f"""Based on this lead score breakdown, provide:
1. A 2-sentence summary of why this lead is Tier {breakdown['tier']}
2. The 1-2 most important factors affecting the score
3. 1-2 actionable suggestions to improve lead quality (if applicable)

Lead: {lead.get('first_name', '')} {lead.get('last_name', '')}
Company: {lead.get('company_name', 'Unknown')}
Score: {breakdown['total_score']} (Tier {breakdown['tier']})

Breakdown:
{breakdown['categories']}

Keep response under 150 words. Be specific and actionable."""

        try:
            ai_insight = await self.ai_service.generate(
                feature_type=AIFeatureType.LEAD_INTELLIGENCE,
                prompt=prompt,
                system_message=system_message,
                temperature=0.5,
                max_tokens=500
            )
            
            explanation_parts.append(f"\n**AI Analysis:**\n{ai_insight}")
            
        except (AIServiceError, AINotConfiguredError):
            explanation_parts.append("\n*AI analysis unavailable - showing score breakdown only*")
        
        await self._log_ai_request(
            "lead_intelligence", "score_breakdown", lead_id, True
        )
        
        return LeadIntelligenceResponse(
            lead_id=lead_id,
            query_type="score_breakdown",
            explanation="\n".join(explanation_parts),
            data=breakdown,
            suggested_actions=[],
            disclaimer="Score is calculated by CRM system. AI analysis is advisory only."
        )
    
    async def explain_tier(self, lead_id: str) -> LeadIntelligenceResponse:
        """
        Explain what a lead's tier means and recommended actions.
        
        GOVERNANCE:
        - Read-only operation
        - Tier is determined by CRM, AI explains it
        """
        db = get_database()
        
        lead = await db.leads.find_one(
            {"id": lead_id},
            {"_id": 0}
        )
        
        if not lead:
            raise ValueError("Lead not found")
        
        tier = lead.get("tier", "D")
        score = lead.get("lead_score", 0)
        sales_motion = lead.get("sales_motion_type", "partnership_sales")
        
        tier_info = {
            "A": {
                "description": "Priority Account",
                "action": "Senior ownership required. High-touch engagement.",
                "probability": "60-80%",
                "cadence": "Daily follow-up, exec involvement"
            },
            "B": {
                "description": "Strategic Account", 
                "action": "Strategic SDR or AE motion. Accelerated qualification.",
                "probability": "35-60%",
                "cadence": "Every 2-3 days, personalized outreach"
            },
            "C": {
                "description": "Standard Account",
                "action": "Standard SDR motion. Follow playbook.",
                "probability": "15-30%",
                "cadence": "Weekly touchpoints, nurture sequence"
            },
            "D": {
                "description": "Nurture Account",
                "action": "Low priority. Automated nurture only.",
                "probability": "0%",
                "cadence": "Monthly newsletter, re-qualify in 90 days"
            }
        }
        
        info = tier_info.get(tier, tier_info["D"])
        
        explanation = f"""**Tier {tier}: {info['description']}**

**Score:** {score}/100
**Forecast Probability:** {info['probability']}
**Sales Motion:** {sales_motion.replace('_', ' ').title()}

**Recommended Action:**
{info['action']}

**Suggested Cadence:**
{info['cadence']}"""

        await self._log_ai_request(
            "lead_intelligence", "tier_explanation", lead_id, True
        )
        
        return LeadIntelligenceResponse(
            lead_id=lead_id,
            query_type="tier_explanation",
            explanation=explanation,
            data={"tier": tier, "score": score, "tier_info": info},
            suggested_actions=[info['action']],
            disclaimer="Tier is determined by CRM scoring. Recommendations are guidelines."
        )
    
    async def suggest_outreach(self, request: OutreachDraftRequest) -> OutreachDraftResponse:
        """
        Generate outreach message draft based on lead context.
        
        GOVERNANCE:
        - Output is DRAFT-ONLY
        - User must edit and send manually
        """
        db = get_database()
        
        lead = await db.leads.find_one(
            {"id": request.lead_id},
            {"_id": 0}
        )
        
        if not lead:
            raise ValueError("Lead not found")
        
        # Build context
        first_name = lead.get("first_name", "there")
        company = lead.get("company_name", "your company")
        title = lead.get("title", "")
        tier = lead.get("tier", "C")
        sales_motion = lead.get("sales_motion_type", "partnership_sales")
        source = lead.get("source", "")
        motivation = lead.get("primary_motivation", "")
        
        # Determine tone based on tier
        tone = "formal" if tier in ["A", "B"] else "friendly"
        
        message_templates = {
            "first_touch": {
                "subject": f"Quick question about {company}",
                "system": "Write a brief, personalized first-touch cold email. Be direct and value-focused. 3-4 sentences max."
            },
            "follow_up": {
                "subject": f"Following up - {company}",
                "system": "Write a polite follow-up email. Reference previous contact attempt. Offer new value or insight. 2-3 sentences."
            },
            "discovery_prep": {
                "subject": None,
                "system": "Create a discovery call prep sheet with: key questions to ask, objections to anticipate, and value props to highlight."
            },
            "demo_agenda": {
                "subject": f"Agenda for our demo - {company}",
                "system": "Create a professional demo agenda email. Include: intro, demo outline, time for questions, next steps."
            }
        }
        
        template = message_templates.get(request.message_type, message_templates["first_touch"])
        
        prompt = f"""Generate a {request.message_type.replace('_', ' ')} message for:
        
Lead: {first_name} {lead.get('last_name', '')}
Title: {title}
Company: {company}
Tier: {tier} ({tier_info.get(tier, {}).get('description', '')})
Sales Motion: {sales_motion.replace('_', ' ')}
Source: {source}
Primary Motivation: {motivation}

Additional context: {request.additional_context or 'None provided'}

Requirements:
- Personalize using the context above
- Tone: {tone}
- Keep it concise and actionable
- End with a clear call-to-action"""

        try:
            response = await self.ai_service.generate(
                feature_type=AIFeatureType.LEAD_INTELLIGENCE,
                prompt=prompt,
                system_message=template["system"],
                temperature=0.7,
                max_tokens=800
            )
            
            await self._log_ai_request(
                "lead_intelligence", "outreach_draft", request.lead_id, True
            )
            
            personalization = []
            if first_name != "there":
                personalization.append(f"Personalized with name: {first_name}")
            if company:
                personalization.append(f"Referenced company: {company}")
            if motivation:
                personalization.append(f"Aligned to motivation: {motivation}")
            
            return OutreachDraftResponse(
                subject=template.get("subject"),
                body=response,
                tone=tone,
                personalization_notes=personalization,
                disclaimer="AI-generated draft. Edit and personalize before sending.",
                is_draft=True
            )
            
        except (AIServiceError, AINotConfiguredError) as e:
            await self._log_ai_request(
                "lead_intelligence", "outreach_draft", request.lead_id, False, str(e)
            )
            raise


# Tier info for reference
tier_info = {
    "A": {"description": "Priority Account", "probability": "60-80%"},
    "B": {"description": "Strategic Account", "probability": "35-60%"},
    "C": {"description": "Standard Account", "probability": "15-30%"},
    "D": {"description": "Nurture Account", "probability": "0%"}
}


def get_ai_assistant(workspace_id: str, user_id: str, user_role: str) -> Elev8AIAssistant:
    """Factory function to get an AI assistant instance"""
    return Elev8AIAssistant(workspace_id, user_id, user_role)
