"""Admin review flow against the local Postgres. Skipped if it is not running."""

import time
from collections.abc import Iterator
from typing import Any

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import decode_token
from app.config import Settings, get_settings
from app.db import get_conn
from app.main import app

GOOD = {
    "copy_store": True,
    "ai_use": True,
    "excerpt_display": True,
    "redistribution": False,
    "derivatives": False,
    "third_party_content_checked": True,
}


@pytest.fixture
def client(tmp_path: Any) -> Iterator[TestClient]:
    settings = Settings(auth_mode="dev", snapshot_dir=str(tmp_path))
    try:
        conn = psycopg.connect(settings.database_url, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    conn.rollback()  # nothing from tests is kept
    conn.close()
    app.dependency_overrides.clear()


def make_candidate(client: TestClient) -> str:
    conn = app.dependency_overrides[get_conn]()
    row = conn.execute(
        "INSERT INTO sources (source_id, title) VALUES ('src_9001', 'Test') RETURNING source_id"
    ).fetchone()
    return str(row["source_id"])


def test_approve_requires_everything(client: TestClient) -> None:
    sid = make_candidate(client)
    r = client.post(f"/admin/sources/{sid}/decision", json={"decision": "approve"})
    assert r.status_code == 422
    detail = " ".join(r.json()["detail"])
    assert "checklist" in detail and "attribution" in detail and "snapshot" in detail


def test_full_approval_flow_and_blocked_uses(client: TestClient) -> None:
    sid = make_candidate(client)
    up = client.post(
        f"/admin/sources/{sid}/license-snapshot",
        files={"file": ("l.txt", b"CC BY 4.0", "text/plain")},
    )
    assert up.status_code == 200
    body = {
        "decision": "approve",
        "license": "cc-by",
        "attribution": "Author (2020), CC BY 4.0",
        "checklist": GOOD,
        "topics": ["phonics"],
        "grades": ["1"],
    }
    r = client.post(f"/admin/sources/{sid}/decision", json=body)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert r.json()["approved_by"] == "dev-admin"

    bad = {**body, "checklist": {**GOOD, "ai_use": False}}
    sid2 = make_candidate_2(client)
    client.post(
        f"/admin/sources/{sid2}/license-snapshot", files={"file": ("l.txt", b"x", "text/plain")}
    )
    r2 = client.post(f"/admin/sources/{sid2}/decision", json=bad)
    assert r2.status_code == 422 and "AI use" in r2.json()["detail"][0]


def make_candidate_2(client: TestClient) -> str:
    conn = app.dependency_overrides[get_conn]()
    conn.execute("INSERT INTO sources (source_id, title) VALUES ('src_9002', 'Second')")
    return "src_9002"


def test_reject_and_list(client: TestClient) -> None:
    sid = make_candidate(client)
    assert any(s["source_id"] == sid for s in client.get("/admin/sources").json())
    r = client.post(
        f"/admin/sources/{sid}/decision",
        json={"decision": "reject", "reviewer_notes": "no license"},
    )
    assert r.json()["status"] == "rejected"
    assert not any(s["source_id"] == sid for s in client.get("/admin/sources").json())


def test_snapshot_rejects_bad_type(client: TestClient) -> None:
    sid = make_candidate(client)
    r = client.post(
        f"/admin/sources/{sid}/license-snapshot", files={"file": ("x.exe", b"x", "application/x")}
    )
    assert r.status_code == 400


# ---- auth (no database needed) ----


def test_cognito_mode_fails_closed_when_unconfigured() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(auth_mode="cognito")
    try:
        assert TestClient(app).get("/admin/sources").status_code == 503
    finally:
        app.dependency_overrides.clear()


KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
S = Settings(cognito_user_pool_id="pool", cognito_client_id="cid")
ISS = "https://cognito-idp.us-east-2.amazonaws.com/pool"


def token(**over: Any) -> str:  # noqa: S106
    claims = {
        "iss": ISS,
        "token_use": "access",
        "client_id": "cid",
        "sub": "u1",
        "username": "ann",
        "exp": int(time.time()) + 60,
        "cognito:groups": ["admin"],
        **over,
    }
    return jwt.encode(claims, KEY, algorithm="RS256")


def test_token_checks() -> None:
    pub = KEY.public_key()
    assert decode_token(token(), S, pub)["username"] == "ann"
    for bad in (
        token(client_id="other"),
        token(token_use="id"),
        token(iss="https://evil"),
        token(exp=1),
    ):
        with pytest.raises(jwt.PyJWTError):
            decode_token(bad, S, pub)


def test_non_admin_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.auth as auth

    monkeypatch.setattr(
        auth, "decode_token", lambda t, s: {"sub": "u", "cognito:groups": ["teacher"]}
    )
    app.dependency_overrides[get_settings] = lambda: S
    try:
        r = TestClient(app).get("/admin/sources", headers={"Authorization": "Bearer x"})
        assert r.status_code == 403
        assert TestClient(app).get("/admin/sources").status_code == 401
    finally:
        app.dependency_overrides.clear()


def approve(client: TestClient, sid: str) -> None:
    client.post(
        f"/admin/sources/{sid}/license-snapshot", files={"file": ("l.txt", b"x", "text/plain")}
    )
    r = client.post(
        f"/admin/sources/{sid}/decision",
        json={"decision": "approve", "license": "cc-by", "attribution": "A", "checklist": GOOD},
    )
    assert r.status_code == 200


def test_reopen_needs_reason_and_logs_who_when_why(client: TestClient) -> None:
    sid = make_candidate(client)
    client.post(
        f"/admin/sources/{sid}/decision", json={"decision": "reject", "reviewer_notes": "oops"}
    )
    assert client.post(f"/admin/sources/{sid}/reopen", json={}).status_code == 422
    assert client.post(f"/admin/sources/{sid}/reopen", json={"reason": "  "}).status_code == 422
    r = client.post(f"/admin/sources/{sid}/reopen", json={"reason": "Rejected by mistake"})
    assert r.status_code == 200 and r.json()["status"] == "candidate"
    assert client.post(f"/admin/sources/{sid}/reopen", json={"reason": "again"}).status_code == 409
    log = client.get(f"/admin/sources/{sid}/audit").json()
    assert [(e["from_status"], e["to_status"]) for e in log] == [
        ("candidate", "rejected"),
        ("rejected", "candidate"),
    ]
    assert log[-1]["actor"] == "dev-admin" and "Rejected by mistake" in log[-1]["reason"]
    assert log[-1]["ts"]


def test_reopen_approved_clears_approval_and_leaves_retrieval(client: TestClient) -> None:
    sid = make_candidate(client)
    approve(client, sid)
    conn = app.dependency_overrides[get_conn]()
    conn.execute(
        "INSERT INTO passages (passage_id, source_id, text) VALUES (%s, %s, 'phonics text')",
        (f"{sid}_p001", sid),
    )
    q = "SELECT count(*) AS n FROM retrievable_passages WHERE source_id = %s"
    assert conn.execute(q, (sid,)).fetchone()["n"] == 1
    r = client.post(f"/admin/sources/{sid}/reopen", json={"reason": "license questioned"})
    assert r.json()["status"] == "candidate" and r.json()["approved_by"] is None
    assert conn.execute(q, (sid,)).fetchone()["n"] == 0  # passages stay, but are not retrievable


def test_held_sources_are_excluded_from_retrieval_even_if_approved(client: TestClient) -> None:
    sid = make_candidate(client)
    approve(client, sid)
    conn = app.dependency_overrides[get_conn]()
    conn.execute(
        "INSERT INTO passages (passage_id, source_id, text) VALUES (%s, %s, 'text')",
        (f"{sid}_p001", sid),
    )
    q = "SELECT count(*) AS n FROM retrievable_passages WHERE source_id = %s"
    assert conn.execute(q, (sid,)).fetchone()["n"] == 1
    conn.execute("UPDATE sources SET curation_status = 'quote_only' WHERE source_id = %s", (sid,))
    assert conn.execute(q, (sid,)).fetchone()["n"] == 0
    conn.execute("UPDATE sources SET curation_status = 'ready' WHERE source_id = %s", (sid,))
    assert conn.execute(q, (sid,)).fetchone()["n"] == 1


def test_study_design_facts_are_saved_on_approval(client: TestClient) -> None:
    sid = make_candidate(client)
    client.post(
        f"/admin/sources/{sid}/license-snapshot", files={"file": ("l.txt", b"x", "text/plain")}
    )
    r = client.post(
        f"/admin/sources/{sid}/decision",
        json={
            "decision": "approve", "license": "cc-by", "attribution": "A", "checklist": GOOD,
            "randomized": True, "sample_size": 1200, "has_comparison_group": True,
        },
    )  # fmt: skip
    assert r.status_code == 200
    assert (r.json()["randomized"], r.json()["sample_size"]) == (True, 1200)
