"""Command line for the one thing the API must never do: create the first administrator.

    cd api && uv run python -m app.users create-admin --email a@school.org --name "A B" \
        --district "Example District"

The password is typed at a prompt (never an argument, never logged).
"""

from __future__ import annotations

import argparse
import getpass
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .accounts import MIN_PASSWORD, _norm_email, hash_password
from .config import get_settings


def create_admin(
    conn: psycopg.Connection[dict[str, Any]], *, email: str, name: str, district: str, password: str
) -> str:
    email = _norm_email(email)
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
    row = conn.execute(
        """INSERT INTO users (name, email, district, role, password_hash)
           VALUES (%s, %s, %s, 'admin', %s) RETURNING user_id::text AS user_id""",
        (name.strip(), email, district.strip(), hash_password(password)),
    ).fetchone()
    if row is None:
        raise RuntimeError("could not create the admin")
    return str(row["user_id"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.users")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-admin")
    c.add_argument("--email", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--district", required=True)
    args = ap.parse_args(argv)
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Again: "):
        print("The passwords do not match.", file=sys.stderr)
        return 1
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        user_id = create_admin(
            conn, email=args.email, name=args.name, district=args.district, password=password
        )
    print(f"created admin {user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
