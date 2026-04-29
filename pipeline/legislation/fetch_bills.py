#!/usr/bin/env python3
"""
Fetch the most recent PA General Assembly bills and write them to
data/legislation/bills.json.

Status: STUB. The current bills.json was hand-seeded with 10 real bills
from palegis.us so the dashboard has data to render. Wiring this script up
to the live source is the next step.

Two viable sources to evaluate:
  1. https://www.palegis.us/legislation/bills — official PA listing,
     HTML scrape needed
  2. https://openstates.org/api — covers all 50 states, free tier
     (500 req/day), requires a free API key

Whichever source we pick, this script must:
  - fetch the latest N bills
  - merge with existing bills.json (preserving manual_review.json keys)
  - preserve any existing matchedPositions (overwritten by match_bills.py)
  - update the lastFetched timestamp

Run locally:
    python pipeline/legislation/fetch_bills.py

Run via GitHub Actions: see .github/workflows/data-pipeline.yml
"""

from __future__ import annotations

import sys


def main() -> int:
    print("fetch_bills.py is a stub — bills.json is currently hand-seeded.", file=sys.stderr)
    print("See module docstring for next steps.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
