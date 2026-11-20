"""WWC practice guides rate the evidence behind each recommendation (Strong / Moderate / Minimal).

We keep that rating on every passage that belongs to the recommendation, so the answer label can
use it. Headings are carried as empty-text marker blocks by the parser, so a heading such as
"Level of evidence: Strong" is seen even when no body text follows it.
"""

from __future__ import annotations

import dataclasses
import re

from .chunking import Block

REC_RE = re.compile(r"^\s*Recommendation\s+(\d+)\b", re.IGNORECASE)
LEVEL_RE = re.compile(r"Level of evidence\s*[:\-–—]?\s*(Strong|Moderate|Minimal)\b", re.IGNORECASE)
RESET_RE = re.compile(
    r"^\s*(Appendix|References|Endnotes|Glossary|Introduction|Overview|Acknowledg|Disclosure)",
    re.IGNORECASE,
)


def annotate_recommendations(blocks: list[Block]) -> list[Block]:
    """Fill in `recommendation` and `evidence_rating` on blocks where the document has them."""
    rec_key: str | None = None
    rec_label: dict[str, str] = {}
    rating: dict[str, str] = {}
    keys: list[str | None] = []
    for b in blocks:
        heading = b.section or ""
        if RESET_RE.match(heading):
            rec_key = None
        m = REC_RE.match(heading) or (REC_RE.match(b.text) if b.text.strip() else None)
        if m:
            rec_key = f"Recommendation {m.group(1)}"
            rec_label.setdefault(rec_key, (heading if REC_RE.match(heading) else b.text)[:200])
        keys.append(rec_key)
        if rec_key:
            found = LEVEL_RE.search(heading) or LEVEL_RE.search(b.text)
            if found:
                rating.setdefault(rec_key, found.group(1).capitalize())
    return [
        dataclasses.replace(b, recommendation=rec_label.get(k) if k else None,
                            evidence_rating=rating.get(k) if k else None)
        for b, k in zip(blocks, keys, strict=True)
    ]  # fmt: skip
