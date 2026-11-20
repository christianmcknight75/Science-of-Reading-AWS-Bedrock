"""Closed-access accounts against the local Postgres (skipped if it is not running)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import accounts, auth
from app.config import Settings, get_settings
from app.db import get_conn
from app.main import app
from app.users import create_admin

PASSWORD = "correct horse battery"  # noqa: S105
ADMIN_EMAIL = "boss@district.example"


# ---------------------------------------------------------------- no database needed
def test_passwords_are_hashed_salted_and_verified() -> None:
    h1, h2 = accounts.hash_password(PASSWORD), accounts.hash_password(PASSWORD)
    assert h1 != h2 and PASSWORD not in h1 and h1.startswith("scrypt$")
    assert accounts.verify_password(PASSWORD, h1) and accounts.verify_password(PASSWORD, h2)
    assert not accounts.verify_password("wrong password!", h1)
    for junk in ("", "plain", "scrypt$1$2", "md5$a$b$c$d$e", "scrypt$x$y$z$!!$!!"):
        assert not accounts.verify_password(PASSWORD, junk)


def local(tmp_path: Path, **kw: Any) -> Settings:
    return Settings(auth_mode="local", dev_issuer_key_path=str(tmp_path / "k.pem"), **kw)


def test_local_issuer_tokens_are_verified_like_cognito_tokens(tmp_path: Path) -> None:
    s = local(tmp_path)
    issuer = auth.local_issuer(s)
    now = int(time.time())
    good = {
        "iss": auth.issuer(s),
        "sub": "u1",
        "username": "a@b.org",
        "client_id": auth.client_id(s),
        "token_use": "access",
        "jti": "j1",
        "iat": now,
        "exp": now + 60,
    }
    assert auth.decode_token(issuer.sign(good), s)["sub"] == "u1"
    for name, bad in {
        "wrong issuer": {**good, "iss": "https://evil.example"},
        "wrong client": {**good, "client_id": "someone-else"},
        "wrong use": {**good, "token_use": "id"},
        "wrong audience": {**good, "aud": "someone-else"},
        "expired": {**good, "exp": now - 5},
        "no expiry": {k: v for k, v in good.items() if k != "exp"},
    }.items():
        with pytest.raises(jwt.PyJWTError):
            auth.decode_token(issuer.sign(bad), s)
        assert name  # (name shows in the failure output)


def test_forged_tokens_are_rejected(tmp_path: Path) -> None:
    s = local(tmp_path)
    now = int(time.time())
    claims = {
        "iss": auth.issuer(s),
        "sub": "u1",
        "client_id": auth.client_id(s),
        "token_use": "access",
        "exp": now + 60,
    }
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = auth.local_issuer(s).kid
    forged = jwt.encode(claims, other, algorithm="RS256", headers={"kid": kid})  # wrong signing key
    unknown_kid = jwt.encode(claims, other, algorithm="RS256", headers={"kid": "nope"})
    hs256 = jwt.encode(claims, "secret", algorithm="HS256", headers={"kid": kid})  # alg confusion
    none_alg = jwt.encode(claims, None, algorithm="none", headers={"kid": kid})  # type: ignore[arg-type]
    for t in (forged, unknown_kid, hs256, none_alg, "garbage", ""):
        with pytest.raises(jwt.PyJWTError):
            auth.decode_token(t, s)


def test_jwks_has_the_public_key_only(tmp_path: Path) -> None:
    keys = auth.local_issuer(local(tmp_path)).jwks()["keys"]
    assert keys[0]["kty"] == "RSA" and keys[0]["alg"] == "RS256" and "d" not in keys[0]


def test_dev_key_file_is_private_and_reused(tmp_path: Path) -> None:
    s = local(tmp_path)
    first = auth.local_issuer(s).kid
    assert (tmp_path / "k.pem").stat().st_mode & 0o077 == 0
    assert auth.LocalIssuer(tmp_path / "k.pem").kid == first


def test_sign_in_and_issuer_endpoints_do_not_exist_outside_local_mode() -> None:
    for mode in ("cognito", "dev"):
        app.dependency_overrides[get_settings] = lambda m=mode: Settings(auth_mode=m)
        c = TestClient(app)
        assert c.get("/dev-issuer/.well-known/jwks.json").status_code == 404
        r = c.post("/api/auth/sign-in", json={"email": "a@b.org", "password": "x"})
        assert r.status_code in (404, 500)  # 404 before any database is touched
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- with the database
@pytest.fixture
def db() -> Iterator[psycopg.Connection[Any]]:
    try:
        conn = psycopg.connect(Settings().database_url, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    try:
        conn.execute("SELECT 1 FROM users LIMIT 1")
    except psycopg.errors.UndefinedTable:
        conn.close()
        pytest.skip("run `make migrate` first")
    yield conn
    conn.rollback()  # nothing from tests is kept
    conn.close()


@pytest.fixture
def client(db: psycopg.Connection[Any], tmp_path: Path) -> Iterator[TestClient]:
    s = local(tmp_path, sign_in_max_failures=5, request_access_per_hour=3)
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[get_conn] = lambda: db
    app.dependency_overrides[auth.auth_db] = lambda: auth.LazyDb(s.database_url, db)
    accounts.reset_limiters()
    create_admin(
        db, email=ADMIN_EMAIL, name="Pat Admin", district="Example District", password=PASSWORD
    )
    yield TestClient(app)
    app.dependency_overrides.clear()
    accounts.reset_limiters()


def sign_in(c: TestClient, email: str = ADMIN_EMAIL, password: str = PASSWORD) -> Any:
    return c.post("/api/auth/sign-in", json={"email": email, "password": password})


def bearer(c: TestClient, email: str = ADMIN_EMAIL, password: str = PASSWORD) -> dict[str, str]:
    r = sign_in(c, email, password)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ask_access(c: TestClient, email: str = "teacher@school.example") -> Any:
    return c.post(
        "/api/auth/request-access",
        json={"name": "Terry Teacher", "email": email, "district": "Example District"},
    )


def onboard(c: TestClient, email: str = "teacher@school.example", role: str = "teacher") -> str:
    """Request, approve, accept the invite. Returns the new user's id."""
    assert ask_access(c, email).status_code == 202
    admin = bearer(c)
    rid = c.get("/api/admin/access-requests", headers=admin).json()[0]["request_id"]
    inv = c.post(f"/api/admin/access-requests/{rid}/approve", json={"role": role}, headers=admin)
    assert inv.status_code == 200, inv.text
    r = c.post(
        "/api/auth/accept-invite",
        json={"email": email, "invite_code": inv.json()["invite_code"], "password": PASSWORD},
    )
    assert r.status_code == 200, r.text
    return str(inv.json()["user_id"])


