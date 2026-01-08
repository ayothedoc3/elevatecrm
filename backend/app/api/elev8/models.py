"""
Elev8 CRM - Shared Models

Enums and Pydantic schemas used across the Elev8 CRM module.
Per Elev8 specification sections 3, 4, and 6.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ==================== ENUMS ====================

class SalesMotionType(str, Enum):
    PARTNERSHIP_SALES = "partnership_sales"  # Selling Elev8 services
    PARTNER_SALES = "partner_sales"  # Selling partner products


class LeadTier(str, Enum):
    A = "A"  # 80-100: Priority account, senior ownership
    B = "B"  # 60-79: Strategic SDR or AE motion
    C = "C"  # 40-59: Standard SDR motion
    D = "D"  # 0-39: Low priority, nurture only


class LeadStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    WORKING = "working"
    INFO_COLLECTED = "info_collected"
    UNRESPONSIVE = "unresponsive"
    DISQUALIFIED = "disqualified"
    QUALIFIED = "qualified"


class PartnerType(str, Enum):
    CHANNEL = "channel"
    RESELLER = "reseller"
    TECHNOLOGY = "technology"
    STRATEGIC = "strategic"


class PartnerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"


# ==================== LEAD SCHEMAS ====================

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    
    # Sales Motion (Required per Section 4)
    sales_motion_type: SalesMotionType = SalesMotionType.PARTNERSHIP_SALES
    partner_id: Optional[str] = None  # Required if partner_sales
    product_id: Optional[str] = None  # Required if partner_sales
    
    # Lead Source
    source: Optional[str] = None
    source_detail: Optional[str] = None
    
    # Scoring Inputs (Section 6.2)
    economic_units: Optional[int] = None  # e.g., locations, sites, licenses
    usage_volume: Optional[int] = None  # e.g., fryers, users, lines
    urgency: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale
    trigger_event: Optional[str] = None
    primary_motivation: Optional[str] = None
    decision_role: Optional[str] = None  # Decision Maker, Influencer, Champion, etc.
    decision_process_clarity: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale
    
    # Assignment
    owner_id: Optional[str] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    sales_motion_type: Optional[SalesMotionType] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    source: Optional[str] = None
    source_detail: Optional[str] = None
    economic_units: Optional[int] = None
    usage_volume: Optional[int] = None
    urgency: Optional[int] = Field(None, ge=1, le=5)
    trigger_event: Optional[str] = None
    primary_motivation: Optional[str] = None
    decision_role: Optional[str] = None
    decision_process_clarity: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[LeadStatus] = None
    owner_id: Optional[str] = None


# ==================== PARTNER SCHEMAS ====================

class PartnerCreate(BaseModel):
    name: str
    partner_type: PartnerType = PartnerType.CHANNEL
    status: PartnerStatus = PartnerStatus.PROSPECT
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    
    # Partner-specific configuration (Section 12)
    config_json: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None
    kpi_config: Optional[Dict[str, Any]] = None
    compliance_rules: Optional[List[str]] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    partner_type: Optional[PartnerType] = None
    status: Optional[PartnerStatus] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None
    kpi_config: Optional[Dict[str, Any]] = None
    compliance_rules: Optional[List[str]] = None


# ==================== PRODUCT SCHEMAS ====================

class ProductCreate(BaseModel):
    name: str
    partner_id: str  # Required - link to partner
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    is_active: bool = True
    
    # Product-specific details
    details_json: Optional[Dict[str, Any]] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    partner_id: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None
    details_json: Optional[Dict[str, Any]] = None


# ==================== COMPANY SCHEMAS ====================

class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    description: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    description: Optional[str] = None
