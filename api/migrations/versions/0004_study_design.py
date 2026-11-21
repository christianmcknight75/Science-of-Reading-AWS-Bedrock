"""study design facts used by the evidence label (randomized, sample size, comparison group)

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sources
            ADD COLUMN randomized           boolean,
            ADD COLUMN sample_size          integer CHECK (sample_size IS NULL OR sample_size > 0),
            ADD COLUMN has_comparison_group boolean
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE sources DROP COLUMN randomized, DROP COLUMN sample_size, "
        "DROP COLUMN has_comparison_group"
    )
