"""Closed-access accounts (docs/API_CONTRACT.md, "Accounts").

Invite-only: nobody can sign up. A person asks for access, an admin approves it, and approval
creates the user with a one-time invite code. Passwords are stored only as scrypt hashes. In
Phase 5, Cognito replaces sign-in, accept-invite and sign-out; request/approve/deny/me stay.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from . import auth
from .auth import current_user
from .config import Settings, get_settings
from .db import get_conn
from .ratelimit import FailureLimiter, RateLimiter

router = APIRouter()
Conn = Annotated[psycopg.Connection[dict[str, Any]], Depends(get_conn)]
Cfg = Annotated[Settings, Depends(get_settings)]
Admin = Annotated[str, Depends(auth.require_admin)]

INVITE_HOURS = 24
MIN_PASSWORD = 12
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 1
BAD_LOGIN = "That email and password do not match."
BAD_INVITE = "That invite is not valid or has expired."


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=2**26, dklen=32
    )
    b64 = base64.b64encode
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt).decode()}${b64(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt_b64),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=2**26,
            dklen=32,
        )
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


@lru_cache
def _dummy_hash() -> str:
    """Checked when the email is unknown, so a miss takes as long as a wrong password."""
    return hash_password("not-a-real-password")


def _invite_digest(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _norm_email(v: str) -> str:
    e = v.strip().lower()
    if len(e) > 254 or not _EMAIL.match(e):
        raise ValueError("enter a valid email")
    return e


# ------------------------------------------------------------------ limiters (in memory)
@lru_cache
def _sign_in_limiter(max_failures: int, window_s: float) -> FailureLimiter:
    return FailureLimiter(max_failures, window_s)


@lru_cache
def _request_limiter(per_hour: int) -> RateLimiter:
    return RateLimiter(per_hour, 3600.0)


def reset_limiters() -> None:
    _sign_in_limiter.cache_clear()
    _request_limiter.cache_clear()


def _ip(request: Request) -> str:
    # Behind App Runner this is the load balancer unless X-Forwarded-For is trusted (Phase 5).
    return request.client.host if request.client else "unknown"


# ------------------------------------------------------------------ models
class Me(BaseModel):
    user_id: str
    name: str
    email: str
    district: str
    role: Literal["teacher", "admin"]
    status: Literal["active", "disabled"]


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105
    expires_in: int
    user: Me


class RequestAccess(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    district: str = Field(min_length=1, max_length=120)
    job_role: str | None = Field(default=None, max_length=60)  # e.g. "Reading coach"; info only

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _norm_email(v)

    @field_validator("job_role")
    @classmethod
    def _job(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None

    @field_validator("name", "district")
    @classmethod
    def _trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("required")
        return v


class AccessRequestOut(BaseModel):
    request_id: int
    name: str
    email: str
    district: str
    job_role: str | None = None
    status: str
    requested_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    decision_reason: str | None


class Approve(BaseModel):
    role: Literal["teacher", "admin"] = "teacher"
    reason: str = Field(default="Approved", min_length=1, max_length=500)


class Deny(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class Invite(BaseModel):
    user_id: str
    invite_code: str
    expires_at: datetime


class AcceptInvite(BaseModel):
    email: str
    invite_code: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=MIN_PASSWORD, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _norm_email(v)


class SignIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


def _me(row: dict[str, Any]) -> Me:
    return Me.model_validate({k: str(row[k]) for k in Me.model_fields})


def _local_only(s: Settings) -> None:
    """Sign-in, accept-invite and sign-out are the local dev issuer's. Cognito replaces them."""
    if s.auth_mode != "local":
        raise HTTPException(404, "Sign in with your school account.")


