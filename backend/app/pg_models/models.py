from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False, default="viewer")  # admin | manager | sales | viewer
    is_active = Column(Boolean, default=True, nullable=False)

    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name_lower", name="uq_accounts_tenant_name_lower"),
        Index("ix_accounts_tenant_name_lower", "tenant_id", "name_lower"),
    )


class Partner(Base):
    __tablename__ = "partners"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    default_pipeline_id = Column(
        String(36), ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name_lower", name="uq_partners_tenant_name_lower"),
        Index("ix_partners_tenant_name_lower", "tenant_id", "name_lower"),
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    partner_id = Column(String(36), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "partner_id", "name_lower", name="uq_products_tenant_partner_name_lower"),
        Index("ix_products_tenant_partner", "tenant_id", "partner_id"),
    )


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    company_name = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True)

    sales_motion_type = Column(String(50), nullable=False, default="partnership_sales")
    partner_id = Column(String(36), nullable=True, index=True)
    product_id = Column(String(36), nullable=True, index=True)
    partner_name = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)

    score = Column(Integer, default=0, nullable=False)
    tier = Column(String(2), default="D", nullable=False, index=True)
    scoring_data = Column(JSONB, default=dict, nullable=False)

    status = Column(String(50), default="new", nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    touchpoints_count = Column(Integer, default=0, nullable=False)
    last_touchpoint_at = Column(DateTime(timezone=True), nullable=True)
    first_touchpoint_at = Column(DateTime(timezone=True), nullable=True, index=True)

    tags = Column(JSONB, default=list, nullable=False)

    # Conversion tracking
    converted_at = Column(DateTime(timezone=True), nullable=True)
    contact_id = Column(String(36), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_leads_tenant_owner_status", "tenant_id", "owner_id", "status"),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)

    company_name = Column(String(255), nullable=True)

    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    account_name = Column(String(255), nullable=True)

    source = Column(String(100), nullable=True)
    lifecycle_stage = Column(String(50), default="lead", nullable=False)

    lead_score = Column(Integer, default=0, nullable=False)
    lead_tier = Column(String(2), default="D", nullable=False, index=True)

    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    tags = Column(JSONB, default=list, nullable=False)
    status = Column(String(50), default="active", nullable=False)
    converted_from_lead_id = Column(String(36), nullable=True, index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_contacts_tenant_owner", "tenant_id", "owner_id"),
    )


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_pipelines_tenant_order", "tenant_id", "display_order"),
    )


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id = Column(String(36), primary_key=True, default=_uuid)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    color = Column(String(20), default="#6366F1", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    probability = Column(Float, default=0.0, nullable=False)

    required_fields = Column(JSONB, default=list, nullable=False)
    requires_calculation_complete = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_pipeline_stages_pipeline_order", "pipeline_id", "display_order"),
    )


class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(20), default="open", nullable=False, index=True)  # open | won | lost

    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    account_name = Column(String(255), nullable=True)

    pipeline_id = Column(String(36), ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_id = Column(String(36), ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True, index=True)

    next_step_at = Column(DateTime(timezone=True), nullable=True, index=True)
    next_step_note = Column(Text, nullable=True)

    last_touchpoint_at = Column(DateTime(timezone=True), nullable=True, index=True)

    lead_score = Column(Integer, default=0, nullable=False)
    lead_tier = Column(String(2), default="D", nullable=False, index=True)

    sales_motion_type = Column(String(50), default="partnership_sales", nullable=False, index=True)
    partner_id = Column(String(36), nullable=True, index=True)
    product_id = Column(String(36), nullable=True, index=True)
    partner_name = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)

    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Close/reopen tracking
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_won_at = Column(DateTime(timezone=True), nullable=True)
    closed_lost_at = Column(DateTime(timezone=True), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)

    # Discovery / Demo / Qualification capture
    spiced = Column(JSONB, default=dict, nullable=False)

    demo_title = Column(String(255), nullable=True)
    demo_type = Column(String(50), nullable=True)
    demo_status = Column(String(30), nullable=True, index=True)  # scheduled | completed | no_show | canceled
    demo_scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    demo_duration_minutes = Column(Integer, default=30, nullable=False)
    demo_meet_url = Column(String(500), nullable=True)
    demo_calendar_url = Column(String(1000), nullable=True)
    demo_completed_at = Column(DateTime(timezone=True), nullable=True)
    demo_notes = Column(Text, nullable=True)

    last_override = Column(JSONB, default=dict, nullable=False)

    # Handoff tracking
    handoff_status = Column(String(20), default="pending", nullable=False)
    handoff_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_deals_tenant_pipeline_stage", "tenant_id", "pipeline_id", "stage_id"),
        Index("ix_deals_tenant_owner", "tenant_id", "owner_id"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)

    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(20), default="open", nullable=False, index=True)  # open | completed | canceled
    kind = Column(String(30), default="manual", nullable=False, index=True)  # manual | next_step

    related_type = Column(String(30), nullable=True, index=True)  # deal | lead | contact | account
    related_id = Column(String(36), nullable=True, index=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_tasks_tenant_status_due", "tenant_id", "status", "due_at"),
        Index("ix_tasks_related", "tenant_id", "related_type", "related_id", "status"),
    )


