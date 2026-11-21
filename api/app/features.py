"""Phase 4 features: group plan, story, stuck, training, refresher, feedback.

Every feature follows the same rules as /api/ask (docs/API_CONTRACT.md):
- research claims are retrieved, cited, quote-matched and claim-checked by `verify`;
- the evidence label is computed by code;
- everything the model adds beyond cited claims is an *idea* (our suggestion, never research),
  size-limited and type-checked before it is returned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from . import modelconfig, retrieval, stuck
from .decodable import DecodabilityChecker, WordCheck, load_heart_words
from .decodable.checker import UnknownGrapheme
from .decodable.gpc import UNIVERSAL
from .engine import Engine, cite, parse_draft, sources_out
from .llm import LLMError, ToolSpec
from .prompt import ANSWER_TOOL, SYSTEM, build_answer_prompt
from .schemas import DISCLAIMER, Claim, ResearchClaim, SourceOut, StepOut
from .verifier import verify

SEED = Path(__file__).resolve().parents[1] / "seed"
Skill = Literal["hear-sounds", "blend", "digraphs", "tricky-words"]
Grade = Literal["K", "1", "2", "3"]
_GRAPHEME = re.compile(r"^[a-z]{1,4}(_[a-z])?$")
_WORD = re.compile(r"^[A-Za-z]{1,20}$")
_STORY_TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
MAX_STORY_WORDS = 80
STORY_REPAIRS = 2


class FeatureUnavailable(Exception):
    """A teacher-ready reason the feature could not be answered honestly (HTTP 503)."""


class BadInput(Exception):
    """A teacher-ready reason the input was refused (HTTP 422)."""


SKILL_QUERY: dict[str, str] = {
    "hear-sounds": "phonemic awareness instruction hearing segmenting and blending sounds in words",
    "blend": "teaching students to blend letter sounds to read words",
    "digraphs": "explicit systematic phonics instruction letter-sound correspondences digraphs",
    "tricky-words": "teaching irregular high-frequency words heart words in the early grades",
}
_CLAIM_RULES = (
    "Put research in `claims` (cited, with an exact quote), exactly as above. Everything in "
    "`idea` is YOUR suggestion, not research: do not state research findings in it, never "
    "mention a student, and keep it short."
)


# ------------------------------------------------------------------ grounded claims
@dataclass
class Grounded:
    research: list[ResearchClaim]
    sources: list[SourceOut]
    label: str
    mixed: bool
    idea: dict[str, Any]
    ids: list[str]
    claims: list[Claim] = field(default_factory=list)


def ground(
    engine: Engine,
    *,
    query: str,
    grade: str | None,
    instructions: str,
    idea_schema: dict[str, Any] | None,
    meta: dict[str, Any],
) -> Grounded | None:
    """Retrieve, generate cited claims (+ optional idea), verify, label. None = unsupported."""
    s = engine.settings
    found = retrieval.search(
        engine.conn,
        query,
        engine.embedder.embed_query(query),
        min_similarity=s.min_similarity,
        top_k=s.retrieval_top_k,
        recent_years=s.recent_years,
        grade=grade,
    )
    ids = [p.passage_id for p in found]
    meta["retrieved"] = len(ids)
    if not found:
        return None
    props: dict[str, Any] = {
        k: ANSWER_TOOL.schema["properties"][k] for k in ("answerable", "claims")
    }
    required = ["answerable", "claims"]
    if idea_schema is not None:
        props["idea"] = idea_schema
        required.append("idea")
    tool = ToolSpec(
        "submit_plan",
        "Return cited research claims and your own ideas.",
        {"type": "object", "properties": props, "required": required},
    )
    try:
        out = engine.llm.converse(
            model_id=modelconfig.model_id("generation"),
            system=f"{SYSTEM}\n\n{instructions}\n{_CLAIM_RULES}",
            user=build_answer_prompt(query, found, grade),
            max_tokens=s.max_output_tokens,
            tool=tool,
        )
    except LLMError as exc:
        meta["generation_error"] = str(exc)
        return None
    meta["tokens"] = meta.get("tokens", 0) + out.input_tokens + out.output_tokens
    data = out.tool_input or {}
    draft = parse_draft({"answerable": data.get("answerable"), "claims": data.get("claims", [])})
    if draft is None or not draft.answerable or not draft.claims:
        return None
    retrieved = {p.passage_id: p for p in found}
    result = verify(
        draft.claims,
        retrieved,
        llm=engine.llm,
        model_id=modelconfig.model_id("claim_check"),
        max_tokens=s.claim_check_max_tokens,
    )
    meta["verifier"] = result.summary()
    meta["tokens"] += result.input_tokens + result.output_tokens
    if not result.ok:
        return None
    cited = cite(result.kept, retrieved, result.contradicted_passage_ids)
    idea = data.get("idea")
    return Grounded(
        research=cited.research,
        sources=sources_out(cited.numbers, retrieved, cited.quotes),
        label=cited.evidence.label,
        mixed=cited.evidence.mixed,
        idea=idea if isinstance(idea, dict) else {},
        ids=ids,
        claims=result.kept,
    )


def _finish(
    engine: Engine,
    feature: str,
    redacted: str,
    ids: list[str],
    summary: str,
    label: str,
    started: float,
    meta: dict[str, Any],
) -> tuple[int | None, str | None]:
    ms = int((engine.clock() - started) * 1000)
    qid = engine.log(feature, redacted, ids, summary, label, ms, meta)
    return qid, engine.last_updated()


# ------------------------------------------------------------------ idea cleaning
def _text(v: Any, limit: int) -> str:
    return re.sub(r"\s+", " ", v).strip()[:limit] if isinstance(v, str) else ""


def _minutes(v: Any, lo: int = 1, hi: int = 15) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return lo


def _str_list(v: Any, n: int, limit: int) -> list[str]:
    return [t for x in (v if isinstance(v, list) else [])[:n] if (t := _text(x, limit))]


@cache
def default_heart_words() -> tuple[str, ...]:
    return tuple(load_heart_words())


def make_checker(sounds: list[str], heart_words: list[str] | None) -> DecodabilityChecker:
    try:
        return DecodabilityChecker(
            sounds, heart_words if heart_words is not None else default_heart_words()
        )
    except UnknownGrapheme as exc:
        raise BadInput(
            "I do not know these sounds: " + ", ".join(exc.names) + ". Try ones like sh, ch, a_e."
        ) from exc


# ------------------------------------------------------------------ group plan
class GroupPlanRequest(BaseModel):
    focus: Skill
    sounds: list[str] = Field(default_factory=list, max_length=12)
    grade: Grade | None = None

    @field_validator("sounds")
    @classmethod
    def _sounds(cls, v: list[str]) -> list[str]:
        out = [x.strip().lower() for x in v]
        if any(not _GRAPHEME.match(x) for x in out):
            raise ValueError("sounds must be letters such as s, sh or a_e")
        return out


class PlanStep(BaseModel):
    title: str
    minutes: int
    body: str
    words: list[str] | None = None
    sounds: list[str] | None = None
    story: list[str] | None = None
    tip: str | None = None
    alt: dict[str, str] | None = None


class GroupPlan(BaseModel):
    minutes: int
    why: str
    evidence_label: str
    mixed: bool = False
    research_says: list[ResearchClaim]
    steps: list[PlanStep]
    sources: list[SourceOut]
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None


_STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "minutes": {"type": "integer"},
        "body": {"type": "string"},
        "words": {"type": "array", "items": {"type": "string"}},
        "sounds": {"type": "array", "items": {"type": "string"}},
        "story": {"type": "array", "items": {"type": "string"}},
        "tip": {"type": "string"},
        "alt": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
        },
    },
    "required": ["title", "minutes", "body"],
}
_PLAN_IDEA: dict[str, Any] = {
    "type": "object",
    "properties": {"steps": {"type": "array", "maxItems": 4, "items": _STEP_SCHEMA}},
    "required": ["steps"],
}


def clean_steps(
    raw: Any, focus: str, checker: DecodabilityChecker | None, hearts: set[str]
) -> list[PlanStep]:
    """Type-check the model's steps. Practice words must pass the decodability checker."""
    steps: list[PlanStep] = []
    for item in (raw if isinstance(raw, list) else [])[:4]:
        if not isinstance(item, dict):
            continue
        title, body = _text(item.get("title"), 80), _text(item.get("body"), 400)
        if not title or not body:
            continue
        words = [w for w in _str_list(item.get("words"), 12, 20) if _WORD.match(w)]
        if focus == "tricky-words":
            words = [w for w in words if w.lower() in hearts]
        elif checker is not None:
            words = [w for w in words if checker.check(w).decodable]
        else:
            words = []
        story = [w for w in _str_list(item.get("story"), 40, 20) if _WORD.match(w)]
        if checker is None or not story or not all(checker.check(w).allowed for w in story):
            story = []
        sounds = [x.lower() for x in _str_list(item.get("sounds"), 6, 6) if x.lower() in UNIVERSAL]
        alt_raw = item.get("alt")
        alt = None
        if isinstance(alt_raw, dict) and (_text(alt_raw.get("title"), 80)):
            alt = {
                "title": _text(alt_raw.get("title"), 80),
                "body": _text(alt_raw.get("body"), 400),
            }
        steps.append(
            PlanStep(
                title=title,
                minutes=_minutes(item.get("minutes")),
                body=body,
                words=words or None,
                sounds=sounds or None,
                story=story or None,
                tip=_text(item.get("tip"), 200) or None,
                alt=alt,
            )
        )
    return steps


