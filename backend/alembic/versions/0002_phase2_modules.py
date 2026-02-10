"""phase2 modules (landing pages, inbox, campaigns, affiliates, settings, workflows, custom objects, blueprints)

Revision ID: 0002_phase2_modules
Revises: 0001_init_core
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0002_phase2_modules"
down_revision = "0001_init_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== SETTINGS / CONFIG ====================

    op.create_table(
        "workspace_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("primary_color", sa.String(length=20), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_workspace_settings_tenant"),
    )
    op.create_index("ix_workspace_settings_tenant_id", "workspace_settings", ["tenant_id"])

    op.create_table(
        "workspace_integrations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.String(length=50), nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_status", sa.String(length=30), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider_type", name="uq_workspace_integrations_tenant_provider"),
    )
    op.create_index("ix_workspace_integrations_tenant_id", "workspace_integrations", ["tenant_id"])
    op.create_index(
        "ix_workspace_integrations_tenant_provider",
        "workspace_integrations",
        ["tenant_id", "provider_type"],
        unique=False,
    )

    op.create_table(
        "ai_usage_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("default_provider", sa.String(length=50), nullable=False),
        sa.Column("default_model", sa.String(length=100), nullable=False),
        sa.Column(
            "provider_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "usage_limits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "features_enabled",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_ai_usage_configs_tenant"),
    )
    op.create_index("ix_ai_usage_configs_tenant_id", "ai_usage_configs", ["tenant_id"])

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("feature", sa.String(length=50), nullable=True),
        sa.Column("requests", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_usage_logs_tenant_id", "ai_usage_logs", ["tenant_id"])
    op.create_index("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("ix_ai_usage_logs_tenant_created", "ai_usage_logs", ["tenant_id", "created_at"])

    op.create_table(
        "settings_audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_settings_audit_logs_tenant_id", "settings_audit_logs", ["tenant_id"])
    op.create_index("ix_settings_audit_logs_actor_id", "settings_audit_logs", ["actor_id"])
    op.create_index("ix_settings_audit_logs_action", "settings_audit_logs", ["action"])
    op.create_index("ix_settings_audit_logs_provider_type", "settings_audit_logs", ["provider_type"])
    op.create_index("ix_settings_audit_tenant_created", "settings_audit_logs", ["tenant_id", "created_at"])

    # ==================== AFFILIATES / MATERIALS ====================

    op.create_table(
        "affiliate_programs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_lower", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(length=30), nullable=False),
        sa.Column("journey_type", sa.String(length=30), nullable=False),
        sa.Column("attribution_type", sa.String(length=30), nullable=False),
        sa.Column("attribution_model", sa.String(length=30), nullable=False),
        sa.Column("attribution_window_days", sa.Integer(), nullable=False),
        sa.Column("commission_type", sa.String(length=30), nullable=False),
        sa.Column("commission_value", sa.Float(), nullable=False),
        sa.Column("min_payout_threshold", sa.Float(), nullable=False),
        sa.Column("cookie_duration_days", sa.Integer(), nullable=False),
        sa.Column("pipeline_scope", sa.String(length=36), sa.ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "qualifying_stage_id",
            sa.String(length=36),
            sa.ForeignKey("pipeline_stages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("auto_approve", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name_lower", name="uq_affiliate_programs_tenant_name_lower"),
    )
    op.create_index("ix_affiliate_programs_tenant_id", "affiliate_programs", ["tenant_id"])
    op.create_index("ix_affiliate_programs_tenant_active", "affiliate_programs", ["tenant_id", "is_active"])

    op.create_table(
        "affiliates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payout_method", sa.String(length=20), nullable=False),
        sa.Column(
            "payout_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_earnings", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_paid", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_affiliates_tenant_email"),
    )
    op.create_index("ix_affiliates_tenant_id", "affiliates", ["tenant_id"])
    op.create_index("ix_affiliates_email", "affiliates", ["email"])
    op.create_index("ix_affiliates_tenant_status", "affiliates", ["tenant_id", "status"])

    op.create_table(
        "affiliate_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("default_currency", sa.String(length=10), nullable=False),
        sa.Column("default_attribution_window_days", sa.Integer(), nullable=False),
        sa.Column("approval_mode", sa.String(length=20), nullable=False),
        sa.Column("min_payout_threshold", sa.Float(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_affiliate_settings_tenant"),
    )
    op.create_index("ix_affiliate_settings_tenant_id", "affiliate_settings", ["tenant_id"])

    op.create_table(
        "marketing_materials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("material_type", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("storage_provider", sa.String(length=50), nullable=True),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_materials_tenant_id", "marketing_materials", ["tenant_id"])
    op.create_index("ix_marketing_materials_program_id", "marketing_materials", ["program_id"])
    op.create_index("ix_marketing_materials_category", "marketing_materials", ["category"])
    op.create_index("ix_marketing_materials_material_type", "marketing_materials", ["material_type"])
    op.create_index("ix_marketing_materials_is_active", "marketing_materials", ["is_active"])
    op.create_index("ix_marketing_materials_tenant_created", "marketing_materials", ["tenant_id", "created_at"])

    op.create_table(
        "affiliate_links",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "affiliate_id",
            sa.String(length=36),
            sa.ForeignKey("affiliates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("referral_code", sa.String(length=50), nullable=False),
        sa.Column("landing_page_url", sa.String(length=1000), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("conversion_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("referral_code", name="uq_affiliate_links_referral_code"),
    )
    op.create_index("ix_affiliate_links_tenant_id", "affiliate_links", ["tenant_id"])
    op.create_index("ix_affiliate_links_referral_code", "affiliate_links", ["referral_code"], unique=True)
    op.create_index("ix_affiliate_links_tenant_referral", "affiliate_links", ["tenant_id", "referral_code"])
    op.create_index("ix_affiliate_links_affiliate_program", "affiliate_links", ["affiliate_id", "program_id"])

    op.create_table(
        "affiliate_commissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "affiliate_id",
            sa.String(length=36),
            sa.ForeignKey("affiliates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payment_id", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_affiliate_commissions_tenant_id", "affiliate_commissions", ["tenant_id"])
    op.create_index("ix_affiliate_commissions_affiliate_id", "affiliate_commissions", ["affiliate_id"])
    op.create_index("ix_affiliate_commissions_program_id", "affiliate_commissions", ["program_id"])
    op.create_index("ix_affiliate_commissions_deal_id", "affiliate_commissions", ["deal_id"])
    op.create_index("ix_affiliate_commissions_payment_id", "affiliate_commissions", ["payment_id"])
    op.create_index("ix_affiliate_commissions_tenant_status", "affiliate_commissions", ["tenant_id", "status"])

    op.create_table(
        "affiliate_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("affiliate_id", sa.String(length=36), sa.ForeignKey("affiliates.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "link_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_links.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "commission_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_commissions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_affiliate_events_tenant_id", "affiliate_events", ["tenant_id"])
    op.create_index("ix_affiliate_events_event_type", "affiliate_events", ["event_type"])
    op.create_index("ix_affiliate_events_affiliate_id", "affiliate_events", ["affiliate_id"])
    op.create_index("ix_affiliate_events_link_id", "affiliate_events", ["link_id"])
    op.create_index("ix_affiliate_events_program_id", "affiliate_events", ["program_id"])
    op.create_index("ix_affiliate_events_deal_id", "affiliate_events", ["deal_id"])
    op.create_index("ix_affiliate_events_contact_id", "affiliate_events", ["contact_id"])
    op.create_index("ix_affiliate_events_commission_id", "affiliate_events", ["commission_id"])
    op.create_index("ix_affiliate_events_payment_id", "affiliate_events", ["payment_id"])
    op.create_index("ix_affiliate_events_tenant_created", "affiliate_events", ["tenant_id", "created_at"])

    op.create_table(
        "affiliate_notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "affiliate_id",
            sa.String(length=36),
            sa.ForeignKey("affiliates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_affiliate_notifications_tenant_id", "affiliate_notifications", ["tenant_id"])
    op.create_index("ix_affiliate_notifications_affiliate_id", "affiliate_notifications", ["affiliate_id"])
    op.create_index("ix_affiliate_notifications_is_read", "affiliate_notifications", ["is_read"])
    op.create_index(
        "ix_affiliate_notifications_affiliate_created",
        "affiliate_notifications",
        ["affiliate_id", "created_at"],
    )

    # ==================== LANDING PAGES ====================

    op.create_table(
        "landing_pages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("page_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "page_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "affiliate_program_id",
            sa.String(length=36),
            sa.ForeignKey("affiliate_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_model_used", sa.String(length=100), nullable=True),
        sa.Column("custom_slug", sa.String(length=255), nullable=True),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("conversion_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_landing_pages_slug"),
    )
    op.create_index("ix_landing_pages_tenant_id", "landing_pages", ["tenant_id"])
    op.create_index("ix_landing_pages_page_type", "landing_pages", ["page_type"])
    op.create_index("ix_landing_pages_status", "landing_pages", ["status"])
    op.create_index("ix_landing_pages_published_at", "landing_pages", ["published_at"])
    op.create_index("ix_landing_pages_tenant_status", "landing_pages", ["tenant_id", "status"])
    op.create_index("ix_landing_pages_tenant_created", "landing_pages", ["tenant_id", "created_at"])

    op.create_table(
        "landing_page_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "landing_page_id",
            sa.String(length=36),
            sa.ForeignKey("landing_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "page_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("landing_page_id", "version_number", name="uq_landing_page_versions_page_version"),
    )
    op.create_index("ix_landing_page_versions_page_id", "landing_page_versions", ["landing_page_id"])
    op.create_index("ix_landing_page_versions_page_created", "landing_page_versions", ["landing_page_id", "created_at"])

    op.create_table(
        "landing_page_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "landing_page_id",
            sa.String(length=36),
            sa.ForeignKey("landing_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("affiliate_ref", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_landing_page_events_tenant_id", "landing_page_events", ["tenant_id"])
    op.create_index("ix_landing_page_events_landing_page_id", "landing_page_events", ["landing_page_id"])
    op.create_index("ix_landing_page_events_event_type", "landing_page_events", ["event_type"])
    op.create_index("ix_landing_page_events_affiliate_ref", "landing_page_events", ["affiliate_ref"])
    op.create_index("ix_landing_page_events_created_at", "landing_page_events", ["created_at"])
    op.create_index("ix_landing_page_events_page_created", "landing_page_events", ["landing_page_id", "created_at"])
    op.create_index(
        "ix_landing_page_events_tenant_type_created",
        "landing_page_events",
        ["tenant_id", "event_type", "created_at"],
    )

    op.create_table(
        "landing_page_conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=100), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("current_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "conversation_id", name="uq_landing_page_conversations_tenant_conversation"),
    )
    op.create_index("ix_landing_page_conversations_tenant_id", "landing_page_conversations", ["tenant_id"])
    op.create_index("ix_landing_page_conversations_user_id", "landing_page_conversations", ["user_id"])
    op.create_index("ix_landing_page_conversations_tenant_updated", "landing_page_conversations", ["tenant_id", "updated_at"])

    op.create_table(
        "landing_page_generations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column(
            "prompt_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_landing_page_generations_tenant_id", "landing_page_generations", ["tenant_id"])
    op.create_index("ix_landing_page_generations_user_id", "landing_page_generations", ["user_id"])
    op.create_index("ix_landing_page_generations_success", "landing_page_generations", ["success"])
    op.create_index(
        "ix_landing_page_generations_tenant_created",
        "landing_page_generations",
        ["tenant_id", "created_at"],
    )

    # ==================== INBOX ====================

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_message_preview", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "contact_id", "channel", name="uq_conversations_tenant_contact_channel"),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_contact_id", "conversations", ["contact_id"])
    op.create_index("ix_conversations_channel", "conversations", ["channel"])
    op.create_index("ix_conversations_is_read", "conversations", ["is_read"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])
    op.create_index("ix_conversations_tenant_last_message", "conversations", ["tenant_id", "last_message_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("from_address", sa.String(length=255), nullable=True),
        sa.Column("to_address", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("sent_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sent_by_name", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_channel", "messages", ["channel"])
    op.create_index("ix_messages_direction", "messages", ["direction"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_messages_sent_by_user_id", "messages", ["sent_by_user_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    # ==================== LISTS / CAMPAIGNS ====================

    op.create_table(
        "lists",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lists_tenant_id", "lists", ["tenant_id"])
    op.create_index("ix_lists_type", "lists", ["type"])
    op.create_index("ix_lists_tenant_created", "lists", ["tenant_id", "created_at"])

    op.create_table(
        "list_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("list_id", sa.String(length=36), sa.ForeignKey("lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("list_id", "contact_id", name="uq_list_members_list_contact"),
    )
    op.create_index("ix_list_members_tenant_id", "list_members", ["tenant_id"])
    op.create_index("ix_list_members_list_id", "list_members", ["list_id"])
    op.create_index("ix_list_members_contact_id", "list_members", ["contact_id"])
    op.create_index("ix_list_members_list", "list_members", ["list_id"])

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("campaign_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("list_id", sa.String(length=36), sa.ForeignKey("lists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("bounce_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsubscribe_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_campaign_type", "campaigns", ["campaign_type"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_list_id", "campaigns", ["list_id"])
    op.create_index("ix_campaigns_tenant_status", "campaigns", ["tenant_id", "status"])
    op.create_index("ix_campaigns_tenant_created", "campaigns", ["tenant_id", "created_at"])

    # ==================== WORKFLOWS ====================

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column(
            "trigger_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "actions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("successful_runs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_runs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"])
    op.create_index("ix_workflows_status", "workflows", ["status"])
    op.create_index("ix_workflows_trigger_type", "workflows", ["trigger_type"])
    op.create_index("ix_workflows_tenant_status", "workflows", ["tenant_id", "status"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=True),
        sa.Column(
            "trigger_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workflow_runs_tenant_id", "workflow_runs", ["tenant_id"])
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index("ix_workflow_runs_contact_id", "workflow_runs", ["contact_id"])
    op.create_index("ix_workflow_runs_deal_id", "workflow_runs", ["deal_id"])
    op.create_index("ix_workflow_runs_workflow_started", "workflow_runs", ["workflow_id", "started_at"])

    op.create_table(
        "workflow_blueprints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "stages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_blueprints_tenant_id", "workflow_blueprints", ["tenant_id"])
    op.create_index("ix_workflow_blueprints_is_active", "workflow_blueprints", ["is_active"])
    op.create_index("ix_workflow_blueprints_tenant_active", "workflow_blueprints", ["tenant_id", "is_active"])

    # ==================== CUSTOM OBJECTS ====================

    op.create_table(
        "custom_object_definitions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("plural_name", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.Column("label_field", sa.String(length=100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_in_nav", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_custom_object_definitions_tenant_slug"),
    )
    op.create_index("ix_custom_object_definitions_tenant_id", "custom_object_definitions", ["tenant_id"])
    op.create_index("ix_custom_object_definitions_slug", "custom_object_definitions", ["slug"])
    op.create_index("ix_custom_object_definitions_is_active", "custom_object_definitions", ["is_active"])
    op.create_index(
        "ix_custom_object_definitions_tenant_active",
        "custom_object_definitions",
        ["tenant_id", "is_active"],
    )

    op.create_table(
        "custom_object_fields",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "object_id",
            sa.String(length=36),
            sa.ForeignKey("custom_object_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_unique", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("show_in_list", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_in_detail", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("placeholder", sa.String(length=255), nullable=True),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("object_id", "name", name="uq_custom_object_fields_object_name"),
    )
    op.create_index("ix_custom_object_fields_object_id", "custom_object_fields", ["object_id"])
    op.create_index("ix_custom_object_fields_name", "custom_object_fields", ["name"])
    op.create_index("ix_custom_object_fields_object_order", "custom_object_fields", ["object_id", "display_order"])

    op.create_table(
        "custom_object_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "object_id",
            sa.String(length=36),
            sa.ForeignKey("custom_object_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_custom_object_records_tenant_id", "custom_object_records", ["tenant_id"])
    op.create_index("ix_custom_object_records_object_id", "custom_object_records", ["object_id"])
    op.create_index("ix_custom_object_records_owner_id", "custom_object_records", ["owner_id"])
    op.create_index("ix_custom_object_records_object_created", "custom_object_records", ["object_id", "created_at"])

    # ==================== CRM BLUEPRINTS ====================

    op.create_table(
        "crm_blueprints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("icon", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_crm_blueprints_tenant_slug"),
    )
    op.create_index("ix_crm_blueprints_tenant_id", "crm_blueprints", ["tenant_id"])
    op.create_index("ix_crm_blueprints_slug", "crm_blueprints", ["slug"])
    op.create_index("ix_crm_blueprints_is_default", "crm_blueprints", ["is_default"])
    op.create_index("ix_crm_blueprints_is_system", "crm_blueprints", ["is_system"])
    op.create_index("ix_crm_blueprints_is_active", "crm_blueprints", ["is_active"])
    op.create_index("ix_crm_blueprints_tenant_default", "crm_blueprints", ["tenant_id", "is_default"])


def downgrade() -> None:
    # Reverse of upgrade().
    op.drop_table("crm_blueprints")
    op.drop_table("custom_object_records")
    op.drop_table("custom_object_fields")
    op.drop_table("custom_object_definitions")
    op.drop_table("workflow_blueprints")
    op.drop_table("workflow_runs")
    op.drop_table("workflows")
    op.drop_table("campaigns")
    op.drop_table("list_members")
    op.drop_table("lists")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("landing_page_generations")
    op.drop_table("landing_page_conversations")
    op.drop_table("landing_page_events")
    op.drop_table("landing_page_versions")
    op.drop_table("landing_pages")
    op.drop_table("affiliate_notifications")
    op.drop_table("affiliate_events")
    op.drop_table("affiliate_commissions")
    op.drop_table("affiliate_links")
    op.drop_table("marketing_materials")
    op.drop_table("affiliate_settings")
    op.drop_table("affiliates")
    op.drop_table("affiliate_programs")
    op.drop_table("settings_audit_logs")
    op.drop_table("ai_usage_logs")
    op.drop_table("ai_usage_configs")
    op.drop_table("workspace_integrations")
    op.drop_table("workspace_settings")