class OutreachActivity(Base):
    __tablename__ = "outreach_activities"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    activity_type = Column(String(50), nullable=False, index=True)
    direction = Column(String(30), default="outbound", nullable=False)
    status = Column(String(30), default="completed", nullable=False)

    subject = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    got_response = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_outreach_tenant_deal_created", "tenant_id", "deal_id", "created_at"),
    )


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name = Column(String(255), nullable=True)

    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True, index=True)

    visibility = Column(String(30), default="internal_only", nullable=False)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_timeline_tenant_created", "tenant_id", "created_at"),
    )


class DealHandoff(Base):
    __tablename__ = "deal_handoffs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)

    delivery_owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    kickoff_at = Column(DateTime(timezone=True), nullable=True)
    checklist = Column(JSONB, default=dict, nullable=False)
    notes = Column(Text, nullable=True)

    status = Column(String(20), default="pending", nullable=False, index=True)  # pending | completed
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "deal_id", name="uq_deal_handoffs_tenant_deal"),
    )


class CalculationDefinition(Base):
    __tablename__ = "calculation_definitions"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    input_schema = Column(JSONB, default=list, nullable=False)
    output_schema = Column(JSONB, default=list, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_calc_defs_tenant_active", "tenant_id", "is_active"),
    )


class CalculationResult(Base):
    __tablename__ = "calculation_results"

    id = Column(String(36), primary_key=True, default=_uuid)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    definition_id = Column(String(36), ForeignKey("calculation_definitions.id", ondelete="CASCADE"), nullable=False, index=True)

    inputs = Column(JSONB, default=dict, nullable=False)
    outputs = Column(JSONB, default=dict, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("deal_id", "definition_id", name="uq_calc_results_deal_definition"),
    )


# ==================== SETTINGS / CONFIG ====================


class WorkspaceSetting(Base):
    __tablename__ = "workspace_settings"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(20), default="#6366F1", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    sla_config = Column(
        JSONB,
        default=lambda: {"speed_to_lead_minutes": 15, "lead_cadence_hours": 24, "deal_cadence_hours": 72},
        nullable=False,
    )

    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_workspace_settings_tenant"),)


class WorkspaceIntegration(Base):
    __tablename__ = "workspace_integrations"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    provider_type = Column(String(50), nullable=False)
    encrypted_api_key = Column(Text, nullable=False)
    key_hash = Column(String(50), nullable=True)

    config = Column(JSONB, default=dict, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_test_at = Column(DateTime(timezone=True), nullable=True)
    test_status = Column(String(30), nullable=True)  # success | failure

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_type", name="uq_workspace_integrations_tenant_provider"),
        Index("ix_workspace_integrations_tenant_provider", "tenant_id", "provider_type"),
    )


class AIUsageConfig(Base):
    __tablename__ = "ai_usage_configs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    default_provider = Column(String(50), default="openai", nullable=False)
    default_model = Column(String(100), default="gpt-4o", nullable=False)

    provider_overrides = Column(JSONB, default=dict, nullable=False)
    usage_limits = Column(JSONB, default=lambda: {"daily_requests": 1000, "monthly_requests": 25000}, nullable=False)
    features_enabled = Column(JSONB, default=dict, nullable=False)

    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_ai_usage_configs_tenant"),)


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    feature = Column(String(50), nullable=True)
    requests = Column(Integer, default=1, nullable=False)
    tokens_in = Column(Integer, default=0, nullable=False)
    tokens_out = Column(Integer, default=0, nullable=False)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_ai_usage_logs_tenant_created", "tenant_id", "created_at"),
    )


