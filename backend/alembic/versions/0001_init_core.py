"""init core tables

Revision ID: 0001_init_core
Revises: None
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_init_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_tenant_role", "users", ["tenant_id", "role"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_lower", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name_lower", name="uq_accounts_tenant_name_lower"),
    )
    op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_tenant_name_lower", "accounts", ["tenant_id", "name_lower"])

    op.create_table(
        "partners",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_lower", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name_lower", name="uq_partners_tenant_name_lower"),
    )
    op.create_index("ix_partners_tenant_id", "partners", ["tenant_id"])
    op.create_index("ix_partners_tenant_name_lower", "partners", ["tenant_id", "name_lower"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("partner_id", sa.String(length=36), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_lower", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "partner_id", "name_lower", name="uq_products_tenant_partner_name_lower"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_tenant_partner", "products", ["tenant_id", "partner_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("sales_motion_type", sa.String(length=50), nullable=False, server_default="partnership_sales"),
        sa.Column("partner_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("partner_name", sa.String(length=255), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier", sa.String(length=2), nullable=False, server_default="D"),
        sa.Column("scoring_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("touchpoints_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_touchpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_email", "leads", ["email"])
    op.create_index("ix_leads_tier", "leads", ["tier"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_tenant_owner_status", "leads", ["tenant_id", "owner_id", "status"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("lifecycle_stage", sa.String(length=50), nullable=False, server_default="lead"),
        sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lead_tier", sa.String(length=2), nullable=False, server_default="D"),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("converted_from_lead_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contacts_tenant_id", "contacts", ["tenant_id"])
    op.create_index("ix_contacts_email", "contacts", ["email"])
    op.create_index("ix_contacts_lead_tier", "contacts", ["lead_tier"])
    op.create_index("ix_contacts_tenant_owner", "contacts", ["tenant_id", "owner_id"])

    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pipelines_tenant_id", "pipelines", ["tenant_id"])
    op.create_index("ix_pipelines_tenant_order", "pipelines", ["tenant_id", "display_order"])

    op.create_table(
        "pipeline_stages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("pipeline_id", sa.String(length=36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False, server_default="#6366F1"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probability", sa.Float(), nullable=False, server_default="0"),
        sa.Column("required_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("requires_calculation_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pipeline_stages_pipeline_id", "pipeline_stages", ["pipeline_id"])
    op.create_index("ix_pipeline_stages_pipeline_order", "pipeline_stages", ["pipeline_id", "display_order"])

    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("pipeline_id", sa.String(length=36), sa.ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage_id", sa.String(length=36), sa.ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("next_step_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_step_note", sa.Text(), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lead_tier", sa.String(length=2), nullable=False, server_default="D"),
        sa.Column("sales_motion_type", sa.String(length=50), nullable=False, server_default="partnership_sales"),
        sa.Column("partner_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("partner_name", sa.String(length=255), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_won_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_lost_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_override", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("handoff_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("handoff_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deals_tenant_id", "deals", ["tenant_id"])
    op.create_index("ix_deals_status", "deals", ["status"])
    op.create_index("ix_deals_contact_id", "deals", ["contact_id"])
    op.create_index("ix_deals_pipeline_id", "deals", ["pipeline_id"])
    op.create_index("ix_deals_stage_id", "deals", ["stage_id"])
    op.create_index("ix_deals_next_step_at", "deals", ["next_step_at"])
    op.create_index("ix_deals_lead_tier", "deals", ["lead_tier"])
    op.create_index("ix_deals_sales_motion_type", "deals", ["sales_motion_type"])
    op.create_index("ix_deals_partner_id", "deals", ["partner_id"])
    op.create_index("ix_deals_product_id", "deals", ["product_id"])
    op.create_index("ix_deals_tenant_pipeline_stage", "deals", ["tenant_id", "pipeline_id", "stage_id"])
    op.create_index("ix_deals_tenant_owner", "deals", ["tenant_id", "owner_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("related_type", sa.String(length=30), nullable=True),
        sa.Column("related_id", sa.String(length=36), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_kind", "tasks", ["kind"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])
    op.create_index("ix_tasks_related_type", "tasks", ["related_type"])
    op.create_index("ix_tasks_related_id", "tasks", ["related_id"])
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.create_index("ix_tasks_tenant_status_due", "tasks", ["tenant_id", "status", "due_at"])
    op.create_index("ix_tasks_related", "tasks", ["tenant_id", "related_type", "related_id", "status"])

    op.create_table(
        "outreach_activities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False, server_default="outbound"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="completed"),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("got_response", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outreach_activities_tenant_id", "outreach_activities", ["tenant_id"])
    op.create_index("ix_outreach_activities_deal_id", "outreach_activities", ["deal_id"])
    op.create_index("ix_outreach_activities_user_id", "outreach_activities", ["user_id"])
    op.create_index("ix_outreach_activities_activity_type", "outreach_activities", ["activity_type"])
    op.create_index("ix_outreach_activities_created_at", "outreach_activities", ["created_at"])
    op.create_index("ix_outreach_tenant_deal_created", "outreach_activities", ["tenant_id", "deal_id", "created_at"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=True),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=True),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("visibility", sa.String(length=30), nullable=False, server_default="internal_only"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_timeline_events_tenant_id", "timeline_events", ["tenant_id"])
    op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
    op.create_index("ix_timeline_events_deal_id", "timeline_events", ["deal_id"])
    op.create_index("ix_timeline_events_contact_id", "timeline_events", ["contact_id"])
    op.create_index("ix_timeline_events_created_at", "timeline_events", ["created_at"])
    op.create_index("ix_timeline_tenant_created", "timeline_events", ["tenant_id", "created_at"])

    op.create_table(
        "deal_handoffs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivery_owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "deal_id", name="uq_deal_handoffs_tenant_deal"),
    )
    op.create_index("ix_deal_handoffs_tenant_id", "deal_handoffs", ["tenant_id"])
    op.create_index("ix_deal_handoffs_deal_id", "deal_handoffs", ["deal_id"])
    op.create_index("ix_deal_handoffs_status", "deal_handoffs", ["status"])

    op.create_table(
        "calculation_definitions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_calculation_definitions_tenant_id", "calculation_definitions", ["tenant_id"])
    op.create_index("ix_calculation_definitions_is_active", "calculation_definitions", ["is_active"])
    op.create_index("ix_calc_defs_tenant_active", "calculation_definitions", ["tenant_id", "is_active"])

    op.create_table(
        "calculation_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("definition_id", sa.String(length=36), sa.ForeignKey("calculation_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deal_id", "definition_id", name="uq_calc_results_deal_definition"),
    )
    op.create_index("ix_calculation_results_deal_id", "calculation_results", ["deal_id"])
    op.create_index("ix_calculation_results_definition_id", "calculation_results", ["definition_id"])


def downgrade() -> None:
    op.drop_table("calculation_results")
    op.drop_table("calculation_definitions")
    op.drop_table("deal_handoffs")
    op.drop_table("timeline_events")
    op.drop_table("outreach_activities")
    op.drop_table("tasks")
    op.drop_table("deals")
    op.drop_table("pipeline_stages")
    op.drop_table("pipelines")
    op.drop_table("contacts")
    op.drop_table("leads")
    op.drop_table("products")
    op.drop_table("partners")
    op.drop_table("accounts")
    op.drop_table("users")
    op.drop_table("tenants")
