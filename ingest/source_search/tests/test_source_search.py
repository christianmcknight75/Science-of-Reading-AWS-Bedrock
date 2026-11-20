"""Offline tests: they use saved API responses, so CI never calls ERIC or OpenAlex."""
import datetime as dt
import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import source_search as ss  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_ten_year_rule():
    assert ss.default_since_year(dt.date(2026, 10, 26)) == 2016


def test_eric_url_has_all_filters():
    url = urllib.parse.unquote_plus(ss.build_eric_url("phonics", 2016, 5, until_year=2026))
    assert '"phonics"' in url
    assert "peerreviewed:T" in url
    assert "e_fulltextauth:1" in url
    assert "publicationdateyear:[2016 TO 2026]" in url
    assert "format=json" in url


def test_openalex_url_filters_and_key():
    url = urllib.parse.unquote(ss.build_openalex_url("phonics", 2016, 5, api_key="KEY"))
    for f in ["is_oa:true", "from_publication_date:2016-01-01", "type:article",
              "primary_location.source.type:journal"]:
        assert f in url
    assert "api_key=KEY" in url
    assert "api_key" not in ss.build_openalex_url("phonics", 2016, 5)


def test_parse_eric():
    total, records = ss.parse_eric(load("eric_sample.json"))
    assert total == 100
    assert records[0]["source_id"] == "EJ1291358"
    assert records[0]["pdf_url"] == "https://files.eric.ed.gov/fulltext/EJ1291358.pdf"
    assert records[1]["doi"].startswith("https://doi.org/")
    assert records[0]["license"] is None


def test_parse_openalex():
    total, records = ss.parse_openalex(load("openalex_sample.json"))
    assert total == 11366
    assert records[0]["license"] == "cc-by"
    assert records[0]["authors"] == ["A. Author"]
    assert records[2]["journal"] is None  # missing source must not crash


def test_rules_eric():
    _, records = ss.parse_eric(load("eric_sample.json"))
    checked = [ss.check_record(r, 2016) for r in records]
    assert checked[0]["status"] == "candidate"
    assert checked[0]["license_status"].startswith("unknown")
    assert checked[2]["status"] == "rejected"
    assert "older than 2016" in checked[2]["problems"]


def test_rules_openalex_license():
    _, records = ss.parse_openalex(load("openalex_sample.json"))
    checked = [ss.check_record(r, 2016) for r in records]
    assert checked[0]["license_status"] == "ok" and checked[0]["status"] == "candidate"
    assert checked[1]["license_status"].startswith("unknown")
    assert checked[2]["status"] == "rejected"


def test_main_reports_failure_without_network(monkeypatch, capsys):
    def boom(url):
        raise ss.urllib.error.URLError("no network")
    monkeypatch.setattr(ss, "fetch_json", boom)
    assert ss.main(["--topic", "phonics", "--rows", "1"]) == 1
    assert "FAILED" in capsys.readouterr().out


def test_main_success_with_fixtures(monkeypatch, tmp_path):
    def fake(url):
        return load("eric_sample.json") if "ies.ed.gov" in url else load("openalex_sample.json")
    monkeypatch.setattr(ss, "fetch_json", fake)
    out = tmp_path / "r.json"
    assert ss.main(["--topic", "phonics", "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["results"][0]["eric"]["total_found"] == 100
