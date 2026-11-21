from pathlib import Path

import pymupdf

from sor_ingest.chunking import chunk_blocks
from sor_ingest.parse import parse_pdf


def make_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 80), "Phonemic Awareness", fontsize=18)
    body = "Children learn to blend sounds into words when teachers model it clearly. " * 3
    page.insert_textbox(pymupdf.Rect(72, 100, 520, 300), body, fontsize=10)
    page2 = doc.new_page()
    page2.insert_text((72, 80), "Phonics", fontsize=18)
    page2.insert_textbox(pymupdf.Rect(72, 100, 520, 300), body, fontsize=10)
    doc.save(path)


def test_parse_keeps_sections_and_pages(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    make_pdf(pdf)
    blocks = [b for b in parse_pdf(pdf) if b.text]
    assert [(b.section, b.page) for b in blocks] == [("Phonemic Awareness", 1), ("Phonics", 2)]
    ps = chunk_blocks("src_0001", blocks)
    # two short sections are merged into one passage that keeps both headings and both pages
    assert [(p.section, p.page, p.page_end) for p in ps] == [("Phonemic Awareness", 1, 2)]
    assert "Phonics\n\n" in ps[0].text


def test_printed_page_labels_and_glossary_are_handled(tmp_path: Path) -> None:
    doc = pymupdf.open()
    body = "Children learn to blend sounds into words when teachers model it clearly. " * 3
    for title in ["Phonics", "Glossary"]:
        page = doc.new_page()
        page.insert_text((72, 80), title, fontsize=18)
        page.insert_textbox(pymupdf.Rect(72, 100, 520, 300), body, fontsize=10)
    doc.set_page_labels([{"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1}])
    pdf = tmp_path / "labels.pdf"
    doc.save(pdf)
    dropped: list[tuple[int, str]] = []
    blocks = parse_pdf(pdf, on_drop=lambda page, reason, _t: dropped.append((page, reason)))
    text_blocks = [b for b in blocks if b.text]
    assert [(b.section, b.page, b.page_label) for b in text_blocks] == [("Phonics", 1, "i")]
    assert any(page == 2 and "Glossary" in reason for page, reason in dropped)
