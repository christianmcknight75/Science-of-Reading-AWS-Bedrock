"""sor-ingest: find candidates, then process approved sources.

sor-ingest search --topic "phonemic awareness" --rows 20   # -> status 'candidate' (no parsing)
sor-ingest allowlist                                       # foundational docs -> 'candidate'
sor-ingest process --embedder stub|titan                   # approved sources only
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path

from . import store
from .chunking import chunk_blocks
from .curated import load_curated
from .embedder import get_embedder
from .parse import parse_pdf

PDF_DIR = Path(os.environ.get("SOR_PDF_DIR", "data/local/pdfs"))


def cmd_search(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "source_search"))
    import source_search as ss  # stdlib-only script kept in ingest/source_search

    since = ss.default_since_year()
    topics = args.topic or ss.DEFAULT_TOPICS
    added = skipped = 0
    with store.connect() as conn:
        for topic in topics:
            result = ss.search(topic, since, args.rows, os.environ.get("OPENALEX_API_KEY"))
            for api in ("eric", "openalex"):
                for rec in result[api].get("records", []):
                    if rec["status"] != "candidate":
                        continue
                    if store.add_candidate(conn, rec):
                        added += 1
                    else:
                        skipped += 1
    print(f"added {added} candidates, skipped {skipped} already known")
    return 0


def cmd_curated(args: argparse.Namespace) -> int:
    with store.connect() as conn:
        report = load_curated(conn)
        if args.dry_run:
            conn.rollback()
    prefix = "[dry run, nothing saved] " if args.dry_run else ""
    for key, items in report.items():
        print(f"{prefix}{key}: {len(items)}")
        for item in items:
            print(f"    {item}")
    return 0


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": "SoR-Assistant-ingest/0.1"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        dest.write_bytes(r.read())


def cmd_process(args: argparse.Namespace) -> int:
    embedder = get_embedder(args.embedder)
    done = 0
    with store.connect() as conn:
        for source_id, pdf_url in store.approved_unprocessed(conn):
            pdf = PDF_DIR / f"{source_id}.pdf"
            if not pdf.exists():
                if not pdf_url:
                    print(f"{source_id}: no pdf_url and no local file; skipping")
                    continue
                _download(pdf_url, pdf)
            passages = chunk_blocks(source_id, parse_pdf(pdf))
            n = store.upsert_passages(
                conn, source_id, passages, [embedder.embed(p.text) for p in passages]
            )
            print(f"{source_id}: {n} passages")
            done += 1
    print(f"processed {done} sources")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sor-ingest")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--topic", action="append")
    s.add_argument("--rows", type=int, default=20)
    s.set_defaults(fn=cmd_search)
    cu = sub.add_parser("curated")
    cu.add_argument("--dry-run", action="store_true")
    cu.set_defaults(fn=cmd_curated)
    pr = sub.add_parser("process")
    pr.add_argument("--embedder", choices=["stub", "titan"], default="stub")
    pr.set_defaults(fn=cmd_process)
    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
