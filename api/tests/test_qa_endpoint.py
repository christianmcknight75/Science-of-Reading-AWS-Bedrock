"""Kill switch, auth and rate limit on POST /api/ask (fake model and fake database)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import qa, retrieval
from app.config import Settings, get_settings
from app.main import app
from app.ratelimit import RateLimiter
from tests.fakes import FakeConn, FakeEmbedder, FakeLLM, NameRedactor, passage

ANSWER: dict[str, Any] = {
    "answerable": True,
    "claims": [
        {
            "text": "Blend sounds.",
            "passage_ids": ["src_0011_p001"],
            "quote": "Blending means pushing the sounds together",
        }
    ],
    "steps": [],
}


def client(monkeypatch: pytest.MonkeyPatch, **settings: Any) -> TestClient:
    s = Settings(auth_mode="dev", **settings)
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[qa.conn_dep] = lambda: FakeConn()
    app.dependency_overrides[qa.get_llm] = lambda: FakeLLM(ANSWER)
    app.dependency_overrides[qa.get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[qa.get_redact] = lambda: NameRedactor()
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [passage()])
    monkeypatch.setattr(retrieval, "fetch", lambda *a, **k: [])
    qa._limiter.cache_clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
    qa._limiter.cache_clear()


BODY = {"question": "How do I teach blending to kindergartners?", "grade": "K"}


def test_kill_switch_is_off_by_default() -> None:
    assert Settings().qa_enabled is False


def test_switched_off_returns_503_and_never_touches_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert client(monkeypatch, qa_enabled=False).post("/api/ask", json=BODY).status_code == 503


def test_enabled_returns_a_cited_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    r = client(monkeypatch, qa_enabled=True).post("/api/ask", json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "answer" and body["evidence_label"] == "Very sure"
    assert body["sources"][0]["passage_id"] == "src_0011_p001" and body["disclaimer"]


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    c = client(monkeypatch, qa_enabled=True, rate_limit_per_minute=2)
    codes = [c.post("/api/ask", json=BODY).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert isinstance(qa._limiter(2), RateLimiter)


def test_needs_a_signed_in_user(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(auth_mode="cognito", qa_enabled=True)  # no pool configured: fails closed
    c = client(monkeypatch, qa_enabled=True)
    app.dependency_overrides[get_settings] = lambda: s
    assert c.post("/api/ask", json=BODY).status_code == 503


def test_rejects_empty_and_oversized_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    c = client(monkeypatch, qa_enabled=True)
    assert c.post("/api/ask", json={"question": ""}).status_code == 422
    assert c.post("/api/ask", json={"question": "x" * 1001}).status_code == 422
