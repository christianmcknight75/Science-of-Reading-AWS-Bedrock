"""Evidence label, computed by code (never guessed by the model).

Rules (Viktoriia, 2026-11-19; docs/DECISIONS.md):
1. WWC practice guides carry a rating per recommendation, stored on that recommendation's passages:
   Strong -> Very sure, Moderate -> Fairly sure, Minimal -> Not sure yet.
   An unrated WWC passage does not raise the label.
2. Government guides and other summaries (England, Australia, NSW, Put Reading First, REL tools)
   support an answer but never raise the label: they mostly summarize the same research.
3. Unrated primary evidence:
   - 2+ independent reviews/meta-analyses that agree -> Very sure; 1 review/meta-analysis ->
     Fairly sure.
   - 1 single study -> Not sure yet, unless it is large and controlled (randomized, or at least
     1,000 students with a comparison group) -> Fairly sure.
4. If cited primary evidence disagrees, the label is capped at Not sure yet and `mixed` is True so
   the answer says the research is mixed.
5. Count independent evidence, not documents or passages: a source counts once. KNOWN LIMITATION
   (PoC): overlap between reviews is not detected, except that the National Reading Panel and any
   meta-analysis published before 2001 are treated as one overlapping body of evidence.
"""

from dataclasses import dataclass

NO_RESEARCH = "No research found"
NOT_SURE = "Not sure yet"
FAIRLY = "Fairly sure"
VERY = "Very sure"
_RANK = {NO_RESEARCH: 0, NOT_SURE: 1, FAIRLY: 2, VERY: 3}
_RATING = {"Strong": VERY, "Moderate": FAIRLY, "Minimal": NOT_SURE}
_REVIEW_TYPES = {"meta_analysis", "foundational"}
LARGE_STUDY = 1000
OVERLAP_CUTOFF_YEAR = 2001  # NRP (2000) and meta-analyses before this year count once together


@dataclass(frozen=True)
class CitedPassage:
    source_id: str
    source_type: str  # practice_guide | meta_analysis | study | foundational | government_guide
    evidence_role: str  # primary | summary
    evidence_rating: str | None = None  # Strong | Moderate | Minimal (WWC passages only)
    year: int | None = None
    randomized: bool | None = None
    sample_size: int | None = None
    has_comparison_group: bool | None = None
    contradicts: bool = False  # this evidence disagrees with the answer's claim


@dataclass(frozen=True)
class EvidenceResult:
    label: str
    mixed: bool = False


def _best(a: str, b: str) -> str:
    return a if _RANK[a] >= _RANK[b] else b


def _large_and_controlled(c: CitedPassage) -> bool:
    if c.randomized:
        return True
    return bool(c.has_comparison_group and c.sample_size and c.sample_size >= LARGE_STUDY)


def _review_group(c: CitedPassage) -> str:
    """Independent body of evidence a review belongs to."""
    early = c.year is not None and c.year < OVERLAP_CUTOFF_YEAR
    if c.source_type == "foundational" or (c.source_type == "meta_analysis" and early):
        return "nrp-and-pre-2001"
    return c.source_id


def evidence_result(cited: list[CitedPassage]) -> EvidenceResult:
    if not cited:
        return EvidenceResult(NO_RESEARCH)
    best = NOT_SURE
    reviews: set[str] = set()
    controlled_study = False
    mixed = any(c.contradicts and c.evidence_role == "primary" for c in cited)
    for c in cited:
        if c.contradicts:
            continue  # disagreeing evidence never supports the label
        if c.evidence_rating in _RATING:
            best = _best(best, _RATING[c.evidence_rating])
        elif c.evidence_role == "primary":
            if c.source_type in _REVIEW_TYPES:
                reviews.add(_review_group(c))
            elif c.source_type == "study" and _large_and_controlled(c):
                controlled_study = True
    if len(reviews) >= 2:
        best = _best(best, VERY)
    elif reviews or controlled_study:
        best = _best(best, FAIRLY)
    if mixed:
        best = NOT_SURE
    return EvidenceResult(best, mixed)


def evidence_label(cited: list[CitedPassage]) -> str:
    return evidence_result(cited).label
