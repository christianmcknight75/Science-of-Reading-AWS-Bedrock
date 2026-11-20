"""The local stand-in model passes through the REAL verifier, retrieval stubbed, no database."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import qa, retrieval
from app.config import Settings, get_settings
from app.fake_llm import LocalFakeLLM
from app.main import app
from tests.fakes import FakeConn, FakeEmbedder, NameRedactor, passage

LONG = (
    "Teach students to blend letter sounds and sound-spelling patterns from left to right "
    "within a word to produce a recognizable pronunciation of the whole word today."
)


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
    qa._limiter.cache_clear()


def client(monkeypatch: pytest.MonkeyPatch, **settings: Any) -> TestClient:
    s = Settings(auth_mode="dev", qa_enabled=True, llm_mode="fake", **settings)
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[qa.conn_dep] = lambda: FakeConn()
    app.dependency_overrides[qa.get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[qa.get_redact] = lambda: NameRedactor()
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [passage(text=LONG)])
    qa._limiter.cache_clear()
    return TestClient(app)


def test_ask_passes_the_real_verifier_and_is_labelled(monkeypatch: pytest.MonkeyPatch) -> None:
    body = (
        client(monkeypatch).post("/api/ask", json={"question": "How do I teach blending?"}).json()
    )
    assert body["kind"] == "answer" and body["evidence_label"] == "Very sure"
    assert body["research_says"][0]["text"].startswith("[Fake model]")
    assert body["sources"][0]["quote"] in body["sources"][0]["passage_text"]


def test_every_phase_4_endpoint_works_with_the_fake_model(monkeypatch: pytest.MonkeyPatch) -> None:
    c = client(monkeypatch)
    sounds = ["s", "a", "t", "p", "i", "n", "m", "c"]
    plan = c.post("/api/group-plan", json={"focus": "blend", "sounds": sounds})
    assert plan.status_code == 200 and plan.json()["steps"][1]["words"] == ["cat", "sat"]
    story = c.post("/api/story", json={"sounds": sounds}).json()
    assert story["all_decodable"] and story["flagged"] == []
    stuck = c.post("/api/stuck", json={"pairs": [{"word": "ship", "said": "sip"}]})
    assert stuck.status_code == 200 and stuck.json()["try_it"]["text"].startswith("[Fake model]")
    assert c.get("/api/training/topics/blending").status_code == 200
    assert c.get("/api/refresher/today").status_code == 200


def test_story_follows_the_sounds_and_changes_with_the_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c = client(monkeypatch)
    sounds = ["s", "a", "t", "p", "i", "n", "m", "d", "h", "c", "f"]
    a = c.post("/api/story", json={"sounds": sounds, "variant": 0}).json()
    b = c.post("/api/story", json={"sounds": sounds, "variant": 1}).json()
    assert a["all_decodable"] and b["all_decodable"] and a["words"] != b["words"]
    few = c.post(
        "/api/story", json={"sounds": ["s", "a"]}
    ).json()  # nothing fits: flagged, not hidden
    assert few["all_decodable"] is False and few["flagged"]


def test_the_fake_model_is_refused_with_cognito_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    c = client(monkeypatch)
    s = Settings(auth_mode="cognito", qa_enabled=True, llm_mode="fake")
    with pytest.raises(Exception, match="local development only|503"):
        qa.get_llm(s)
    app.dependency_overrides[get_settings] = lambda: s
    assert c.get("/api/training/topics").status_code == 503  # not signed in either way


def test_no_quotable_passage_means_not_answerable() -> None:
    from app.llm import ToolSpec

    out = LocalFakeLLM().converse(
        model_id="m",
        system="s",
        user="no passages here",
        max_tokens=10,
        tool=ToolSpec("submit_answer", "d", {}),
    )
    assert out.tool_input == {"answerable": False, "claims": []}


def test_default_mode_is_bedrock_and_cors_is_configurable() -> None:
    s = Settings()
    assert s.llm_mode == "bedrock" and "localhost:5173" in s.cors_origins
