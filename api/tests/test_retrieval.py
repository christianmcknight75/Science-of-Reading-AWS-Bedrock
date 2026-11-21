from __future__ import annotations

from typing import Any

import psycopg
import pytest

from app.config import Settings
from app.retrieval import fuse, or_query, search, select
from tests.fakes import passage


def test_or_query_keeps_content_words_and_is_safe() -> None:
    q = or_query("How do I teach 'blending'; drop table--?")
    assert q == "how | teach | blending | drop | table"
    assert or_query("?! ..") == ""


def test_rrf_rewards_passages_found_by_both_searches() -> None:
    a, b, c = (passage(f"src_0001_p00{i}") for i in (1, 2, 3))
    fused = fuse([[a, b], [c, b]])
    assert fused[0].passage_id == b.passage_id  # in both lists


def test_threshold_and_per_source_cap() -> None:
    ps = [passage(f"src_0001_p00{i}", similarity=0.9 - i / 100) for i in range(1, 6)]
    ps.append(passage("src_0002_p001", similarity=0.5))
    out = select(ps, min_similarity=0.7, top_k=6, per_source=3)
    assert [p.passage_id for p in out] == ["src_0001_p001", "src_0001_p002", "src_0001_p003"]
    assert select(ps, min_similarity=0.99, top_k=6) == []  # nothing relevant -> no research


@pytest.fixture
def conn() -> Any:
    try:
        c = psycopg.connect(Settings().database_url, row_factory=psycopg.rows.dict_row)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    yield c
    c.close()


def test_search_runs_and_returns_only_retrievable_passages(conn: Any) -> None:
    """Against the real local corpus: same SQL the API uses, only the view's rows come back."""
    vec = [0.05] * 384
    found = search(conn, "teach blending sounds", vec, min_similarity=-1, top_k=50, recent_years=10)
    if not found:
        pytest.skip("no embedded passages in the local database")
    ids = [p.passage_id for p in found]
    ok = conn.execute(
        "SELECT count(*) AS n FROM retrievable_passages WHERE passage_id = ANY(%s)", (ids,)
    ).fetchone()["n"]
    assert ok == len(ids)
    held = conn.execute(
        "SELECT count(*) AS n FROM passages p JOIN sources s USING (source_id) "
        "WHERE p.passage_id = ANY(%s) AND (s.status <> 'approved' "
        "OR s.curation_status IN ('permission','quote_only'))",
        (ids,),
    ).fetchone()["n"]
    assert held == 0
