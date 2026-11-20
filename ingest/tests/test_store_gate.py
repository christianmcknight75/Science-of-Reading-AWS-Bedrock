"""Needs the local Postgres (make dev / docker compose up db). Skipped if unreachable."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from sor_ingest import store
from sor_ingest.chunking import Passage
from sor_ingest.embedder import StubEmbedder


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[Any]]:
    try:
        c = store.connect()
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    yield c
    c.rollback()  # every test runs inside a transaction that is rolled back
    c.close()


def test_candidate_cannot_get_passages(conn: psycopg.Connection[Any]) -> None:
    sid = store.add_candidate(conn, {"source_api": "eric", "source_id": "EJ_TEST1", "title": "T"})
    assert sid is not None
    p = Passage(f"{sid}_p001", "A", 1, "text")
    with pytest.raises(PermissionError):
        store.upsert_passages(conn, sid, [p], [StubEmbedder().embed("text")])


def test_duplicate_candidate_skipped(conn: psycopg.Connection[Any]) -> None:
    rec = {"source_api": "openalex", "source_id": "W1", "title": "T", "doi": "10.1/x"}
    assert store.add_candidate(conn, rec)
    assert store.add_candidate(conn, rec) is None


def test_db_refuses_approval_without_license_record(conn: psycopg.Connection[Any]) -> None:
    sid = store.add_candidate(conn, {"source_api": "eric", "source_id": "EJ_TEST2", "title": "T"})
    assert sid is not None
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE sources SET status = 'approved' WHERE source_id = %s", (sid,))


def test_approved_source_gets_passages_and_reupsert_bumps_version(
    conn: psycopg.Connection[Any],
) -> None:
    sid = store.add_candidate(conn, {"source_api": "eric", "source_id": "EJ_TEST3", "title": "T"})
    assert sid is not None
    conn.execute(
        """UPDATE sources SET status='approved', approved_by='tester', approved_at=now(),
           license='cc-by', attribution='A', license_snapshot_url='x', license_checklist='{}'
           WHERE source_id=%s""",
        (sid,),
    )
    p = Passage(f"{sid}_p001", "A", 1, "phonics text")
    emb = [StubEmbedder().embed("phonics text")]
    store.upsert_passages(conn, sid, [p], emb)
    store.upsert_passages(conn, sid, [p], emb)
    row = conn.execute(
        "SELECT version FROM passages WHERE passage_id=%s", (p.passage_id,)
    ).fetchone()
    assert row and row[0] == 2
