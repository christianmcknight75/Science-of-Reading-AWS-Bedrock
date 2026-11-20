"""passages keep the page range they cover and, for per-grade documents, the grade

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

VIEW = """
CREATE VIEW retrievable_passages AS
SELECT p.*, s.source_type, s.evidence_role, s.jurisdiction, s.year, s.title AS source_title
FROM passages p JOIN sources s USING (source_id)
WHERE s.status = 'approved'
  AND coalesce(s.curation_status, 'ready') NOT IN ('permission', 'quote_only')
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute("ALTER TABLE passages ADD COLUMN page_end integer, ADD COLUMN grade text")
    op.execute("UPDATE passages SET page_end = page")
    op.execute(
        "ALTER TABLE passages ADD CONSTRAINT passages_page_range_check "
        "CHECK (page_end IS NULL OR page IS NULL OR page_end >= page)"
    )
    op.execute(VIEW)  # p.* now includes page_end and grade


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute("ALTER TABLE passages DROP COLUMN page_end, DROP COLUMN grade")
    op.execute(VIEW)
