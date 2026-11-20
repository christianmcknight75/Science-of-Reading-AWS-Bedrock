"""Turn parsed paragraphs into passages of about 300-500 words that keep section, pages and grade.

Rules
- Aim for 300-500 words. A passage never goes over HARD_MAX (600) words, section heading included.
- A passage starts with its section heading, so it reads on its own when shown to a teacher.
- Paragraphs are packed in order. A cut is made where the section, recommendation, evidence rating
  or grade changes.
- A passage under MERGE_BELOW (150) words is merged into its neighbour. The merge may cross a
  section boundary (the later heading is written in front of its text), but never a change of
  recommendation, evidence rating or grade, so a rating can never leak onto text it does not cover.
- A passage records the first and last PDF page it covers.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

MIN_WORDS = 300  # a passage is closed once it reaches this
MAX_WORDS = 500  # packing target ceiling
HARD_MAX = 600  # merging never goes past this
MERGE_BELOW = 150  # smaller passages are merged into a neighbour when that is allowed

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(])")


@dataclass(frozen=True)
class Block:
    """One paragraph of parsed text with where it came from."""

    text: str
    page: int
    section: str | None = None
    recommendation: str | None = None
    evidence_rating: str | None = None
    grade: str | None = None


@dataclass(frozen=True)
class Passage:
    passage_id: str
    section: str | None
    page: int
    text: str
    recommendation: str | None = None
    evidence_rating: str | None = None
    page_end: int | None = None
    grade: str | None = None


def words(text: str) -> int:
    return len(text.split())


def _cut_key(b: Block) -> tuple[str | None, str | None, str | None, str | None]:
    return (b.section, b.recommendation, b.evidence_rating, b.grade)


def _merge_key(b: Block) -> tuple[str | None, str | None, str | None]:
    return (b.recommendation, b.evidence_rating, b.grade)


def _split_long(block: Block) -> list[Block]:
    """A paragraph longer than MAX_WORDS is cut at sentence ends into pieces of <= MAX_WORDS
    (a single sentence that is itself too long is cut at word boundaries)."""
    if words(block.text) <= MAX_WORDS:
        return [block]
    units: list[str] = []
    for sentence in _SENTENCE_END.split(block.text):
        w = sentence.split()
        units.extend(" ".join(w[i : i + MAX_WORDS]) for i in range(0, len(w), MAX_WORDS))
    pieces: list[str] = []
    current: list[str] = []
    count = 0
    for u in units:
        n = words(u)
        if current and count + n > MAX_WORDS:
            pieces.append(" ".join(current))
            current, count = [], 0
        current.append(u)
        count += n
    if current:
        pieces.append(" ".join(current))
    return [dataclasses.replace(block, text=t) for t in pieces]


def render(group: list[Block]) -> str:
    """Passage text: each section heading in front of the text that falls under it."""
    parts: list[str] = []
    shown: str | None = None
    for b in group:
        if b.section and b.section != shown:
            parts.append(b.section)
            shown = b.section
        parts.append(b.text)
    return "\n\n".join(parts)


def _rendered_words(group: list[Block]) -> int:
    return words(render(group))


def chunk_blocks(source_id: str, blocks: list[Block]) -> list[Passage]:
    pieces = [p for b in blocks if b.text.strip() for p in _split_long(b)]

    groups: list[list[Block]] = []
    current: list[Block] = []
    count = 0
    for piece in pieces:
        n = words(piece.text)
        if current and (_cut_key(piece) != _cut_key(current[0]) or count + n > MAX_WORDS):
            groups.append(current)
            current, count = [], 0
        current.append(piece)
        count += n
        if count >= MIN_WORDS:
            groups.append(current)
            current, count = [], 0
    if current:
        groups.append(current)

    merged: list[list[Block]] = []
    for g in groups:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and _merge_key(prev[0]) == _merge_key(g[0])
            and (_rendered_words(prev) < MERGE_BELOW or _rendered_words(g) < MERGE_BELOW)
            and _rendered_words(prev + g) <= HARD_MAX
        ):
            prev.extend(g)
        else:
            merged.append(g)

    return [
        Passage(
            passage_id=f"{source_id}_p{i:03d}",
            section=g[0].section,
            page=min(b.page for b in g),
            page_end=max(b.page for b in g),
            text=render(g),
            recommendation=g[0].recommendation,
            evidence_rating=g[0].evidence_rating,
            grade=g[0].grade,
        )
        for i, g in enumerate(merged, start=1)
    ]
