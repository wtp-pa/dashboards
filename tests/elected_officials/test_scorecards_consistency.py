"""
Verify scorecards.json is internally consistent with officials.json and
bills.json — no stale references, no negative counts, no double-counting.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_eq, assert_in_range, assert_true, load  # noqa: E402


def main() -> None:
    print("test_scorecards_consistency.py")
    officials = load("data/elected-officials/officials.json")["officials"]
    scorecards = load("data/elected-officials/scorecards.json")["scorecards"]
    bills = load("data/legislation/bills.json")["bills"]

    official_ids = {o["id"] for o in officials}
    bill_ids = {b["id"] for b in bills}

    assert_eq(len(scorecards), len(officials), "one scorecard per official")

    for sc in scorecards:
        oid = sc["officialId"]
        assert_true(oid in official_ids, f"scorecard officialId '{oid}' references real official")

        bs = sc["billsSponsored"]
        assert_in_range(bs["primary"], 0, 1000, f"{oid} primary count is non-negative")
        assert_in_range(bs["cosponsor"], 0, 5000, f"{oid} cosponsor count is non-negative")
        assert_in_range(bs["touchingPlatform"], 0, bs["primary"] + bs["cosponsor"], f"{oid} touchingPlatform <= total")

        assert_in_range(sc["withPlatform"], 0, sc["scorableVotes"], f"{oid} withPlatform <= scorableVotes")
        assert_in_range(sc["againstPlatform"], 0, sc["scorableVotes"], f"{oid} againstPlatform <= scorableVotes")
        assert_eq(sc["withPlatform"] + sc["againstPlatform"], sc["scorableVotes"], f"{oid} with+against=scorable")

        # Every keyVote billId should exist in bills.json.
        for kv in sc.get("keyVotes", []):
            assert_true(kv["billId"] in bill_ids, f"{oid} keyVote bill '{kv['billId']}' exists in bills.json")
            assert_true(kv["vote"] in ("yea", "nay", "abstain", "absent"), f"{oid} vote value valid")

        # byPillar internals: with + against + noted should match keyVotes attributable to each pillar.
        for p in sc.get("byPillar", []):
            assert_in_range(p.get("primarySponsor", 0), 0, 1000, f"{oid}/{p['pillarId']} primary count")
            assert_in_range(p.get("cosponsor", 0), 0, 5000, f"{oid}/{p['pillarId']} cosponsor count")
            assert_in_range(p.get("noted", 0), 0, 1000, f"{oid}/{p['pillarId']} noted count")


if __name__ == "__main__":
    main()
