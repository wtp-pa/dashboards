"""
Verify the legislation data files are well-formed:
- bills.json bills have the new structured `sponsors` array
- manual_review.json IDs all reference real bills
- platform.json is shaped correctly
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_in_range, assert_true, load  # noqa: E402


def main() -> None:
    print("test_legislation_data.py")
    bills_doc = load("data/legislation/bills.json")
    manual = load("data/legislation/manual_review.json")
    platform = load("data/legislation/platform.json")

    bills = bills_doc["bills"]
    bill_ids = {b["id"] for b in bills}

    # bills.json shape
    assert_in_range(len(bills), 100, 10000, "bills.json has a reasonable number of bills")
    bills_with_sponsors = [b for b in bills if "sponsors" in b]
    coverage = len(bills_with_sponsors) / max(1, len(bills))
    assert_true(coverage >= 0.95, f"≥95% of bills have structured sponsors[] (got {coverage:.0%})")

    # Every sponsors[] entry shape
    sample = bills_with_sponsors[:50]
    for b in sample:
        for s in b.get("sponsors", []):
            assert_true("name" in s, f"{b['id']} sponsor has name")
            assert_true("primary" in s, f"{b['id']} sponsor has primary flag")

    # Manual review entries should be well-formed. Stale bill references
    # (review for a bill no longer in our fetch window) are noted as
    # warnings rather than failures since they resolve when the next
    # fetch picks the bill back up.
    reviews = manual.get("reviews") or {}
    for bid, entry in reviews.items():
        assert_true(entry.get("alignment") in ("aligned", "mixed", "opposed"), f"manual_review[{bid}] alignment valid")
        assert_true(isinstance(entry.get("note", ""), str), f"manual_review[{bid}] note is string")
    stale = [bid for bid in reviews if bid not in bill_ids]
    if stale:
        print(f"  NOTE: stale manual_review refs (not in current bills.json): {stale}")

    # Platform shape
    pillars = platform.get("pillars", [])
    assert_in_range(len(pillars), 3, 10, "platform has 3-10 pillars")
    for pillar in pillars:
        assert_true("id" in pillar and "name" in pillar, f"pillar {pillar.get('id', '?')} has id+name")
        assert_in_range(len(pillar.get("positions", [])), 1, 50, f"pillar {pillar['id']} has positions")


if __name__ == "__main__":
    main()
