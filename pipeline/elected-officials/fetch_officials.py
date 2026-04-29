#!/usr/bin/env python3
"""
Fetch the PA legislature roster from the OpenStates API and write to
data/elected-officials/officials.json.

Status: STUB. The current officials.json is hand-seeded with 4 PA senators
for layout testing. Wiring this script to OpenStates is the next step.

OpenStates API (free tier):
    https://docs.openstates.org/api-v3/
    Endpoint: GET https://v3.openstates.org/people?jurisdiction=pa
    Auth: header `X-API-Key: $OPENSTATES_API_KEY`
    Free tier: 500 requests/day — plenty for a daily roster refresh.

Required env var:
    OPENSTATES_API_KEY  — register at https://openstates.org/accounts/profile/

When wiring this up, this script must:
  - paginate through every PA legislator (House + Senate, ~252 records)
  - normalize each record to the schema in officials.json
  - preserve manually-curated fields (e.g., region) when re-fetching
  - update lastFetched timestamp; clear lastFetchedNote on real fetch

Run locally:
    export OPENSTATES_API_KEY=...
    python pipeline/elected-officials/fetch_officials.py

Run via GitHub Actions: stash the API key as repo secret and reference it
from .github/workflows/data-pipeline.yml.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if not os.environ.get("OPENSTATES_API_KEY"):
        print("OPENSTATES_API_KEY not set — would fail at request time.", file=sys.stderr)

    print("fetch_officials.py is a stub — officials.json is currently hand-seeded.", file=sys.stderr)
    print("See module docstring for next steps.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
