"""Search ERIC and OpenAlex for K-3 Science of Reading research.

Checks that both APIs are reachable and that our corpus rules work:
  - published in the last 10 years
  - peer-reviewed (ERIC) / journal articles (OpenAlex)
  - free full text, with the license recorded so Aidan can check it

Uses only the Python standard library, so there is nothing to install.

Usage:
    python source_search.py                      # run the default test topics
    python source_search.py --topic "decodable text" --rows 20
    python source_search.py --out results.json   # also save the results

OpenAlex works best with a free API key (https://openalex.org/settings/api).
Set it as an environment variable; never commit it to the repo:
    export OPENALEX_API_KEY=your_key_here
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ERIC_URL = "https://api.ies.ed.gov/eric/"
OPENALEX_URL = "https://api.openalex.org/works"

DEFAULT_TOPICS = [
    "phonemic awareness",
    "phonics instruction",
    "decodable text",
    "letter-sound correspondence",
]

# Licenses we can store and reuse. Anything else, or missing, goes to manual review.
ALLOWED_LICENSES = {
    "cc0", "public-domain", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa",
    "cc-by-nd", "cc-by-nc-nd",
}

TIMEOUT_SECONDS = 30


def default_since_year(today: dt.date | None = None) -> int:
    """The 10-year rule: e.g. in 2026 we accept 2016 and later."""
    today = today or dt.date.today()
    return today.year - 10


# --------------------------------------------------------------------------- #
# URL builders (kept separate so tests can check them without the network)
# --------------------------------------------------------------------------- #

def build_eric_url(topic: str, since_year: int, rows: int, until_year: int | None = None) -> str:
    until_year = until_year or dt.date.today().year
    query = (
        f'"{topic}" AND peerreviewed:T AND e_fulltextauth:1 '
        f"AND publicationdateyear:[{since_year} TO {until_year}]"
    )
    params = {
        "search": query,
        "fields": "id,title,author,publicationdateyear,peerreviewed,e_fulltextauth,url,source,publicationtype",
        "rows": str(rows),
        "format": "json",
    }
    return ERIC_URL + "?" + urllib.parse.urlencode(params)


def build_openalex_url(topic: str, since_year: int, rows: int, api_key: str | None = None) -> str:
    filters = ",".join([
        "is_oa:true",
        f"from_publication_date:{since_year}-01-01",
        "type:article",
        "primary_location.source.type:journal",  # drops dissertations and repository copies
    ])
    params = {
        "search": topic,
        "filter": filters,
        "per_page": str(rows),
        "select": "id,doi,title,publication_year,authorships,open_access,best_oa_location,primary_location",
    }
    if api_key:
        params["api_key"] = api_key
    return OPENALEX_URL + "?" + urllib.parse.urlencode(params)


# --------------------------------------------------------------------------- #
# Response parsers -> one shared record shape (matches our citation schema)
# --------------------------------------------------------------------------- #

def parse_eric(payload: dict) -> tuple[int, list[dict]]:
    response = payload.get("response", {})
    records = []
    for doc in response.get("docs", []):
        eric_id = doc.get("id", "")
        records.append({
            "source_api": "eric",
            "source_id": eric_id,
            "title": doc.get("title", ""),
            "authors": doc.get("author", []),
            "year": doc.get("publicationdateyear"),
            "doi": doc.get("url") if "doi.org" in (doc.get("url") or "") else None,
            "landing_url": f"https://eric.ed.gov/?id={eric_id}",
            "pdf_url": f"https://files.eric.ed.gov/fulltext/{eric_id}.pdf" if doc.get("e_fulltextauth") == 1 else None,
            "is_open_access": doc.get("e_fulltextauth") == 1,
            "peer_reviewed": doc.get("peerreviewed") == "T",
            "license": None,  # ERIC does not report a reuse license
            "journal": doc.get("source"),
        })
    return response.get("numFound", 0), records


def parse_openalex(payload: dict) -> tuple[int, list[dict]]:
    records = []
    for work in payload.get("results", []):
        best = work.get("best_oa_location") or {}
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        records.append({
            "source_api": "openalex",
            "source_id": work.get("id", ""),
            "title": work.get("title") or "",
            "authors": [
                (a.get("author") or {}).get("display_name", "")
                for a in work.get("authorships", [])
            ],
            "year": work.get("publication_year"),
            "doi": work.get("doi"),
            "landing_url": best.get("landing_page_url") or work.get("doi"),
            "pdf_url": best.get("pdf_url"),
            "is_open_access": (work.get("open_access") or {}).get("is_oa", False),
            "peer_reviewed": None,  # OpenAlex does not report peer review
            "license": best.get("license"),
            "journal": source.get("display_name"),
        })
    return payload.get("meta", {}).get("count", 0), records


# --------------------------------------------------------------------------- #
# Corpus rules
# --------------------------------------------------------------------------- #

def check_record(record: dict, since_year: int) -> dict:
    """Add a 'status' and the reasons for it. Nothing is auto-approved:
    'candidate' still goes to the Notion Sources review queue."""
    problems = []
    if not record.get("year") or record["year"] < since_year:
        problems.append(f"older than {since_year}")
    if not record.get("is_open_access"):
        problems.append("not open access")
    if record.get("peer_reviewed") is False:
        problems.append("not peer-reviewed")

    license_ = record.get("license")
    if license_ is None:
        license_status = "unknown - needs license check"
    elif license_ in ALLOWED_LICENSES:
        license_status = "ok"
    else:
        license_status = f"not allowed ({license_})"
        problems.append(f"license {license_}")

    record = dict(record)
    record["license_status"] = license_status
    record["problems"] = problems
    record["status"] = "rejected" if problems else "candidate"
    return record


# --------------------------------------------------------------------------- #
# Network
# --------------------------------------------------------------------------- #

def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "SoR-Assistant-source-check/0.1"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def search(topic: str, since_year: int, rows: int, api_key: str | None) -> dict:
    result = {"topic": topic, "eric": {}, "openalex": {}}
    for name, url, parser in [
        ("eric", build_eric_url(topic, since_year, rows), parse_eric),
        ("openalex", build_openalex_url(topic, since_year, rows, api_key), parse_openalex),
    ]:
        try:
            total, records = parser(fetch_json(url))
            result[name] = {
                "ok": True,
                "total_found": total,
                "records": [check_record(r, since_year) for r in records],
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            result[name] = {"ok": False, "error": str(exc), "records": []}
    return result


def print_summary(results: list[dict]) -> None:
    for res in results:
        print(f'\n=== "{res["topic"]}" ===')
        for api in ("eric", "openalex"):
            r = res[api]
            if not r["ok"]:
                print(f"  {api:9} FAILED: {r['error']}")
                continue
            candidates = sum(1 for rec in r["records"] if rec["status"] == "candidate")
            unknown_license = sum(1 for rec in r["records"] if rec["license"] is None)
            print(f"  {api:9} found {r['total_found']:>6}  | showing {len(r['records'])}"
                  f"  | candidates {candidates}  | license unknown {unknown_license}")
            for rec in r["records"][:3]:
                print(f"     - [{rec['year']}] {rec['title'][:80]}  ({rec['status']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", action="append", help="search topic (repeatable); default: 4 test topics")
    parser.add_argument("--rows", type=int, default=10, help="results per API per topic (default 10)")
    parser.add_argument("--since", type=int, default=default_since_year(), help="earliest year (default: 10 years ago)")
    parser.add_argument("--out", help="save full results to this JSON file")
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENALEX_API_KEY")
    if not api_key:
        print("Note: OPENALEX_API_KEY is not set. OpenAlex will use a small shared daily budget.\n"
              "      Get a free key at https://openalex.org/settings/api", file=sys.stderr)

    results = [search(t, args.since, args.rows, api_key) for t in (args.topic or DEFAULT_TOPICS)]
    print_summary(results)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"since_year": args.since, "results": results}, f, indent=2, ensure_ascii=False)
        print(f"\nSaved full results to {args.out}")

    all_ok = all(r[api]["ok"] for r in results for api in ("eric", "openalex"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
