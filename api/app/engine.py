"""Q&A pipeline: redact -> route -> retrieve -> threshold -> prompt -> Claude -> verify ->
evidence label -> myth check -> response -> query_log.

Every step that can say "no" says it honestly. No model is called when there is nothing to
ground an answer on.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psycopg

from . import modelconfig, myths, retrieval
from .config import Settings
from .embedding import QueryEmbedder
from .evidence import CitedPassage, EvidenceResult, evidence_result
from .llm import LLM, LLMError
from .prompt import ANSWER_TOOL, SYSTEM, build_answer_prompt
from .redact import Redactor
from .router import route
from .schemas import (
    DISCLAIMER,
    OFFER,
    AnswerResponse,
    AskRequest,
    Claim,
    Draft,
    Passage,
    ResearchClaim,
    SourceOut,
    Step,
    StepOut,
    WatchOut,
)
from .verifier import verify

NO_RESEARCH = "No research found"
MAX_STEPS = 3


@dataclass
class Engine:
    conn: psycopg.Connection[dict[str, Any]]
    llm: LLM
    embedder: QueryEmbedder
    redactor: Redactor
    settings: Settings
    clock: Callable[[], float] = time.perf_counter

    def ask(self, req: AskRequest) -> AnswerResponse:
        started = self.clock()
        meta: dict[str, Any] = {}
        redacted = self.redactor.redact(req.question)
        response, retrieved_ids = self._run(req, redacted, meta)
        response.content_last_updated = self.last_updated()
        self._log(redacted, retrieved_ids, response, int((self.clock() - started) * 1000), meta)
        return response

    # ------------------------------------------------------------------ pipeline
    def _run(
        self, req: AskRequest, redacted: str, meta: dict[str, Any]
    ) -> tuple[AnswerResponse, list[str]]:
        r = route(redacted)
        meta["route"] = r.kind
        if r.kind == "off_topic":
            meta["route_reason"] = r.reason
            return (
                _non_answer(
                    "no_research",
                    "I did not find research in my library that answers this, so I won't guess.",
                ),
                [],
            )
        if r.kind != "answer":
            meta["route_reason"] = r.reason
            return _non_answer("out_of_scope", r.reply), []

        s = self.settings
        found = retrieval.search(
            self.conn,
            redacted,
            self.embedder.embed_query(redacted),
            min_similarity=s.min_similarity,
            top_k=s.retrieval_top_k,
            recent_years=s.recent_years,
            grade=req.grade,
        )
        ids = [p.passage_id for p in found]
        if not found:
            return (
                _non_answer(
                    "no_research",
                    "I did not find research in my library that answers this, so I won't guess.",
                ),
                ids,
            )
        retrieved = {p.passage_id: p for p in found}

        draft = self._generate(redacted, found, req.grade, meta)
        if draft is None or not draft.answerable or not draft.claims:
            return _non_answer("insufficient", _INSUFFICIENT), ids

        result = verify(
            draft.claims,
            retrieved,
            llm=self.llm,
            model_id=modelconfig.model_id("claim_check"),
            max_tokens=s.claim_check_max_tokens,
        )
        meta["verifier"] = result.summary()
        meta["tokens"] = meta.get("tokens", 0) + result.input_tokens + result.output_tokens
        if not result.ok:
            return _non_answer("insufficient", _INSUFFICIENT), ids
        return self._assemble(redacted, result.kept, draft.steps, retrieved, result, meta), ids

    def _generate(
        self, redacted: str, found: list[Passage], grade: str | None, meta: dict[str, Any]
    ) -> Draft | None:
        try:
            out = self.llm.converse(
                model_id=modelconfig.model_id("generation"),
                system=SYSTEM,
                user=build_answer_prompt(redacted, found, grade),
                max_tokens=self.settings.max_output_tokens,
                tool=ANSWER_TOOL,
            )
        except LLMError as exc:
            meta["generation_error"] = str(exc)
            return None
        meta["tokens"] = out.input_tokens + out.output_tokens
        return parse_draft(out.tool_input)

    def _assemble(
        self,
        redacted: str,
        kept: list[Claim],
        steps: list[Step],
        retrieved: dict[str, Passage],
        result: Any,
        meta: dict[str, Any],
    ) -> AnswerResponse:
        cited = cite(kept, retrieved, result.contradicted_passage_ids)
        numbers = cited.numbers

        # myth check: the correction is shown only with its own cited passages
        watch: WatchOut | None = None
        found_myths = myths.detect(redacted, myths.load_myths(self.conn))
        meta["myths_detected"] = [m.myth_id for m in found_myths]
        for m in found_myths:
            linked = retrieval.fetch(self.conn, m.passage_ids)
            if not linked:
                meta.setdefault("myths_without_sources", []).append(m.myth_id)
                continue
            for p in linked:
                retrieved.setdefault(p.passage_id, p)
                numbers.setdefault(p.passage_id, len(numbers) + 1)
            watch = WatchOut(
                myth=m.name,
                correction=m.sor_correction,
                citations=sorted(numbers[p.passage_id] for p in linked),
            )
            break

        sources = sources_out(numbers, retrieved, cited.quotes)
        research = cited.research
        evidence = cited.evidence
        return AnswerResponse(
            kind="answer",
            evidence_label=evidence.label,
            mixed=evidence.mixed,
            short_answer=" ".join(
                f"{c.text} {''.join(f'[{n}]' for n in c.citations)}" for c in research
            ),
            research_says=research,
            idea_for_class=[StepOut(text=s.text, minutes=s.minutes) for s in steps[:MAX_STEPS]],
            watch_out=watch,
            sources=sources,
        )

    # ------------------------------------------------------------------ logging
    def last_updated(self) -> str | None:
        row = self.conn.execute(
            "SELECT max(approved_at) AS d FROM sources WHERE status = 'approved'"
        ).fetchone()
        return row["d"].date().isoformat() if row and row["d"] else None

    def log(
        self,
        feature: str,
        redacted: str,
        ids: list[str],
        summary: str,
        label: str,
        ms: int,
        meta: dict[str, Any],
    ) -> int | None:
        """One query_log row. Redacted text only (Public Records Act: logs are records)."""
        row = self.conn.execute(
            """INSERT INTO query_log (feature, redacted_question, passage_ids, answer,
                                      evidence_label, latency_ms, verifier_result)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb) RETURNING id""",
            (feature, redacted, ids, summary, label, ms, json.dumps(meta)),
        ).fetchone()
        self.conn.commit()
        return int(row["id"]) if row and row.get("id") is not None else None

    def _log(
        self, redacted: str, ids: list[str], r: AnswerResponse, ms: int, meta: dict[str, Any]
    ) -> None:
        r.query_id = self.log(
            "qa",
            redacted,
            ids,
            r.short_answer or r.message,
            r.evidence_label,
            ms,
            {"kind": r.kind, **meta},
        )


_INSUFFICIENT = (
    "I found related research, but I could not put together an answer that the sources fully "
    "support, so I won't guess."
)


def _non_answer(kind: str, message: str) -> AnswerResponse:
    return AnswerResponse(
        kind=kind,  # type: ignore[arg-type]
        evidence_label=NO_RESEARCH,
        message=message,
        offer=OFFER,
        disclaimer=DISCLAIMER,
    )


@dataclass
class Cited:
    numbers: dict[str, int]
    research: list[ResearchClaim]
    quotes: dict[str, str]
    evidence: EvidenceResult


def cite(kept: list[Claim], retrieved: dict[str, Passage], contradicted_ids: list[str]) -> Cited:
    """Citation numbers (in order of first use), cited claims, quotes and the rule-based label."""
    numbers: dict[str, int] = {}
    for c in kept:
        for pid in c.passage_ids:
            numbers.setdefault(pid, len(numbers) + 1)
    research = [
        ResearchClaim(text=c.text, citations=[numbers[pid] for pid in c.passage_ids]) for c in kept
    ]
    quotes = {pid: c.quote for c in reversed(kept) for pid in c.passage_ids}
    cited_ids = {pid for c in kept for pid in c.passage_ids}
    evidence = evidence_result(
        [_cited(retrieved[pid], contradicts=False) for pid in cited_ids]
        + [_cited(retrieved[pid], contradicts=True) for pid in contradicted_ids]
    )
    return Cited(numbers, research, quotes, evidence)


def sources_out(
    numbers: dict[str, int], retrieved: dict[str, Passage], quotes: dict[str, str]
) -> list[SourceOut]:
    return [
        _source_out(n, retrieved[pid], quotes.get(pid))
        for pid, n in sorted(numbers.items(), key=lambda kv: kv[1])
    ]


def parse_draft(data: dict[str, Any] | None) -> Draft | None:
    """Validate the model's tool output. Anything malformed means no draft (honest fallback)."""
    if not isinstance(data, dict):
        return None
    try:
        claims = [
            Claim(str(c["text"]).strip(), [str(i) for i in c["passage_ids"]], str(c["quote"]))
            for c in data.get("claims", [])
        ]
        steps = [
            Step(str(s["text"]).strip(), max(1, min(30, int(s["minutes"]))))
            for s in data.get("steps", [])
        ]
    except (KeyError, TypeError, ValueError):
        return None
    return Draft(answerable=bool(data.get("answerable")), claims=claims, steps=steps)


def _cited(p: Passage, *, contradicts: bool) -> CitedPassage:
    return CitedPassage(
        source_id=p.source_id,
        source_type=p.source_type,
        evidence_role=p.evidence_role,
        evidence_rating=p.evidence_rating,
        year=p.year,
        randomized=p.randomized,
        sample_size=p.sample_size,
        has_comparison_group=p.has_comparison_group,
        contradicts=contradicts,
    )


def _source_out(n: int, p: Passage, quote: str | None) -> SourceOut:
    page = (
        p.page_label
        if p.page_label == p.page_end_label or not p.page_end_label
        else (f"{p.page_label}-{p.page_end_label}")
    )
    return SourceOut(
        n=n,
        passage_id=p.passage_id,
        title=p.source_title,
        year=p.year,
        source_type=p.source_type,
        section=p.section,
        page=page,
        passage_text=p.text,
        quote=quote,
    )
