from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from app.config import get_settings
from app.seed import SEED_DIR, load_myths, load_standards


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    try:
        c = psycopg.connect(get_settings().database_url)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not running")
    yield c
    c.rollback()
    c.close()


def test_myths_load_and_are_idempotent(conn: psycopg.Connection[tuple[object, ...]]) -> None:
    n = load_myths(conn, SEED_DIR / "myths.json")
    assert n >= 4 and load_myths(conn, SEED_DIR / "myths.json") == n
    row = conn.execute("SELECT count(*) FROM myths").fetchone()
    assert row and row[0] == n


def test_standards_csv_validated(
    conn: psycopg.Connection[tuple[object, ...]], tmp_path: Path
) -> None:
    good = tmp_path / "s.csv"
    good.write_text("standard_id,state,grade,domain,description\nMS_ELA_RF_K_2,MS,K,RF,Test text\n")
    assert load_standards(conn, good) == 1
    bad = tmp_path / "b.csv"
    bad.write_text("id,text\n1,x\n")
    with pytest.raises(ValueError):
        load_standards(conn, bad)
