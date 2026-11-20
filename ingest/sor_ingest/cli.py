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
from .ratings import annotate_recommendations

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


def cmd_correct(args: argparse.Namespace) -> int:
    """Fix title/year/url of a reviewed source. The database logs who, what changed and why."""
    fields = {
        k: v
        for k, v in {
            "title": args.title,
            "year": args.year,
            "url": args.url,
            "pdf_url": args.pdf_url,
        }.items()
        if v is not None
    }
    if not fields:
        print("nothing to change: pass --title, --year, --url or --pdf-url", file=sys.stderr)
        return 2
    with store.connect() as conn:
        store.audit_context(conn, args.actor, args.reason)
        sets = ", ".join(f"{k} = %s" for k in fields)
        cur = conn.execute(
            f"UPDATE sources SET {sets} WHERE source_id = %s",  # noqa: S608 (keys are fixed above)
            (*fields.values(), args.source_id),
        )
        if cur.rowcount != 1:
            print(f"no such source: {args.source_id}", file=sys.stderr)
            conn.rollback()
            return 1
    print(f"{args.source_id} updated: {', '.join(fields)}")
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
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("the link did not return a PDF file")
    dest.write_bytes(data)


GRADE_SUFFIX = {"k": "K", "g1": "1", "g2": "2", "g3": "3"}


def _local_files(source_id: str) -> list[tuple[Path, str | None]]:
    """PDFs for a source: `<id>.pdf`, or one per grade named `<id>_k.pdf`, `<id>_g1.pdf`, ..."""
    single = PDF_DIR / f"{source_id}.pdf"
    if single.exists():
        return [(single, None)]
    files = []
    for f in sorted(PDF_DIR.glob(f"{source_id}_*.pdf")):
        suffix = f.stem.removeprefix(f"{source_id}_").lower()
        files.append((f, GRADE_SUFFIX.get(suffix, suffix.upper())))
    order = {g: i for i, g in enumerate(["K", "1", "2", "3"])}
    return sorted(files, key=lambda fg: order.get(fg[1] or "", 99))


def cmd_process(args: argparse.Namespace) -> int:
    embedder = get_embedder(args.embedder)
    done = skipped = 0
    with store.connect() as conn:
        for source_id, pdf_url, rated in store.approved_sources(conn, args.all):
            files = _local_files(source_id)
            if not files:
                if not pdf_url:
                    print(f"{source_id}: no pdf_url and no local file; skipping")
                    skipped += 1
                    continue
                pdf = PDF_DIR / f"{source_id}.pdf"
                try:
                    _download(pdf_url, pdf)
                except (OSError, ValueError) as exc:  # URLError and HTTPError are OSErrors
                    print(f"{source_id}: download failed ({exc}); skipping")
                    skipped += 1
                    continue
                files = [(pdf, None)]
            blocks = []
            try:
                for pdf, grade in files:
                    part = parse_pdf(pdf, grade)
                    blocks.extend(annotate_recommendations(part) if rated else part)
            except Exception as exc:  # noqa: BLE001 (unreadable file: report and go on)
                print(f"{source_id}: could not read a PDF ({exc}); skipping")
                skipped += 1
                continue
            passages = chunk_blocks(source_id, blocks)
            if rated and not any(p.evidence_rating for p in passages):
                print(f"WARNING {source_id}: no evidence ratings found; treated as 'Not sure yet'")
            n = store.upsert_passages(
                conn, source_id, passages, [embedder.embed(p.text) for p in passages]
            )
            print(f"{source_id}: {n} passages from {len(files)} file(s)")
            done += 1
    print(f"processed {done} sources, skipped {skipped}")
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
    co = sub.add_parser("correct", help="fix title/year/url of a reviewed source (audited)")
    co.add_argument("source_id")
    co.add_argument("--title")
    co.add_argument("--year", type=int)
    co.add_argument("--url")
    co.add_argument("--pdf-url")
    co.add_argument("--reason", required=True)
    co.add_argument("--actor", required=True)
    co.set_defaults(fn=cmd_correct)
    pr = sub.add_parser("process")
    pr.add_argument("--embedder", choices=["stub", "titan"], default="stub")
    pr.add_argument("--all", action="store_true", help="also re-process sources that have passages")
    pr.set_defaults(fn=cmd_process)
    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
