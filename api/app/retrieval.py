"""Hybrid retrieval: vector + full-text, reciprocal rank fusion, filters, relevance threshold.

Reads ONLY the `retrievable_passages` view, never `passages` (held sources stay out).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

import psycopg

from .schemas import Passage

RRF_K = 60
POOL = 30
MAX_PER_SOURCE = 3  # keeps one huge source (the NRP report) from crowding out the rest
_WORD = re.compile(r"[a-z0-9]{3,}")

_BASE = """
WITH base AS (
  SELECT rp.passage_id, rp.source_id, rp.source_title, rp.source_type, rp.evidence_role,
         rp.evidence_rating, rp.year, rp.section, rp.page_label, rp.page_end_label, rp.text,
         rp.tsv, rp.embedding, s.randomized, s.sample_size, s.has_comparison_group
  FROM retrievable_passages rp JOIN sources s USING (source_id)
  WHERE (%(grade)s::text IS NULL OR rp.grade IS NULL OR rp.grade = %(grade)s::text)
    AND (%(topic)s::text IS NULL OR %(topic)s::text = ANY(s.topics))
    AND (rp.year IS NULL OR rp.year >= %(min_year)s
         OR rp.source_type NOT IN ('study', 'meta_analysis') OR s.foundational_allow_list)
)
"""
_COLS = (
    "passage_id, source_id, source_title, source_type, evidence_role, evidence_rating, year, "
    "section, page_label, page_end_label, text, randomized, sample_size, has_comparison_group, "
    "1 - (embedding <=> %(vec)s::vector) AS similarity"
)
# The pieces below are constants (no user input); values are passed as bound parameters.
_VECTOR_SQL = (
    _BASE
    + f"SELECT {_COLS} FROM base WHERE embedding IS NOT NULL "
    + "ORDER BY embedding <=> %(vec)s::vector LIMIT %(pool)s"
)
_FTS_SQL = (
    _BASE
    + f"SELECT {_COLS} FROM base, to_tsquery('english', %(tsq)s) q WHERE tsv @@ q "
    + "ORDER BY ts_rank_cd(tsv, q) DESC LIMIT %(pool)s"
)


def or_query(question: str) -> str:
    """'a | b | c' from the question's words (stop words are dropped by Postgres)."""
    words = dict.fromkeys(_WORD.findall(question.lower()))
    return " | ".join(words)


def _passage(row: dict[str, Any]) -> Passage:
    return Passage(
        passage_id=row["passage_id"],
        source_id=row["source_id"],
        source_title=row["source_title"],
        source_type=row["source_type"],
        evidence_role=row["evidence_role"],
        evidence_rating=row["evidence_rating"],
        year=row["year"],
        section=row["section"],
        page_label=row["page_label"],
        page_end_label=row["page_end_label"],
        text=row["text"],
        similarity=float(row["similarity"] or 0.0),
        randomized=row["randomized"],
        sample_size=row["sample_size"],
        has_comparison_group=row["has_comparison_group"],
    )


def fuse(ranked_lists: list[list[Passage]]) -> list[Passage]:
    """Reciprocal rank fusion over several ranked lists."""
    score: dict[str, float] = {}
    by_id: dict[str, Passage] = {}
    for lst in ranked_lists:
        for rank, p in enumerate(lst, start=1):
            score[p.passage_id] = score.get(p.passage_id, 0.0) + 1.0 / (RRF_K + rank)
            by_id[p.passage_id] = p
    return [by_id[pid] for pid, _ in sorted(score.items(), key=lambda kv: -kv[1])]


def select(
    fused: list[Passage], *, min_similarity: float, top_k: int, per_source: int = MAX_PER_SOURCE
) -> list[Passage]:
    """Relevance threshold, then top-k with a cap per source."""
    taken: Counter[str] = Counter()
    out: list[Passage] = []
    for p in fused:
        if p.similarity < min_similarity or taken[p.source_id] >= per_source:
            continue
        taken[p.source_id] += 1
        out.append(p)
        if len(out) == top_k:
            break
    return out


def search(
    conn: psycopg.Connection[dict[str, Any]],
    question: str,
    query_vec: list[float],
    *,
    min_similarity: float,
    top_k: int,
    recent_years: int,
    grade: str | None = None,
    topic: str | None = None,
    today: date | None = None,
) -> list[Passage]:
    params: dict[str, Any] = {
        "grade": grade,
        "topic": topic,
        "min_year": (today or date.today()).year - recent_years,
        "vec": str(query_vec),
        "pool": POOL,
    }
    lists = [[_passage(r) for r in conn.execute(_VECTOR_SQL, params).fetchall()]]
    tsq = or_query(question)
    if tsq:
        fts = conn.execute(_FTS_SQL, {**params, "tsq": tsq}).fetchall()
        lists.append([_passage(r) for r in fts])
    return select(fuse(lists), min_similarity=min_similarity, top_k=top_k)


def fetch(conn: psycopg.Connection[dict[str, Any]], passage_ids: list[str]) -> list[Passage]:
    """Passages by id, still through the retrievable view (used for myth sources)."""
    if not passage_ids:
        return []
    rows = conn.execute(
        """SELECT rp.passage_id, rp.source_id, rp.source_title, rp.source_type, rp.evidence_role,
                  rp.evidence_rating, rp.year, rp.section, rp.page_label, rp.page_end_label,
                  rp.text, s.randomized, s.sample_size, s.has_comparison_group,
                  1.0 AS similarity
           FROM retrievable_passages rp JOIN sources s USING (source_id)
           WHERE rp.passage_id = ANY(%s)""",
        (passage_ids,),
    ).fetchall()
    return [_passage(r) for r in rows]
