"""Shared types for the Q&A engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = (
    "Reading Helper offers research-based ideas for teachers. It is advice only. It does not "
    "evaluate you, your students, or any program."
)
OFFER = (
    "I can help with research on phonemic awareness, phonics and decoding, fluency, vocabulary, "
    "comprehension, and supporting struggling readers in kindergarten through 3rd grade."
)


@dataclass(frozen=True)
class Passage:
    passage_id: str
    source_id: str
    source_title: str
    source_type: str
    evidence_role: str
    evidence_rating: str | None
    year: int | None
    section: str | None
    page_label: str | None
    page_end_label: str | None
    text: str
    similarity: float = 0.0
    randomized: bool | None = None
    sample_size: int | None = None
    has_comparison_group: bool | None = None


@dataclass(frozen=True)
class Claim:
    text: str
    passage_ids: list[str]
    quote: str


@dataclass(frozen=True)
class Step:
    text: str
    minutes: int


@dataclass
class Draft:
    """What the model returned, validated but not yet verified."""

    answerable: bool
    claims: list[Claim] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    grade: Literal["K", "1", "2", "3"] | None = None


class ResearchClaim(BaseModel):
    text: str
    citations: list[int]


class SourceOut(BaseModel):
    n: int
    passage_id: str
    title: str
    year: int | None
    source_type: str
    section: str | None
    page: str | None
    passage_text: str
    quote: str | None = None


class StepOut(BaseModel):
    text: str
    minutes: int


class WatchOut(BaseModel):
    myth: str
    correction: str
    citations: list[int]


class AnswerResponse(BaseModel):
    kind: Literal["answer", "no_research", "insufficient", "out_of_scope", "unavailable"]
    evidence_label: str
    mixed: bool = False
    short_answer: str = ""
    research_says: list[ResearchClaim] = []
    idea_for_class: list[StepOut] = []
    watch_out: WatchOut | None = None
    sources: list[SourceOut] = []
    message: str = ""  # honest explanation for every non-answer
    offer: str = ""  # what we can help with
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None
