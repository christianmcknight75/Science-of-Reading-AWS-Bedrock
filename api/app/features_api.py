"""Phase 4 endpoints (docs/API_CONTRACT.md). All model-backed ones sit behind the kill switch."""

from __future__ import annotations

from typing import Annotated, Any, NoReturn

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response

from . import features as f
from .auth import require_user
from .config import Settings, get_settings
from .embedding import QueryEmbedder
from .engine import Engine
from .llm import LLM
from .qa import conn_dep, get_embedder, get_llm, get_redact, guard
from .redact import Redactor

router = APIRouter(prefix="/api")
Conn = Annotated[psycopg.Connection[dict[str, Any]], Depends(conn_dep)]
User = Annotated[str, Depends(require_user)]
Cfg = Annotated[Settings, Depends(get_settings)]


def _engine(
    conn: Conn,
    s: Cfg,
    llm: Annotated[LLM, Depends(get_llm)],
    embedder: Annotated[QueryEmbedder, Depends(get_embedder)],
    redactor: Annotated[Redactor, Depends(get_redact)],
) -> Engine:
    return Engine(conn, llm, embedder, redactor, s)


Eng = Annotated[Engine, Depends(_engine)]


def _fail(exc: Exception) -> NoReturn:
    if isinstance(exc, f.BadInput):
        raise HTTPException(422, str(exc)) from exc
    raise HTTPException(503, str(exc)) from exc


@router.post("/group-plan", response_model=f.GroupPlan)
def group_plan(req: f.GroupPlanRequest, user: User, s: Cfg, engine: Eng) -> f.GroupPlan:
    guard(user, s)
    try:
        return f.group_plan(engine, req)
    except (f.BadInput, f.FeatureUnavailable) as exc:
        _fail(exc)


@router.post("/story", response_model=f.Story)
def story(req: f.StoryRequest, user: User, s: Cfg, engine: Eng) -> f.Story:
    guard(user, s)
    try:
        return f.make_story(engine, req)
    except (f.BadInput, f.FeatureUnavailable) as exc:
        _fail(exc)


@router.post("/decodable/check")
def decodable_check(req: f.DecodableCheckRequest, user: User) -> dict[str, list[f.WordCheckOut]]:
    """Plain code, no model: works even when the kill switch is off."""
    try:
        return {"checks": f.decodable_check(req)}
    except f.BadInput as exc:
        _fail(exc)


@router.post("/stuck", response_model=f.MistakeResult)
def stuck(req: f.StuckRequest, user: User, s: Cfg, engine: Eng) -> f.MistakeResult:
    guard(user, s)
    try:
        return f.diagnose(engine, req)
    except (f.BadInput, f.FeatureUnavailable) as exc:
        _fail(exc)


@router.get("/training/topics", response_model=list[f.TrainingTopic])
def training_topics(user: User) -> list[f.TrainingTopic]:
    return f.list_topics()


@router.get("/training/topics/{topic_id}", response_model=f.TrainingPlan)
def training_topic(topic_id: str, user: User, s: Cfg, engine: Eng) -> f.TrainingPlan:
    guard(user, s)
    try:
        plan = f.training_plan(engine, topic_id)
    except f.FeatureUnavailable as exc:
        _fail(exc)
    if plan is None:
        raise HTTPException(404, "I do not know that training topic.")
    return plan


@router.get("/refresher/today", response_model=f.Refresher)
def refresher_today(user: User, s: Cfg, engine: Eng) -> f.Refresher:
    guard(user, s)
    try:
        return f.refresher(engine)
    except f.FeatureUnavailable as exc:
        _fail(exc)


@router.post("/feedback", status_code=204)
def feedback(fb: f.Feedback, user: User, s: Cfg, conn: Conn) -> Response:
    """Rating only. No model call, so it works with the kill switch off."""
    f.save_feedback(
        Engine(conn, None, None, None, s),  # type: ignore[arg-type]
        fb,
    )
    return Response(status_code=204)
