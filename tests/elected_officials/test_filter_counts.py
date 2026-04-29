"""
Verify chamber + party totals in officials.json match PA General Assembly
shape (50 senators + 203 representatives = 253). OpenStates may report
fewer than 203 reps when there are vacancies between resignation and
special election, so we tolerate up to 5 missing House seats.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_eq, assert_in_range, load  # noqa: E402


def main() -> None:
    print("test_filter_counts.py")
    doc = load("data/elected-officials/officials.json")
    officials = doc["officials"]

    senate = sum(1 for o in officials if o["chamber"] == "Senate")
    house = sum(1 for o in officials if o["chamber"] == "House")
    parties: dict[str, int] = {}
    for o in officials:
        parties[o["party"]] = parties.get(o["party"], 0) + 1

    assert_eq(senate, 50, "Senate count")
    # House: PA has 203 seats; OpenStates may show vacancies. Tolerate ±5.
    assert_in_range(house, 198, 203, "House count (with vacancy tolerance)")
    assert_eq(senate + house, len(officials), "Senate + House sum to total")

    # Parties sanity: no third party should be larger than 2 in PA.
    for p, n in parties.items():
        if p not in ("D", "R"):
            assert_in_range(n, 0, 2, f"Party '{p}' size sanity")

    # Every official has the required schema fields.
    for o in officials:
        for key in ("id", "name", "title", "chamber", "district", "party"):
            assert_in_range(len(str(o.get(key, ""))), 1, 200, f"{o.get('id', '?')}.{key} present")


if __name__ == "__main__":
    main()
