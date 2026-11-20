"""printed page labels on passages; evidence ratings are only usable once a person verified them

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

COLUMNS = (
    "passage_id, source_id, section, page, page_end, page_label, page_end_label, grade, text, "
    "embedding, tsv, version, recommendation"
)


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute(
        """
        ALTER TABLE passages ADD COLUMN page_label text, ADD COLUMN page_end_label text;
        UPDATE passages SET page_label = page::text, page_end_label = page_end::text;
        ALTER TABLE sources
            ADD COLUMN ratings_verified_by   text,
            ADD COLUMN ratings_verified_at   timestamptz,
            ADD COLUMN ratings_verified_note text,
            ADD COLUMN ratings_signature     text,
            ADD CONSTRAINT ratings_verified_together
                CHECK ((ratings_verified_by IS NULL) = (ratings_verified_at IS NULL))
        """
    )
    # `page` stays the PDF page number; `page_label` is what is printed on the page (what a
    # teacher looks up). A WWC rating is shown only for a source whose ratings were verified.
    op.execute(
        f"""
        CREATE VIEW retrievable_passages AS
        SELECT {", ".join("p." + c.strip() for c in COLUMNS.split(","))},
               CASE WHEN s.ratings_verified_at IS NOT NULL THEN p.evidence_rating END
                 AS evidence_rating,
               s.source_type, s.evidence_role, s.jurisdiction, s.year, s.title AS source_title
        FROM passages p JOIN sources s USING (source_id)
        WHERE s.status = 'approved'
          AND coalesce(s.curation_status, 'ready') NOT IN ('permission', 'quote_only')
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute(
        """
        ALTER TABLE sources DROP CONSTRAINT ratings_verified_together,
            DROP COLUMN ratings_verified_by, DROP COLUMN ratings_verified_at,
            DROP COLUMN ratings_verified_note, DROP COLUMN ratings_signature;
        ALTER TABLE passages DROP COLUMN page_label, DROP COLUMN page_end_label
        """
    )
    op.execute(
        """
        CREATE VIEW retrievable_passages AS
        SELECT p.*, s.source_type, s.evidence_role, s.jurisdiction, s.year, s.title AS source_title
        FROM passages p JOIN sources s USING (source_id)
        WHERE s.status = 'approved'
          AND coalesce(s.curation_status, 'ready') NOT IN ('permission', 'quote_only')
        """
    )
