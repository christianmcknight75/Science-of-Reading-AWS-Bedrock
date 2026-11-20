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
