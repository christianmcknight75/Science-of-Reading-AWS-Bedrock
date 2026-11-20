from sor_ingest.chunking import Block, chunk_blocks
from sor_ingest.ratings import annotate_recommendations

WORDS = " ".join(["word"] * 320)


def doc() -> list[Block]:
    return [
        Block("", 3, "Introduction"),
        Block(WORDS, 3, "Introduction"),
        Block("", 10, "Recommendation 1. Teach academic language"),
        Block("", 10, "Level of evidence: Moderate"),
        Block(WORDS, 10, "Level of evidence: Moderate"),
        Block("", 12, "How to carry out the recommendation"),
        Block(WORDS, 12, "How to carry out the recommendation"),
        Block("", 20, "Recommendation 2. Develop awareness of sounds"),
        Block("Level of evidence: Strong", 20, "Recommendation 2. Develop awareness of sounds"),
        Block(WORDS, 21, "Recommendation 2. Develop awareness of sounds"),
        Block("", 40, "References"),
        Block(WORDS, 40, "References"),
    ]


def test_rating_applies_to_the_whole_recommendation_only() -> None:
    ps = chunk_blocks("src_0001", annotate_recommendations(doc()))
    got = [(p.recommendation and p.recommendation[:16], p.evidence_rating) for p in ps]
    assert got == [
        (None, None),  # introduction
        ("Recommendation 1", "Moderate"),
        ("Recommendation 1", "Moderate"),  # sub-section "How to carry out" inherits it
        ("Recommendation 2", "Strong"),
        (None, None),  # references
    ]


def test_no_rating_found_stays_none() -> None:
    blocks = [Block("", 1, "Recommendation 1. X"), Block(WORDS, 1, "Recommendation 1. X")]
    assert all(b.evidence_rating is None for b in annotate_recommendations(blocks))


def test_a_line_listing_all_recommendations_is_not_a_heading() -> None:
    blocks = [
        Block("", 5, "Recommendation 1 Recommendation 2 Recommendation 3"),
        Block(WORDS, 5, "Recommendation 1 Recommendation 2 Recommendation 3"),
        Block("", 10, "Recommendation 1. Teach academic language"),
        Block("Level of evidence: Minimal", 10, "Recommendation 1. Teach academic language"),
        Block(WORDS, 10, "Recommendation 1. Teach academic language"),
    ]
    out = annotate_recommendations(blocks)
    assert out[1].recommendation is None  # the overview line belongs to no recommendation
    assert out[4].recommendation == "Recommendation 1. Teach academic language"
    assert out[4].evidence_rating == "Minimal"


def test_prose_that_mentions_a_recommendation_is_not_a_heading() -> None:
    blocks = [
        Block("Recommendation 4 addresses using data to monitor progress.", 3, "Introduction"),
        Block("", 10, "Recommendation 1. Screen all students"),
        Block("Level of evidence: Moderate", 10, "Recommendation 1. Screen all students"),
        Block(WORDS, 10, "Recommendation 1. Screen all students"),
    ]
    out = annotate_recommendations(blocks)
    assert out[0].recommendation is None and out[0].evidence_rating is None
    assert out[3].evidence_rating == "Moderate"


def test_a_bare_recommendation_number_is_a_heading() -> None:
    blocks = [
        Block("", 49, "Recommendation 1"),
        Block("", 49, "Level of evidence: Strong Evidence"),
        Block(WORDS, 49, "Level of evidence: Strong Evidence"),
    ]
    out = annotate_recommendations(blocks)
    assert out[2].recommendation == "Recommendation 1" and out[2].evidence_rating == "Strong"


def test_falls_back_to_prose_when_a_guide_states_ratings_only_in_an_appendix() -> None:
    blocks = [
        Block("", 49, "Level of evidence: Strong Evidence"),
        Block(
            "Recommendation 1 advocates classroom strategy instruction. " + WORDS,
            49,
            "Level of evidence: Strong Evidence",
        ),
    ]
    out = annotate_recommendations(blocks)
    assert out[1].recommendation is not None and out[1].evidence_rating == "Strong"


def test_low_is_stored_as_minimal() -> None:
    blocks = [
        Block("", 40, "Recommendation 4. Monitor the progress of tier 2 students"),
        Block(WORDS, 40, "Level of evidence: Low"),
    ]
    out = annotate_recommendations(blocks)
    assert out[1].evidence_rating == "Minimal"


def test_rating_is_not_taken_from_the_previous_recommendations_heading() -> None:
    """Appendix layout: each recommendation's title line comes first, its rating heading after."""
    blocks = [
        Block("", 60, "Recommendation 4 Select texts purposefully"),
        Block("", 60, "Level of evidence: Minimal Evidence"),
        Block(WORDS, 60, "Level of evidence: Minimal Evidence"),
        # Rec 5's title sits under Rec 4's heading; its own heading follows
        Block(
            "Recommendation 5 Establish an engaging context",
            61,
            "Level of evidence: Minimal Evidence",
        ),
        Block("", 61, "Level of evidence: Moderate Evidence"),
        Block(WORDS, 61, "Level of evidence: Moderate Evidence"),
        # Rec 1's heading comes before its prose, which must still be rated Strong
        Block("", 70, "Level of evidence: Strong Evidence"),
        Block(
            "Recommendation 1 advocates classroom strategy instruction. " + WORDS,
            70,
            "Level of evidence: Strong Evidence",
        ),
    ]
    got = {
        b.recommendation: b.evidence_rating
        for b in annotate_recommendations(blocks)
        if b.recommendation
    }
    assert got["Recommendation 4 Select texts purposefully"] == "Minimal"
    assert got["Recommendation 5 Establish an engaging context"] == "Moderate"
    assert got[[k for k in got if k.startswith("Recommendation 1")][0]] == "Strong"
