from app.evidence import CitedPassage, evidence_label, evidence_result


def wwc(sid: str, rating: str | None) -> CitedPassage:
    return CitedPassage(sid, "practice_guide", "primary", rating)


def gov(sid: str) -> CitedPassage:
    return CitedPassage(sid, "government_guide", "summary")


def review(sid: str, year: int = 2015, contradicts: bool = False) -> CitedPassage:
    return CitedPassage(sid, "meta_analysis", "primary", year=year, contradicts=contradicts)


def study(
    sid: str,
    randomized: bool | None = None,
    sample_size: int | None = None,
    has_comparison_group: bool | None = None,
    contradicts: bool = False,
) -> CitedPassage:
    return CitedPassage(
        sid,
        "study",
        "primary",
        None,
        None,
        randomized,
        sample_size,
        has_comparison_group,
        contradicts,
    )


NRP = CitedPassage("nrp", "foundational", "primary", year=2000)


def test_nothing_cited() -> None:
    assert evidence_label([]) == "No research found"


def test_wwc_ratings_map_directly() -> None:
    assert evidence_label([wwc("a", "Strong")]) == "Very sure"
    assert evidence_label([wwc("a", "Moderate")]) == "Fairly sure"
    assert evidence_label([wwc("a", "Minimal")]) == "Not sure yet"


def test_unrated_wwc_passage_does_not_raise() -> None:
    assert evidence_label([wwc("a", None)]) == "Not sure yet"


def test_government_guides_never_raise_the_label() -> None:
    many = [gov("uk"), gov("au"), gov("nsw"), CitedPassage("prf", "foundational", "summary")]
    assert evidence_label(many) == "Not sure yet"
    assert evidence_label([wwc("a", "Minimal"), *many]) == "Not sure yet"
    assert evidence_label([wwc("a", "Moderate"), *many]) == "Fairly sure"


def test_reviews_count_independent_sources_not_passages() -> None:
    r = review("m1")
    assert evidence_label([r, r, r]) == "Fairly sure"
    assert evidence_label([r, review("m2")]) == "Very sure"


def test_nrp_and_pre_2001_meta_analyses_count_once_together() -> None:
    assert evidence_label([NRP, review("old", year=1999)]) == "Fairly sure"
    assert evidence_label([NRP, review("new", year=2012)]) == "Very sure"
    assert evidence_label([review("old1", year=1998), review("old2", year=2000)]) == "Fairly sure"


def test_single_study_is_not_sure_unless_large_and_controlled() -> None:
    assert evidence_label([study("s1")]) == "Not sure yet"
    assert evidence_label([study("s1", sample_size=5000)]) == "Not sure yet"  # no comparison group
    assert evidence_label([study("s1", randomized=True)]) == "Fairly sure"
    big = study("s1", sample_size=1000, has_comparison_group=True)
    assert evidence_label([big]) == "Fairly sure"
    small = study("s1", sample_size=999, has_comparison_group=True)
    assert evidence_label([small]) == "Not sure yet"


def test_disagreement_caps_at_not_sure_and_is_flagged_mixed() -> None:
    agree = [review("m1"), review("m2")]
    assert evidence_result(agree).mixed is False
    split = [*agree, study("s9", contradicts=True)]
    res = evidence_result(split)
    assert res.label == "Not sure yet" and res.mixed
    assert (
        evidence_result([wwc("a", "Strong"), study("s9", contradicts=True)]).label == "Not sure yet"
    )


def test_disagreeing_evidence_never_supports_the_label() -> None:
    res = evidence_result([review("m1", contradicts=True)])
    assert res.label == "Not sure yet" and res.mixed


def test_best_signal_wins_without_disagreement() -> None:
    assert evidence_label([wwc("a", "Minimal"), review("m1")]) == "Fairly sure"
