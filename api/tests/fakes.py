"""Fakes so the whole Q&A engine runs with no AWS, no model download and no database."""

from __future__ import annotations

import datetime as dt
from typing import Any

from app.llm import LLMError, LLMResult, ToolSpec
from app.schemas import Passage

P1_TEXT = (
    "Teach students to blend letter sounds to read words. Blending means pushing the sounds "
    "together smoothly so the word can be heard and recognized."
)
P2_TEXT = "Explicit instruction in phonics helps beginning readers decode unfamiliar words."


def passage(pid: str = "src_0011_p001", **kw: Any) -> Passage:
    base: dict[str, Any] = {
        "passage_id": pid,
        "source_id": pid.split("_p")[0],
        "source_title": "Foundational Skills (IES Practice Guide)",
        "source_type": "practice_guide",
        "evidence_role": "primary",
        "evidence_rating": "Strong",
        "year": 2016,
        "section": "Recommendation 2",
        "page_label": "20",
        "page_end_label": "20",
        "text": P1_TEXT,
        "similarity": 0.8,
    }
    base.update(kw)
    return Passage(**base)


class FakeLLM:
    """Returns scripted tool output by tool name and records every call."""

    def __init__(
        self,
        answer: dict[str, Any] | None = None,
        checks: list[str] | str | None = "supported",
        fail_answer: bool = False,
        fail_check: bool = False,
    ) -> None:
        self.answer = answer
        self.checks = checks
        self.fail_answer = fail_answer
        self.fail_check = fail_check
        self.calls: list[dict[str, Any]] = []

    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult:
        self.calls.append(
            {"model_id": model_id, "tool": tool.name, "user": user, "max_tokens": max_tokens}
        )
        if tool.name == "submit_answer":
            if self.fail_answer:
                raise LLMError("boom")
            return LLMResult(self.answer, "", 1000, 200)
        if self.fail_check:
            raise LLMError("boom")
        n = user.count("<claim index=")
        verdicts = self.checks if isinstance(self.checks, list) else [self.checks] * n
        items = [{"index": i, "verdict": v} for i, v in enumerate(verdicts)]
        return LLMResult({"checks": items}, "", 500, 50)


class Cursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConn:
    """Stands in for the database: the engine only needs the query_log insert and two selects."""

    def __init__(self, myth_rows: list[dict[str, Any]] | None = None) -> None:
        self.logged: list[tuple[Any, ...]] = []
        self.myth_rows = myth_rows or []
        self.commits = 0

    def execute(self, sql: str, params: Any = None) -> Cursor:
        if "INSERT INTO query_log" in sql:
            self.logged.append(params)
            return Cursor([])
        if "FROM myths" in sql:
            return Cursor(self.myth_rows)
        if "max(approved_at)" in sql:
            return Cursor([{"d": dt.datetime(2026, 11, 19, tzinfo=dt.UTC)}])
        raise AssertionError(f"unexpected SQL: {sql[:60]}")

    def commit(self) -> None:
        self.commits += 1


class FakeEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384


class NameRedactor:
    """Masks the name 'Jamal' so tests can prove the raw name never reaches the model or log."""

    def redact(self, text: str) -> str:
        return text.replace("Jamal", "[PERSON]")
