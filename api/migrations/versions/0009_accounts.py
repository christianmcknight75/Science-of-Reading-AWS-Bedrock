"""closed-access accounts: users, access requests, an audit log, and revoked tokens

Invite-only: there is no public sign-up. A person asks for access (access_requests), an admin
approves or denies it, and approval creates the user. Every status change of a request is logged
in access_audit by a database trigger, like source_audit.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            user_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name              text NOT NULL CHECK (length(btrim(name)) > 0),
            email             text NOT NULL CHECK (email = lower(email)),
            district          text NOT NULL,
            role              text NOT NULL CHECK (role IN ('teacher', 'admin')),
            status            text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
            password_hash     text,                -- scrypt; never the password. NULL until the invite is accepted
            invite_hash       text,                -- sha256 of the one-time invite code
            invite_expires_at timestamptz,
            cognito_sub       text UNIQUE,         -- filled in when Cognito takes over (Phase 5)
            created_at        timestamptz NOT NULL DEFAULT now(),
            last_sign_in_at   timestamptz
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX users_email_idx ON users (email)")
    op.execute(
        """
        CREATE TABLE access_requests (
            request_id      bigserial PRIMARY KEY,
            name            text NOT NULL CHECK (length(btrim(name)) > 0),
            email           text NOT NULL CHECK (email = lower(email)),
            district        text NOT NULL,
            status          text NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'approved', 'denied')),
            requested_at    timestamptz NOT NULL DEFAULT now(),
            decided_by      text,
            decided_at      timestamptz,
            decision_reason text,
            CHECK ((status = 'pending') = (decided_by IS NULL))
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX access_requests_one_pending ON access_requests (email) "
        "WHERE status = 'pending'"
    )
    op.execute(
        """
        CREATE TABLE access_audit (
            id          bigserial PRIMARY KEY,
            ts          timestamptz NOT NULL DEFAULT now(),
            request_id  bigint NOT NULL REFERENCES access_requests (request_id),
            actor       text NOT NULL,
            from_status text,
            to_status   text NOT NULL,
            reason      text NOT NULL CHECK (length(btrim(reason)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE FUNCTION access_requests_audit() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            who text := nullif(btrim(coalesce(current_setting('app.actor', true), '')), '');
            why text := nullif(btrim(coalesce(current_setting('app.reason', true), '')), '');
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.status <> 'pending' THEN
                    RAISE EXCEPTION 'access requests start as pending'
                        USING ERRCODE = 'check_violation';
                END IF;
                INSERT INTO access_audit (request_id, actor, from_status, to_status, reason)
                VALUES (NEW.request_id, 'requester', NULL, 'pending', 'Access requested');
                RETURN NEW;
            END IF;
            IF NEW.status = OLD.status THEN
                RETURN NEW;
            END IF;
            IF who IS NULL OR why IS NULL THEN
                RAISE EXCEPTION 'access request status changes need an actor and a reason'
                    USING ERRCODE = 'check_violation';
            END IF;
            INSERT INTO access_audit (request_id, actor, from_status, to_status, reason)
            VALUES (NEW.request_id, who, OLD.status, NEW.status, why);
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        """CREATE TRIGGER access_requests_audit_trg
           AFTER INSERT OR UPDATE OF status ON access_requests
           FOR EACH ROW EXECUTE FUNCTION access_requests_audit()"""
    )
    op.execute(
        """
        CREATE TABLE revoked_tokens (
            jti        text PRIMARY KEY,
            expires_at timestamptz NOT NULL
        )
        """
    )


def downgrade() -> None:
    for t in ("revoked_tokens", "access_audit", "access_requests", "users"):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    op.execute("DROP FUNCTION IF EXISTS access_requests_audit()")
