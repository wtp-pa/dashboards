#!/usr/bin/env python3
"""
Fetch PA roll-call votes from the OpenStates API and write to
data/elected-officials/votes.json.

Status: STUB. votes.json is currently hand-seeded with DEMO data for layout
testing — the dashboard surfaces a visible DEMO banner until demoData is
flipped to false here.

OpenStates API (free tier):
    https://docs.openstates.org/api-v3/
    Bills: GET /bills?jurisdiction=pa&include=votes
    Each vote object has voter_id (mappable to officials.json[].openstatesId),
    option (yes / no / not voting / absent — normalize to yea/nay/abstain/absent),
    and a vote_event with chamber and stage.

Required env var:
    OPENSTATES_API_KEY  — register at https://openstates.org/accounts/profile/

When wiring this up, this script must:
  - iterate the bill IDs already in data/legislation/bills.json
  - request roll-call data for each (or batch via the bills-with-votes endpoint)
  - normalize OpenStates vote options to {yea, nay, abstain, absent}
  - merge with existing votes.json without duplicating
  - flip demoData to false
  - update lastFetched timestamp

Run locally:
    export OPENSTATES_API_KEY=...
    python pipeline/elected-officials/fetch_votes.py

Run via GitHub Actions: stash the API key as repo secret and reference it
from .github/workflows/data-pipeline.yml.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if not os.environ.get("OPENSTATES_API_KEY"):
        print("OPENSTATES_API_KEY not set — would fail at request time.", file=sys.stderr)

    print("fetch_votes.py is a stub — votes.json is currently DEMO seed data.", file=sys.stderr)
    print("See module docstring for next steps.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
