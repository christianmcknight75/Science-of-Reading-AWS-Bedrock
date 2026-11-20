"""Database access. The approval gate lives here: only approved sources are ever processed."""

from __future__ import annotations

import html
import os
from typing import Any

import psycopg

from .chunking import Passage

DEFAULT_URL = "postgresql://sor:local-dev-only@localhost:5433/sor"


def connect() -> psycopg.Connection[Any]:
    return psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_URL))


def audit_context(conn: psycopg.Connection[Any], actor: str, reason: str) -> None:
    """Who is changing a source status and why. The database refuses status changes without it
    and writes the audit row itself. Transaction-local."""
    conn.execute(
        "SELECT set_config('app.actor', %s, true), set_config('app.reason', %s, true)",
        (actor, reason),
    )


def next_source_id(conn: psycopg.Connection[Any]) -> str:
    row = conn.execute(
        "SELECT COALESCE(MAX(substring(source_id from 5)::int), 0) + 1 FROM sources"
    ).fetchone()
    if row is None:
        raise RuntimeError("could not compute next source id")
    return f"src_{row[0]:04d}"


def add_candidate(conn: psycopg.Connection[Any], rec: dict[str, Any]) -> str | None:
    """Insert a search result as status 'candidate'. Returns the new source_id, or None if the
    paper (by DOI or ERIC id) is already known."""
    doi = rec.get("doi") or None
    eric_id = rec["source_id"] if rec.get("source_api") == "eric" else None
    exists = conn.execute(
        "SELECT 1 FROM sources WHERE (%s::text IS NOT NULL AND lower(doi) = lower(%s::text)) "
        "OR (%s::text IS NOT NULL AND eric_id = %s::text)",
        (doi, doi, eric_id, eric_id),
    ).fetchone()
    if exists:
        return None
    sid = next_source_id(conn)
    conn.execute(
        """INSERT INTO sources (source_id, title, authors, year, doi, eric_id, url, pdf_url,
                                license, discovered_from)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            sid,
            html.unescape(rec["title"]),
            rec.get("authors") or [],
            rec.get("year"),
            doi,
            eric_id,
            rec.get("landing_url"),
            rec.get("pdf_url"),
            rec.get("license"),
            rec.get("source_api"),
        ),
    )
    return sid


def approved_sources(
    conn: psycopg.Connection[Any], include_processed: bool = False
) -> list[tuple[str, str | None, bool]]:
    """(source_id, pdf_url, has_evidence_ratings) for approved sources. By default only those with
    no passages yet. WWC practice guides carry a Strong/Moderate/Minimal rating per
    recommendation."""
    rows = conn.execute(
        """SELECT s.source_id, s.pdf_url,
                  (s.source_type = 'practice_guide'
                   AND s.publisher ILIKE '%%What Works Clearinghouse%%') AS rated
           FROM sources s
           WHERE s.status = 'approved'
             AND (%s OR NOT EXISTS (SELECT 1 FROM passages p WHERE p.source_id = s.source_id))
           ORDER BY s.source_id""",
        (include_processed,),
    ).fetchall()
    return [(r[0], r[1], bool(r[2])) for r in rows]


def is_approved(conn: psycopg.Connection[Any], source_id: str) -> bool:
    row = conn.execute("SELECT status FROM sources WHERE source_id = %s", (source_id,)).fetchone()
    return bool(row and row[0] == "approved")


def upsert_passages(
    conn: psycopg.Connection[Any],
    source_id: str,
    passages: list[Passage],
    embeddings: list[list[float]],
) -> int:
    """Refuses unapproved sources. Re-running replaces passages and bumps their version."""
    if not is_approved(conn, source_id):
        raise PermissionError(f"{source_id} is not approved; refusing to store passages")
    for p, emb in zip(passages, embeddings, strict=True):
        vec = "[" + ",".join(f"{x:.8f}" for x in emb) + "]"
        conn.execute(
            """INSERT INTO passages (passage_id, source_id, section, page, page_end, grade, text,
                                     embedding, recommendation, evidence_rating)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)
               ON CONFLICT (passage_id) DO UPDATE SET
                 section = EXCLUDED.section, page = EXCLUDED.page, page_end = EXCLUDED.page_end,
                 grade = EXCLUDED.grade, text = EXCLUDED.text,
                 embedding = EXCLUDED.embedding, recommendation = EXCLUDED.recommendation,
                 evidence_rating = EXCLUDED.evidence_rating, version = passages.version + 1""",
            (
                p.passage_id,
                source_id,
                p.section,
                p.page,
                p.page_end if p.page_end is not None else p.page,
                p.grade,
                p.text,
                vec,
                p.recommendation,
                p.evidence_rating,
            ),
        )
    conn.execute(
        "DELETE FROM passages WHERE source_id = %s AND NOT (passage_id = ANY(%s))",
        (source_id, [p.passage_id for p in passages]),
    )
    return len(passages)
