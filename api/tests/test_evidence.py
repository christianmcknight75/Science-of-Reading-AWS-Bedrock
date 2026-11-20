from app.evidence import CitedPassage, evidence_label


def wwc(sid: str, rating: str | None) -> CitedPassage:
    return CitedPassage(sid, "practice_guide", "primary", rating)


def gov(sid: str) -> CitedPassage:
    return CitedPassage(sid, "government_guide", "summary")


def test_nothing_cited() -> None:
    assert evidence_label([]) == "No research found"


def test_wwc_ratings_map_directly() -> None:
    assert evidence_label([wwc("a", "Strong")]) == "Very sure"
    assert evidence_label([wwc("a", "Moderate")]) == "Fairly sure"
    assert evidence_label([wwc("a", "Minimal")]) == "Not sure yet"


def test_government_guides_never_raise_the_label() -> None:
    many = [gov("uk"), gov("au"), gov("nsw"), CitedPassage("prf", "foundational", "summary")]
    assert evidence_label(many) == "Not sure yet"
    assert evidence_label([wwc("a", "Minimal"), *many]) == "Not sure yet"
    assert evidence_label([wwc("a", "Moderate"), *many]) == "Fairly sure"


def test_unrated_guide_passage_does_not_raise() -> None:
    assert evidence_label([wwc("a", None)]) == "Not sure yet"


def test_counts_independent_sources_not_passages() -> None:
    review = CitedPassage("meta1", "meta_analysis", "primary")
    assert evidence_label([review, review, review]) == "Fairly sure"  # one review, three passages
    assert evidence_label([review, CitedPassage("nrp", "foundational", "primary")]) == "Very sure"


def test_single_study_is_fairly_sure() -> None:
    assert evidence_label([CitedPassage("s1", "study", "primary")]) == "Fairly sure"
    two = [CitedPassage("s1", "study", "primary"), CitedPassage("s2", "study", "primary")]
    assert evidence_label(two) == "Fairly sure"


def test_best_signal_wins() -> None:
    mixed = [wwc("a", "Minimal"), CitedPassage("s1", "study", "primary")]
    assert evidence_label(mixed) == "Fairly sure"