class SettingsAuditLog(Base):
    __tablename__ = "settings_audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)

    action = Column(String(50), nullable=False, index=True)
    provider_type = Column(String(50), nullable=True, index=True)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_settings_audit_tenant_created", "tenant_id", "created_at"),
    )


# ==================== LANDING PAGES ====================


class LandingPage(Base):
    __tablename__ = "landing_pages"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    slug = Column(String(255), nullable=False)
    page_type = Column(String(50), default="generic", nullable=False, index=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)

    page_schema = Column(JSONB, default=dict, nullable=False)

    affiliate_program_id = Column(
        String(36), ForeignKey("affiliate_programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)

    ai_model_used = Column(String(100), nullable=True)
    custom_slug = Column(String(255), nullable=True)
    seo_title = Column(String(255), nullable=True)
    seo_description = Column(Text, nullable=True)

    view_count = Column(Integer, default=0, nullable=False)
    conversion_count = Column(Integer, default=0, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("slug", name="uq_landing_pages_slug"),
        Index("ix_landing_pages_tenant_status", "tenant_id", "status"),
        Index("ix_landing_pages_tenant_created", "tenant_id", "created_at"),
    )


class LandingPageVersion(Base):
    __tablename__ = "landing_page_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    landing_page_id = Column(
        String(36), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number = Column(Integer, nullable=False)
    page_schema = Column(JSONB, default=dict, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("landing_page_id", "version_number", name="uq_landing_page_versions_page_version"),
        Index("ix_landing_page_versions_page_created", "landing_page_id", "created_at"),
    )


class LandingPageEvent(Base):
    __tablename__ = "landing_page_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    landing_page_id = Column(
        String(36), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_type = Column(String(50), nullable=False, index=True)
    affiliate_ref = Column(String(50), nullable=True, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_landing_page_events_page_created", "landing_page_id", "created_at"),
        Index("ix_landing_page_events_tenant_type_created", "tenant_id", "event_type", "created_at"),
    )


class LandingPageConversation(Base):
    __tablename__ = "landing_page_conversations"

    id = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(100), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    messages = Column(JSONB, default=list, nullable=False)
    current_schema = Column(JSONB, default=dict, nullable=True)
    page_context = Column(JSONB, default=dict, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "conversation_id", name="uq_landing_page_conversations_tenant_conversation"),
        Index("ix_landing_page_conversations_tenant_updated", "tenant_id", "updated_at"),
    )


class LandingPageGeneration(Base):
    __tablename__ = "landing_page_generations"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    ai_model = Column(String(100), nullable=True)
    prompt_data = Column(JSONB, default=dict, nullable=False)
    success = Column(Boolean, default=True, nullable=False, index=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_landing_page_generations_tenant_created", "tenant_id", "created_at"),
    )


# ==================== INBOX ====================


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    channel = Column(String(20), default="email", nullable=False, index=True)
    subject = Column(String(255), nullable=True)

    is_open = Column(Boolean, default=True, nullable=False)
    is_read = Column(Boolean, default=True, nullable=False, index=True)
    message_count = Column(Integer, default=0, nullable=False)
    unread_count = Column(Integer, default=0, nullable=False)

    last_message_preview = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "contact_id", "channel", name="uq_conversations_tenant_contact_channel"),
        Index("ix_conversations_tenant_last_message", "tenant_id", "last_message_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    channel = Column(String(20), default="email", nullable=False, index=True)
    direction = Column(String(20), default="outbound", nullable=False, index=True)
    status = Column(String(30), default="sent", nullable=False, index=True)

    from_address = Column(String(255), nullable=True)
    to_address = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)

    sent_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sent_by_name = Column(String(255), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


# ==================== LISTS / CAMPAIGNS ====================


class MarketingList(Base):
    __tablename__ = "lists"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default="static", nullable=False, index=True)
    filters = Column(JSONB, nullable=True)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_lists_tenant_created", "tenant_id", "created_at"),
    )


