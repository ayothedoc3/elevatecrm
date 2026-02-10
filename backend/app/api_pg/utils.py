from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VALID_SALES_MOTION_TYPES = {"partnership_sales", "partner_sales"}
VALID_LEAD_TIERS = {"A", "B", "C", "D"}

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
    required_keys = [
        "economic_units",
        "usage_volume",
        "urgency",
        "trigger_event",
        "primary_motivation",
        "decision_role",
        "decision_process_clarity",
    ]
    for key in required_keys:
        value = (scoring_data or {}).get(key)
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True


def compute_universal_score(scoring_data: Dict[str, Any], lead_source: str) -> int:
    """
    Compute product-agnostic lead score (0-100) using Elev8 weights.

    Required inputs (stored in scoring_data):
    - economic_units (number)
    - usage_volume (number)
    - urgency (1-5)
    - trigger_event (string)
    - primary_motivation (string)
    - decision_role (string)
    - decision_process_clarity (1-5)

    Lead source comes from the Lead.source field.
    """

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

