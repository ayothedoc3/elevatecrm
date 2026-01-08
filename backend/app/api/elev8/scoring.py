"""
Elev8 CRM - Lead Scoring Engine

Deterministic lead scoring based on Section 6 of the Elev8 specification.
This is the source of truth for scoring - AI cannot modify these calculations.

Categories & Weights:
- Size & Economic Impact: 30%
- Urgency & Willingness to Act: 20%
- Lead Source Quality: 15%
- Strategic Motivation & Vision: 20%
- Decision Readiness: 15%
"""

from .models import LeadTier


def calculate_lead_score(lead: dict) -> tuple[int, str]:
    """
    Calculate lead score (0-100) based on Section 6.1 weights.
    Returns (score, tier).
    
    This is a deterministic, server-side calculation.
    AI may explain but never modify this logic.
    """
    score = 0
    
    # 1. Size & Economic Impact (30 points max)
    economic_units = lead.get("economic_units") or 0
    usage_volume = lead.get("usage_volume") or 0
    
    # Scale economic units (assume 1-10 = low, 11-50 = medium, 51+ = high)
    if economic_units >= 50:
        score += 30
    elif economic_units >= 20:
        score += 22
    elif economic_units >= 10:
        score += 15
    elif economic_units >= 5:
        score += 10
    elif economic_units >= 1:
        score += 5
    
    # Boost for high usage volume
    if usage_volume >= 100:
        score = min(score + 5, 30)
    
    # 2. Urgency & Willingness to Act (20 points max)
    urgency = lead.get("urgency") or 0
    trigger_event = lead.get("trigger_event")
    
    # Urgency score (1-5 scale)
    urgency_score = (urgency / 5) * 15
    score += int(urgency_score)
    
    # Trigger event bonus
    if trigger_event and len(trigger_event) > 5:
        score += 5
    
    # 3. Lead Source Quality (15 points max)
    source = (lead.get("source") or "").lower()
    source_scores = {
        "referral": 15,
        "partner_referral": 15,
        "inbound_demo": 13,
        "website_demo": 12,
        "trade_show": 10,
        "webinar": 9,
        "content_download": 7,
        "cold_outreach": 5,
        "purchased_list": 3,
        "unknown": 2
    }
    score += source_scores.get(source, 5)
    
    # 4. Strategic Motivation & Vision (20 points max)
    primary_motivation = (lead.get("primary_motivation") or "")
    motivation_scores = {
        "cost_reduction": 18,
        "revenue_growth": 20,
        "compliance": 15,
        "efficiency": 17,
        "competitive_pressure": 16,
        "modernization": 12,
        "expansion": 14,
        "other": 8
    }
    score += motivation_scores.get(primary_motivation.lower(), 8) if primary_motivation else 5
    
    # 5. Decision Readiness (15 points max)
    decision_role = (lead.get("decision_role") or "").lower()
    decision_clarity = lead.get("decision_process_clarity") or 0
    
    role_scores = {
        "decision_maker": 8,
        "economic_buyer": 8,
        "champion": 6,
        "influencer": 4,
        "user": 2,
        "unknown": 1
    }
    score += role_scores.get(decision_role, 3)
    
    # Decision process clarity (1-5 scale)
    clarity_score = (decision_clarity / 5) * 7
    score += int(clarity_score)
    
    # Cap score at 100
    score = min(score, 100)
    
    # Determine tier (Section 6.3)
    if score >= 80:
        tier = LeadTier.A.value
    elif score >= 60:
        tier = LeadTier.B.value
    elif score >= 40:
        tier = LeadTier.C.value
    else:
        tier = LeadTier.D.value
    
    return score, tier


def get_tier_probability(tier: str) -> float:
    """Get forecast probability by tier (Section 6.4)"""
    probabilities = {
        "A": 0.70,  # 60-80%
        "B": 0.475,  # 35-60%
        "C": 0.225,  # 15-30%
        "D": 0.0    # 0%
    }
    return probabilities.get(tier, 0.0)


