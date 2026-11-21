"""Draft myth links: proposals never reach teachers until a named reviewer approves them."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from app import myth_links, myths
from app.config import Settings


@pytest.fixture
def db() -> Iterator[psycopg.Connection[Any]]:
    try:
        conn = psycopg.connect(Settings().database_url, row_factory=psycopg.rows.dict_row)
        conn.execute("SELECT 1 FROM myth_link_proposals LIMIT 1")
        if not conn.execute("SELECT 1 FROM retrievable_passages LIMIT 1").fetchone():
            pytest.skip("no corpus in the local database")
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    except psycopg.errors.UndefinedTable:
        pytest.skip("run `make migrate` first")
    # a clean slate inside this transaction only
    conn.execute("DELETE FROM myth_link_proposals")
    yield conn
    conn.rollback()
    conn.close()


def shown(conn: Any) -> dict[str, list[str]]:
    return {m.myth_id: m.passage_ids for m, _ in myths.load_myths(conn)}


def test_the_seed_file_is_well_formed() -> None:
    data = json.loads(myth_links.SEED.read_text())["proposals"]
    assert 6 <= len(data) <= 18
    per_myth: dict[str, int] = {}
    for p in data:
        per_myth[p["myth_id"]] = per_myth.get(p["myth_id"], 0) + 1
        assert p["relation"] in ("refutes", "partly", "supports_alternative")
        assert p["quote"].strip() and p["rationale"].strip()
    assert all(1 <= n <= 3 for n in per_myth.values())  # 1-3 candidates per myth
    assert len(per_myth) == 6


def test_every_proposed_quote_is_verbatim_in_a_retrievable_passage(db: Any) -> None:
    assert myth_links.load_proposals(db) == []  # no problems, nothing skipped
    rows = db.execute("SELECT * FROM myth_link_proposals").fetchall()
    assert len(rows) == len(json.loads(myth_links.SEED.read_text())["proposals"])
    assert {r["status"] for r in rows} == {"proposed"} and {r["proposed_by"] for r in rows} == {
        "claude-draft"
    }


def test_loading_proposals_changes_nothing_a_teacher_can_see(db: Any) -> None:
    before = shown(db)
    myth_links.load_proposals(db)
    assert shown(db) == before


def test_a_proposal_pointing_outside_the_retrievable_set_is_skipped(db: Any, tmp_path: Any) -> None:
    bad = {
        "proposals": [
            {
                "myth_id": "myth_three_cueing",
                "passage_id": "src_9999_p001",
                "relation": "refutes",
                "quote": "x y z",
                "rationale": "r",
            },
            {
                "myth_id": "myth_three_cueing",
                "passage_id": "src_0011_p037",
                "relation": "refutes",
                "quote": "words that are not in the passage at all",
                "rationale": "r",
            },
        ]
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(bad))
    problems = myth_links.load_proposals(db, f)
    assert len(problems) == 2 and "not in retrievable_passages" in problems[0]
    assert "verbatim" in problems[1]
    assert db.execute("SELECT count(*) AS n FROM myth_link_proposals").fetchone()["n"] == 0


def test_approval_needs_a_named_reviewer_and_a_note_and_is_the_only_way_in(db: Any) -> None:
    myth_links.load_proposals(db)
    row = db.execute(
        "SELECT proposal_id, myth_id, passage_id FROM myth_link_proposals "
        "ORDER BY proposal_id LIMIT 1"
    ).fetchone()
    pid = row["proposal_id"]
    for who, why in (("", "ok"), ("Dr. Reader", ""), ("  ", "  ")):
        with pytest.raises(ValueError, match="required"):
            myth_links.review(db, pid, approve=True, reviewer=who, note=why)
    assert row["passage_id"] not in shown(db)[row["myth_id"]]
    myth_links.review(db, pid, approve=True, reviewer="Dr. Reader", note="Matches the guide")
    assert row["passage_id"] in shown(db)[row["myth_id"]]
    done = db.execute("SELECT * FROM myth_link_proposals WHERE proposal_id = %s", (pid,)).fetchone()
    assert done["status"] == "approved" and done["reviewed_by"] == "Dr. Reader"
    assert done["review_note"] == "Matches the guide" and done["reviewed_at"] is not None
    with pytest.raises(ValueError, match="already approved"):
        myth_links.review(db, pid, approve=False, reviewer="Someone", note="changed my mind")


def test_rejection_adds_nothing(db: Any) -> None:
    myth_links.load_proposals(db)
    before = shown(db)
    pid = db.execute("SELECT proposal_id FROM myth_link_proposals LIMIT 1").fetchone()[
        "proposal_id"
    ]
    myth_links.review(db, pid, approve=False, reviewer="Dr. Reader", note="Too indirect")
    assert shown(db) == before
    with pytest.raises(ValueError, match="no such"):
        myth_links.review(db, 999999, approve=True, reviewer="x", note="y")


def test_reloading_never_overwrites_a_reviewed_proposal(db: Any) -> None:
    myth_links.load_proposals(db)
    pid = db.execute("SELECT proposal_id FROM myth_link_proposals LIMIT 1").fetchone()[
        "proposal_id"
    ]
    db.execute("UPDATE myth_link_proposals SET rationale = 'EDITED' WHERE proposal_id = %s", (pid,))
    myth_links.review(db, pid, approve=True, reviewer="Dr. Reader", note="ok")
    myth_links.load_proposals(db)
    row = db.execute(
        "SELECT status, rationale FROM myth_link_proposals WHERE proposal_id = %s", (pid,)
    ).fetchone()
    assert row == {"status": "approved", "rationale": "EDITED"}


def test_a_proposal_cannot_claim_review_without_a_reviewer(db: Any) -> None:
    myth_links.load_proposals(db)
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("UPDATE myth_link_proposals SET status = 'approved'")
    db.rollback()
