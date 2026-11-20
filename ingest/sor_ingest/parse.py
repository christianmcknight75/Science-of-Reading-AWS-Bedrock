"""PDF -> Blocks using PyMuPDF. Headings are lines set in a larger or bold font than body text."""

from __future__ import annotations

import statistics
from pathlib import Path

import pymupdf

from .chunking import Block


def parse_pdf(path: Path) -> list[Block]:
    blocks: list[Block] = []
    section: str | None = None
    with pymupdf.open(path) as doc:
        sizes = [
            span["size"]
            for page in doc
            for b in page.get_text("dict")["blocks"]
            if b["type"] == 0
            for line in b["lines"]
            for span in line["spans"]
            if span["text"].strip()
        ]
        body = statistics.median(sizes) if sizes else 10.0
        for page_no, page in enumerate(doc, start=1):
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
                is_heading = (
                    len(text.split()) <= 12
                    and not text.endswith(".")
                    and (
                        max(s["size"] for s in spans) > body * 1.15
                        or all(s["flags"] & 16 for s in spans)
                    )
                )
                if is_heading:
                    section = text
                    blocks.append(Block(text="", page=page_no, section=section))  # heading marker
                else:
                    blocks.append(Block(text=text, page=page_no, section=section))
    return blocks
