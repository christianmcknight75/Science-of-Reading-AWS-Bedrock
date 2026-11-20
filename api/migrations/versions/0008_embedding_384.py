"""embeddings are 384 dims (local BAAI/bge-small-en-v1.5); no Bedrock embedding model is approved

Existing embeddings (stub, 1024 dims) are cleared: re-run `sor-ingest process --embedder local --all`.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

COLUMNS = (
    "passage_id, source_id, section, page, page_end, page_label, page_end_label, grade, text, "
    "embedding, tsv, version, recommendation"
)


def _view() -> None:
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


def _retype(dims: int) -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute("DROP INDEX IF EXISTS passages_embedding_idx")
    op.execute("UPDATE passages SET embedding = NULL")
    op.execute(f"ALTER TABLE passages ALTER COLUMN embedding TYPE vector({dims})")
    op.execute(
        "CREATE INDEX passages_embedding_idx ON passages USING hnsw (embedding vector_cosine_ops)"
    )
    _view()


def upgrade() -> None:
    _retype(384)


def downgrade() -> None:
    _retype(1024)
