"""audit identity-field corrections (title, authors, year, url, pdf_url) on reviewed sources

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Once a source has been decided, changing what document it points to needs an actor and a
    # reason. The trigger writes the audit row (status unchanged) with the old and new values.
    op.execute(
        """
        CREATE FUNCTION sources_identity_audit() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            who text := nullif(btrim(coalesce(current_setting('app.actor', true), '')), '');
            why text := nullif(btrim(coalesce(current_setting('app.reason', true), '')), '');
            changes text := '';
        BEGIN
            IF OLD.status = 'candidate' THEN
                RETURN NEW;
            END IF;
            IF who IS NULL OR why IS NULL THEN
                RAISE EXCEPTION 'changing title, authors, year or URL of a reviewed source needs an actor and a reason'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF NEW.title IS DISTINCT FROM OLD.title THEN
                changes := changes || format('title: %L -> %L; ', OLD.title, NEW.title);
            END IF;
            IF NEW.authors IS DISTINCT FROM OLD.authors THEN
                changes := changes || format('authors: %L -> %L; ', OLD.authors, NEW.authors);
            END IF;
            IF NEW.year IS DISTINCT FROM OLD.year THEN
                changes := changes || format('year: %L -> %L; ', OLD.year, NEW.year);
            END IF;
            IF NEW.url IS DISTINCT FROM OLD.url THEN
                changes := changes || format('url: %L -> %L; ', OLD.url, NEW.url);
            END IF;
            IF NEW.pdf_url IS DISTINCT FROM OLD.pdf_url THEN
                changes := changes || format('pdf_url: %L -> %L; ', OLD.pdf_url, NEW.pdf_url);
            END IF;
            IF changes <> '' THEN
                INSERT INTO source_audit (source_id, actor, from_status, to_status, reason)
                VALUES (NEW.source_id, who, OLD.status, NEW.status,
                        'Details corrected: ' || changes || 'Reason: ' || why);
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        """CREATE TRIGGER sources_identity_audit_trg
           BEFORE UPDATE OF title, authors, year, url, pdf_url ON sources
           FOR EACH ROW
           WHEN (OLD.title IS DISTINCT FROM NEW.title OR OLD.authors IS DISTINCT FROM NEW.authors
                 OR OLD.year IS DISTINCT FROM NEW.year OR OLD.url IS DISTINCT FROM NEW.url
                 OR OLD.pdf_url IS DISTINCT FROM NEW.pdf_url)
           EXECUTE FUNCTION sources_identity_audit()"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS sources_identity_audit_trg ON sources")
    op.execute("DROP FUNCTION IF EXISTS sources_identity_audit()")
