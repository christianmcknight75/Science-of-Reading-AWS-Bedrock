"""knowledge layer: sources, passages, standards, myths, grapheme_scope, query_log

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # A source enters the corpus only when status = 'approved' AND the license checklist is complete.
    op.execute(
        """
        CREATE TABLE sources (
            source_id            text PRIMARY KEY,           -- e.g. src_0001
            title                text NOT NULL,
            authors              text[] NOT NULL DEFAULT '{}',
            year                 integer,
            doi                  text,
            eric_id              text,
            url                  text,
            pdf_url              text,
            license              text,
            license_snapshot_url text,
            attribution          text,
            source_type          text NOT NULL DEFAULT 'study'
                CHECK (source_type IN ('practice_guide','meta_analysis','study','foundational')),
            topics               text[] NOT NULL DEFAULT '{}',
            grades               text[] NOT NULL DEFAULT '{}',
            status               text NOT NULL DEFAULT 'candidate'
                CHECK (status IN ('candidate','approved','rejected')),
            license_checklist    jsonb,                       -- answers to the license checklist form
            reviewer_notes       text,
            approved_by          text,
            approved_at          timestamptz,
            version              integer NOT NULL DEFAULT 1,
            discovered_from      text,                        -- eric | openalex | allowlist
            created_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT approved_needs_record CHECK (
                status <> 'approved' OR (
                    approved_by IS NOT NULL AND approved_at IS NOT NULL
                    AND license IS NOT NULL AND attribution IS NOT NULL
                    AND license_snapshot_url IS NOT NULL AND license_checklist IS NOT NULL
                )
            )
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX sources_doi_key ON sources (lower(doi)) WHERE doi IS NOT NULL")
    op.execute(
        "CREATE UNIQUE INDEX sources_eric_key ON sources (eric_id) WHERE eric_id IS NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE passages (
            passage_id text PRIMARY KEY,                      -- src_0001_p012
            source_id  text NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
            section    text,
            page       integer,
            text       text NOT NULL,
            embedding  vector(1024),
            tsv        tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
            version    integer NOT NULL DEFAULT 1
        )
        """
    )
    op.execute("CREATE INDEX passages_source_idx ON passages (source_id)")
    op.execute("CREATE INDEX passages_tsv_idx ON passages USING gin (tsv)")
    op.execute(
        "CREATE INDEX passages_embedding_idx ON passages USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute(
        """
        CREATE TABLE standards (
            standard_id text PRIMARY KEY,                     -- MS_ELA_RF_K_2
            state       text NOT NULL,
            grade       text NOT NULL,
            domain      text NOT NULL,
            description text NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE myths (
            myth_id        text PRIMARY KEY,
            name           text NOT NULL,
            cue_patterns   text[] NOT NULL DEFAULT '{}',
            sor_correction text NOT NULL,
            passage_ids    text[] NOT NULL DEFAULT '{}'       -- filled once the corpus exists
        )
        """
    )
    op.execute(
        """
        CREATE TABLE grapheme_scope (
            position  integer PRIMARY KEY,
            grapheme  text NOT NULL,
            phonemes  text[] NOT NULL,
            grade     text,
            note      text
        )
        """
    )
    op.execute(
        """
        CREATE TABLE query_log (
            id                 bigserial PRIMARY KEY,
            ts                 timestamptz NOT NULL DEFAULT now(),
            feature            text NOT NULL,
            redacted_question  text NOT NULL,                  -- PII-stripped text only
            passage_ids        text[] NOT NULL DEFAULT '{}',
            answer             text,
            evidence_label     text,
            latency_ms         integer,
            verifier_result    jsonb,
            feedback           text
        )
        """
    )


def downgrade() -> None:
    for t in ("query_log", "grapheme_scope", "myths", "standards", "passages", "sources"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
