"""deal contacts junction + enforcement gap support

Revision ID: 0006_deal_contacts_and_enforcement_gaps
Revises: 0005_elev8_matrix_core_enforcement
Create Date: 2026-03-06
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_deal_contacts_and_enforcement_gaps"
down_revision = "0005_elev8_matrix_core_enforcement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("deal_id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "deal_id", "contact_id", name="uq_deal_contacts_tenant_deal_contact"),
    )
    op.create_index("ix_deal_contacts_tenant_id", "deal_contacts", ["tenant_id"])
    op.create_index("ix_deal_contacts_deal_id", "deal_contacts", ["deal_id"])
    op.create_index("ix_deal_contacts_contact_id", "deal_contacts", ["contact_id"])
    op.create_index("ix_deal_contacts_is_primary", "deal_contacts", ["is_primary"])
    op.create_index("ix_deal_contacts_tenant_deal", "deal_contacts", ["tenant_id", "deal_id"])
    op.create_index("ix_deal_contacts_contact", "deal_contacts", ["tenant_id", "contact_id"])

    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    rows = bind.execute(
        sa.text(
            """
            SELECT id, tenant_id, contact_id
            FROM deals
            WHERE contact_id IS NOT NULL
            """
        )
    ).fetchall()

    for row in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO deal_contacts (
                    id, tenant_id, deal_id, contact_id, is_primary, role, created_by, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :deal_id, :contact_id, true, NULL, NULL, :created_at, :updated_at
                )
                ON CONFLICT (tenant_id, deal_id, contact_id)
                DO UPDATE SET is_primary = EXCLUDED.is_primary, updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": row.tenant_id,
                "deal_id": row.id,
                "contact_id": row.contact_id,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_deal_contacts_contact", table_name="deal_contacts")
    op.drop_index("ix_deal_contacts_tenant_deal", table_name="deal_contacts")
    op.drop_index("ix_deal_contacts_is_primary", table_name="deal_contacts")
    op.drop_index("ix_deal_contacts_contact_id", table_name="deal_contacts")
    op.drop_index("ix_deal_contacts_deal_id", table_name="deal_contacts")
    op.drop_index("ix_deal_contacts_tenant_id", table_name="deal_contacts")
    op.drop_table("deal_contacts")
