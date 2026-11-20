"""Myth detector: matches cue phrases from the `myths` table against the (redacted) question.

A myth's correction is shown only when the myth is linked to passages (`passage_ids`), so the
"Watch out for" text always carries a citation (rule: no source, no claim). Unlinked myths are
still logged so the team can see which sources are missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg


@dataclass(frozen=True)
class Myth:
    myth_id: str
    name: str
    sor_correction: str
    passage_ids: list[str]


def load_myths(conn: psycopg.Connection[dict[str, Any]]) -> list[tuple[Myth, list[str]]]:
    rows = conn.execute(
        "SELECT myth_id, name, cue_patterns, sor_correction, passage_ids FROM myths"
    ).fetchall()
    return [
        (
            Myth(r["myth_id"], r["name"], r["sor_correction"], list(r["passage_ids"])),
            list(r["cue_patterns"]),
        )
        for r in rows
    ]


def detect(question: str, myths: list[tuple[Myth, list[str]]]) -> list[Myth]:
    q = question.lower()
    return [m for m, cues in myths if any(c.lower() in q for c in cues)]