def test_full_invite_flow_and_me(client: TestClient) -> None:
    uid = onboard(client)
    me = client.get("/api/auth/me", headers=bearer(client, "teacher@school.example"))
    assert me.status_code == 200
    assert me.json() == {
        "user_id": uid,
        "name": "Terry Teacher",
        "email": "teacher@school.example",
        "district": "Example District",
        "role": "teacher",
        "status": "active",
    }


def test_request_access_gives_the_same_answer_for_everyone(client: TestClient, db: Any) -> None:
    new = ask_access(client, "new@school.example")
    again = ask_access(client, "new@school.example")  # already pending
    existing = ask_access(client, ADMIN_EMAIL)  # already has an account
    assert new.status_code == again.status_code == existing.status_code == 202
    assert new.json() == again.json() == existing.json()
    n = db.execute(
        "SELECT count(*) AS n FROM access_requests WHERE email = %s", ("new@school.example",)
    )
    assert n.fetchone()["n"] == 1
    assert (
        db.execute(
            "SELECT count(*) AS n FROM access_requests WHERE email = %s", (ADMIN_EMAIL,)
        ).fetchone()["n"]
        == 0
    )


def test_the_job_role_is_kept_for_the_reviewing_admin(client: TestClient) -> None:
    body = {
        "name": "Terry",
        "email": "coach@school.example",
        "district": "D",
        "job_role": " Reading coach ",
    }
    assert client.post("/api/auth/request-access", json=body).status_code == 202
    row = client.get("/api/admin/access-requests", headers=bearer(client)).json()[0]
    assert row["job_role"] == "Reading coach"
    too_long = {**body, "email": "x@school.example", "job_role": "r" * 61}
    assert client.post("/api/auth/request-access", json=too_long).status_code == 422
    plain = {"name": "T", "email": "y@school.example", "district": "D"}  # still optional
    assert client.post("/api/auth/request-access", json=plain).status_code == 202


def test_request_access_validation_and_rate_limit(client: TestClient) -> None:
    bad = client.post(
        "/api/auth/request-access", json={"name": "A", "email": "nope", "district": "D"}
    )
    assert bad.status_code == 422 and isinstance(bad.json()["detail"], str)
    assert (
        client.post(
            "/api/auth/request-access", json={"name": " ", "email": "a@b.org", "district": "D"}
        ).status_code
        == 422
    )
    codes = [ask_access(client, f"t{i}@school.example").status_code for i in range(4)]
    assert codes == [202, 202, 202, 429]


def test_there_is_no_public_sign_up(client: TestClient) -> None:
    assert (
        sign_in(client, "teacher@school.example").status_code == 401
    )  # unknown: cannot just sign in
    assert client.get("/api/admin/access-requests").status_code == 401
    ask_access(client)
    assert (
        sign_in(client, "teacher@school.example").status_code == 401
    )  # requested but not approved


