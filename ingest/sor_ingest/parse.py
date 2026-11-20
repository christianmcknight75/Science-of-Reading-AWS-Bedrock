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
from collections.abc import Callable
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
    r"|author contributions?|ethics statement|open access|affiliations?|correspondence"
    r"|glossary|overview of recommendations)\b",
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
FRONT_PAGES = 2  # journal front matter is only looked for on the first two pages
JOURNAL_META_RE = re.compile(
    r"journal homepage|contents lists available|licensee mdpi|open access article|\u00a9"
    r"|creative commons attribution|terms and conditions of the creative commons"
    r"|^distributed under the terms\b|^conditions of the creative commons|^attribution \(cc by"
    r"|^(received|revised|accepted|published)( online| in revised form)?\s*[:\d]"
    r"|^(academic editors?|available online|article history)\b"
    r"|^a r t i c l e\s+i n f o|^article info\b|\bissn\b|^correspondence:|\bcorresponding author"
    r"|@[\w-]+\.\w{2,}",
    re.IGNORECASE,
)
DOI_LINE_RE = re.compile(r"doi\.org/\S+", re.IGNORECASE)
AFFIL_MARK = r"(?:\d|[a-z]|\*)"
AUTHOR_MARK_RE = re.compile(rf"\s{AFFIL_MARK}\s?(?:[,\u00b7]|$)")
NAME_WITH_MARK_RE = re.compile(r"^[A-Z][\w.'\u2019-]+(?: [A-Z][\w.'\u2019-]*){0,3} (?:[a-z]|\*)$")
AFFIL_START_RE = re.compile(rf"^{AFFIL_MARK}\s")
INSTITUTION_RE = re.compile(
    r"University|Universit[e\u00e9y]|Institute|Department|Laborator|CNRS|College|Centre|Center"
    r"|School of|Faculty",
)
ADDRESS_RE = re.compile(r"\b\d{4,5}\b|\b(USA|UK|France|Australia|Canada|Germany|Spain|Italy)\b")
EDGE = 0.07  # top and bottom 7% of a page are where headers and footers live


def _norm(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def front_matter_reason(text: str) -> str | None:
    """Journal title-page text that is not part of the paper's content: article history, licence
    and copyright lines, DOI lines, author lists and affiliations. Only used on the first pages."""
    n = len(text.split())
    if JOURNAL_META_RE.search(text) and n <= 90:
        return "journal front matter (article history, licence or contact line)"
    if n <= 25 and DOI_LINE_RE.search(text):
        return "journal front matter (DOI line)"
    if n <= 6 and NAME_WITH_MARK_RE.match(text):
        return "author name"
    if n <= 60 and len(AUTHOR_MARK_RE.findall(text)) >= 2:
        caps = sum(1 for w in text.split() if w[:1].isupper())
        if caps / n >= 0.3:
            return "author list"
    if (
        n <= 120
        and AFFIL_START_RE.match(text)
        and INSTITUTION_RE.search(text)
        and ADDRESS_RE.search(text)
    ):
        return "author affiliations"
    return None


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


def parse_pdf(
    path: Path,
    grade: str | None = None,
    on_drop: Callable[[int, str, str], None] | None = None,
) -> list[Block]:
    """`on_drop(pdf_page, reason, text)` is called for every block that is left out, so a person
    can see what was dropped and why."""

    def drop(page_no: int, reason: str, text: str) -> None:
        if on_drop:
            on_drop(page_no, reason, text)

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
        after_editors = False
        for page_no, page_blocks in enumerate(raw, start=1):
            label = doc[page_no - 1].get_label() or str(page_no)
            for text, _bbox, size, bold in page_blocks:
                if PAGE_NUMBER_RE.match(text):
                    drop(page_no, "page number", text)
                    continue
                if _norm(text) in repeated:
                    drop(page_no, "running header or footer", text)
                    continue
                if page_no <= FRONT_PAGES:
                    why = front_matter_reason(text)
                    if why is None and after_editors and len(text.split()) <= 6:
                        why = "editor name (continues an 'Academic Editors' line)"
                    after_editors = bool(why) and text.lower().startswith("academic editor")
                    if why:
                        drop(page_no, why, text)
                        continue
                if re.fullmatch(r"[A-Za-z]", text):
                    drop(page_no, "single-letter heading", text)
                    continue  # glossary letter dividers; not a section
                is_heading = (
                    len(text.split()) <= 12
                    and not text.endswith(".")
                    and (size > body * 1.15 or bold)
                    and not TOC_LEADER_RE.search(text)
                )
                if is_heading:
                    section = text
                    skipping = bool(SKIP_SECTION_RE.match(text))
                    blocks.append(Block("", page_no, section, grade=grade, page_label=label))
                    continue
                if skipping:
                    drop(page_no, f"inside skipped section '{(section or '')[:40]}'", text)
                    continue
                if TOC_LEADER_RE.search(text):
                    drop(page_no, "table-of-contents line", text)
                    continue
                if _is_reference(text):
                    drop(page_no, "reference-list entry", text)
                    continue
                if len(text.split()) < 3:
                    drop(page_no, "stray label (under 3 words)", text)
                    continue
                blocks.append(Block(text, page_no, section, grade=grade, page_label=label))
    return blocks
