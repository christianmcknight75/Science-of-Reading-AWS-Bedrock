"""Eval metrics, and the harness's safety rails (live mode must refuse without approval)."""

from __future__ import annotations

from typing import Any

import pytest
from evals import run
from evals.metrics import Result, gates, p95, summarize

from app.verifier import quote_in

TEXT = "Blending means pushing the sounds together smoothly so the word can be heard."


def res(**kw: Any) -> Result:
    base: dict[str, Any] = {
        "id": "q",
        "category": "core",
        "expected": "answer",
        "kind": "answer",
        "label": "Very sure",
        "allowed_labels": ["Very sure"],
        "latency_ms": 100,
        "cited_ids": ["a"],
        "retrieved_ids": ["a"],
        "quotes": [("Blending means pushing the sounds", TEXT)],
    }
    base.update(kw)
    return Result(**base)


def test_p95() -> None:
    assert p95([]) == 0 and p95([5]) == 5
    assert p95(list(range(1, 101))) == 95


def test_clean_run_passes_every_gate() -> None:
    results = [
        res(),
        res(
            id="n",
            expected="no_research",
            kind="no_research",
            cited_ids=[],
            quotes=[],
            label="No research found",
            allowed_labels=[],
        ),
    ]
    s = summarize(results, quote_in)
    assert s["fabricated_citations_shown"] == 0 and s["quote_match_rate"] == 1.0
    assert s["honest_no_research_rate"] == 1.0 and all(gates(s).values())


def test_a_citation_that_was_not_retrieved_is_counted_and_fails_the_gate() -> None:
    s = summarize([res(cited_ids=["a", "zzz"])], quote_in)
    assert s["fabricated_citations_shown"] == 1 and not gates(s)["fabricated citations shown = 0"]


def test_a_changed_quote_fails_quote_match() -> None:
    s = summarize([res(quotes=[("Blending is pushing sounds", TEXT)])], quote_in)
    assert s["quote_match_rate"] == 0.0 and not gates(s)["quote match = 100%"]


def test_answering_a_no_research_question_is_dishonest() -> None:
    s = summarize([res(expected="no_research", kind="answer")], quote_in)
    assert s["honest_no_research_rate"] == 0.0


def test_pii_leak_and_slow_p95_fail_gates() -> None:
    s = summarize([res(pii_leaked=True, latency_ms=9000)], quote_in)
    g = gates(s)
    assert not g["no PII in logs"] and not g["latency p95 < 8000 ms"]


def test_label_and_myth_rates() -> None:
    results = [res(), res(label="Not sure yet", myth_expected=["m1", "m2"], myth_detected=["m2"])]
    s = summarize(results, quote_in)
    assert s["label_correct_rate"] == 0.5 and s["myth_detected_rate"] == 1.0


def test_nothing_to_measure_is_not_a_silent_pass() -> None:
    s = summarize([], quote_in)
    assert s["quote_match_rate"] is None and not gates(s)["quote match = 100%"]


def test_question_file_is_well_formed_and_marked_unreviewed() -> None:
    qs = run.load_questions()
    assert len(qs) >= 36
    assert sum(1 for q in qs if q.get("source") == "team") == 6
    assert not any("letter we are learning today" in q["question"] for q in qs)  # student-facing
    cats = {q["category"] for q in qs}
    assert {"core", "myth", "no_research", "out_of_scope", "pii"} <= cats
    assert all(q["behavior"] in ("answer", "no_research", "out_of_scope") for q in qs)
    assert all(q["reviewed"] is False for q in qs)  # flip per question only after SME review


def test_live_mode_refuses_without_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(run.ALLOW_ENV, raising=False)
    assert run.main(["--mode", "live"]) == 2
    assert run.main(["--mode", "live", "--live"]) == 2  # flag alone is not enough
    monkeypatch.setenv(run.ALLOW_ENV, "1")
    assert run.main(["--mode", "live"]) == 2  # env alone is not enough either