def test_admin_endpoints_need_an_admin(client: TestClient) -> None:
    onboard(client)
    teacher = bearer(client, "teacher@school.example")
    assert client.get("/api/admin/access-requests", headers=teacher).status_code == 403
    assert (
        client.post(
            "/api/admin/access-requests/1/deny", json={"reason": "no reason"}, headers=teacher
        ).status_code
        == 403
    )
    assert client.get("/api/admin/access-requests", headers=bearer(client)).status_code == 200


def test_approval_is_audited_and_the_invite_is_stored_only_as_a_hash(
    client: TestClient, db: Any
) -> None:
    ask_access(client)
    admin = bearer(client)
    rid = client.get("/api/admin/access-requests", headers=admin).json()[0]["request_id"]
    r = client.post(
        f"/api/admin/access-requests/{rid}/approve",
        json={"role": "teacher", "reason": "Confirmed with the principal"},
        headers=admin,
    )
    code = r.json()["invite_code"]
    row = db.execute(
        "SELECT invite_hash, password_hash FROM users WHERE user_id::text = %s",
        (r.json()["user_id"],),
    ).fetchone()
    assert code not in str(row) and len(row["invite_hash"]) == 64 and row["password_hash"] is None
    audit = db.execute(
        "SELECT actor, from_status, to_status, reason FROM access_audit "
        "WHERE request_id = %s ORDER BY id",
        (rid,),
    ).fetchall()
    assert [(a["from_status"], a["to_status"]) for a in audit] == [
        (None, "pending"),
        ("pending", "approved"),
    ]
    assert audit[1]["actor"] == ADMIN_EMAIL and audit[1]["reason"] == "Confirmed with the principal"
    assert (
        client.post(f"/api/admin/access-requests/{rid}/approve", json={}, headers=admin).status_code
        == 409
    )
    done = client.get("/api/admin/access-requests?status=approved", headers=admin).json()
    assert done[0]["decided_by"] == ADMIN_EMAIL


def test_deny_needs_a_reason_and_is_audited(client: TestClient, db: Any) -> None:
    ask_access(client)
    admin = bearer(client)
    rid = client.get("/api/admin/access-requests", headers=admin).json()[0]["request_id"]
    assert (
        client.post(f"/api/admin/access-requests/{rid}/deny", json={}, headers=admin).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/admin/access-requests/{rid}/deny", json={"reason": "no"}, headers=admin
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/admin/access-requests/{rid}/deny",
            json={"reason": "Not a district email"},
            headers=admin,
        ).status_code
        == 204
    )
    last = db.execute(
        "SELECT to_status, reason FROM access_audit WHERE request_id = %s ORDER BY id DESC LIMIT 1",
        (rid,),
    ).fetchone()
    assert last == {"to_status": "denied", "reason": "Not a district email"}
    assert sign_in(client, "teacher@school.example").status_code == 401
    assert (
        client.post(
            "/api/admin/access-requests/99999/deny",
            json={"reason": "whatever it is"},
            headers=admin,
        ).status_code
        == 404
    )


def test_the_database_refuses_a_status_change_without_actor_and_reason(
    client: TestClient, db: Any
) -> None:
    ask_access(client)
    rid = db.execute(
        "SELECT request_id FROM access_requests WHERE email = 'teacher@school.example'"
    ).fetchone()["request_id"]
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "UPDATE access_requests SET status = 'denied', decided_by = 'x' WHERE request_id = %s",
            (rid,),
        )
    db.rollback()


def test_invite_codes_are_single_use_and_expire(client: TestClient, db: Any) -> None:
    ask_access(client)
    admin = bearer(client)
    rid = client.get("/api/admin/access-requests", headers=admin).json()[0]["request_id"]
    inv = client.post(f"/api/admin/access-requests/{rid}/approve", json={}, headers=admin).json()
    body = {
        "email": "teacher@school.example",
        "invite_code": inv["invite_code"],
        "password": PASSWORD,
    }
    wrong = client.post("/api/auth/accept-invite", json={**body, "invite_code": "x" * 30})
    assert wrong.status_code == 401 and wrong.json()["detail"] == accounts.BAD_INVITE
    short = client.post("/api/auth/accept-invite", json={**body, "password": "short"})
    assert short.status_code == 422
    assert client.post("/api/auth/accept-invite", json=body).status_code == 200
    assert client.post("/api/auth/accept-invite", json=body).status_code == 401  # used up
    assert sign_in(client, "teacher@school.example").status_code == 200
    # expired
    ask_access(client, "late@school.example")
    rid2 = client.get("/api/admin/access-requests", headers=admin).json()[0]["request_id"]
    inv2 = client.post(f"/api/admin/access-requests/{rid2}/approve", json={}, headers=admin).json()
    db.execute(
        "UPDATE users SET invite_expires_at = now() - interval '1 minute' "
        "WHERE email = 'late@school.example'"
    )
    r = client.post(
        "/api/auth/accept-invite",
        json={
            "email": "late@school.example",
            "invite_code": inv2["invite_code"],
            "password": PASSWORD,
        },
    )
    assert r.status_code == 401