def _token_for(s: Settings, user: dict[str, Any]) -> TokenOut:
    now = int(time.time())
    ttl = s.auth_token_minutes * 60
    claims = {
        "iss": auth.issuer(s),
        "sub": str(user["user_id"]),
        "username": user["email"],
        "client_id": auth.client_id(s),
        "token_use": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + ttl,
        "cognito:groups": ["admin"] if user["role"] == "admin" else ["teacher"],
    }
    return TokenOut(access_token=auth.local_issuer(s).sign(claims), expires_in=ttl, user=_me(user))


def _guard_sign_in(s: Settings, request: Request, email: str) -> tuple[FailureLimiter, list[str]]:
    lim = _sign_in_limiter(s.sign_in_max_failures, s.sign_in_window_minutes * 60.0)
    keys = [f"email:{email}", f"ip:{_ip(request)}"]
    if any(lim.blocked(k) for k in keys):
        raise HTTPException(
            429,
            f"Too many sign-in attempts. Please try again in {s.sign_in_window_minutes} minutes.",
        )
    return lim, keys


# ------------------------------------------------------------------ public endpoints
@router.post("/api/auth/request-access", status_code=202)
def request_access(body: RequestAccess, request: Request, s: Cfg, conn: Conn) -> dict[str, str]:
    """Same answer whether or not the email is known, so it cannot reveal who has an account."""
    if not _request_limiter(s.request_access_per_hour).allow(_ip(request)):
        raise HTTPException(429, "Too many requests from this device. Please try again later.")
    known = conn.execute(
        """SELECT 1 FROM users WHERE email = %s
           UNION SELECT 1 FROM access_requests WHERE email = %s AND status = 'pending'""",
        (body.email, body.email),
    ).fetchone()
    if not known:
        conn.execute(
            "INSERT INTO access_requests (name, email, district, job_role) VALUES (%s, %s, %s, %s)",
            (body.name, body.email, body.district, body.job_role),
        )
    return {
        "message": "Thanks. If your school email can be added, an administrator will be in touch."
    }


@router.post("/api/auth/accept-invite", response_model=TokenOut)
def accept_invite(body: AcceptInvite, request: Request, s: Cfg, conn: Conn) -> TokenOut:
    _local_only(s)
    lim, keys = _guard_sign_in(s, request, body.email)
    row = conn.execute(
        """SELECT user_id::text AS user_id, name, email, district, role, status, invite_hash,
                  invite_expires_at FROM users WHERE email = %s FOR UPDATE""",
        (body.email,),
    ).fetchone()
    good = (
        row is not None
        and row["status"] == "active"
        and row["invite_hash"] is not None
        and row["invite_expires_at"] > datetime.now(UTC)
        and hmac.compare_digest(row["invite_hash"], _invite_digest(body.invite_code))
    )
    if not good or row is None:
        for k in keys:
            lim.record_failure(k)
        raise HTTPException(401, BAD_INVITE)
    if body.password.lower() == body.email:
        raise HTTPException(422, "Please choose a password that is not your email.")
    conn.execute(
        """UPDATE users SET password_hash = %s, invite_hash = NULL, invite_expires_at = NULL,
                  last_sign_in_at = now() WHERE user_id::text = %s""",
        (hash_password(body.password), row["user_id"]),
    )
    return _token_for(s, row)


@router.post("/api/auth/sign-in", response_model=TokenOut)
def sign_in(body: SignIn, request: Request, s: Cfg, conn: Conn) -> TokenOut:
    _local_only(s)
    lim, keys = _guard_sign_in(s, request, body.email)
    row = conn.execute(
        """SELECT user_id::text AS user_id, name, email, district, role, status, password_hash
           FROM users WHERE email = %s""",
        (body.email,),
    ).fetchone()
    stored = row["password_hash"] if row and row["password_hash"] else _dummy_hash()
    matches = verify_password(body.password, stored)  # always run: same time for every case
    if not (row and row["password_hash"] and row["status"] == "active" and matches):
        for k in keys:
            lim.record_failure(k)
        raise HTTPException(401, BAD_LOGIN)  # one message for wrong password, unknown, disabled
    lim.reset(keys[0])
    conn.execute(
        "UPDATE users SET last_sign_in_at = now() WHERE user_id::text = %s", (row["user_id"],)
    )
    return _token_for(s, row)


