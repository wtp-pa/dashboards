#!/usr/bin/env python3
"""
Fetch PA population, household count, and county-level demographics from the U.S. Census API.

Source: https://api.census.gov/ (ACS 5-year estimates)

Output:
  data/population.json — state-level totals + county breakdown

STATUS: stub. Census API requires a free API key — set CENSUS_API_KEY env var
in GitHub Actions secrets before enabling this fetcher.
"""

import os
import sys


def main() -> int:
    api_key = os.getenv("CENSUS_API_KEY")
    if not api_key:
        print("[fetch_census] STUB — CENSUS_API_KEY not set (would skip in real run)")
    else:
        print("[fetch_census] STUB — would fetch Census data here")
    print("[fetch_census] No data written. Implementation pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