def test_wrong_password_unknown_email_and_disabled_user_look_the_same(
    client: TestClient, db: Any
) -> None:
    onboard(client)
    wrong = sign_in(client, "teacher@school.example", "not the password!!")
    unknown = sign_in(client, "ghost@school.example")
    db.execute("UPDATE users SET status = 'disabled' WHERE email = 'teacher@school.example'")
    disabled = sign_in(client, "teacher@school.example")
    assert wrong.status_code == unknown.status_code == disabled.status_code == 401
    assert wrong.json() == unknown.json() == disabled.json() == {"detail": accounts.BAD_LOGIN}


def test_five_failures_block_an_email_even_from_another_address(client: TestClient) -> None:
    onboard(client)
    for _ in range(5):
        assert sign_in(client, "teacher@school.example", "wrong password!!").status_code == 401
    elsewhere = TestClient(app, client=("203.0.113.9", 4000))
    blocked = sign_in(elsewhere, "teacher@school.example")  # right password, other address
    assert blocked.status_code == 429 and "minutes" in blocked.json()["detail"]
    assert sign_in(elsewhere, ADMIN_EMAIL).status_code == 200  # other emails are unaffected


def test_a_successful_sign_in_resets_that_emails_failures(client: TestClient) -> None:
    onboard(client)
    for _ in range(4):
        assert sign_in(client, "teacher@school.example", "wrong password!!").status_code == 401
    elsewhere = TestClient(app, client=("203.0.113.10", 4000))
    assert sign_in(elsewhere, "teacher@school.example").status_code == 200
    for _ in range(4):  # a fresh count of 4 more is still allowed
        assert sign_in(elsewhere, "teacher@school.example", "wrong password!!").status_code == 401


def test_sign_in_is_also_limited_per_address(client: TestClient) -> None:
    for i in range(5):
        assert sign_in(client, f"nobody{i}@school.example").status_code == 401
    assert sign_in(client, "another@school.example").status_code == 429


def test_signed_out_and_disabled_users_lose_access_immediately(client: TestClient, db: Any) -> None:
    onboard(client)
    h = bearer(client, "teacher@school.example")
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.post("/api/auth/sign-out", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401  # token revoked
    h2 = bearer(client, "teacher@school.example")
    db.execute("UPDATE users SET status = 'disabled' WHERE email = 'teacher@school.example'")
    assert client.get("/api/auth/me", headers=h2).status_code == 403


def test_a_demoted_admin_keeps_a_valid_token_but_loses_admin_rights(
    client: TestClient, db: Any
) -> None:
    h = bearer(client)
    db.execute("UPDATE users SET role = 'teacher' WHERE email = %s", (ADMIN_EMAIL,))
    assert client.get("/api/admin/access-requests", headers=h).status_code == 403


def test_other_endpoints_accept_a_signed_in_teacher_and_refuse_everyone_else(
    client: TestClient,
) -> None:
    onboard(client)
    assert client.get("/api/training/topics").status_code == 401
    assert (
        client.get("/api/training/topics", headers={"Authorization": "Bearer junk"}).status_code
        == 401
    )
    assert (
        client.get(
            "/api/training/topics", headers=bearer(client, "teacher@school.example")
        ).status_code
        == 200
    )


def test_the_jwks_endpoint_serves_the_key_that_verifies_tokens(client: TestClient) -> None:
    jwks = client.get("/dev-issuer/.well-known/jwks.json").json()
    token = sign_in(client).json()["access_token"]
    kid = jwt.get_unverified_header(token)["kid"]
    assert kid in {k["kid"] for k in jwks["keys"]}
    claims = jwt.decode(
        token,
        jwt.PyJWK(jwks["keys"][0]).key,
        algorithms=["RS256"],
        issuer=auth.DEV_ISSUER,
        options={"verify_aud": False},
    )
    assert claims["cognito:groups"] == ["admin"] and claims["token_use"] == "access"  # noqa: S105
    assert claims["exp"] - claims["iat"] == 3600


def test_create_admin_refuses_a_short_password(db: Any) -> None:
    with pytest.raises(ValueError, match="at least"):
        create_admin(db, email="a@b.org", name="A", district="D", password="short")