class ListMember(Base):
    __tablename__ = "list_members"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    list_id = Column(String(36), ForeignKey("lists.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("list_id", "contact_id", name="uq_list_members_list_contact"),
        Index("ix_list_members_list", "list_id"),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    content = Column(Text, default="", nullable=False)
    campaign_type = Column(String(20), default="email", nullable=False, index=True)
    status = Column(String(20), default="draft", nullable=False, index=True)

    list_id = Column(String(36), ForeignKey("lists.id", ondelete="SET NULL"), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    open_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    bounce_count = Column(Integer, default=0, nullable=False)
    unsubscribe_count = Column(Integer, default=0, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_campaigns_tenant_status", "tenant_id", "status"),
        Index("ix_campaigns_tenant_created", "tenant_id", "created_at"),
    )


# ==================== AFFILIATES ====================


class AffiliateProgram(Base):
    __tablename__ = "affiliate_programs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    product_type = Column(String(30), default="service", nullable=False)
    journey_type = Column(String(30), default="demo_first", nullable=False)
    attribution_type = Column(String(30), default="deal", nullable=False)
    attribution_model = Column(String(30), default="first_touch", nullable=False)
    attribution_window_days = Column(Integer, default=30, nullable=False)

    commission_type = Column(String(30), default="percentage", nullable=False)
    commission_value = Column(Float, default=0.0, nullable=False)
    min_payout_threshold = Column(Float, default=50.0, nullable=False)
    cookie_duration_days = Column(Integer, default=30, nullable=False)

    pipeline_scope = Column(String(36), ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True, index=True)
    qualifying_stage_id = Column(String(36), ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True, index=True)

    auto_approve = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name_lower", name="uq_affiliate_programs_tenant_name_lower"),
        Index("ix_affiliate_programs_tenant_active", "tenant_id", "is_active"),
    )


class Affiliate(Base):
    __tablename__ = "affiliates"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)

    status = Column(String(20), default="pending", nullable=False, index=True)
    payout_method = Column(String(20), default="manual", nullable=False)
    payout_details = Column(JSONB, default=dict, nullable=False)
    notes = Column(Text, nullable=True)

    total_earnings = Column(Float, default=0.0, nullable=False)
    total_paid = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_affiliates_tenant_email"),
        Index("ix_affiliates_tenant_status", "tenant_id", "status"),
    )


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id = Column(String(36), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(String(36), ForeignKey("affiliate_programs.id", ondelete="CASCADE"), nullable=False, index=True)

    referral_code = Column(String(50), nullable=False)
    landing_page_url = Column(String(1000), nullable=True)
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)

    click_count = Column(Integer, default=0, nullable=False)
    conversion_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("referral_code", name="uq_affiliate_links_referral_code"),
        Index("ix_affiliate_links_tenant_referral", "tenant_id", "referral_code"),
        Index("ix_affiliate_links_affiliate_program", "affiliate_id", "program_id"),
    )


class AffiliateEvent(Base):
    __tablename__ = "affiliate_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    affiliate_id = Column(String(36), ForeignKey("affiliates.id", ondelete="SET NULL"), nullable=True, index=True)
    link_id = Column(String(36), ForeignKey("affiliate_links.id", ondelete="SET NULL"), nullable=True, index=True)
    program_id = Column(String(36), ForeignKey("affiliate_programs.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    commission_id = Column(String(36), ForeignKey("affiliate_commissions.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_id = Column(String(100), nullable=True, index=True)

    meta = Column("metadata", JSONB, default=dict, nullable=False)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_affiliate_events_tenant_created", "tenant_id", "created_at"),
    )


class AffiliateCommission(Base):
    __tablename__ = "affiliate_commissions"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id = Column(String(36), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(String(36), ForeignKey("affiliate_programs.id", ondelete="CASCADE"), nullable=False, index=True)

    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_id = Column(String(100), nullable=True, index=True)

    amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    notes = Column(Text, nullable=True)

    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_affiliate_commissions_tenant_status", "tenant_id", "status"),
        Index("ix_affiliate_commissions_affiliate", "affiliate_id"),
    )


class AffiliateNotification(Base):
    __tablename__ = "affiliate_notifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id = Column(String(36), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False, index=True)

    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_affiliate_notifications_affiliate_created", "affiliate_id", "created_at"),
    )


