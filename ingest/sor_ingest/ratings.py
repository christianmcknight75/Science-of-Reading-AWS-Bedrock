"""WWC practice guides rate the evidence behind each recommendation (Strong / Moderate / Minimal).

We keep that rating on every passage that belongs to the recommendation, so the answer label can
use it. Headings are carried as empty-text marker blocks by the parser, so a heading such as
"Level of evidence: Strong" is seen even when no body text follows it.
"""

from __future__ import annotations

import dataclasses
import re

from .chunking import Block

# A heading reads "Recommendation 2. Title", "Recommendation 2: Title" or just "Recommendation 2".
# Prose such as "Recommendation 4 addresses using data..." is not a heading.
# Older WWC guides (2009-2010) rate evidence Strong / Moderate / Low. Low is the same bottom tier as
# the later "Minimal", so it is stored as Minimal (decision 2026-11-20).
RATING_NAMES = {"strong": "Strong", "moderate": "Moderate", "minimal": "Minimal", "low": "Minimal"}
REC_RE = re.compile(r"^\s*Recommendation\s+(\d+)\s*(?:[.:]|$)", re.IGNORECASE)
LEVEL_RE = re.compile(
    r"Level of evidence\s*[:\-–—]?\s*(Strong|Moderate|Minimal|Low)\b", re.IGNORECASE
)
RESET_RE = re.compile(
    r"^\s*(Appendix|References|Endnotes|Glossary|Introduction|Overview|Acknowledg|Disclosure)",
    re.IGNORECASE,
)


LOOSE_REC_RE = re.compile(r"^\s*Recommendation\s+(\d+)\b", re.IGNORECASE)


def _start(text: str, loose: bool = False) -> re.Match[str] | None:
    """A recommendation's own heading. A line that lists several recommendations (a table of
    contents or an overview) is not the start of any one of them."""
    if len(re.findall(r"Recommendation\s+\d+", text, re.IGNORECASE)) != 1:
        return None
    return (LOOSE_REC_RE if loose else REC_RE).match(text)


def annotate_recommendations(blocks: list[Block]) -> list[Block]:
    """Fill in `recommendation` and `evidence_rating` on blocks where the document has them.

    Recommendation headings are recognised strictly first ("Recommendation 2." or a bare
    "Recommendation 2"). If that finds no rating anywhere (a guide that states its ratings only in
    an appendix, next to prose that begins "Recommendation 1 advocates..."), the looser rule is
    used: a block that starts with "Recommendation N"."""
    strict = _annotate(blocks, loose=False)
    if any(b.evidence_rating for b in strict):
        return strict
    return _annotate(blocks, loose=True)


def _annotate(blocks: list[Block], loose: bool) -> list[Block]:
    rec_key: str | None = None
    rec_label: dict[str, str] = {}
    rating: dict[str, str] = {}
    keys: list[str | None] = []
    for b in blocks:
        heading = b.section or ""
        if RESET_RE.match(heading):
            rec_key = None
        m = _start(heading, loose) or (_start(b.text, loose) if b.text.strip() else None)
        if m:
            rec_key = f"Recommendation {m.group(1)}"
            rec_label.setdefault(rec_key, (heading if _start(heading, loose) else b.text)[:200])
        keys.append(rec_key)
        if rec_key:
            found = LEVEL_RE.search(heading) or LEVEL_RE.search(b.text)
            if found:
                rating.setdefault(rec_key, RATING_NAMES[found.group(1).lower()])
    return [
        dataclasses.replace(b, recommendation=rec_label.get(k) if k else None,
                            evidence_rating=rating.get(k) if k else None)
        for b, k in zip(blocks, keys, strict=True)
    ]  # fmt: skip
