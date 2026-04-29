"""
Spot-check term-date parity rule for known PA senators.

Rule: PA Senate seats are 4-year staggered terms. Odd-numbered districts
elect in non-presidential years (2018, 2022, 2026); even-numbered districts
elect in presidential years (2020, 2024, 2028). Terms begin the year after
election. Pre-November of an election year, the previous term is still in
force.

Known anchors as of 2026-04 (pre-November):
- SD-1 Saval (odd) → 2023-2026
- SD-7 Hughes (odd) → 2023-2026
- SD-18 Boscola (even) → 2025-2028
- SD-24 Pennycuick (even) → 2025-2028
- SD-40 Brown (even) → 2025-2028
- SD-46 Bartolotta (even) → 2025-2028

PA House: 2-year terms, all elected even years. Pre-November 2026, House
terms are 2025-2026.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_eq, assert_in_range, load  # noqa: E402


def main() -> None:
    print("test_term_dates.py")
    doc = load("data/elected-officials/officials.json")
    officials = {o["id"]: o for o in doc["officials"]}

    senate_anchors = {
        "sen-vincent-hughes": (2023, 2026),
        "sen-rosemary-brown": (2025, 2028),
        "sen-lisa-boscola": (2025, 2028),
        "sen-camera-bartolotta": (2025, 2028),
    }
    for oid, (s, e) in senate_anchors.items():
        if oid not in officials:
            print(f"  SKIP: {oid} not in roster")
            continue
        o = officials[oid]
        assert_eq(o.get("currentTermStart"), s, f"{o['name']} start")
        assert_eq(o.get("currentTermEnd"), e, f"{o['name']} end")

    # Sample non-anchor senators by district parity.
    sample_odd = [o for o in officials.values() if o["chamber"] == "Senate" and int(o["district"].split("-")[1]) % 2 == 1][:3]
    sample_even = [o for o in officials.values() if o["chamber"] == "Senate" and int(o["district"].split("-")[1]) % 2 == 0][:3]
    for o in sample_odd:
        assert_eq((o.get("currentTermStart"), o.get("currentTermEnd")), (2023, 2026), f"odd-district {o['district']} term")
    for o in sample_even:
        assert_eq((o.get("currentTermStart"), o.get("currentTermEnd")), (2025, 2028), f"even-district {o['district']} term")

    # Sample House — should all be 2025-2026 pre-Nov-2026.
    sample_house = [o for o in officials.values() if o["chamber"] == "House"][:5]
    for o in sample_house:
        assert_eq((o.get("currentTermStart"), o.get("currentTermEnd")), (2025, 2026), f"House {o['district']} term")

    # End year - start year should be 3 for Senate (4 calendar years
    # inclusive: 2025-26-27-28) or 1 for House (2 calendar years).
    for o in officials.values():
        s, e = o.get("currentTermStart"), o.get("currentTermEnd")
        if s is None or e is None:
            continue
        expected_span = 3 if o["chamber"] == "Senate" else 1
        assert_in_range(e - s, expected_span, expected_span, f"{o['id']} term span")


if __name__ == "__main__":
    main()
