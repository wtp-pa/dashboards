#!/usr/bin/env python3
"""
Tag each PA bill in data/legislation/bills.json with WTP-PA platform position
matches, by substring-matching keywords from data/legislation/platform.json
against each bill's title + summary.

This is intentionally NOT an LLM-based scorer — alignment calls are made by a
human editor in data/legislation/manual_review.json. This script only computes
which platform topics each bill *touches*, so the dashboard can show the
relevant context in the drill-down.

Run locally:
    python pipeline/legislation/match_bills.py

Run via GitHub Actions: see .github/workflows/data-pipeline.yml
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "legislation"
BILLS_PATH = DATA_DIR / "bills.json"
PLATFORM_PATH = DATA_DIR / "platform.json"


@lru_cache(maxsize=None)
def keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Word-boundary regex for a keyword phrase, case-insensitive.

    Uses \\b on each end so 'PAC' won't match 'impact' and 'cte' won't match
    'convicted'. Internal whitespace allows one or more whitespace characters
    so 'school choice' matches 'school   choice' or 'school\\nchoice'.
    """
    parts = [re.escape(p) for p in keyword.lower().split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b", re.IGNORECASE)


def positions_matching(text: str, platform: dict) -> list[str]:
    """Return position IDs whose keywords appear (word-boundary, case-insensitive) in text."""
    matched: list[str] = []
    for pillar in platform["pillars"]:
        for position in pillar["positions"]:
            for keyword in position["keywords"]:
                if keyword_pattern(keyword).search(text):
                    matched.append(position["id"])
                    break
    return matched


def main() -> int:
    if not BILLS_PATH.exists() or not PLATFORM_PATH.exists():
        print(f"Missing input file. Need {BILLS_PATH} and {PLATFORM_PATH}", file=sys.stderr)
        return 1

    bills_doc = json.loads(BILLS_PATH.read_text())
    platform = json.loads(PLATFORM_PATH.read_text())

    changed = 0
    for bill in bills_doc["bills"]:
        haystack = " ".join([bill.get("title", ""), bill.get("summary", "")])
        new_matches = positions_matching(haystack, platform)
        if new_matches != bill.get("matchedPositions"):
            bill["matchedPositions"] = new_matches
            changed += 1

    bills_doc["lastMatched"] = datetime.now(timezone.utc).isoformat()
    BILLS_PATH.write_text(json.dumps(bills_doc, indent=2) + "\n")

    total = len(bills_doc["bills"])
    print(f"Matched {total} bills against platform ({changed} updated). Wrote {BILLS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
