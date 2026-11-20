"""Draft myth-to-passage links, kept apart from what teachers see.

    cd api && uv run python -m app.myth_links load            # (re)load the draft proposals
    uv run python -m app.myth_links list
    uv run python -m app.myth_links approve 3 --reviewer "Name" --note "Why"
    uv run python -m app.myth_links reject  3 --reviewer "Name" --note "Why"

`load` only ever writes status 'proposed' and never touches a reviewed row. The engine reads
`myths.passage_ids`; only `approve` adds to it, and only with a named reviewer and a note.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import get_settings
from .verifier import quote_in

SEED = Path(__file__).resolve().parents[1] / "seed" / "myth_link_proposals.json"
PROPOSER = "claude-draft"


def load_proposals(conn: psycopg.Connection[dict[str, Any]], path: Path = SEED) -> list[str]:
    """Insert draft proposals. Returns problems found (a proposal with a problem is skipped)."""
    problems: list[str] = []
    for p in json.loads(path.read_text())["proposals"]:
        row = conn.execute(
            "SELECT text FROM retrievable_passages WHERE passage_id = %s", (p["passage_id"],)
        ).fetchone()
        if row is None:
            problems.append(f"{p['myth_id']} -> {p['passage_id']}: not in retrievable_passages")
            continue
        if not quote_in(p["quote"], row["text"]):
            problems.append(f"{p['myth_id']} -> {p['passage_id']}: quote not found verbatim")
            continue
        conn.execute(
            """INSERT INTO myth_link_proposals
                   (myth_id, passage_id, relation, quote, rationale, proposed_by)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (myth_id, passage_id) DO UPDATE
                   SET relation = EXCLUDED.relation, quote = EXCLUDED.quote,
                       rationale = EXCLUDED.rationale
                   WHERE myth_link_proposals.status = 'proposed'""",
            (p["myth_id"], p["passage_id"], p["relation"], p["quote"], p["rationale"], PROPOSER),
        )
    return problems


def review(
    conn: psycopg.Connection[dict[str, Any]],
    proposal_id: int,
    *,
    approve: bool,
    reviewer: str,
    note: str,
) -> None:
    if not reviewer.strip() or not note.strip():
        raise ValueError("a reviewer name and a note are required")
    row = conn.execute(
        "SELECT myth_id, passage_id, status FROM myth_link_proposals WHERE proposal_id = %s "
        "FOR UPDATE",
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise ValueError("no such proposal")
    if row["status"] != "proposed":
        raise ValueError(f"already {row['status']}")
    conn.execute(
        """UPDATE myth_link_proposals SET status = %s, reviewed_by = %s, reviewed_at = now(),
                  review_note = %s WHERE proposal_id = %s""",
        ("approved" if approve else "rejected", reviewer.strip(), note.strip(), proposal_id),
    )
    if approve:  # the only place a draft becomes visible to teachers
        conn.execute(
            """UPDATE myths SET passage_ids = array_append(passage_ids, %s)
               WHERE myth_id = %s AND NOT (%s = ANY(passage_ids))""",
            (row["passage_id"], row["myth_id"], row["passage_id"]),
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.myth_links")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load")
    sub.add_parser("list")
    for name in ("approve", "reject"):
        c = sub.add_parser(name)
        c.add_argument("proposal_id", type=int)
        c.add_argument("--reviewer", required=True)
        c.add_argument("--note", required=True)
    args = ap.parse_args(argv)
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        if args.cmd == "load":
            for problem in load_proposals(conn):
                print("SKIPPED", problem)
            print("loaded draft proposals (status: proposed)")
        elif args.cmd == "list":
            for r in conn.execute(
                "SELECT proposal_id, myth_id, passage_id, relation, status "
                "FROM myth_link_proposals ORDER BY myth_id, proposal_id"
            ):
                print(r["proposal_id"], r["status"], r["myth_id"], r["passage_id"], r["relation"])
        else:
            review(
                conn,
                args.proposal_id,
                approve=args.cmd == "approve",
                reviewer=args.reviewer,
                note=args.note,
            )
            print(f"{args.cmd}d proposal {args.proposal_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