@router.get("/dev-issuer/.well-known/jwks.json")
def dev_jwks(s: Cfg) -> dict[str, Any]:
    if s.auth_mode != "local":
        raise HTTPException(404, "Not found.")
    return auth.local_issuer(s).jwks()


# ------------------------------------------------------------------ signed-in endpoints
@router.post("/api/auth/sign-out", status_code=204)
def sign_out(
    user: Annotated[dict[str, Any], Depends(current_user)], s: Cfg, conn: Conn
) -> Response:
    if user.get("jti") and user.get("exp"):
        conn.execute(
            "INSERT INTO revoked_tokens (jti, expires_at) VALUES (%s, to_timestamp(%s)) "
            "ON CONFLICT DO NOTHING",
            (user["jti"], user["exp"]),
        )
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at < now()")
    return Response(status_code=204)


@router.get("/api/auth/me", response_model=Me)
def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> Me:
    return _me(user)


# ------------------------------------------------------------------ admin endpoints
def _set_audit(conn: Conn, actor: str, reason: str) -> None:
    conn.execute(
        "SELECT set_config('app.actor', %s, true), set_config('app.reason', %s, true)",
        (actor, reason.strip()),
    )


@router.get("/api/admin/access-requests", response_model=list[AccessRequestOut])
def list_requests(
    _: Admin, conn: Conn, status: Literal["pending", "approved", "denied"] = "pending"
) -> list[dict[str, Any]]:
    return conn.execute(
        """SELECT request_id, name, email, district, job_role, status, requested_at, decided_by,
                  decided_at, decision_reason
           FROM access_requests WHERE status = %s ORDER BY requested_at""",
        (status,),
    ).fetchall()


def _pending(conn: Conn, request_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM access_requests WHERE request_id = %s FOR UPDATE", (request_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "I do not know that request.")
    if row["status"] != "pending":
        raise HTTPException(409, f"That request was already {row['status']}.")
    return row


@router.post("/api/admin/access-requests/{request_id}/approve", response_model=Invite)
def approve(request_id: int, body: Approve, admin: Admin, conn: Conn) -> Invite:
    req = _pending(conn, request_id)
    if conn.execute("SELECT 1 FROM users WHERE email = %s", (req["email"],)).fetchone():
        raise HTTPException(409, "That email already has an account.")
    _set_audit(conn, admin, body.reason)
    conn.execute(
        """UPDATE access_requests SET status = 'approved', decided_by = %s, decided_at = now(),
                  decision_reason = %s WHERE request_id = %s""",
        (admin, body.reason.strip(), request_id),
    )
    code = secrets.token_urlsafe(24)
    expires = datetime.now(UTC) + timedelta(hours=INVITE_HOURS)
    user = conn.execute(
        """INSERT INTO users (name, email, district, role, invite_hash, invite_expires_at)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id::text AS user_id""",
        (req["name"], req["email"], req["district"], body.role, _invite_digest(code), expires),
    ).fetchone()
    if user is None:
        raise HTTPException(500, "Could not create the account.")
    return Invite(user_id=user["user_id"], invite_code=code, expires_at=expires)


@router.post("/api/admin/access-requests/{request_id}/deny", status_code=204)
def deny(request_id: int, body: Deny, admin: Admin, conn: Conn) -> Response:
    _pending(conn, request_id)
    _set_audit(conn, admin, body.reason)
    conn.execute(
        """UPDATE access_requests SET status = 'denied', decided_by = %s, decided_at = now(),
                  decision_reason = %s WHERE request_id = %s""",
        (admin, body.reason.strip(), request_id),
    )
    return Response(status_code=204)
