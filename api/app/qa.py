"""POST /api/ask: the Q&A endpoint. Off until QA_ENABLED=true (kill switch)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from . import modelconfig
from .auth import require_user
from .config import Settings, get_settings
from .db import get_conn
from .embedding import QueryEmbedder, get_query_embedder
from .engine import Engine
from .llm import LLM, BedrockLLM
from .ratelimit import RateLimiter
from .redact import Redactor, get_redactor
from .schemas import AnswerResponse, AskRequest

router = APIRouter(prefix="/api")


@lru_cache(maxsize=1)
def _limiter(max_per_minute: int) -> RateLimiter:
    return RateLimiter(max_per_minute)


def get_llm(s: Annotated[Settings, Depends(get_settings)]) -> LLM:
    return BedrockLLM(
        region=modelconfig.region(),
        profile=s.aws_profile,
        guardrail_id=s.guardrail_id,
        guardrail_version=s.guardrail_version,
    )


def get_embedder() -> QueryEmbedder:
    return get_query_embedder()


def get_redact() -> Redactor:
    return get_redactor()


def conn_dep() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    yield from get_conn()


def guard(user: str, s: Settings) -> None:
    """Kill switch, then the per-user rate limit. Shared by every model-backed endpoint."""
    if not s.qa_enabled:
        raise HTTPException(503, "Reading Helper is switched off right now.")
    if not _limiter(s.rate_limit_per_minute).allow(user):
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")


@router.post("/ask", response_model=AnswerResponse)
def ask(
    req: AskRequest,
    user: Annotated[str, Depends(require_user)],
    s: Annotated[Settings, Depends(get_settings)],
    conn: Annotated[psycopg.Connection[dict[str, Any]], Depends(conn_dep)],
    llm: Annotated[LLM, Depends(get_llm)],
    embedder: Annotated[QueryEmbedder, Depends(get_embedder)],
    redactor: Annotated[Redactor, Depends(get_redact)],
) -> AnswerResponse:
    guard(user, s)
    return Engine(conn, llm, embedder, redactor, s).ask(req)
