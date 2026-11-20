"""Split parsed pages into 300-500 word passages that keep section and page."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

MIN_WORDS = 300
MAX_WORDS = 500


@dataclass(frozen=True)
class Block:
    """One paragraph of parsed text with where it came from."""

    text: str
    page: int
    section: str | None = None
    recommendation: str | None = None
    evidence_rating: str | None = None


@dataclass(frozen=True)
class Passage:
    passage_id: str
    section: str | None
    page: int
    text: str
    recommendation: str | None = None
    evidence_rating: str | None = None


def _key(b: Block) -> tuple[str | None, str | None, str | None]:
    return (b.section, b.recommendation, b.evidence_rating)


def _words(text: str) -> int:
    return len(text.split())


def _split_long(block: Block) -> list[Block]:
    """A paragraph longer than MAX_WORDS is cut at word boundaries into <= MAX_WORDS pieces."""
    words = block.text.split()
    if len(words) <= MAX_WORDS:
        return [block]
    pieces = []
    for i in range(0, len(words), MAX_WORDS):
        pieces.append(dataclasses.replace(block, text=" ".join(words[i : i + MAX_WORDS])))
    return pieces


def chunk_blocks(source_id: str, blocks: list[Block]) -> list[Passage]:
    """Greedy packing. A passage never crosses a section boundary.

    Page recorded is the page the passage starts on. A trailing piece shorter than MIN_WORDS is
    merged into the previous passage of the same section when that stays within MAX_WORDS;
    otherwise it is kept (short sections are real).
    """
    pieces = [p for b in blocks if b.text.strip() for p in _split_long(b)]
    groups: list[list[Block]] = []
    current: list[Block] = []
    count = 0
    for piece in pieces:
        n = _words(piece.text)
        section_changed = bool(current) and _key(piece) != _key(current[0])
        if current and (section_changed or count + n > MAX_WORDS):
            groups.append(current)
            current, count = [], 0
        current.append(piece)
        count += n
        if count >= MIN_WORDS:
            groups.append(current)
            current, count = [], 0
    if current:
        prev = groups[-1] if groups else None
        if (
            prev
            and _key(prev[0]) == _key(current[0])
            and sum(_words(b.text) for b in prev) + count <= MAX_WORDS
        ):
            prev.extend(current)
        else:
            groups.append(current)

    passages = []
    for i, group in enumerate(groups, start=1):
        passages.append(
            Passage(
                passage_id=f"{source_id}_p{i:03d}",
                section=group[0].section,
                page=group[0].page,
                text="\n\n".join(b.text for b in group),
                recommendation=group[0].recommendation,
                evidence_rating=group[0].evidence_rating,
            )
        )
    return passages
