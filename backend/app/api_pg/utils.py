from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VALID_SALES_MOTION_TYPES = {"partnership_sales", "partner_sales"}
VALID_LEAD_TIERS = {"A", "B", "C", "D"}
VALID_ICP_TIERS = {"A", "B", "C", "D"}
VALID_BUYING_ROLES = {"decision_maker", "champion", "influencer", "technical", "finance"}

# Phase 1 discipline: minimum touchpoints before "unresponsive"
MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE = 3

# Midpoint probabilities from the spec's tier bands:
# A: 0.60-0.80, B: 0.35-0.60, C: 0.15-0.30, D: 0.00
TIER_PROBABILITY = {"A": 0.70, "B": 0.475, "C": 0.225, "D": 0.00}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def normalize_lower(value: Optional[str]) -> str:
    return " ".join((value or "").strip().split()).lower()


def normalize_icp_tier(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip().upper()
    if not raw:
        return None
    if raw in VALID_ICP_TIERS:
        return raw
    return None


def normalize_buying_role(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return None
    aliases = {
        "decisionmaker": "decision_maker",
        "decision_maker": "decision_maker",
        "decision-maker": "decision_maker",
        "owner": "decision_maker",
        "ceo": "decision_maker",
        "founder": "decision_maker",
        "cfo": "decision_maker",
        "champion": "champion",
        "influencer": "influencer",
        "technical": "technical",
        "tech": "technical",
        "technical_buyer": "technical",
        "finance": "finance",
        "financial": "finance",
    }
    normalized = aliases.get(raw, raw)
    if normalized in VALID_BUYING_ROLES:
        return normalized
    return None


def ensure_valid_icp_tier(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    normalized = normalize_icp_tier(raw)
    if normalized is None:
        raise ValueError("Invalid icp_tier. Must be one of: A, B, C, D")
    return normalized


def ensure_valid_buying_role(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    normalized = normalize_buying_role(raw)
    if normalized is None:
        raise ValueError(
            "Invalid buying_role. Must be one of: decision_maker, champion, influencer, technical, finance"
        )
    return normalized


def calculate_tier(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def tier_probability(tier: Optional[str]) -> float:
    if not tier:
        return 0.0
    return float(TIER_PROBABILITY.get(str(tier).strip().upper(), 0.0))


def is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def get_by_path(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def scoring_inputs_complete(scoring_data: Dict[str, Any]) -> bool:
    data = scoring_data or {}

    # Elev8 Matrix scoring model (preferred).
    has_new_inputs = all(
        [
            str(data.get("icp_tier") or "").strip() != "",
            str(data.get("company_size_fit") or "").strip() != "",
            str(data.get("buying_role_strength") or data.get("buying_role") or "").strip() != "",
        ]
    )
    has_engagement_inputs = (
        data.get("engagement_score") is not None
        or (
            data.get("email_open") is not None
            and data.get("link_click") is not None
            and data.get("demo_booked") is not None
        )
    )
    if has_new_inputs and has_engagement_inputs:
        return True

    # Backward-compatible scoring model (legacy workspaces).
    legacy_required = [
        "economic_units",
        "usage_volume",
        "urgency",
        "trigger_event",
        "primary_motivation",
        "decision_role",
        "decision_process_clarity",
    ]
    for key in legacy_required:
        value = data.get(key)
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True


def compute_universal_score(scoring_data: Dict[str, Any], lead_source: str) -> int:
    """Compute lead score (0-100) with Elev8 Matrix inputs and a legacy fallback."""

    def _to_float(value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    def _to_int(value, default=0):
        try:
            if value is None or value == "":
                return default
            return int(value)
        except Exception:
            return default

    scoring_data = scoring_data or {}

    # Elev8 Matrix model:
    # ICP tier (40) + Engagement (30) + Company size fit (15) + Buying role strength (15)
    icp_tier = (scoring_data.get("icp_tier") or "").strip().upper()
    icp_points = {"A": 40, "B": 25, "C": 10, "D": 0}.get(icp_tier, 0)

    if scoring_data.get("engagement_score") is not None:
        engagement_points = max(0, min(30, _to_int(scoring_data.get("engagement_score"), 0)))
    else:
        email_open = _to_int(scoring_data.get("email_open"), 0) > 0
        link_click = _to_int(scoring_data.get("link_click"), 0) > 0
        demo_booked = bool(scoring_data.get("demo_booked"))
        engagement_points = (10 if email_open else 0) + (10 if link_click else 0) + (10 if demo_booked else 0)

    raw_company_fit = scoring_data.get("company_size_fit")
    if raw_company_fit is None:
        company_fit_points = 0
    elif isinstance(raw_company_fit, (int, float)):
        company_fit_points = max(0, min(15, int(raw_company_fit)))
    else:
        company_fit = str(raw_company_fit).strip().lower()
        company_fit_points = {
            "ideal": 15,
            "high": 15,
            "strong": 12,
            "medium": 8,
            "partial": 6,
            "low": 3,
            "poor": 0,
        }.get(company_fit, 0)

    raw_role_strength = scoring_data.get("buying_role_strength")
    if raw_role_strength is None:
        buying_role = str(scoring_data.get("buying_role") or "").strip().lower()
        role_points = {
            "decision_maker": 15,
            "owner": 15,
            "ceo": 15,
            "cfo": 15,
            "founder": 15,
            "champion": 12,
            "influencer": 10,
            "manager": 8,
            "director": 8,
            "technical": 8,
            "finance": 7,
            "researcher": 4,
            "assistant": 3,
        }.get(buying_role, 0)
    elif isinstance(raw_role_strength, (int, float)):
        role_points = max(0, min(15, int(raw_role_strength)))
    else:
        role_label = str(raw_role_strength).strip().lower()
        role_points = {
            "strong": 15,
            "high": 15,
            "medium": 9,
            "low": 4,
            "poor": 0,
        }.get(role_label, 0)

    has_matrix_inputs = (
        icp_tier in {"A", "B", "C", "D"}
        and (scoring_data.get("engagement_score") is not None or scoring_data.get("email_open") is not None or scoring_data.get("link_click") is not None or scoring_data.get("demo_booked") is not None)
        and raw_company_fit is not None
        and (raw_role_strength is not None or scoring_data.get("buying_role") is not None)
    )
    matrix_score = int(max(0, min(100, icp_points + engagement_points + company_fit_points + role_points)))
    if has_matrix_inputs:
        return matrix_score

    # Legacy fallback model (existing data compatibility).
    economic_units = max(0.0, _to_float(scoring_data.get("economic_units"), 0.0))
    usage_volume = max(0.0, _to_float(scoring_data.get("usage_volume"), 0.0))
    urgency = min(5, max(1, _to_int(scoring_data.get("urgency"), 1)))
    trigger_event = (scoring_data.get("trigger_event") or "").strip()
    primary_motivation = (scoring_data.get("primary_motivation") or "").strip().lower()
    decision_role = (scoring_data.get("decision_role") or "").strip().lower()
    decision_process_clarity = min(5, max(1, _to_int(scoring_data.get("decision_process_clarity"), 1)))

    # Size & Economic Impact (30) split across economic_units (15) and usage_volume (15)
    if economic_units >= 20:
        econ_points = 15
    elif economic_units >= 10:
        econ_points = 12
    elif economic_units >= 5:
        econ_points = 9
    elif economic_units >= 2:
        econ_points = 6
    elif economic_units >= 1:
        econ_points = 3
    else:
        econ_points = 0

    if usage_volume >= 100:
        usage_points = 15
    elif usage_volume >= 50:
        usage_points = 12
    elif usage_volume >= 20:
        usage_points = 9
    elif usage_volume >= 6:
        usage_points = 6
    elif usage_volume >= 1:
        usage_points = 3
    else:
        usage_points = 0

    size_impact = econ_points + usage_points  # 0-30

    # Urgency & Willingness to Act (20)
    urgency_points = (urgency - 1) * 4  # 0,4,8,12,16
    trigger_points = 4 if trigger_event else 0
    urgency_total = min(20, urgency_points + trigger_points)

    # Lead Source Quality (15)
    source = (lead_source or "").strip().lower()
    source_map = {
        "referral": 15,
        "event": 12,
        "web": 10,
        "social": 8,
        "email": 6,
        "manual": 5,
        "cold_call": 4,
    }
    source_quality = source_map.get(source, 6)

    # Strategic Motivation & Vision (20)
    motivation_points = 12
    if any(k in primary_motivation for k in ["growth", "scale", "expansion"]):
        motivation_points = 18
    elif any(k in primary_motivation for k in ["save", "savings", "cost"]):
        motivation_points = 20
    elif any(k in primary_motivation for k in ["efficien", "process", "automation"]):
        motivation_points = 15
    elif any(k in primary_motivation for k in ["compliance", "risk", "audit"]):
        motivation_points = 15
    elif any(k in primary_motivation for k in ["curious", "learn", "explore"]):
        motivation_points = 6

    # Decision Readiness (15)
    role_points = 3
    if decision_role in ["decision_maker", "dm", "owner", "ceo", "cfo", "founder"]:
        role_points = 8
    elif decision_role in ["influencer", "champion", "manager", "director"]:
        role_points = 5
    elif decision_role in ["researcher", "analyst", "assistant"]:
        role_points = 2

    clarity_points = (decision_process_clarity - 1) * 2  # 0,2,4,6,8
    clarity_points = min(7, clarity_points)  # cap at 7
    decision_readiness = min(15, role_points + clarity_points)

    score = int(round(size_impact + urgency_total + source_quality + motivation_points + decision_readiness))
    return min(100, max(0, score))

