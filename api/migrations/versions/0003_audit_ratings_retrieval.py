"""audit log for status changes, evidence ratings on passages, retrieval view

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source_audit (
            id          bigserial PRIMARY KEY,
            ts          timestamptz NOT NULL DEFAULT now(),
            source_id   text NOT NULL,
            actor       text NOT NULL,
            from_status text,
            to_status   text NOT NULL,
            reason      text NOT NULL CHECK (length(btrim(reason)) > 0)
        )
        """
    )
    op.execute("CREATE INDEX source_audit_source_idx ON source_audit (source_id, ts)")

    # Status can only change when an actor and a reason are set for the transaction
    # (SELECT set_config('app.actor', ..., true), set_config('app.reason', ..., true)).
    # The trigger writes the audit row itself, so no change can skip the log.
    op.execute(
        """
        CREATE FUNCTION sources_status_audit() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            who text := nullif(btrim(coalesce(current_setting('app.actor', true), '')), '');
            why text := nullif(btrim(coalesce(current_setting('app.reason', true), '')), '');
        BEGIN
            IF TG_OP = 'INSERT' AND NEW.status = 'candidate' THEN
                RETURN NEW;                      -- new candidates need no decision
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.status = OLD.status THEN
                RETURN NEW;
            END IF;
            IF who IS NULL OR why IS NULL THEN
                RAISE EXCEPTION 'source status changes need an actor and a reason (use the admin API)'
                    USING ERRCODE = 'check_violation';
            END IF;
            INSERT INTO source_audit (source_id, actor, from_status, to_status, reason)
            VALUES (NEW.source_id, who, CASE WHEN TG_OP = 'UPDATE' THEN OLD.status END,
                    NEW.status, why);
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        """CREATE TRIGGER sources_status_audit_trg
           BEFORE INSERT OR UPDATE OF status ON sources
           FOR EACH ROW EXECUTE FUNCTION sources_status_audit()"""
    )

    # Evidence: how much weight a source carries toward the answer label.
    op.execute(
        """ALTER TABLE sources ADD COLUMN evidence_role text NOT NULL DEFAULT 'primary'
           CHECK (evidence_role IN ('primary','summary'))"""
    )
    op.execute(
        "UPDATE sources SET evidence_role = 'summary' WHERE source_type = 'government_guide'"
    )
    op.execute(
        """
        ALTER TABLE passages
            ADD COLUMN recommendation  text,
            ADD COLUMN evidence_rating text CHECK (evidence_rating IN ('Strong','Moderate','Minimal'))
        """
    )

    # The ONLY thing retrieval may read: approved, and not waiting on a license/permission decision.
    op.execute(
        """
        CREATE VIEW retrievable_passages AS
        SELECT p.*, s.source_type, s.evidence_role, s.jurisdiction, s.year, s.title AS source_title
        FROM passages p JOIN sources s USING (source_id)
        WHERE s.status = 'approved'
          AND coalesce(s.curation_status, 'ready') NOT IN ('permission', 'quote_only')
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS retrievable_passages")
    op.execute("ALTER TABLE passages DROP COLUMN recommendation, DROP COLUMN evidence_rating")
    op.execute("ALTER TABLE sources DROP COLUMN evidence_role")
    op.execute("DROP TRIGGER IF EXISTS sources_status_audit_trg ON sources")
    op.execute("DROP FUNCTION IF EXISTS sources_status_audit()")
    op.execute("DROP TABLE IF EXISTS source_audit")
