from sor_ingest.parse import PAGE_NUMBER_RE, SKIP_SECTION_RE, TOC_LEADER_RE, _is_reference


def test_skipped_sections() -> None:
    for h in [
        "References",
        "Table of Contents",
        "About the Authors",
        "Acknowledgments",
        "Endnotes",
    ]:
        assert SKIP_SECTION_RE.match(h), h
    for h in ["Recommendation 1", "Introduction", "Referencing the letters", "Phonics"]:
        assert not SKIP_SECTION_RE.match(h), h


def test_page_numbers_and_toc_lines() -> None:
    assert PAGE_NUMBER_RE.match("12") and PAGE_NUMBER_RE.match("Page 3 of 40")
    assert not PAGE_NUMBER_RE.match("Chapter 12")
    assert TOC_LEADER_RE.search("Recommendation 2 ........ 14")
    assert not TOC_LEADER_RE.search("Teach letters in 14 steps.")


def test_reference_entries_but_not_ordinary_sentences() -> None:
    ref = "Smith, J. A., & Lee, K. (2019). Phonics in grade 1. Journal of Reading, 12(3), 45-67. https://doi.org/10.1/x"
    assert _is_reference(ref)
    assert not _is_reference("Smith (2019) found that children who practised blending improved.")


def test_journal_front_matter_is_recognised() -> None:
    from sor_ingest.parse import front_matter_reason as why

    for text in [
        "Journal of Reading Studies journal homepage: www.example.com/locate/jrs",
        "Received 1 March 2025; Accepted 2 June 2025 Available online 3 July 2025",
        "Accepted: 31 May 2024 / Published online: 23 July 2024 © The Author(s) 2024",
        "Reading Research (2025) 38:1607–1633 https://doi.org/10.1000/xyz123",
        "Ana Lopez a , Ben Carter a , * , Chen Wu b",
        "Ana Lopez 1 · Ben Carter 2 · Chen Wu 1",
        "1 Department of Education, Example University, 12 Main Street, Springfield, 12345, USA "
        "2 Institute of Learning, Other College, London, UK",
        "A R T I C L E I N F O",
        "Ana Lopez a , Ben Carter a , * , J \u00b4 er \u02c6 ome Dupont b",
        "distributed under the terms and",
        "conditions of the Creative Commons",
        "Attribution (CC BY) license .",
        "Paul Gioia a",
    ]:
        assert why(text), text


def test_ordinary_first_page_text_is_not_front_matter() -> None:
    from sor_ingest.parse import front_matter_reason as why

    for text in [
        "Children who practise blending sounds with their teacher learn to read words faster "
        "than children who only listen to stories, as shown in Table 1, 2 and 3.",
        "The University of Mississippi ran a pilot in 2022 with 40 classrooms.",
        "Published research on phonics instruction is large and consistent.",
        "Abstract Background: learning to read is a foundational milestone.",
        "Level 2",
        "Phonics and Reading",
    ]:
        assert why(text) is None, text
