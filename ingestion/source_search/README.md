# source_search

Checks that we can pull K-3 Science of Reading research from **ERIC** and **OpenAlex** with our corpus rules applied:

- published in the last 10 years
- peer-reviewed (ERIC) or a journal article (OpenAlex)
- free full text, with the license recorded

Every result is marked `candidate` or `rejected`. **Nothing is auto-approved.** Candidates still go to the Notion Sources review queue, and anything with `license_status: unknown` goes to Aidan's license check.

## Run it

Python 3.9+ only. The script uses the standard library, so there's nothing to install.

```bash
# optional but recommended: free key from https://openalex.org/settings/api
export OPENALEX_API_KEY=your_key_here      # Windows PowerShell: $env:OPENALEX_API_KEY="your_key_here"

python source_search.py                              # 4 default test topics
python source_search.py --topic "decodable text" --rows 20
python source_search.py --out results.json           # save every record as JSON
```

The exit code is `0` if both APIs answered and `1` if either failed.

## Output record (same shape for both APIs)

| field | meaning |
|---|---|
| `source_api` | `eric` or `openalex` |
| `source_id` | ERIC ID (e.g. `EJ1291358`) or OpenAlex work URL |
| `title`, `authors`, `year`, `journal` | citation details |
| `doi`, `landing_url`, `pdf_url` | where to get the paper |
| `is_open_access`, `peer_reviewed` | `peer_reviewed` is `null` for OpenAlex (it doesn't report it) |
| `license`, `license_status` | ERIC never reports a license, so its results always need a manual check |
| `status`, `problems` | `candidate` or `rejected`, and why |

## Tests

```bash
pip install pytest
python -m pytest
```

The tests use saved API responses in `tests/fixtures/`, so CI never calls the real APIs.

## Known limits (found while testing, Oct 26)

- **OpenAlex without a key** shares a $0.10/day budget with everyone on your network. Get a free key, and never commit it.
- **OpenAlex `license` is often empty**, even for real journal articles, so most results need a manual license check.
- **Off-target results still appear**, such as studies of EFL learners outside the US. Human review catches these.
