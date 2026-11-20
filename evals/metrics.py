"""Eval metrics. Pure functions over per-question results so they can be unit-tested."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Bedrock list price, USD per million tokens (Sonnet 4.5). Third-party listing: confirm on the
# AWS pricing page (docs/DECISIONS.md). Used only for the report's cost line.
PRICE_IN_PER_M = 3.0
PRICE_OUT_PER_M = 15.0
P95_LIMIT_MS = 8000


@dataclass
class Result:
    id: str
    category: str
    expected: str  # answer | no_research | out_of_scope
    kind: str  # what the engine returned
    label: str
    allowed_labels: list[str] = field(default_factory=list)
    latency_ms: int = 0
    cited_ids: list[str] = field(default_factory=list)  # shown to the teacher
    retrieved_ids: list[str] = field(default_factory=list)
    raw_fabricated: int = 0  # ids the model cited that were not retrieved (before the verifier)
    raw_cited: int = 0
    quotes: list[tuple[str, str]] = field(default_factory=list)  # (quote, passage text) shown
    pii_leaked: bool = False
    myth_expected: str | None = None
    myth_detected: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


def p95(values: list[int]) -> int:
    if not values:
        return 0
    s = sorted(values)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def _rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def summarize(results: list[Result], quote_in: Any) -> dict[str, Any]:
    answered = [r for r in results if r.kind == "answer"]
    shown = sum(len(r.cited_ids) for r in answered)
    not_retrieved = sum(len(set(r.cited_ids) - set(r.retrieved_ids)) for r in answered)
    quotes = [q for r in answered for q in r.quotes]
    quote_ok = sum(1 for q, text in quotes if quote_in(q, text))
    with_label = [r for r in answered if r.allowed_labels]
    label_ok = sum(1 for r in with_label if r.label in r.allowed_labels)
    honest_den = [r for r in results if r.expected in ("no_research", "out_of_scope")]
    honest_ok = sum(1 for r in honest_den if r.kind != "answer")
    scope_den = [r for r in results if r.expected == "out_of_scope"]
    scope_ok = sum(1 for r in scope_den if r.kind == "out_of_scope")
    answer_den = [r for r in results if r.expected == "answer"]
    answer_ok = sum(1 for r in answer_den if r.kind == "answer")
    myth_den = [r for r in results if r.myth_expected]
    myth_ok = sum(1 for r in myth_den if r.myth_expected in r.myth_detected)
    tin = sum(r.input_tokens for r in results)
    tout = sum(r.output_tokens for r in results)
    return {
        "questions": len(results),
        "fabricated_citations_shown": not_retrieved,
        "citations_shown": shown,
        "model_fabricated_before_verifier": sum(r.raw_fabricated for r in results),
        "model_citations_before_verifier": sum(r.raw_cited for r in results),
        "quote_match_rate": _rate(quote_ok, len(quotes)),
        "quotes_checked": len(quotes),
        "label_correct_rate": _rate(label_ok, len(with_label)),
        "honest_no_research_rate": _rate(honest_ok, len(honest_den)),
        "out_of_scope_refused_rate": _rate(scope_ok, len(scope_den)),
        "answered_when_expected_rate": _rate(answer_ok, len(answer_den)),
        "myth_detected_rate": _rate(myth_ok, len(myth_den)),
        "pii_leaks": sum(1 for r in results if r.pii_leaked),
        "latency_p95_ms": p95([r.latency_ms for r in results]),
        "input_tokens": tin,
        "output_tokens": tout,
        "estimated_cost_usd": round(tin * PRICE_IN_PER_M / 1e6 + tout * PRICE_OUT_PER_M / 1e6, 4),
    }


def gates(s: dict[str, Any]) -> dict[str, bool]:
    """CLAUDE.md quality gates. A rate of None (nothing to measure) does not pass silently."""
    return {
        "fabricated citations shown = 0": s["fabricated_citations_shown"] == 0,
        "quote match = 100%": s["quote_match_rate"] == 1.0,
        "no-research cases answered honestly = 100%": s["honest_no_research_rate"] == 1.0,
        "no PII in logs": s["pii_leaks"] == 0,
        f"latency p95 < {P95_LIMIT_MS} ms": s["latency_p95_ms"] < P95_LIMIT_MS,
    }
