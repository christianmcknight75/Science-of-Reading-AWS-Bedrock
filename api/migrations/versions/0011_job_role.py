"""what job the requester does (free text, e.g. "Reading coach"); not an authorization role

`users.role` (teacher | admin) decides what a person may do. `job_role` is only information for
the administrator who reviews the request.

Revision ID: 0011
Revises: 0010
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE access_requests ADD COLUMN job_role text CHECK (length(job_role) <= 60)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE access_requests DROP COLUMN job_role")
