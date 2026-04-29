# Data accuracy tests

Plain-Python tests that verify the WTPPPA dashboards data files and pipeline
outputs are sane. Designed to run on bare `python3` with stdlib only — no
pytest, no virtualenv setup. Each test exits non-zero on failure so they
plug into CI directly.

## Run all

```bash
python3 tests/run.py
```

Exits 0 if everything passes, 1 otherwise.

## Two tiers

**Data tests** (`tests/elected_officials/test_*.py`) — read JSON files from
`data/`. No network. Fast. Run on every Pages deploy.

**API integration tests** (`tests/elected_officials/integration_*.py`) —
hit OpenStates and the Census/Nominatim geocoders. Need
`OPENSTATES_API_KEY`. Slow (rate-limited). Run on the weekly cron after a
fresh data fetch.

## What's covered

| File | What it checks |
|---|---|
| `test_filter_counts.py` | Chamber/party totals match the PA General Assembly's 50 senators / 203 reps shape (within the OpenStates vacancy tolerance) |
| `test_term_dates.py` | The PA-cycle parity rule produced sane currentTermStart/End for known senators and a sample of others |
| `test_scorecards_consistency.py` | Every scorecard ID exists in officials.json; every keyVote.billId exists in bills.json; sponsorship counts are non-negative |
| `test_legislation_data.py` | bills.json has the new `sponsors` array on every entry; manual_review.json IDs all exist in bills.json |
| `integration_address_lookup.py` | A handful of canonical PA addresses resolve through the geocoder + OpenStates and return PA state reps that exist in our roster |
| `integration_county_coverage.py` | Multi-point county sampling for Philadelphia returns at least 25 unique state reps |
