"""elev8 matrix core enforcement fields

Revision ID: 0005_elev8_core
Revises: 0004_demos_spiced_slas
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005_elev8_core"
down_revision = "0004_demos_spiced_slas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Accounts: domain-level dedupe + ICP metadata
    op.add_column("accounts", sa.Column("domain_lower", sa.String(length=255), nullable=True))
    op.add_column("accounts", sa.Column("industry", sa.String(length=100), nullable=True))
    op.add_column("accounts", sa.Column("company_size", sa.String(length=100), nullable=True))
    op.add_column("accounts", sa.Column("country", sa.String(length=100), nullable=True))
    op.add_column("accounts", sa.Column("icp_tier", sa.String(length=2), nullable=True))
    op.create_index("ix_accounts_icp_tier", "accounts", ["icp_tier"])

    # Normalize any existing domain values before enforcing uniqueness.
    op.execute(
        """
        UPDATE accounts
        SET domain_lower = NULLIF(lower(trim(domain)), '')
        WHERE domain_lower IS NULL
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, domain_lower
                    ORDER BY created_at ASC, id ASC
                ) AS rn
            FROM accounts
            WHERE domain_lower IS NOT NULL
        )
        UPDATE accounts a
        SET domain_lower = NULL
        FROM ranked r
        WHERE a.id = r.id AND r.rn > 1
        """
    )
    op.create_unique_constraint("uq_accounts_tenant_domain_lower", "accounts", ["tenant_id", "domain_lower"])
    op.create_index("ix_accounts_tenant_domain_lower", "accounts", ["tenant_id", "domain_lower"])

    # Leads: stricter qualification metadata + partner-sales fields
    op.add_column("leads", sa.Column("country_region", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("client_name", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("partner_commission_structure", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("product_category", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("disqualification_reason", sa.String(length=255), nullable=True))

    # Contacts: explicit buying role attributes
    op.add_column("contacts", sa.Column("job_title", sa.String(length=255), nullable=True))
    op.add_column("contacts", sa.Column("buying_role", sa.String(length=50), nullable=True))

    # Deals: lead-first lineage + sales enforcement payload
    op.add_column("deals", sa.Column("origin_lead_id", sa.String(length=36), nullable=True))
    op.create_index("ix_deals_origin_lead_id", "deals", ["origin_lead_id"])
    op.add_column("deals", sa.Column("estimated_close_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("product_service_type", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("client_name", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("partner_commission_structure", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("product_category", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("proposal_value", sa.Float(), nullable=True))
    op.add_column("deals", sa.Column("commercial_summary_url", sa.String(length=1000), nullable=True))
    op.add_column(
        "deals",
        sa.Column(
            "stakeholder_map",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("deals", sa.Column("contract_final_value", sa.Float(), nullable=True))
    op.add_column("deals", sa.Column("payment_terms", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("deal_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("deals", sa.Column("at_risk", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_deals_at_risk", "deals", ["at_risk"])


def downgrade() -> None:
    op.drop_index("ix_deals_at_risk", table_name="deals")
    op.drop_column("deals", "at_risk")
    op.drop_column("deals", "deal_locked")
    op.drop_column("deals", "payment_terms")
    op.drop_column("deals", "contract_final_value")
    op.drop_column("deals", "stakeholder_map")
    op.drop_column("deals", "commercial_summary_url")
    op.drop_column("deals", "proposal_value")
    op.drop_column("deals", "product_category")
    op.drop_column("deals", "partner_commission_structure")
    op.drop_column("deals", "client_name")
    op.drop_column("deals", "product_service_type")
    op.drop_column("deals", "estimated_close_date")
    op.drop_index("ix_deals_origin_lead_id", table_name="deals")
    op.drop_column("deals", "origin_lead_id")

    op.drop_column("contacts", "buying_role")
    op.drop_column("contacts", "job_title")

    op.drop_column("leads", "disqualification_reason")
    op.drop_column("leads", "product_category")
    op.drop_column("leads", "partner_commission_structure")
    op.drop_column("leads", "client_name")
    op.drop_column("leads", "country_region")

    op.drop_index("ix_accounts_tenant_domain_lower", table_name="accounts")
    op.drop_constraint("uq_accounts_tenant_domain_lower", "accounts", type_="unique")
    op.drop_index("ix_accounts_icp_tier", table_name="accounts")
    op.drop_column("accounts", "icp_tier")
    op.drop_column("accounts", "country")
    op.drop_column("accounts", "company_size")
    op.drop_column("accounts", "industry")
    op.drop_column("accounts", "domain_lower")
