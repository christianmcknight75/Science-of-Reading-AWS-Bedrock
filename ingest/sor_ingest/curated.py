"""Load curated_sources.yaml into the review queue.

Nothing here approves anything, and a decision a human already made is never changed: a source that
is already approved or rejected only gets its curation metadata attached (and any disagreement is
reported). A human still attaches the license snapshot and clicks Approve in the admin page.

  ready / verify      -> status 'candidate' (shows in the review queue)
  permission / quote_only -> status 'rejected' with an ON HOLD note, so they can never reach the
                         corpus but stay visible. Re-open them by deciding the question, then
                         changing the status in the YAML and re-running.
"""

from __future__ import annotations

import difflib
import html
import re
from pathlib import Path
from typing import Any

import psycopg
import yaml

from .store import audit_context

CURATED_FILE = Path(__file__).resolve().parent.parent / "curated_sources.yaml"
HOLD = {"permission", "quote_only"}
HOLD_TEXT = {
    "permission": "ON HOLD: rights reserved. Ask the publisher/authors for permission first.",
    "quote_only": "ON HOLD: CC BY-NC-ND. Waiting on the team's no-derivatives decision.",
}


def _url_fields(url: str | None) -> tuple[str | None, str | None, str | None]:
    """(landing url, pdf url, doi). 'TODO...' placeholders become None."""
    if not url or url.upper().startswith("TODO"):
        return None, None, None
    if url.startswith("https://doi.org/"):
        return url, None, url.removeprefix("https://doi.org/")
    if url.lower().endswith(".pdf"):
        return url, url, None
    return url, None, None


def _note(entry: dict[str, Any]) -> str | None:
    parts = []
    if entry.get("note"):
        parts.append(entry["note"])
    if entry.get("contact"):
        parts.append(f"Contact: {entry['contact']}")
    if str(entry.get("url", "")).upper().startswith("TODO"):
        parts.append(f"URL still to find ({entry['url']})")
    return " ".join(parts) or None


def _norm(title: str) -> str:
    t = re.sub(r"\(.*?\)", " ", html.unescape(title).lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def _find_existing(
    conn: psycopg.Connection[Any], title: str, url: str | None, doi: str | None
) -> tuple[str, str] | None:
    """An already-known source (found by search or an earlier allow-list) = same DOI/URL, or a
    near-identical title. Returns (source_id, status)."""
    rows = conn.execute(
        "SELECT source_id, status, title, lower(doi), url FROM sources WHERE curated_id IS NULL"
    ).fetchall()
    target = _norm(title)
    for sid, status, t, d, u in rows:
        if (doi and d == doi.lower()) or (url and u and u.rstrip("/") == url.rstrip("/")):
            return sid, status
        if difflib.SequenceMatcher(None, target, _norm(t)).ratio() >= 0.9:
            return sid, status
    return None


def load_curated(conn: psycopg.Connection[Any], path: Path = CURATED_FILE) -> dict[str, Any]:
    entries: list[dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))["sources"]
    report: dict[str, Any] = {"added": [], "on_hold": [], "attached": [], "already_loaded": [],
                              "conflicts": []}  # fmt: skip
    for e in entries:
        cur = e["status"]
        if cur not in {"ready", "verify"} | HOLD:
            raise ValueError(f"{e['id']}: unknown status {cur!r}")
        title = html.unescape(e["title"])
        url, pdf_url, doi = _url_fields(e.get("url"))
        held = cur in HOLD
        role = e.get("evidence_role") or (
            "summary" if e.get("source_type") == "government_guide" else "primary"
        )
        meta = (
            e["id"], e.get("publisher"), e.get("jurisdiction"), e.get("priority"),
            e.get("used_for", []), bool(e.get("foundational_allow_list", False)), cur, _note(e),
            role,
        )  # fmt: skip
        if conn.execute("SELECT 1 FROM sources WHERE curated_id = %s", (e["id"],)).fetchone():
            # Re-run: refresh curation details and fill in a missing link. Never touch status.
            conn.execute(
                """UPDATE sources SET publisher=%s, jurisdiction=%s, priority=%s, used_for=%s,
                     foundational_allow_list=%s, curation_status=%s, curation_note=%s,
                     evidence_role=%s, url=COALESCE(url, %s), pdf_url=COALESCE(pdf_url, %s),
                     doi=COALESCE(doi, %s) WHERE curated_id=%s""",
                (*meta[1:], url, pdf_url, doi, e["id"]),
            )
            report["already_loaded"].append(e["id"])
            continue
        found = _find_existing(conn, title, url, doi)
        if found:
            sid, status = found
            conn.execute(
                """UPDATE sources SET curated_id=%s, publisher=%s, jurisdiction=%s, priority=%s,
                     used_for=%s, foundational_allow_list=%s, curation_status=%s, curation_note=%s,
                     evidence_role=%s, url=COALESCE(url, %s), pdf_url=COALESCE(pdf_url, %s)
                   WHERE source_id=%s""",
                (*meta, url, pdf_url, sid),
            )
            if status == "candidate" and held:  # undecided and on hold: park it
                audit_context(conn, "curated-loader", HOLD_TEXT[cur])
                conn.execute(
                    """UPDATE sources SET status=%s, reviewer_notes=%s,
                         license=COALESCE(license, %s) WHERE source_id=%s""",
                    (
                        "rejected" if held else "candidate",
                        HOLD_TEXT.get(cur),
                        e.get("license"),
                        sid,
                    ),
                )
            elif (status == "approved" and held) or (status == "rejected" and not held):
                report["conflicts"].append(
                    f"{sid} is {status} but curated list says {cur} ({e['id']})"
                )
            report["attached"].append(f"{e['id']} -> {sid} ({status})")
            continue
        row = conn.execute(
            "SELECT COALESCE(MAX(substring(source_id from 5)::int), 0) + 1 FROM sources"
        ).fetchone()
        if row is None:
            raise RuntimeError("could not compute next source id")
        sid = f"src_{row[0]:04d}"
        if held:
            audit_context(conn, "curated-loader", HOLD_TEXT[cur])
        conn.execute(
            """INSERT INTO sources (source_id, title, authors, year, doi, url, pdf_url,
                 discovered_from, curated_id, publisher, jurisdiction, priority, used_for,
                 foundational_allow_list, curation_status, curation_note, evidence_role, status,
                 reviewer_notes, license, source_type)
               VALUES (%s,%s,%s,%s,%s,%s,%s,'curated',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                sid, title, [e["publisher"]] if e.get("publisher") else [], e.get("year"),
                doi, url, pdf_url, *meta, "rejected" if held else "candidate",
                HOLD_TEXT.get(cur), e.get("license"), e.get("source_type", "study"),
            ),
        )  # fmt: skip
        report["on_hold" if held else "added"].append(f"{e['id']} -> {sid}")
    return report
