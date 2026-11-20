"""Eval harness.  Run from the api/ folder:  uv run python ../evals/run.py [--mode ...]

Modes
  retrieval  (default, free)  router + retrieval only. No model call. Checks that no-research
                              and out-of-scope questions are caught and real ones find passages.
  fake                        full pipeline with a scripted stand-in model. Tests the plumbing.
  live                        full pipeline + plain-Claude baseline on Bedrock. COSTS MONEY.
                              Needs --live AND SOR_ALLOW_LIVE_MODEL_CALLS=1, only after approval.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "api"))
sys.path.insert(0, str(ROOT.parent))

from app import modelconfig, retrieval  # noqa: E402
from app.config import Settings  # noqa: E402
from app.embedding import LocalQueryEmbedder  # noqa: E402
from app.engine import Engine  # noqa: E402
from app.llm import LLM, BedrockLLM, LLMResult, ToolSpec  # noqa: E402
from app.redact import PresidioRedactor  # noqa: E402
from app.router import route  # noqa: E402
from app.schemas import AskRequest  # noqa: E402
from app.verifier import quote_in  # noqa: E402
from evals.metrics import PRICE_IN_PER_M, PRICE_OUT_PER_M, Result, gates, summarize  # noqa: E402

ALLOW_ENV = "SOR_ALLOW_LIVE_MODEL_CALLS"
BASELINE_TOOL = ToolSpec(
    "submit_plain_answer",
    "Return the answer.",
    {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
)
BASELINE_SYSTEM = "You are a helpful assistant for K-3 teachers. Answer the question briefly."


class _NoRow:
    def fetchone(self) -> None:
        return None


class EvalConn:
    """Real connection for reads; query_log writes are captured, never stored."""

    def __init__(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self._conn = conn
        self.captured: list[tuple[Any, ...]] = []

    def execute(self, sql: str, params: Any = None) -> Any:
        if "INSERT INTO query_log" in sql:
            self.captured.append(params)
            return _NoRow()
        return self._conn.execute(sql, params)

    def commit(self) -> None:
        pass


class CountingLLM:
    def __init__(self, inner: LLM) -> None:
        self.inner = inner
        self.input_tokens = self.output_tokens = 0
        self.prompts: list[str] = []
        self.answer_claims: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.input_tokens = self.output_tokens = 0
        self.prompts, self.answer_claims = [], []

    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult:
        out = self.inner.converse(
            model_id=model_id, system=system, user=user, max_tokens=max_tokens, tool=tool
        )
        self.input_tokens += out.input_tokens
        self.output_tokens += out.output_tokens
        self.prompts.append(user)
        if tool.name == "submit_answer" and out.tool_input:
            self.answer_claims = list(out.tool_input.get("claims", []))
        return out


class ScriptedLLM:
    """Stand-in model for `--mode fake`: cites the first passage it is shown, quoting it exactly."""

    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult:
        if tool.name == "submit_checks":
            n = user.count("<claim index=")
            checks = [{"index": i, "verdict": "supported"} for i in range(n)]
            return LLMResult({"checks": checks}, "", 600, 40)
        m = re.search(r'<passage id="([^"]+)"[^>]*>\n(.*?)\n</passage>', user, re.S)
        if not m:
            return LLMResult({"answerable": False, "claims": []}, "", 300, 20)
        words = m.group(2).split()
        quote = " ".join(words[:12])
        claim = {
            "text": "The research addresses this.",
            "passage_ids": [m.group(1)],
            "quote": quote,
        }
        return LLMResult({"answerable": True, "claims": [claim], "steps": []}, "", 4000, 120)


def _as_list(v: Any) -> list[str]:
    return [] if v is None else ([v] if isinstance(v, str) else list(v))


def load_questions() -> list[dict[str, Any]]:
    data = yaml.safe_load((ROOT / "questions.yaml").read_text())
    ids = [q["id"] for q in data]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question ids")
    return list(data)


def run_retrieval_only(
    conn: psycopg.Connection[dict[str, Any]], qs: list[dict[str, Any]], s: Settings
) -> list[Result]:
    redactor, embedder = PresidioRedactor(), LocalQueryEmbedder()
    out = []
    for q in qs:
        red = redactor.redact(q["question"])
        r = route(red)
        found: list[Any] = []
        if r.kind == "answer":
            found = retrieval.search(
                conn,
                red,
                embedder.embed_query(red),
                min_similarity=s.min_similarity,
                top_k=s.retrieval_top_k,
                recent_years=s.recent_years,
                grade=q.get("grade"),
            )
        if r.kind == "off_topic":
            kind = "no_research"
        elif r.kind != "answer":
            kind = "out_of_scope"
        else:
            kind = "answer" if found else "no_research"
        out.append(
            Result(
                id=q["id"],
                category=q["category"],
                expected=q["behavior"],
                kind=kind,
                label="n/a",
                retrieved_ids=[p.passage_id for p in found],
                pii_leaked=any(x in red for x in q.get("must_not_log", [])),
            )
        )
    return out


def run_pipeline(
    conn: psycopg.Connection[dict[str, Any]],
    qs: list[dict[str, Any]],
    s: Settings,
    llm: LLM,
) -> tuple[list[Result], list[dict[str, Any]]]:
    counting = CountingLLM(llm)
    ec = EvalConn(conn)
    engine = Engine(ec, counting, LocalQueryEmbedder(), PresidioRedactor(), s)  # type: ignore[arg-type]
    results = []
    for q in qs:
        counting.reset()
        ec.captured.clear()
        resp = engine.ask(AskRequest(question=q["question"], grade=q.get("grade")))
        _feature, redacted, ids, _answer, _label, ms, meta_json = ec.captured[0]
        meta = json.loads(meta_json)
        verifier = meta.get("verifier", {})
        leaked = any(
            x in redacted or any(x in p for p in counting.prompts)
            for x in q.get("must_not_log", [])
        )
        results.append(
            Result(
                id=q["id"],
                category=q["category"],
                expected=q["behavior"],
                kind=resp.kind,
                label=resp.evidence_label,
                allowed_labels=q.get("allowed_labels", []),
                latency_ms=ms,
                cited_ids=[x.passage_id for x in resp.sources],
                retrieved_ids=ids,
                raw_fabricated=int(verifier.get("fabricated_citations", 0)),
                raw_cited=sum(len(set(c.get("passage_ids", []))) for c in counting.answer_claims),
                quotes=[(x.quote, x.passage_text) for x in resp.sources if x.quote],
                pii_leaked=leaked,
                myth_expected=_as_list(q.get("myth_id")),
                source=q.get("source", "claude-draft"),
                myth_detected=meta.get("myths_detected", []),
                input_tokens=counting.input_tokens,
                output_tokens=counting.output_tokens,
            )
        )
    return results, [{"id": r.id, "kind": r.kind, "label": r.label} for r in results]


def run_baseline(qs: list[dict[str, Any]], llm: LLM, model_id: str) -> dict[str, Any]:
    """Plain Claude, no retrieval, no verifier: what a teacher gets from a generic chatbot."""
    answered_anyway = uncited = tin = tout = 0
    should_refuse = [q for q in qs if q["behavior"] != "answer"]
    for q in qs:
        r = llm.converse(
            model_id=model_id,
            system=BASELINE_SYSTEM,
            user=q["question"],
            max_tokens=400,
            tool=BASELINE_TOOL,
        )
        tin, tout, uncited = tin + r.input_tokens, tout + r.output_tokens, uncited + 1
        if q in should_refuse:
            answered_anyway += 1  # it answered a question that should not be answered
    return {
        "answers_with_citations_rate": 0.0,
        "uncited_answers": uncited,
        "answered_no_research_or_out_of_scope": f"{answered_anyway}/{len(should_refuse)}",
        "estimated_cost_usd": round(tin * PRICE_IN_PER_M / 1e6 + tout * PRICE_OUT_PER_M / 1e6, 4),
    }


def write_report(
    mode: str,
    summary: dict[str, Any],
    results: list[Result],
    baseline: dict[str, Any] | None,
    passed: dict[str, bool],
) -> Path:
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    payload = {
        "mode": mode,
        "summary": summary,
        "gates": passed,
        "baseline": baseline,
        "results": [r.__dict__ for r in results],
        "note": "Questions are not SME-reviewed.",
    }
    (out_dir / f"{stamp}-{mode}.json").write_text(json.dumps(payload, indent=2, default=str))
    lines = [
        f"# Eval report ({mode}) {stamp}",
        "",
        "Questions drafted by Claude, **not SME-reviewed**.",
        "",
        "## Gates",
        "",
    ]
    lines += [f"- {'PASS' if ok else 'FAIL'}: {name}" for name, ok in passed.items()]
    lines += ["", "## Summary", "", "| metric | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summary.items()]
    if baseline:
        lines += [
            "",
            "## Plain Claude, no retrieval (baseline)",
            "",
            "| metric | value |",
            "|---|---|",
        ]
        lines += [f"| {k} | {v} |" for k, v in baseline.items()]
    lines += [
        "",
        "## Per question",
        "",
        "| id | source | expected | got | label | latency ms | cited |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.id} | {r.source} | {r.expected} | {r.kind} | {r.label} | "
        f"{r.latency_ms} | {len(r.cited_ids)} |"
        for r in results
    ]
    path = out_dir / f"{stamp}-{mode}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["retrieval", "fake", "live"], default="retrieval")
    ap.add_argument("--live", action="store_true", help="required for --mode live")
    ap.add_argument("--profile", default="sor-dev")
    args = ap.parse_args(argv)
    s = Settings()
    qs = load_questions()
    if args.mode == "live" and not (args.live and os.environ.get(ALLOW_ENV) == "1"):
        print(f"Live mode spends money. Needs --live and {ALLOW_ENV}=1 (only after approval).")
        return 2
    with psycopg.connect(s.database_url, row_factory=dict_row) as conn:
        baseline = None
        if args.mode == "retrieval":
            results = run_retrieval_only(conn, qs, s)
            summary = summarize(results, quote_in)
            passed = {
                "no-research / out-of-scope caught before any model call": summary[
                    "honest_no_research_rate"
                ]
                == 1.0,
                "real questions find passages": summary["answered_when_expected_rate"] == 1.0,
                "no PII in redacted text": summary["pii_leaks"] == 0,
            }
        else:
            if args.mode == "fake":
                llm: LLM = ScriptedLLM()
            else:
                llm = BedrockLLM(
                    region=modelconfig.region(),
                    profile=args.profile,
                    guardrail_id=s.guardrail_id,
                    guardrail_version=s.guardrail_version,
                )
            results, _ = run_pipeline(conn, qs, s, llm)
            if args.mode == "live":
                baseline = run_baseline(qs, llm, modelconfig.model_id("generation"))
            summary = summarize(results, quote_in)
            passed = gates(summary)
    path = write_report(args.mode, summary, results, baseline, passed)
    for name, ok in passed.items():
        print(("PASS " if ok else "FAIL ") + name)
    print(f"report: {path}")
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