def group_plan(engine: Engine, req: GroupPlanRequest) -> GroupPlan:
    started = engine.clock()
    if req.focus in ("blend", "digraphs") and not req.sounds:
        raise BadInput("Pick at least one sound this group has learned.")
    checker = make_checker(req.sounds, None) if req.sounds else None
    meta: dict[str, Any] = {"focus": req.focus, "sounds": req.sounds}
    query = SKILL_QUERY[req.focus]
    g = ground(
        engine,
        query=query,
        grade=req.grade,
        instructions=(
            "Write a 10-15 minute small-group plan of 3 or 4 steps (title, minutes, body). "
            "Practice words must be real words spelled only with the taught sounds: "
            + (", ".join(req.sounds) or "none given")
            + ". For tricky-words, use words from the heart-word list. Optionally add a tip and "
            "an alt (a different way to do the step)."
        ),
        idea_schema=_PLAN_IDEA,
        meta=meta,
    )
    steps = (
        clean_steps(g.idea.get("steps"), req.focus, checker, set(default_heart_words()))
        if g
        else []
    )
    if g is None or not steps:
        _finish(
            engine,
            "group_plan",
            query,
            g.ids if g else [],
            "unsupported",
            "No research found",
            started,
            {**meta, "outcome": "unsupported"},
        )
        raise FeatureUnavailable(
            "I could not build a plan that the research supports right now. Please try again."
        )
    qid, updated = _finish(
        engine, "group_plan", query, g.ids, f"{len(steps)} steps", g.label, started, meta
    )
    return GroupPlan(
        minutes=sum(s.minutes for s in steps),
        why=g.research[0].text,
        evidence_label=g.label,
        mixed=g.mixed,
        research_says=g.research,
        steps=steps,
        sources=g.sources,
        content_last_updated=updated,
        query_id=qid,
    )


