#!/usr/bin/env python3
"""
Fetch federal award totals for every Pennsylvania county from USAspending.gov.

Source: https://api.usaspending.gov/api/v2/search/spending_by_geography/

Output: data/federal-funds-by-county.json — all 67 PA counties with FIPS,
        total obligations for the most recent complete federal fiscal year,
        population, and per-capita figure (all from USAspending directly).

Notes:
- USAspending's "place_of_performance" + county geo_layer returns federal
  obligations occurring in the county, including contracts, grants, direct
  payments, loans, and insurance. It is NOT the same as "federal aid" — big
  contractors (UPMC research, DOD/DOE labs) inflate metro-county totals.
  The /budget/about page methodology entry has to label this honestly.
- Federal FY runs Oct 1 -> Sep 30. We use the most recent complete FY.
- This script is part of the weekly data-pipeline.yml cron.

Run locally:
    python pipeline/fetch_usaspending_counties.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_geography/"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "federal-funds-by-county.json"
USER_AGENT = "wtp-dashboards/0.1 (+https://github.com/wtp-pa/dashboards)"
REQUEST_TIMEOUT = 60


def latest_complete_federal_fy(now: datetime) -> int:
    """Federal FY YYYY runs Oct 1 (YYYY-1) through Sep 30 (YYYY).
    The most recent *complete* FY is the one whose Sep 30 has passed."""
    if now.month >= 10:
        return now.year
    return now.year - 1


def fetch_pa_counties(fy: int) -> list[dict]:
    start = f"{fy - 1}-10-01"
    end = f"{fy}-09-30"
    payload = {
        "scope": "place_of_performance",
        "geo_layer": "county",
        "filters": {
            "time_period": [{"start_date": start, "end_date": end}],
            "place_of_performance_locations": [{"country": "USA", "state": "PA"}],
        },
    }
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def normalize(results: list[dict]) -> list[dict]:
    counties = []
    for r in results:
        counties.append(
            {
                "fips": r["shape_code"],
                "name": r["display_name"],
                "totalObligationsUSD": round(r["aggregated_amount"]),
                "population": r["population"],
                "perCapitaUSD": round(r["per_capita"], 2),
            }
        )
    counties.sort(key=lambda c: c["name"])
    return counties


def main() -> int:
    now = datetime.now(timezone.utc)
    fy = latest_complete_federal_fy(now)
    print(f"Fetching USAspending PA counties for federal FY {fy}...", file=sys.stderr)

    results = fetch_pa_counties(fy)
    if len(results) < 60:
        print(
            f"WARN: expected ~67 PA counties, got {len(results)}; aborting",
            file=sys.stderr,
        )
        return 1

    counties = normalize(results)
    total_usd = sum(c["totalObligationsUSD"] for c in counties)

    doc = {
        "schemaVersion": 1,
        "lastUpdated": now.date().isoformat(),
        "fiscalYear": f"FY {fy} (federal)",
        "fiscalYearStart": f"{fy - 1}-10-01",
        "fiscalYearEnd": f"{fy}-09-30",
        "totalObligationsUSD": total_usd,
        "countyCount": len(counties),
        "source": {
            "primary": "USAspending.gov",
            "url": "https://www.usaspending.gov/state/pennsylvania",
            "apiEndpoint": API_URL,
            "notes": (
                "Federal obligations by county (place of performance). Includes "
                "contracts, grants, direct payments, loans, and insurance. Not "
                "limited to 'aid' — large contractors and federal research "
                "grants inflate metro-county totals."
            ),
        },
        "counties": counties,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(
        f"Wrote {len(counties)} counties, total ${total_usd / 1e9:.1f}B "
        f"to {OUTPUT_PATH.relative_to(Path.cwd())}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
