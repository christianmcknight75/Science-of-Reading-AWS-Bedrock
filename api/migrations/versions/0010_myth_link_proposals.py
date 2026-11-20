"""draft links from myths to passages, for SME review (never shown to teachers)

`myths.passage_ids` is what the engine shows. A proposal changes nothing there until a named
reviewer approves it (app/myth_links.py), so a draft can never reach a teacher.

Revision ID: 0010
Revises: 0009
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE myth_link_proposals (
            proposal_id  bigserial PRIMARY KEY,
            myth_id      text NOT NULL REFERENCES myths (myth_id),
            passage_id   text NOT NULL REFERENCES passages (passage_id),
            status       text NOT NULL DEFAULT 'proposed'
                         CHECK (status IN ('proposed', 'approved', 'rejected')),
            relation     text NOT NULL
                         CHECK (relation IN ('refutes', 'partly', 'supports_alternative')),
            quote        text NOT NULL,        -- exact words in the passage that matter
            rationale    text NOT NULL,        -- why it was proposed, and its limits
            proposed_by  text NOT NULL,
            proposed_at  timestamptz NOT NULL DEFAULT now(),
            reviewed_by  text,
            reviewed_at  timestamptz,
            review_note  text,
            UNIQUE (myth_id, passage_id),
            CHECK ((status = 'proposed') = (reviewed_by IS NULL))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS myth_link_proposals")