# ------------------------------------------------------------------ story
class StoryRequest(BaseModel):
    sounds: list[str] = Field(min_length=1, max_length=12)
    about: str | None = Field(default=None, max_length=60)
    variant: int = Field(default=0, ge=0, le=9)
    heart_words: list[str] | None = Field(default=None, max_length=20)

    @field_validator("sounds")
    @classmethod
    def _sounds(cls, v: list[str]) -> list[str]:
        out = [x.strip().lower() for x in v]
        if any(not _GRAPHEME.match(x) for x in out):
            raise ValueError("sounds must be letters such as s, sh or a_e")
        return out

    @field_validator("heart_words")
    @classmethod
    def _hearts(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and any(not _WORD.match(x) for x in v):
            raise ValueError("heart words must be letters only")
        return v


class WordCheckOut(BaseModel):
    word: str
    status: str
    decodable: bool
    reason: str
    graphemes: list[str]
    needs: list[str]


class Story(BaseModel):
    title: str
    words: list[str]
    checks: list[WordCheckOut]
    all_decodable: bool
    flagged: list[str]
    evidence_label: str
    mixed: bool = False
    research_says: list[ResearchClaim]
    sources: list[SourceOut]
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None


STORY_SYSTEM = (
    "You write very short decodable stories for K-3 beginning readers. Use ONLY words that can be "
    "sounded out with the allowed sounds, plus the allowed heart words. Short simple sentences, "
    "no names of real children or places, 20 to 50 words. Return the story by calling "
    "submit_story."
)
STORY_TOOL = ToolSpec(
    "submit_story",
    "Return the story.",
    {
        "type": "object",
        "properties": {"title": {"type": "string"}, "text": {"type": "string"}},
        "required": ["title", "text"],
    },
)


def word_check_out(c: WordCheck) -> WordCheckOut:
    return WordCheckOut(
        word=c.word,
        status=c.status,
        decodable=c.decodable,
        reason=c.reason,
        graphemes=c.graphemes,
        needs=c.needs,
    )


def make_story(engine: Engine, req: StoryRequest) -> Story:
    started = engine.clock()
    checker = make_checker(req.sounds, req.heart_words)
    about = engine.redactor.redact(req.about).strip() if req.about else ""
    meta: dict[str, Any] = {"sounds": req.sounds, "variant": req.variant, "attempts": 0}
    query = "decodable texts for beginning readers practice with taught letter-sound patterns"
    g = ground(
        engine,
        query=query,
        grade=None,
        instructions="Give 1 to 2 research claims about decodable text. No idea field is needed.",
        idea_schema=None,
        meta=meta,
    )
    if g is None:
        _finish(engine, "story", query, [], "unsupported", "No research found", started, meta)
        raise FeatureUnavailable(
            "I could not back this story with research right now. Please try again."
        )

    best: tuple[str, list[str], list[WordCheck]] | None = None
    bad: list[str] = []
    for attempt in range(1 + STORY_REPAIRS):
        meta["attempts"] = attempt + 1
        prompt = (
            f"Allowed sounds: {', '.join(req.sounds)}\n"
            f"Allowed heart words: {', '.join(sorted(checker.heart_words)) or 'none'}\n"
            f"Topic: {about or 'anything friendly'}\nVersion: {req.variant + 1} "
            "(make it different from other versions)\n"
        )
        if bad:
            prompt += "These words were NOT allowed last time, do not use them: " + ", ".join(bad)
        try:
            out = engine.llm.converse(
                model_id=modelconfig.model_id("generation"),
                system=STORY_SYSTEM,
                user=prompt,
                max_tokens=engine.settings.max_output_tokens,
                tool=STORY_TOOL,
            )
        except LLMError as exc:
            meta["story_error"] = str(exc)
            break
        meta["tokens"] = meta.get("tokens", 0) + out.input_tokens + out.output_tokens
        data = out.tool_input or {}
        words = _STORY_TOKEN.findall(_text(data.get("text"), 600))[:MAX_STORY_WORDS]
        if not words:
            continue
        checks = checker.check_text(words)
        title = _text(data.get("title"), 60)
        flagged_now = [c.word for c in checks if not c.allowed]
        if best is None or len(flagged_now) < sum(1 for c in best[2] if not c.allowed):
            best = (title, words, checks)
        if not flagged_now:
            break
        bad = sorted({w.lower() for w in flagged_now})
    if best is None:
        _finish(engine, "story", query, g.ids, "no story", "No research found", started, meta)
        raise FeatureUnavailable("I could not write a story right now. Please try again.")

    title, words, checks = best
    if not title or not all(c.allowed for c in checker.check_text(_STORY_TOKEN.findall(title))):
        title = "Story for " + ", ".join(
            req.sounds[:4]
        )  # a label for the teacher, not reading text
    flagged = [c.word for c in checks if not c.allowed]
    meta["flagged"] = len(flagged)
    qid, updated = _finish(
        engine,
        "story",
        query,
        g.ids,
        f"{len(words)} words, {len(flagged)} flagged",
        g.label,
        started,
        meta,
    )
    return Story(
        title=title,
        words=words,
        checks=[word_check_out(c) for c in checks],
        all_decodable=not flagged,
        flagged=flagged,
        evidence_label=g.label,
        mixed=g.mixed,
        research_says=g.research,
        sources=g.sources,
        content_last_updated=updated,
        query_id=qid,
    )


class DecodableCheckRequest(BaseModel):
    sounds: list[str] = Field(min_length=1, max_length=60)
    words: list[str] = Field(min_length=1, max_length=200)
    heart_words: list[str] | None = Field(default=None, max_length=20)

    @field_validator("sounds")
    @classmethod
    def _sounds(cls, v: list[str]) -> list[str]:
        return [x.strip().lower() for x in v]


def decodable_check(req: DecodableCheckRequest) -> list[WordCheckOut]:
    checker = make_checker(req.sounds, req.heart_words)
    return [word_check_out(checker.check(w[:40])) for w in req.words]


# ------------------------------------------------------------------ why is a kid stuck?
class MistakePair(BaseModel):
    word: str
    said: str

    @field_validator("word", "said")
    @classmethod
    def _letters(cls, v: str) -> str:
        if not stuck.WORD.match(v):
            raise ValueError("letters only, up to 20")
        return v


class StuckRequest(BaseModel):
    pairs: list[MistakePair] = Field(min_length=1, max_length=8)


class MistakeResult(BaseModel):
    kind: Literal["match", "no_match"]
    pattern: str = ""
    skill: str = ""
    try_it: StepOut | None = None
    also_watch: str = ""
    evidence_label: str
    evidence_note: str = ""
    research_says: list[ResearchClaim] = []
    sources: list[SourceOut] = []
    message: str = ""
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None


_LABEL_NOTE = {
    "Very sure": "Several strong sources agree.",
    "Fairly sure": "One good source supports this.",
    "Not sure yet": "The research here is limited or mixed. Treat it as a starting point.",
}
_TRY_IDEA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "try_it": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "minutes": {"type": "integer"}},
            "required": ["text", "minutes"],
        }
    },
    "required": ["try_it"],
}


