from sor_ingest.chunking import MAX_WORDS, MIN_WORDS, Block, chunk_blocks


def para(n: int, word: str = "word") -> str:
    return " ".join([word] * n)


def test_passages_are_within_bounds_and_keep_page_and_section() -> None:
    blocks = [
        Block(para(200), 1, "Intro"),
        Block(para(200), 2, "Intro"),
        Block(para(150), 3, "Intro"),
    ]
    ps = chunk_blocks("src_0001", blocks)
    assert [p.passage_id for p in ps] == ["src_0001_p001", "src_0001_p002"]
    assert ps[0].page == 1 and ps[0].section == "Intro"
    assert MIN_WORDS <= len(ps[0].text.split()) <= MAX_WORDS
    assert len(ps[1].text.split()) == 150  # short tail kept: merging would exceed MAX_WORDS


def test_never_crosses_sections() -> None:
    ps = chunk_blocks("src_0001", [Block(para(320), 1, "A"), Block(para(320), 2, "B")])
    assert [p.section for p in ps] == ["A", "B"]


def test_long_paragraph_is_split() -> None:
    ps = chunk_blocks("src_0001", [Block(para(1100), 1, "A")])
    assert all(len(p.text.split()) <= MAX_WORDS for p in ps)
    assert sum(len(p.text.split()) for p in ps) == 1100


def test_short_tail_merges_when_it_fits() -> None:
    ps = chunk_blocks("src_0001", [Block(para(310), 1, "A"), Block(para(100), 2, "A")])
    assert len(ps) == 1 and len(ps[0].text.split()) == 410


def test_empty_input() -> None:
    assert chunk_blocks("src_0001", [Block("  ", 1)]) == []
