"""Evidence label, computed by code (never guessed by the model).

Rule (Viktoriia, 2026-11-19; see docs/DECISIONS.md):
- WWC practice guides carry a rating per recommendation, stored on that recommendation's passages:
  Strong -> Very sure, Moderate -> Fairly sure, Minimal -> Not sure yet.
- Government guides and other summaries (England, Australia, NSW, Put Reading First, REL tools)
  support an answer but never raise the label, because they mostly summarize the same research.
- Count independent evidence, not documents or passages: one source counts once.
- Unrated primary evidence: 2+ independent reviews (meta-analysis / National Reading Panel) ->
  Very sure; 1 review or 1 good study -> Fairly sure. (Carried over from CLAUDE.md; confirm.)
- Anything else that was cited -> Not sure yet. Nothing cited -> No research found.
"""

from dataclasses import dataclass

NO_RESEARCH = "No research found"
NOT_SURE = "Not sure yet"
FAIRLY = "Fairly sure"
VERY = "Very sure"
_RANK = {NO_RESEARCH: 0, NOT_SURE: 1, FAIRLY: 2, VERY: 3}
_RATING = {"Strong": VERY, "Moderate": FAIRLY, "Minimal": NOT_SURE}
_REVIEW_TYPES = {"meta_analysis", "foundational"}


@dataclass(frozen=True)
class CitedPassage:
    source_id: str
    source_type: str  # practice_guide | meta_analysis | study | foundational | government_guide
    evidence_role: str  # primary | summary
    evidence_rating: str | None = None  # Strong | Moderate | Minimal (WWC passages only)


def evidence_label(cited: list[CitedPassage]) -> str:
    if not cited:
        return NO_RESEARCH
    best = NOT_SURE
    reviews: set[str] = set()
    studies: set[str] = set()
    for c in cited:
        if c.evidence_rating in _RATING:
            label = _RATING[c.evidence_rating]
            best = max(best, label, key=_RANK.__getitem__)
        elif c.evidence_role == "primary":
            if c.source_type in _REVIEW_TYPES:
                reviews.add(c.source_id)
            elif c.source_type == "study":
                studies.add(c.source_id)
    if len(reviews) >= 2:
        best = max(best, VERY, key=_RANK.__getitem__)
    elif reviews or studies:
        best = max(best, FAIRLY, key=_RANK.__getitem__)
    return best
