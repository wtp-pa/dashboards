# Data Pipeline

Python scripts that fetch PA fiscal data from official sources, normalize it, and write JSON files into `../data/` for the frontend to consume.

## Why Python (not TypeScript)?

The work here is Excel parsing (IFO publishes XLSX), HTML scraping (OpenBookPA may not have a public API), and CSV/JSON wrangling. Python's `pandas`, `openpyxl`, and `beautifulsoup4` are the boring industry standard for this. The frontend is TypeScript; the pipeline is Python. Mixed-language repos are fine.

## Sources

| Script | Source | Schedule |
|---|---|---|
| `fetch_ifo.py` | PA Independent Fiscal Office (https://www.ifo.state.pa.us/data.cfm) | Monthly — when revenue reports drop |
| `fetch_openbookpa.py` | PA Treasury OpenBookPA (https://www.patreasury.gov/openbookpa/) | Quarterly — spending by department |
| `fetch_census.py` | U.S. Census API | Annually — PA population/households |

## Running locally

```bash
# Recommended: use a Homebrew Python 3.12 (system Python is 3.9 on this Mac)
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt

# Run any single fetcher
python pipeline/fetch_ifo.py
```

Each fetcher writes its output into `../data/*.json`. If the data hasn't changed, it should leave the file untouched (so git diffs are meaningful).

## CI

`.github/workflows/data-pipeline.yml` runs all three fetchers monthly and commits any data changes back to the repo. Updates to `data/` show up as commits — every data change is auditable in git history.

## Status

All three fetchers are currently **stubs**. They print what they would do and exit. Real implementation is Phase 1 work after the project foundation is reviewed.