def diagnose(engine: Engine, req: StuckRequest) -> MistakeResult:
    started = engine.clock()
    pairs = [(p.word, p.said) for p in req.pairs]
    for text in {t for pair in pairs for t in pair}:
        if engine.redactor.redact(text) != text:
            raise BadInput("Please enter only the word and what the child said. No names.")
    found = stuck.analyze(pairs)
    meta: dict[str, Any] = {"pairs": len(pairs)}  # the pairs themselves are never stored
    if found is None:
        qid, updated = _finish(
            engine,
            "stuck",
            "(mistake pattern)",
            [],
            "no_match",
            "No research found",
            started,
            {**meta, "outcome": "no_match"},
        )
        return MistakeResult(
            kind="no_match",
            evidence_label="No research found",
            message="I cannot see one clear pattern in these words. Try 3 to 5 words, or listen "
            "to the child read aloud and note what happens.",
            content_last_updated=updated,
            query_id=qid,
        )
    meta["pattern"] = found.pattern.id
    g = ground(
        engine,
        query=found.pattern.query,
        grade=None,
        instructions="Give 1 to 2 research claims about teaching this skill. In `idea.try_it` "
        "suggest one short activity (text, minutes) a teacher could do.",
        idea_schema=_TRY_IDEA,
        meta=meta,
    )
    if g is None:
        _finish(
            engine,
            "stuck",
            "(mistake pattern)",
            [],
            "unsupported",
            "No research found",
            started,
            {**meta, "outcome": "unsupported"},
        )
        raise FeatureUnavailable(
            "I found a pattern but could not back it with research right now. Please try again."
        )
    raw = g.idea.get("try_it")
    try_it = (
        StepOut(text=_text(raw.get("text"), 300), minutes=_minutes(raw.get("minutes")))
        if isinstance(raw, dict) and _text(raw.get("text"), 300)
        else None
    )
    qid, updated = _finish(
        engine, "stuck", "(mistake pattern)", g.ids, found.pattern.id, g.label, started, meta
    )
    note = _LABEL_NOTE.get(g.label, "")
    if g.mixed:
        note = "The research on this is mixed. Treat it as a starting point."
    if found.total == 1:
        note += " This is based on a single word."
    return MistakeResult(
        kind="match",
        pattern=found.pattern.name,
        skill=found.pattern.skill,
        try_it=try_it,
        also_watch=found.pattern.also_watch,
        evidence_label=g.label,
        evidence_note=note.strip(),
        research_says=g.research,
        sources=g.sources,
        content_last_updated=updated,
        query_id=qid,
    )