def get_score_breakdown(lead: dict) -> dict:
    """
    Get detailed breakdown of lead score calculation.
    Used by AI Assistant to explain scores (read-only).
    """
    breakdown = {
        "categories": [],
        "total_score": 0,
        "tier": "",
        "explanation": ""
    }
    
    # 1. Size & Economic Impact
    economic_units = lead.get("economic_units") or 0
    usage_volume = lead.get("usage_volume") or 0
    size_score = 0
    
    if economic_units >= 50:
        size_score = 30
    elif economic_units >= 20:
        size_score = 22
    elif economic_units >= 10:
        size_score = 15
    elif economic_units >= 5:
        size_score = 10
    elif economic_units >= 1:
        size_score = 5
    
    if usage_volume >= 100:
        size_score = min(size_score + 5, 30)
    
    breakdown["categories"].append({
        "name": "Size & Economic Impact",
        "weight": 30,
        "score": size_score,
        "inputs": {"economic_units": economic_units, "usage_volume": usage_volume},
        "explanation": f"Economic units: {economic_units}, Usage volume: {usage_volume}"
    })
    
    # 2. Urgency & Willingness to Act
    urgency = lead.get("urgency") or 0
    trigger_event = lead.get("trigger_event") or ""
    urgency_score = int((urgency / 5) * 15)
    if trigger_event and len(trigger_event) > 5:
        urgency_score += 5
    urgency_score = min(urgency_score, 20)
    
    breakdown["categories"].append({
        "name": "Urgency & Willingness to Act",
        "weight": 20,
        "score": urgency_score,
        "inputs": {"urgency": urgency, "trigger_event": trigger_event[:50] if trigger_event else None},
        "explanation": f"Urgency: {urgency}/5, Trigger: {'Yes' if trigger_event else 'No'}"
    })
    
    # 3. Lead Source Quality
    source = (lead.get("source") or "").lower()
    source_scores = {
        "referral": 15, "partner_referral": 15, "inbound_demo": 13,
        "website_demo": 12, "trade_show": 10, "webinar": 9,
        "content_download": 7, "cold_outreach": 5, "purchased_list": 3, "unknown": 2
    }
    source_score = source_scores.get(source, 5)
    
    breakdown["categories"].append({
        "name": "Lead Source Quality",
        "weight": 15,
        "score": source_score,
        "inputs": {"source": source or "unknown"},
        "explanation": f"Source: {source or 'unknown'}"
    })
    
    # 4. Strategic Motivation & Vision
    primary_motivation = (lead.get("primary_motivation") or "")
    motivation_scores = {
        "cost_reduction": 18, "revenue_growth": 20, "compliance": 15,
        "efficiency": 17, "competitive_pressure": 16, "modernization": 12,
        "expansion": 14, "other": 8
    }
    motivation_score = motivation_scores.get(primary_motivation.lower(), 8) if primary_motivation else 5
    
    breakdown["categories"].append({
        "name": "Strategic Motivation & Vision",
        "weight": 20,
        "score": motivation_score,
        "inputs": {"primary_motivation": primary_motivation or "unknown"},
        "explanation": f"Motivation: {primary_motivation or 'unknown'}"
    })
    
    # 5. Decision Readiness
    decision_role = (lead.get("decision_role") or "").lower()
    decision_clarity = lead.get("decision_process_clarity") or 0
    role_scores = {
        "decision_maker": 8, "economic_buyer": 8, "champion": 6,
        "influencer": 4, "user": 2, "unknown": 1
    }
    decision_score = role_scores.get(decision_role, 3) + int((decision_clarity / 5) * 7)
    decision_score = min(decision_score, 15)
    
    breakdown["categories"].append({
        "name": "Decision Readiness",
        "weight": 15,
        "score": decision_score,
        "inputs": {"decision_role": decision_role or "unknown", "decision_process_clarity": decision_clarity},
        "explanation": f"Role: {decision_role or 'unknown'}, Clarity: {decision_clarity}/5"
    })
    
    # Calculate total
    total_score = sum(cat["score"] for cat in breakdown["categories"])
    total_score = min(total_score, 100)
    
    # Determine tier
    if total_score >= 80:
        tier = "A"
        tier_desc = "Priority account - Senior ownership"
    elif total_score >= 60:
        tier = "B"
        tier_desc = "Strategic SDR or AE motion"
    elif total_score >= 40:
        tier = "C"
        tier_desc = "Standard SDR motion"
    else:
        tier = "D"
        tier_desc = "Low priority - Nurture only"
    
    breakdown["total_score"] = total_score
    breakdown["tier"] = tier
    breakdown["tier_description"] = tier_desc
    breakdown["forecast_probability"] = get_tier_probability(tier)
    
    return breakdown
