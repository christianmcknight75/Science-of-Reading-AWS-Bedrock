"""Phase 4 endpoints with a fake model, fake database and stubbed retrieval."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import features as f
from app import qa, retrieval
from app.config import Settings, get_settings
from app.engine import Engine
from app.main import app
from tests.fakes import FakeConn, FakeEmbedder, FakeLLM, NameRedactor, passage

QUOTE = "Blending means pushing the sounds together smoothly"
CLAIM = {
    "text": "Teach children to blend letter sounds into words.",
    "passage_ids": ["src_0011_p001"],
    "quote": QUOTE,
}
SOUNDS = ["s", "a", "t", "p", "i", "n", "c", "m"]


def plan_payload(steps: list[dict[str, Any]] | None = None, **extra: Any) -> dict[str, Any]:
    idea = {
        "steps": steps
        if steps is not None
        else [
            {
                "title": "Warm up",
                "minutes": 3,
                "body": "Say the sounds.",
                "words": ["cat", "sat", "ship", "dog"],
            },
            {
                "title": "Blend",
                "minutes": 5,
                "body": "Blend with a finger sweep.",
                "sounds": ["s", "zz9"],
            },
        ]
    }
    return {"answerable": True, "claims": [CLAIM], **extra, "idea": idea}


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
    qa._limiter.cache_clear()


def setup(
    monkeypatch: pytest.MonkeyPatch, llm: FakeLLM, conn: FakeConn | None = None, **settings: Any
) -> tuple[TestClient, FakeConn]:
    conn = conn or FakeConn()
    s = Settings(auth_mode="dev", qa_enabled=settings.pop("qa_enabled", True), **settings)
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[qa.conn_dep] = lambda: conn
    app.dependency_overrides[qa.get_llm] = lambda: llm
    app.dependency_overrides[qa.get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[qa.get_redact] = lambda: NameRedactor()
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [passage()])
    qa._limiter.cache_clear()
    return TestClient(app), conn


# ---------------------------------------------------------------- group plan
def test_group_plan_keeps_only_decodable_practice_words(monkeypatch: pytest.MonkeyPatch) -> None:
    client, conn = setup(monkeypatch, FakeLLM(scripts={"submit_plan": plan_payload()}))
    r = client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS, "grade": "K"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["steps"][0]["words"] == ["cat", "sat"]  # "ship" (sh) and "dog" were dropped
    assert body["steps"][1]["sounds"] == ["s"]  # unknown sound names removed
    assert body["minutes"] == 8 and body["why"] == CLAIM["text"]
    assert body["evidence_label"] == "Very sure" and body["research_says"][0]["citations"] == [1]
    assert body["sources"][0]["quote"] == QUOTE and body["disclaimer"] and body["query_id"] == 1
    assert body["content_last_updated"] == "2026-11-19"
    assert conn.logged[0][0] == "group_plan"


def test_tricky_words_plan_keeps_only_heart_words(monkeypatch: pytest.MonkeyPatch) -> None:
    steps = [
        {
            "title": "Tricky",
            "minutes": 4,
            "body": "Say, spell, say.",
            "words": ["the", "cat", "said"],
        }
    ]
    client, _ = setup(monkeypatch, FakeLLM(scripts={"submit_plan": plan_payload(steps)}))
    r = client.post("/api/group-plan", json={"focus": "tricky-words", "sounds": SOUNDS})
    assert r.json()["steps"][0]["words"] == ["the", "said"]


def test_a_story_inside_a_step_must_be_fully_decodable_or_it_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    steps = [
        {
            "title": "Read",
            "minutes": 4,
            "body": "Read it.",
            "story": ["Pat", "sat", "in", "a", "tin"],
        },
        {"title": "Read 2", "minutes": 4, "body": "Read it.", "story": ["Pat", "had", "a", "dog"]},
    ]
    client, _ = setup(monkeypatch, FakeLLM(scripts={"submit_plan": plan_payload(steps)}))
    out = client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS}).json()["steps"]
    assert out[0]["story"] == ["Pat", "sat", "in", "a", "tin"] and out[1]["story"] is None


def test_group_plan_input_errors_are_422_with_a_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(monkeypatch, FakeLLM(scripts={"submit_plan": plan_payload()}))
    r = client.post("/api/group-plan", json={"focus": "blend", "sounds": []})
    assert r.status_code == 422 and "at least one sound" in r.json()["detail"]
    r = client.post("/api/group-plan", json={"focus": "blend", "sounds": ["zh"]})
    assert r.status_code == 422 and "zh" in r.json()["detail"]
    r = client.post("/api/group-plan", json={"focus": "nonsense", "sounds": []})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_group_plan_with_an_unsupported_claim_is_an_honest_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = FakeLLM(scripts={"submit_plan": plan_payload()}, checks="unsupported")
    client, conn = setup(monkeypatch, llm)
    r = client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS})
    assert r.status_code == 503 and "research supports" in r.json()["detail"]
    assert json.loads(conn.logged[0][-1])["outcome"] == "unsupported"


def test_a_fabricated_citation_never_reaches_a_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = plan_payload()
    bad["claims"] = [{**CLAIM, "passage_ids": ["src_9999_p001"]}]
    client, conn = setup(monkeypatch, FakeLLM(scripts={"submit_plan": bad}))
    assert (
        client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS}).status_code == 503
    )
    assert json.loads(conn.logged[0][-1])["verifier"]["fabricated_citations"] == 1


def test_no_retrieved_passages_means_no_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM(scripts={"submit_plan": plan_payload()})
    client, _ = setup(monkeypatch, llm)
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [])
    assert (
        client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS}).status_code == 503
    )
    assert llm.calls == []


# ---------------------------------------------------------------- story
STORY_SOUNDS = ["s", "a", "t", "p", "i", "n", "m"]


def story_llm(*stories: dict[str, str]) -> FakeLLM:
    return FakeLLM(
        scripts={
            "submit_plan": {"answerable": True, "claims": [CLAIM]},
            "submit_story": list(stories),
        }
    )


def test_story_is_checked_word_by_word_and_repaired(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = story_llm(
        {"title": "Sam", "text": "Sam sat. The dog ran."},
        {"title": "Pat", "text": "Pat sat in a tin."},
    )
    client, _ = setup(monkeypatch, llm)
    r = client.post("/api/story", json={"sounds": STORY_SOUNDS})
    body = r.json()
    assert r.status_code == 200 and body["all_decodable"] and body["flagged"] == []
    assert body["words"] == ["Pat", "sat", "in", "a", "tin"] and body["title"] == "Pat"
    status = {c["word"]: c["status"] for c in body["checks"]}
    assert status["a"] == "heart_word" and status["Pat"] == "decodable"
    a = next(c for c in body["checks"] if c["word"] == "a")
    assert a["decodable"] is False  # a heart word is allowed, never called decodable
    repair = [c["user"] for c in llm.calls if "Allowed sounds" in c["user"]][1]
    assert "dog" in repair and "ran" in repair  # the failing words are fed back
    assert body["evidence_label"] == "Very sure" and body["sources"]


def test_a_story_that_cannot_be_fixed_is_flagged_never_called_decodable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = story_llm({"title": "Dog", "text": "The dog ran to the big hill."})
    client, _ = setup(monkeypatch, llm)
    body = client.post("/api/story", json={"sounds": STORY_SOUNDS}).json()
    assert body["all_decodable"] is False
    assert {"dog", "ran", "big", "hill"} <= {w.lower() for w in body["flagged"]}
    for c in body["checks"]:
        if c["word"].lower() in body["flagged"]:
            assert c["decodable"] is False and c["status"] == "not_decodable"
    assert sum(1 for c in llm.calls if c["tool"] == "submit_story") == 1 + f.STORY_REPAIRS
    assert "Allowed sounds" not in body["title"]


def test_story_with_an_explicit_heart_word_list_uses_only_that_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = story_llm({"title": "x", "text": "Pat sat in a tin."})
    client, _ = setup(monkeypatch, llm)
    body = client.post("/api/story", json={"sounds": STORY_SOUNDS, "heart_words": []}).json()
    assert body["flagged"] == ["a"]  # "a" is not decodable and not on this (empty) list


def test_story_topic_is_redacted_and_title_words_are_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = story_llm({"title": "Zorro and the Elephant", "text": "Pat sat in a tin."})
    client, _ = setup(monkeypatch, llm)
    body = client.post(
        "/api/story", json={"sounds": STORY_SOUNDS, "about": "Jamal at the zoo"}
    ).json()
    assert all("Jamal" not in c["user"] for c in llm.calls)
    assert body["title"].startswith("Story for ")  # the model's title was not decodable


def test_story_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(monkeypatch, story_llm({"title": "x", "text": "Pat sat."}))
    assert client.post("/api/story", json={"sounds": []}).status_code == 422
    assert client.post("/api/story", json={"sounds": ["s"], "about": "x" * 61}).status_code == 422
    r = client.post("/api/story", json={"sounds": ["s", "qq"]})
    assert r.status_code == 422 and "qq" in r.json()["detail"]


def test_decodable_check_endpoint_needs_no_model_and_works_when_switched_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = FakeLLM()
    client, _ = setup(monkeypatch, llm, qa_enabled=False)
    r = client.post(
        "/api/decodable/check",
        json={"sounds": STORY_SOUNDS, "words": ["sat", "dog", "the", "blorp"]},
    )
    got = {c["word"]: c["status"] for c in r.json()["checks"]}
    assert got == {
        "sat": "decodable",
        "dog": "not_decodable",
        "the": "heart_word",
        "blorp": "unknown",
    }
    assert llm.calls == []


# ---------------------------------------------------------------- why is a kid stuck?
def stuck_llm() -> FakeLLM:
    plan = {
        "answerable": True,
        "claims": [CLAIM],
        "idea": {"try_it": {"text": "Use sound boxes for sh words.", "minutes": 4}},
    }
    return FakeLLM(scripts={"submit_plan": plan})


def test_stuck_finds_a_pattern_and_cites_research(monkeypatch: pytest.MonkeyPatch) -> None:
    client, conn = setup(monkeypatch, stuck_llm())
    pairs = [
        {"word": "ship", "said": "sip"},
        {"word": "chip", "said": "cip"},
        {"word": "cat", "said": "cat"},
    ]
    body = client.post("/api/stuck", json={"pairs": pairs}).json()
    assert body["kind"] == "match" and "two letters" in body["pattern"]
    assert body["try_it"] == {"text": "Use sound boxes for sh words.", "minutes": 4}
    assert body["evidence_label"] == "Very sure" and body["research_says"] and body["sources"]
    assert body["evidence_note"]
    stored = " ".join(str(x) for row in conn.logged for x in row)
    assert "ship" not in stored and "chip" not in stored  # the child's words are never stored
    assert json.loads(conn.logged[0][-1])["pairs"] == 3


def test_stuck_without_a_clear_pattern_is_honest_and_calls_no_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = stuck_llm()
    client, _ = setup(monkeypatch, llm)
    body = client.post("/api/stuck", json={"pairs": [{"word": "cat", "said": "dog"}]}).json()
    assert body["kind"] == "no_match" and body["evidence_label"] == "No research found"
    assert body["try_it"] is None and body["message"] and llm.calls == []


def test_stuck_refuses_names_and_non_letters(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(monkeypatch, stuck_llm())
    r = client.post("/api/stuck", json={"pairs": [{"word": "Jamal", "said": "jam"}]})
    assert r.status_code == 422 and "No names" in r.json()["detail"]
    for bad in ({"word": "c4t", "said": "cat"}, {"word": "cat", "said": "two words"}):
        assert client.post("/api/stuck", json={"pairs": [bad]}).status_code == 422
    assert client.post("/api/stuck", json={"pairs": []}).status_code == 422
    nine = [{"word": "cat", "said": "cut"}] * 9
    assert client.post("/api/stuck", json={"pairs": nine}).status_code == 422


# ---------------------------------------------------------------- training and refresher
def training_llm() -> FakeLLM:
    idea = {
        "title": "Sound sweep",
        "minutes": 10,
        "steps": ["Say sounds", "Blend"],
        "need": "Cards",
    }
    plan = {
        "answerable": True,
        "claims": [CLAIM],
        "idea": {
            "idea": idea,
            "short_idea": {**idea, "minutes": 5},
            "if_stuck": "Slow down.",
            "if_easy": "Add words.",
            "for_english_learners": "Use pictures.",
            "remember_sounds": [{"letter": "s", "hint": "snake"}],
            "remember_tip": "Keep it quick.",
        },
    }
    return FakeLLM(scripts={"submit_plan": plan})


def test_training_topics_and_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(monkeypatch, training_llm())
    topics = client.get("/api/training/topics").json()
    assert len(topics) >= 5 and set(topics[0]) == {
        "id",
        "title",
        "summary",
        "training_word",
        "fits",
    }
    plan = client.get("/api/training/topics/blending").json()
    assert plan["remember"]["sentence"] == CLAIM["text"] and plan["remember"]["sounds"] == [
        {"letter": "s", "hint": "snake"}
    ]
    assert plan["idea"]["minutes"] == 10 and plan["short_idea"]["minutes"] == 5
    assert plan["evidence_label"] == "Very sure" and plan["sources"] and plan["disclaimer"]
    assert client.get("/api/training/topics/nope").status_code == 404


def test_training_plan_missing_ideas_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM(scripts={"submit_plan": {"answerable": True, "claims": [CLAIM], "idea": {}}})
    client, _ = setup(monkeypatch, llm)
    assert client.get("/api/training/topics/blending").status_code == 503


def test_refresher_statement_is_a_verified_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    second = {
        "text": "Blending helps children read whole words.",
        "passage_ids": ["src_0011_p001"],
        "quote": "pushing the sounds together smoothly",
    }
    llm = FakeLLM(scripts={"submit_plan": {"answerable": True, "claims": [CLAIM, second]}})
    client, _ = setup(monkeypatch, llm)
    body = client.get("/api/refresher/today").json()
    assert body["statement"] == CLAIM["text"] and body["is_true"] is True
    assert body["explanation"] == second["text"] and body["citations"] == [1]
    assert 1 <= body["day"] <= 5 and body["skills"] and body["picked"]


def test_refresher_with_one_claim_explains_with_the_exact_quote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = FakeLLM(scripts={"submit_plan": {"answerable": True, "claims": [CLAIM]}})
    conn = FakeConn()
    setup(monkeypatch, llm, conn)
    engine = Engine(conn, llm, FakeEmbedder(), NameRedactor(), Settings())  # type: ignore[arg-type]
    r = f.refresher(engine, today=date(2026, 11, 20))
    assert r.explanation == QUOTE and r.day == date(2026, 11, 20).toordinal() % 5 + 1


# ---------------------------------------------------------------- feedback, kill switch, auth
def test_feedback_updates_the_answer_row_or_stands_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    client, conn = setup(monkeypatch, FakeLLM(), qa_enabled=False)  # no model needed
    assert client.post("/api/feedback", json={"rating": "worked", "query_id": 1}).status_code == 204
    assert conn.feedback[-1] == ("worked", 1)
    assert client.post("/api/feedback", json={"rating": "stuck", "query_id": 99}).status_code == 204
    assert conn.feedback[-1] == ("unlinked", "stuck")
    assert client.post("/api/feedback", json={"rating": "stuck"}).status_code == 204
    assert client.post("/api/feedback", json={"rating": "angry"}).status_code == 422
    assert (
        client.post("/api/feedback", json={"rating": "worked", "comment": "x"}).status_code == 204
    )


def test_every_model_endpoint_is_off_with_the_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM(scripts={"submit_plan": plan_payload()})
    client, _ = setup(monkeypatch, llm, qa_enabled=False)
    calls = [
        client.post("/api/group-plan", json={"focus": "blend", "sounds": SOUNDS}),
        client.post("/api/story", json={"sounds": ["s"]}),
        client.post("/api/stuck", json={"pairs": [{"word": "cat", "said": "cut"}]}),
        client.get("/api/training/topics/blending"),
        client.get("/api/refresher/today"),
    ]
    assert [c.status_code for c in calls] == [503] * 5 and llm.calls == []


def test_model_endpoints_share_the_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(
        monkeypatch, FakeLLM(scripts={"submit_plan": plan_payload()}), rate_limit_per_minute=2
    )
    codes = [client.get("/api/refresher/today").status_code for _ in range(3)]
    assert codes[2] == 429 and "wait" in client.get("/api/refresher/today").json()["detail"]


def test_endpoints_need_a_signed_in_user(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = setup(monkeypatch, FakeLLM())
    locked = Settings(auth_mode="cognito", qa_enabled=True)  # no pool configured: fails closed
    app.dependency_overrides[get_settings] = lambda: locked
    for call in (
        client.get("/api/training/topics"),
        client.post("/api/decodable/check", json={"sounds": ["s"], "words": ["sat"]}),
        client.post("/api/feedback", json={"rating": "worked"}),
    ):
        assert call.status_code == 503