# ------------------------------------------------------------------ training + refresher
class TrainingTopic(BaseModel):
    id: str
    title: str
    summary: str
    training_word: str
    fits: str


@cache
def _topics() -> dict[str, dict[str, Any]]:
    data = json.loads((SEED / "training_topics.json").read_text())
    return {t["id"]: t for t in data["topics"]}


def list_topics() -> list[TrainingTopic]:
    return [
        TrainingTopic(**{k: t[k] for k in TrainingTopic.model_fields}) for t in _topics().values()
    ]


class Remember(BaseModel):
    sentence: str
    sounds: list[dict[str, str]]
    tip: str


class Idea(BaseModel):
    title: str
    minutes: int
    steps: list[str]
    need: str


class TrainingPlan(BaseModel):
    topic: TrainingTopic
    remember: Remember
    evidence_label: str
    mixed: bool = False
    research_says: list[ResearchClaim]
    idea: Idea
    short_idea: Idea
    if_stuck: str
    if_easy: str
    for_english_learners: str
    sources: list[SourceOut]
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None


_IDEA_SHAPE: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "minutes": {"type": "integer"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "need": {"type": "string"},
    },
    "required": ["title", "minutes", "steps", "need"],
}
_TRAINING_IDEA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "remember_sounds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"letter": {"type": "string"}, "hint": {"type": "string"}},
            },
        },
        "remember_tip": {"type": "string"},
        "idea": _IDEA_SHAPE,
        "short_idea": _IDEA_SHAPE,
        "if_stuck": {"type": "string"},
        "if_easy": {"type": "string"},
        "for_english_learners": {"type": "string"},
    },
    "required": ["idea", "short_idea", "if_stuck", "if_easy", "for_english_learners"],
}


