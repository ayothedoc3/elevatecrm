"""partner pipeline config (default pipeline per partner)

Revision ID: 0003_partner_pipeline_config
Revises: 0002_phase2_modules
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_partner_pipeline_config"
down_revision = "0002_phase2_modules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("partners", sa.Column("default_pipeline_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_partners_default_pipeline_id_pipelines",
        "partners",
        "pipelines",
        ["default_pipeline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_partners_default_pipeline_id", "partners", ["default_pipeline_id"])


def downgrade() -> None:
    op.drop_index("ix_partners_default_pipeline_id", table_name="partners")
    op.drop_constraint("fk_partners_default_pipeline_id_pipelines", "partners", type_="foreignkey")
    op.drop_column("partners", "default_pipeline_id")

