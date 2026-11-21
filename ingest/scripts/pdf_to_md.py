"""Convert every PDF in a folder to a Markdown text file next to it.

    cd ingest && uv run python scripts/pdf_to_md.py ../docs/reference

Plain text extraction with PyMuPDF, one "## Page N" heading per page. No network, no AWS.
Existing .md files are overwritten.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf


def convert(pdf: Path) -> Path:
    out = pdf.with_suffix(".md")
    with pymupdf.open(pdf) as doc:
        pages = [f"## Page {i}\n\n{page.get_text().strip()}\n" for i, page in enumerate(doc, 1)]
    out.write_text(f"# {pdf.stem}\n\n" + "\n".join(pages), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else Path("../docs/reference")
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {folder}")
        return 1
    for pdf in pdfs:
        out = convert(pdf)
        print(f"{pdf.name} -> {out.name} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
