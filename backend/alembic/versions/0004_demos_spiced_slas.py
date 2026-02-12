"""demos v1 + spiced + sla tracking

Revision ID: 0004_demos_spiced_slas
Revises: 0003_partner_pipeline_config
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0004_demos_spiced_slas"
down_revision = "0003_partner_pipeline_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Leads: speed-to-lead tracking
    op.add_column("leads", sa.Column("first_touchpoint_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_leads_first_touchpoint_at", "leads", ["first_touchpoint_at"])

    # Deals: cadence tracking + discovery/demo capture
    op.add_column("deals", sa.Column("last_touchpoint_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_deals_last_touchpoint_at", "deals", ["last_touchpoint_at"])

    op.add_column(
        "deals",
        sa.Column(
            "spiced",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    op.add_column("deals", sa.Column("demo_title", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("demo_type", sa.String(length=50), nullable=True))
    op.add_column("deals", sa.Column("demo_status", sa.String(length=30), nullable=True))
    op.create_index("ix_deals_demo_status", "deals", ["demo_status"])

    op.add_column("deals", sa.Column("demo_scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_deals_demo_scheduled_at", "deals", ["demo_scheduled_at"])

    op.add_column(
        "deals",
        sa.Column("demo_duration_minutes", sa.Integer(), server_default=sa.text("30"), nullable=False),
    )
    op.add_column("deals", sa.Column("demo_meet_url", sa.String(length=500), nullable=True))
    op.add_column("deals", sa.Column("demo_calendar_url", sa.String(length=1000), nullable=True))
    op.add_column("deals", sa.Column("demo_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("demo_notes", sa.Text(), nullable=True))

    # Workspace: SLA config (defaults + future per-source overrides)
    op.add_column(
        "workspace_settings",
        sa.Column(
            "sla_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(
                '\'{"speed_to_lead_minutes": 15, "lead_cadence_hours": 24, "deal_cadence_hours": 72}\'::jsonb'
            ),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("workspace_settings", "sla_config")

    op.drop_column("deals", "demo_notes")
    op.drop_column("deals", "demo_completed_at")
    op.drop_column("deals", "demo_calendar_url")
    op.drop_column("deals", "demo_meet_url")
    op.drop_column("deals", "demo_duration_minutes")
    op.drop_index("ix_deals_demo_scheduled_at", table_name="deals")
    op.drop_column("deals", "demo_scheduled_at")
    op.drop_index("ix_deals_demo_status", table_name="deals")
    op.drop_column("deals", "demo_status")
    op.drop_column("deals", "demo_type")
    op.drop_column("deals", "demo_title")
    op.drop_column("deals", "spiced")
    op.drop_index("ix_deals_last_touchpoint_at", table_name="deals")
    op.drop_column("deals", "last_touchpoint_at")

    op.drop_index("ix_leads_first_touchpoint_at", table_name="leads")
    op.drop_column("leads", "first_touchpoint_at")

