"""Curated loader against the local Postgres (rolled back). Skipped if it is not running."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest

from sor_ingest import store
from sor_ingest.curated import load_curated

YAML = """
sources:
  - {id: t_ready, title: "Ready Guide (NCEE 1)", year: 2016, url: "https://x.gov/a.pdf",
     license: "public-domain", status: ready, jurisdiction: US, source_type: practice_guide,
     priority: 1, used_for: [qa]}
  - {id: t_gov, title: "UK Guide", url: "TODO: find it", status: ready, jurisdiction: UK,
     source_type: government_guide, license: "OGL"}
  - {id: t_hold, title: "Held Paper", status: permission, contact: "Author"}
  - {id: t_known, title: "Already Reviewed Paper", status: ready, source_type: study}
"""


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[Any]]:
    try:
        c = store.connect()
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    yield c
    c.rollback()
    c.close()


def rows(conn: psycopg.Connection[Any], curated_id: str) -> tuple[Any, ...]:
    r = conn.execute(
        "SELECT status, source_type, pdf_url, url, jurisdiction, curation_status, license "
        "FROM sources WHERE curated_id = %s",
        (curated_id,),
    ).fetchone()
    assert r is not None
    return tuple(r)


def test_loads_as_candidates_never_approved(conn: psycopg.Connection[Any], tmp_path: Path) -> None:
    f = tmp_path / "c.yaml"
    f.write_text(YAML)
    rep = load_curated(conn, f)
    assert len(rep["added"]) == 3 and len(rep["on_hold"]) == 1
    assert rows(conn, "t_ready")[:6] == (
        "candidate", "practice_guide", "https://x.gov/a.pdf", "https://x.gov/a.pdf", "US", "ready",
    )  # fmt: skip
    gov = rows(conn, "t_gov")
    assert gov[1] == "government_guide" and gov[3] is None  # TODO url dropped
    held = rows(conn, "t_hold")
    assert held[0] == "rejected" and held[5] == "permission"  # can never reach the corpus
    assert (
        conn.execute("SELECT count(*) FROM sources WHERE status='approved'").fetchone() is not None
    )


def test_idempotent(conn: psycopg.Connection[Any], tmp_path: Path) -> None:
    f = tmp_path / "c.yaml"
    f.write_text(YAML)
    load_curated(conn, f)
    again = load_curated(conn, f)
    assert not again["added"] and len(again["already_loaded"]) == 4


def test_human_decisions_are_never_changed(conn: psycopg.Connection[Any], tmp_path: Path) -> None:
    conn.execute(
        "INSERT INTO sources (source_id, title, status, reviewer_notes) "
        "VALUES ('src_9500', 'Already reviewed paper', 'rejected', 'my note')"
    )
    f = tmp_path / "c.yaml"
    f.write_text(YAML)
    rep = load_curated(conn, f)
    assert any("src_9500" in a for a in rep["attached"])
    r = conn.execute("SELECT status, reviewer_notes FROM sources WHERE source_id='src_9500'")
    assert r.fetchone() == ("rejected", "my note")
    assert any("src_9500" in c for c in rep["conflicts"])  # rejected, but list says ready