def _idea(raw: Any, minutes_cap: int) -> Idea | None:
    if not isinstance(raw, dict):
        return None
    title, need = _text(raw.get("title"), 80), _text(raw.get("need"), 120)
    steps = _str_list(raw.get("steps"), 5, 200)
    if not title or not steps:
        return None
    return Idea(
        title=title, minutes=_minutes(raw.get("minutes"), hi=minutes_cap), steps=steps, need=need
    )


def training_plan(engine: Engine, topic_id: str) -> TrainingPlan | None:
    topic = _topics().get(topic_id)
    if topic is None:
        return None
    started = engine.clock()
    meta: dict[str, Any] = {"topic": topic_id}
    g = ground(
        engine,
        query=topic["query"],
        grade=None,
        instructions="Give 1 to 3 research claims about this topic. In `idea` write this week's "
        "plan for a teacher who just had training on it: a 10-minute idea and a 5-minute idea "
        "(title, minutes, steps, what you need), plus if_stuck, if_easy and "
        "for_english_learners tips, and optionally remember_sounds (letter + hint) and "
        "remember_tip.",
        idea_schema=_TRAINING_IDEA,
        meta=meta,
    )
    idea = _idea(g.idea.get("idea"), 20) if g else None
    short = _idea(g.idea.get("short_idea"), 10) if g else None
    if g is None or idea is None or short is None:
        _finish(
            engine,
            "training",
            f"(topic {topic_id})",
            g.ids if g else [],
            "unsupported",
            "No research found",
            started,
            {**meta, "outcome": "unsupported"},
        )
        raise FeatureUnavailable(
            "I could not build this week's plan from the research right now. Please try again."
        )
    sounds = [
        {"letter": _text(x.get("letter"), 6), "hint": _text(x.get("hint"), 80)}
        for x in (g.idea.get("remember_sounds") or [])[:6]
        if isinstance(x, dict) and _text(x.get("letter"), 6)
    ]
    qid, updated = _finish(
        engine, "training", f"(topic {topic_id})", g.ids, topic_id, g.label, started, meta
    )
    return TrainingPlan(
        topic=TrainingTopic(**{k: topic[k] for k in TrainingTopic.model_fields}),
        remember=Remember(
            sentence=g.research[0].text, sounds=sounds, tip=_text(g.idea.get("remember_tip"), 200)
        ),
        evidence_label=g.label,
        mixed=g.mixed,
        research_says=g.research,
        idea=idea,
        short_idea=short,
        if_stuck=_text(g.idea.get("if_stuck"), 300),
        if_easy=_text(g.idea.get("if_easy"), 300),
        for_english_learners=_text(g.idea.get("for_english_learners"), 300),
        sources=g.sources,
        content_last_updated=updated,
        query_id=qid,
    )


