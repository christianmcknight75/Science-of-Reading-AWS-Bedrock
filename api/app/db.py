from collections.abc import Iterator
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import get_settings


def get_conn() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        yield conn
