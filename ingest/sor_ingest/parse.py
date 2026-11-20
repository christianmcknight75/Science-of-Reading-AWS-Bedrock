"""PDF -> Blocks using PyMuPDF.

Headings are short lines set in a larger or bold font than body text. Text that should never be
retrieved is dropped here: repeated page headers and footers, page numbers, tables of contents,
reference lists, author bios and acknowledgements. Heading markers (empty text) are always kept,
because the evidence-rating step reads them.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from pathlib import Path

import pymupdf

from .chunking import Block

# A heading that starts a part of the document we do not keep. Skipping lasts until the next
# heading that is not one of these.
SKIP_SECTION_RE = re.compile(
    r"^\s*(table of contents|contents|list of (tables|figures|exhibits|boxes|abbreviations)"
    r"|references?( list)?|reference list|bibliography|works cited|endnotes?"
    r"|about the authors?|about the author\(s\)|authors?( information| biograph\w*| bios?)?"
    r"|author(s)? note|contributors?|notes? on contributors|biograph\w*"
    r"|acknowledg\w*|disclosures?|disclaimer|copyright|suggested citation|recommended citation"
    r"|how to cite|funding|conflicts? of interest|declarations?|data availability( statement)?"
    r"|author contributions?|ethics statement|open access|affiliations?|correspondence)\b",
    re.IGNORECASE,
)
PAGE_NUMBER_RE = re.compile(r"^\W*(page\s+)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\W*$", re.IGNORECASE)
TOC_LEADER_RE = re.compile(r"(\.\s?){4,}\s*\d+\s*$|…+\s*\d+\s*$")
# "Smith, J. A., & Lee, K. (2019)." / "National Reading Panel. (2000)." at the start of a block
REFERENCE_RE = re.compile(
    r"^[A-Z][\w'’\-]+(,\s*(?:[A-Z]\.\s?){1,3}|\.)"
    r".{0,250}?\(\s*(?:19|20)\d\d[a-z]?\s*\)",
)
REFERENCE_TAIL_RE = re.compile(
    r"\bdoi\b|https?://|\bpp?\.\s*\d|\b\d+\(\d+\)|\bvol\.|\bRetrieved\b", re.I
)
EDGE = 0.07  # top and bottom 7% of a page are where headers and footers live


def _norm(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def _is_reference(text: str) -> bool:
    return (
        len(text.split()) <= 150
        and bool(REFERENCE_RE.match(text))
        and bool(REFERENCE_TAIL_RE.search(text))
    )


def _repeated_edge_texts(
    pages: list[list[tuple[str, tuple[float, float, float, float]]]], heights: list[float]
) -> set[str]:
    """Normalised texts that sit at the top/bottom of the page on 3 or more pages, or that repeat
    on at least a third of all pages (a running title in the middle of the page)."""
    seen: dict[str, set[int]] = defaultdict(set)
    edge: dict[str, set[int]] = defaultdict(set)
    for i, (blocks, h) in enumerate(zip(pages, heights, strict=True)):
        for text, (_x0, y0, _x1, y1) in blocks:
            if len(text.split()) > 25:
                continue
            key = _norm(text)
            seen[key].add(i)
            if y1 < h * EDGE * 1.6 or y0 > h * (1 - EDGE * 1.6):
                edge[key].add(i)
    n = len(pages)
    repeated = {k for k, v in edge.items() if len(v) >= 3}
    repeated |= {k for k, v in seen.items() if len(v) >= max(3, n // 3)}
    return repeated


def parse_pdf(path: Path, grade: str | None = None) -> list[Block]:
    blocks: list[Block] = []
    with pymupdf.open(path) as doc:
        raw: list[list[tuple[str, tuple[float, float, float, float], float, bool]]] = []
        sizes: list[float] = []
        for page in doc:
            page_blocks = []
            for b in page.get_text("dict")["blocks"]:
                if b["type"] != 0:
                    continue
                spans = [s for line in b["lines"] for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = " ".join(
                    " ".join(s["text"] for s in line["spans"]).strip() for line in b["lines"]
                )
                text = " ".join(text.split())
                sizes.extend(s["size"] for s in spans)
                page_blocks.append(
                    (text, tuple(b["bbox"]), max(s["size"] for s in spans),
                     all(s["flags"] & 16 for s in spans))
                )  # fmt: skip
            raw.append(page_blocks)
        body = statistics.median(sizes) if sizes else 10.0
        repeated = _repeated_edge_texts(
            [[(t, bb) for t, bb, _, _ in p] for p in raw], [pg.rect.height for pg in doc]
        )

        section: str | None = None
        skipping = False
        for page_no, page_blocks in enumerate(raw, start=1):
            for text, _bbox, size, bold in page_blocks:
                if _norm(text) in repeated or PAGE_NUMBER_RE.match(text):
                    continue  # running header/footer or a bare page number
                is_heading = (
                    len(text.split()) <= 12
                    and not text.endswith(".")
                    and (size > body * 1.15 or bold)
                    and not TOC_LEADER_RE.search(text)
                )
                if is_heading:
                    section = text
                    skipping = bool(SKIP_SECTION_RE.match(text))
                    blocks.append(Block(text="", page=page_no, section=section, grade=grade))
                    continue
                if skipping or TOC_LEADER_RE.search(text) or _is_reference(text):
                    continue
                if len(text.split()) < 3:
                    continue  # stray labels and figure numbers
                blocks.append(Block(text=text, page=page_no, section=section, grade=grade))
    return blocks