class Picked(BaseModel):
    minutes: int
    kind: str
    title: str
    you_get: str


class Refresher(BaseModel):
    day: int
    statement: str
    is_true: bool
    explanation: str
    citations: list[int]
    sources: list[SourceOut]
    skills: list[str]
    picked: list[Picked]
    evidence_label: str
    disclaimer: str = DISCLAIMER
    content_last_updated: str | None = None
    query_id: int | None = None


def refresher(engine: Engine, today: date | None = None) -> Refresher:
    started = engine.clock()
    ordinal = (today or date.today()).toordinal()
    topics = list(_topics().values())
    topic = topics[ordinal % len(topics)]
    meta: dict[str, Any] = {"topic": topic["id"]}
    g = ground(
        engine,
        query=topic["query"],
        grade=None,
        instructions="Give exactly 2 research claims. The first is a plain statement a teacher "
        "can check; the second explains why it matters. No idea field is needed.",
        idea_schema=None,
        meta=meta,
    )
    if g is None:
        _finish(
            engine,
            "refresher",
            f"(topic {topic['id']})",
            [],
            "unsupported",
            "No research found",
            started,
            {**meta, "outcome": "unsupported"},
        )
        raise FeatureUnavailable("Today's refresher is not ready. Please try again later.")
    first = g.research[0]
    explanation = g.research[1].text if len(g.research) > 1 else (g.sources[0].quote or "")
    citations = sorted({n for c in g.research for n in c.citations})
    qid, updated = _finish(
        engine, "refresher", f"(topic {topic['id']})", g.ids, topic["id"], g.label, started, meta
    )
    return Refresher(
        day=ordinal % 5 + 1,
        statement=first.text,
        is_true=True,  # statements are verified claims; false ones need SME-approved myth links
        explanation=explanation,
        citations=citations,
        sources=g.sources,
        skills=list(topic["skills"]),
        picked=[Picked(minutes=1, kind="Read", title=topic["title"], you_get="One idea for today")],
        evidence_label=g.label,
        content_last_updated=updated,
        query_id=qid,
    )


# ------------------------------------------------------------------ feedback
class Feedback(BaseModel):
    rating: Literal["worked", "so-so", "stuck"]
    query_id: int | None = None


def save_feedback(engine: Engine, fb: Feedback) -> None:
    """Rating only: never free text. Stored on the answer's query_log row when it exists."""
    if fb.query_id is not None:
        cur = engine.conn.execute(
            "UPDATE query_log SET feedback = %s WHERE id = %s RETURNING id",
            (fb.rating, fb.query_id),
        )
        if cur.fetchone():
            engine.conn.commit()
            return
    engine.conn.execute(
        """INSERT INTO query_log (feature, redacted_question, feedback)
           VALUES ('feedback', '(feedback)', %s)""",
        (fb.rating,),
    )
    engine.conn.commit()
