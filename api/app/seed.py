"""Load seed data.   uv run python -m app.seed myths | standards path/to/standards.csv

Standards CSV columns: standard_id,state,grade,domain,description  (swappable per state).
Re-running is safe: rows are upserted by id.
"""

import csv
import json
import sys
from pathlib import Path

import psycopg

from .config import get_settings

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
STANDARD_COLUMNS = ["standard_id", "state", "grade", "domain", "description"]


def load_myths(conn: psycopg.Connection[tuple[object, ...]], path: Path) -> int:
    myths = json.loads(path.read_text())
    for m in myths:
        conn.execute(
            """INSERT INTO myths (myth_id, name, cue_patterns, sor_correction)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (myth_id) DO UPDATE SET name = EXCLUDED.name,
                 cue_patterns = EXCLUDED.cue_patterns, sor_correction = EXCLUDED.sor_correction""",
            (m["myth_id"], m["name"], m["cue_patterns"], m["sor_correction"]),
        )
    return len(myths)


def load_standards(conn: psycopg.Connection[tuple[object, ...]], path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != STANDARD_COLUMNS:
            raise ValueError(f"CSV columns must be exactly {STANDARD_COLUMNS}")
        rows = list(reader)
    for r in rows:
        conn.execute(
            """INSERT INTO standards (standard_id, state, grade, domain, description)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (standard_id) DO UPDATE SET state = EXCLUDED.state,
                 grade = EXCLUDED.grade, domain = EXCLUDED.domain,
                 description = EXCLUDED.description""",
            tuple(r[c] for c in STANDARD_COLUMNS),
        )
    return len(rows)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"myths", "standards"}:
        print(__doc__)
        return 2
    with psycopg.connect(get_settings().database_url) as conn:
        if argv[0] == "myths":
            n = load_myths(conn, SEED_DIR / "myths.json")
        else:
            n = load_standards(conn, Path(argv[1]))
    print(f"loaded {n} {argv[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
