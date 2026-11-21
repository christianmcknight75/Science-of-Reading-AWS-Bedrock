"""curated source metadata: jurisdiction, priority, intended uses, curation status

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sources DROP CONSTRAINT sources_source_type_check")
    op.execute(
        """ALTER TABLE sources ADD CONSTRAINT sources_source_type_check CHECK (source_type IN
           ('practice_guide','meta_analysis','study','foundational','government_guide'))"""
    )
    op.execute(
        """
        ALTER TABLE sources
            ADD COLUMN curated_id              text UNIQUE,
            ADD COLUMN publisher               text,
            ADD COLUMN jurisdiction            text,          -- US | UK | AU ... lets answers say "UK government guidance"
            ADD COLUMN priority                integer,
            ADD COLUMN used_for                text[] NOT NULL DEFAULT '{}',
            ADD COLUMN foundational_allow_list boolean NOT NULL DEFAULT false,
            ADD COLUMN curation_status         text
                CHECK (curation_status IN ('ready','verify','permission','quote_only')),
            ADD COLUMN curation_note           text
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sources
            DROP COLUMN curated_id, DROP COLUMN publisher, DROP COLUMN jurisdiction,
            DROP COLUMN priority, DROP COLUMN used_for, DROP COLUMN foundational_allow_list,
            DROP COLUMN curation_status, DROP COLUMN curation_note
        """
    )
    op.execute("ALTER TABLE sources DROP CONSTRAINT sources_source_type_check")
    op.execute(
        """ALTER TABLE sources ADD CONSTRAINT sources_source_type_check CHECK (source_type IN
           ('practice_guide','meta_analysis','study','foundational'))"""
    )