class AffiliateSetting(Base):
    __tablename__ = "affiliate_settings"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    enabled = Column(Boolean, default=True, nullable=False)
    default_currency = Column(String(10), default="USD", nullable=False)
    default_attribution_window_days = Column(Integer, default=30, nullable=False)
    approval_mode = Column(String(20), default="manual", nullable=False)
    min_payout_threshold = Column(Float, default=50.0, nullable=False)
    meta = Column("metadata", JSONB, default=dict, nullable=False)

    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_affiliate_settings_tenant"),)


class MarketingMaterial(Base):
    __tablename__ = "marketing_materials"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="other", nullable=False, index=True)
    material_type = Column(String(20), default="image", nullable=False, index=True)

    file_path = Column(String(1000), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, default=0, nullable=False)
    content_type = Column(String(255), nullable=True)
    storage_provider = Column(String(50), nullable=True)
    url = Column(String(2000), nullable=True)

    program_id = Column(String(36), ForeignKey("affiliate_programs.id", ondelete="SET NULL"), nullable=True, index=True)
    tags = Column(JSONB, default=list, nullable=False)

    download_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_marketing_materials_tenant_created", "tenant_id", "created_at"),
    )


# ==================== WORKFLOWS ====================


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    trigger_type = Column(String(50), default="form_submitted", nullable=False, index=True)
    trigger_config = Column(JSONB, default=dict, nullable=False)
    actions = Column(JSONB, default=list, nullable=False)

    total_runs = Column(Integer, default=0, nullable=False)
    successful_runs = Column(Integer, default=0, nullable=False)
    failed_runs = Column(Integer, default=0, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_workflows_tenant_status", "tenant_id", "status"),
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(20), default="pending", nullable=False, index=True)
    trigger_type = Column(String(50), nullable=True)
    trigger_data = Column(JSONB, default=dict, nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_workflow_runs_workflow_started", "workflow_id", "started_at"),
    )


class WorkflowBlueprint(Base):
    __tablename__ = "workflow_blueprints"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    stages = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_workflow_blueprints_tenant_active", "tenant_id", "is_active"),
    )


# ==================== CUSTOM OBJECTS ====================


class CustomObjectDefinition(Base):
    __tablename__ = "custom_object_definitions"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    plural_name = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="Box", nullable=False)
    color = Column(String(20), default="#6366F1", nullable=False)
    label_field = Column(String(100), default="name", nullable=False)

    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    show_in_nav = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_custom_object_definitions_tenant_slug"),
        Index("ix_custom_object_definitions_tenant_active", "tenant_id", "is_active"),
    )


class CustomObjectField(Base):
    __tablename__ = "custom_object_fields"

    id = Column(String(36), primary_key=True, default=_uuid)
    object_id = Column(
        String(36), ForeignKey("custom_object_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = Column(String(100), nullable=False)
    label = Column(String(100), nullable=False)
    field_type = Column(String(50), nullable=False)
    config = Column(JSONB, default=dict, nullable=False)

    is_required = Column(Boolean, default=False, nullable=False)
    is_unique = Column(Boolean, default=False, nullable=False)
    show_in_list = Column(Boolean, default=True, nullable=False)
    show_in_detail = Column(Boolean, default=True, nullable=False)
    is_searchable = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    placeholder = Column(String(255), nullable=True)
    help_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("object_id", "name", name="uq_custom_object_fields_object_name"),
        Index("ix_custom_object_fields_object_order", "object_id", "display_order"),
    )


class CustomObjectRecord(Base):
    __tablename__ = "custom_object_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id = Column(
        String(36), ForeignKey("custom_object_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    data = Column(JSONB, default=dict, nullable=False)
    display_label = Column(String(255), nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_custom_object_records_object_created", "object_id", "created_at"),
    )


# ==================== CRM BLUEPRINTS (WORKSPACES) ====================


class CRMBlueprint(Base):
    __tablename__ = "crm_blueprints"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    icon = Column(String(50), default="building", nullable=False)
    color = Column(String(20), default="#6366F1", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    is_system = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    config = Column(JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_crm_blueprints_tenant_slug"),
        Index("ix_crm_blueprints_tenant_default", "tenant_id", "is_default"),
    )
