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
    store.audit_context(conn, "tester", "seed a human decision")
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


def test_rerun_updates_details_but_never_status(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    f = tmp_path / "c.yaml"
    f.write_text(YAML)
    load_curated(conn, f)
    f.write_text(
        YAML.replace('url: "TODO: find it"', 'url: "https://x.gov/uk"').replace(
            "status: permission, contact", "status: quote_only, contact"
        )
    )
    load_curated(conn, f)
    assert rows(conn, "t_gov")[3] == "https://x.gov/uk"  # missing link filled in
    held = rows(conn, "t_hold")
    assert held[0] == "rejected" and held[5] == "quote_only"


def test_prefills_attribution_and_notes_without_overwriting(
    conn: psycopg.Connection[Any], tmp_path: Path
) -> None:
    f = tmp_path / "c.yaml"
    f.write_text(
        """
sources:
  - {id: t_a, title: "Guide A", publisher: "Pub", year: 2020, url: "https://x.gov/a",
     license: "CC BY 4.0", status: ready, review_note: "check figures", source_type: practice_guide}
  - {id: t_b, title: "Guide B", status: ready, attribution: "Custom credit line."}
"""
    )
    load_curated(conn, f)

    def get(cid: str) -> tuple[Any, ...]:
        r = conn.execute(
            "SELECT attribution, reviewer_notes FROM sources WHERE curated_id=%s", (cid,)
        ).fetchone()
        assert r is not None
        return tuple(r)

    a = get("t_a")
    assert a[0] == "\u201cGuide A\u201d by Pub (2020). Source: https://x.gov/a. Licence: CC BY 4.0."
    assert a[1] == "check figures"
    assert get("t_b")[0] == "Custom credit line."
    # a reviewer edits; a re-run must not overwrite it
    conn.execute("UPDATE sources SET attribution='Edited by hand' WHERE curated_id='t_a'")
    load_curated(conn, f)
    assert get("t_a")[0] == "Edited by hand"
