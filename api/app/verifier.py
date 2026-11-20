"""Verifier: nothing reaches a teacher unless it passes all three checks.

(a) every cited passage_id was retrieved for this request (anything else is a fabricated citation);
(b) the claim's quote appears verbatim in one of its cited passages;
(c) a model check says each claim is supported by its cited passages.
Unsupported claims are removed. If too little remains, the engine falls back to the honest
"not enough research" reply. The checks fail closed: a failed or garbled model check removes the
claims it could not confirm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .llm import LLM, LLMError
from .prompt import CHECK_SYSTEM, CHECK_TOOL, build_check_prompt
from .schemas import Claim, Passage

MIN_QUOTE_WORDS = 3
MIN_KEPT_FRACTION = 0.5

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def normalize(text: str) -> str:
    """Whitespace and typographic quote/dash variants are equal. Nothing else is (case counts)."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


def quote_in(quote: str, passage_text: str) -> bool:
    q = normalize(quote)
    return len(q.split()) >= MIN_QUOTE_WORDS and q in normalize(passage_text)


@dataclass
class VerifierResult:
    kept: list[Claim] = field(default_factory=list)
    removed: list[dict[str, str]] = field(default_factory=list)
    fabricated_citations: int = 0
    quote_mismatches: int = 0
    unsupported: int = 0
    contradicted_passage_ids: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_claims: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.kept) and len(self.kept) / self.total_claims >= MIN_KEPT_FRACTION

    def summary(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total_claims": self.total_claims,
            "kept": len(self.kept),
            "fabricated_citations": self.fabricated_citations,
            "quote_mismatches": self.quote_mismatches,
            "unsupported": self.unsupported,
            "removed": self.removed,
        }


def verify(
    claims: list[Claim],
    retrieved: dict[str, Passage],
    *,
    llm: LLM,
    model_id: str,
    max_tokens: int,
) -> VerifierResult:
    res = VerifierResult(total_claims=len(claims))
    candidates: list[Claim] = []
    for c in claims:
        valid = [pid for pid in dict.fromkeys(c.passage_ids) if pid in retrieved]
        res.fabricated_citations += len(set(c.passage_ids)) - len(valid)
        if not valid:
            res.removed.append({"claim": c.text, "reason": "no retrieved passage cited"})
            continue
        if not any(quote_in(c.quote, retrieved[pid].text) for pid in valid):
            res.quote_mismatches += 1
            res.removed.append({"claim": c.text, "reason": "quote not found verbatim"})
            continue
        candidates.append(Claim(c.text, valid, c.quote))
    if candidates:
        _claim_check(candidates, retrieved, res, llm, model_id, max_tokens)
    return res


def _claim_check(
    candidates: list[Claim],
    retrieved: dict[str, Passage],
    res: VerifierResult,
    llm: LLM,
    model_id: str,
    max_tokens: int,
) -> None:
    verdicts: dict[int, str] = {}
    try:
        out = llm.converse(
            model_id=model_id,
            system=CHECK_SYSTEM,
            user=build_check_prompt(candidates, retrieved),
            max_tokens=max_tokens,
            tool=CHECK_TOOL,
        )
        res.input_tokens += out.input_tokens
        res.output_tokens += out.output_tokens
        for item in (out.tool_input or {}).get("checks", []):
            if isinstance(item, dict) and isinstance(item.get("index"), int):
                verdicts[item["index"]] = str(item.get("verdict"))
    except LLMError:
        pass  # fail closed: no verdicts, so nothing is confirmed
    for i, c in enumerate(candidates):
        verdict = verdicts.get(i)
        if verdict == "supported":
            res.kept.append(c)
            continue
        res.unsupported += 1
        res.removed.append({"claim": c.text, "reason": verdict or "claim check unavailable"})
        if verdict == "contradicted":
            res.contradicted_passage_ids.extend(c.passage_ids)
