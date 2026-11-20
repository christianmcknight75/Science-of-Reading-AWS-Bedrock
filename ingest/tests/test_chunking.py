from sor_ingest.chunking import HARD_MAX, MAX_WORDS, MERGE_BELOW, Block, chunk_blocks, words


def para(n: int, word: str = "word") -> str:
    return " ".join([word] * n)


def test_passages_target_size_keep_page_range_and_start_with_heading() -> None:
    blocks = [
        Block(para(200), 1, "Intro"),
        Block(para(200), 2, "Intro"),
        Block(para(150), 3, "Intro"),
    ]
    ps = chunk_blocks("src_0001", blocks)
    assert [p.passage_id for p in ps] == ["src_0001_p001", "src_0001_p002"]
    assert ps[0].text.startswith("Intro\n\n")
    assert (ps[0].page, ps[0].page_end) == (1, 2)
    assert (ps[1].page, ps[1].page_end) == (3, 3)
    assert 300 <= words(ps[0].text) <= MAX_WORDS + 1


def test_never_goes_over_hard_max() -> None:
    blocks = [Block(para(480), 1, "A"), Block(para(140), 2, "B"), Block(para(480), 3, "C")]
    assert all(words(p.text) <= HARD_MAX for p in chunk_blocks("s", blocks))


def test_small_chunks_are_merged_across_sections_and_keep_both_headings() -> None:
    ps = chunk_blocks(
        "s", [Block(para(80), 1, "A"), Block(para(90), 2, "B"), Block(para(70), 2, "C")]
    )
    assert len(ps) == 1
    assert ps[0].text.count("\n\n") == 5  # three headings and three paragraphs
    assert ps[0].section == "A" and (ps[0].page, ps[0].page_end) == (1, 2)


def test_never_merges_across_a_rating_or_grade() -> None:
    a = Block(para(60), 1, "Rec 1", "Recommendation 1", "Strong")
    b = Block(para(60), 2, "Rec 2", "Recommendation 2", "Minimal")
    ps = chunk_blocks("s", [a, b])
    assert [p.evidence_rating for p in ps] == ["Strong", "Minimal"]
    k = Block(para(60), 1, "Same", grade="K")
    g1 = Block(para(60), 1, "Same", grade="1")
    assert [p.grade for p in chunk_blocks("s", [k, g1])] == ["K", "1"]


def test_long_paragraph_is_split_at_sentence_ends() -> None:
    sentence = "Word " + para(39) + ". "
    ps = chunk_blocks("s", [Block(sentence * 30, 1, "A")])  # 1200 words
    assert all(words(p.text) <= MAX_WORDS + 1 for p in ps)
    assert all(p.text.rstrip().endswith(".") for p in ps)
    assert sum(words(p.text) for p in ps) == 1200 + len(ps)  # plus the heading word each time


def test_unmergeable_small_chunk_is_kept() -> None:
    ps = chunk_blocks("s", [Block(para(500), 1, "A"), Block(para(100), 2, "A")])
    assert [words(p.text) for p in ps] == [501, 101] and 101 < MERGE_BELOW + 1


def test_empty_input() -> None:
    assert chunk_blocks("src_0001", [Block("  ", 1)]) == []
