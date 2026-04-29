#!/usr/bin/env python3
"""
Compute per-official platform alignment scorecards.

Inputs:
  - data/elected-officials/votes.json     — roll-call votes (officialId × billId)
  - data/elected-officials/officials.json — roster
  - data/legislation/bills.json           — bills + matches + autoAlignment
  - data/legislation/manual_review.json   — editor's alignment overrides
  - data/legislation/platform.json        — pillars, for byPillar grouping

This is a JOIN, not a re-match. We never re-evaluate keyword matches here;
we trust whatever the legislation pipeline (match_bills.py) wrote into
bills.json. That single source of truth keeps /legislation and
/elected-officials from disagreeing about a bill.

Alignment resolution mirrors src/lib/bills.ts `resolveAlignment` priority:
  1. manual review (highest authority)
  2. autoAlignment with confidence ≥ AUTO_ALIGNMENT_THRESHOLD
  3. "topic-only" if any platform plank matched
  4. "under-review" otherwise

Vote scoring:
    bill = aligned + vote = yea  →  withPlatform
    bill = aligned + vote = nay  →  againstPlatform
    bill = opposed + vote = nay  →  withPlatform
    bill = opposed + vote = yea  →  againstPlatform
    bill = mixed                  →  noted (shown for transparency, not scored)
    bill = topic-only             →  noted
    bill = under-review           →  noted
    vote ∈ {abstain, absent}      →  noted

Output: data/elected-officials/scorecards.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EO_DIR = DATA_DIR / "elected-officials"
LEG_DIR = DATA_DIR / "legislation"

OFFICIALS_PATH = EO_DIR / "officials.json"
VOTES_PATH = EO_DIR / "votes.json"
SCORECARDS_PATH = EO_DIR / "scorecards.json"
BILLS_PATH = LEG_DIR / "bills.json"
MANUAL_REVIEW_PATH = LEG_DIR / "manual_review.json"
PLATFORM_PATH = LEG_DIR / "platform.json"

# Mirror src/lib/bills.ts AUTO_ALIGNMENT_THRESHOLD. Keep in sync.
AUTO_ALIGNMENT_THRESHOLD = 0.65

WITH_PLATFORM_RULES = {
    ("aligned", "yea"): "with",
    ("aligned", "nay"): "against",
    ("opposed", "yea"): "against",
    ("opposed", "nay"): "with",
}

OUTPUT_COMMENT = (
    "Computed by pipeline/elected-officials/score_officials.py as a JOIN of "
    "data/elected-officials/votes.json against data/legislation/bills.json + "
    "manual_review.json. Refreshed by GitHub Actions whenever votes or bills "
    "change. Do not hand-edit — your changes will be overwritten on the next "
    "pipeline run."
)


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"Missing input file: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def resolve_alignment(bill: dict, review: dict | None) -> str:
    """Mirror of resolveAlignment() in src/lib/bills.ts."""
    if review:
        return review["alignment"]
    auto = bill.get("autoAlignment")
    conf = bill.get("autoConfidence")
    if (
        auto in ("likely-aligned", "likely-opposed")
        and isinstance(conf, (int, float))
        and conf >= AUTO_ALIGNMENT_THRESHOLD
    ):
        return "aligned" if auto == "likely-aligned" else "opposed"
    if bill.get("matches"):
        return "topic-only"
    return "under-review"


def main() -> int:
    officials_doc = load_json(OFFICIALS_PATH)
    votes_doc = load_json(VOTES_PATH)
    bills_doc = load_json(BILLS_PATH)
    manual_review_doc = load_json(MANUAL_REVIEW_PATH)
    platform_doc = load_json(PLATFORM_PATH)

    bills_by_id = {b["id"]: b for b in bills_doc["bills"]}
    reviews = manual_review_doc.get("reviews", {})
    pillar_by_position = {
        position["id"]: pillar["id"]
        for pillar in platform_doc["pillars"]
        for position in pillar["positions"]
    }
    pillar_names = {pillar["id"]: pillar["name"] for pillar in platform_doc["pillars"]}

    votes_by_official: dict[str, list[dict]] = defaultdict(list)
    for vote in votes_doc["votes"]:
        votes_by_official[vote["officialId"]].append(vote)

    scorecards = []
    for official in officials_doc["officials"]:
        official_id = official["id"]
        votes = votes_by_official.get(official_id, [])

        with_count = 0
        against_count = 0
        noted_count = 0  # vote on a bill that touches us but can't be scored
        by_pillar: dict[str, dict[str, int]] = defaultdict(lambda: {"with": 0, "against": 0})
        key_votes: list[dict] = []

        for vote in votes:
            bill = bills_by_id.get(vote["billId"])
            if bill is None:
                # Vote on a bill outside the current legislation tracking
                # window — skip silently, don't penalize the legislator.
                continue

            review = reviews.get(vote["billId"])
            alignment = resolve_alignment(bill, review)
            direction = WITH_PLATFORM_RULES.get((alignment, vote["vote"]))

            if direction is None:
                noted_count += 1
                key_votes.append({
                    "billId": vote["billId"],
                    "billTitle": bill["title"],
                    "vote": vote["vote"],
                    "billAlignment": alignment,
                    "directionRelativeToPlatform": "noted",
                    "date": vote["date"],
                    "stage": vote.get("stage", ""),
                    "matchedPositions": [m["positionId"] for m in bill.get("matches", [])],
                })
                continue

            if direction == "with":
                with_count += 1
            else:
                against_count += 1

            for match in bill.get("matches", []):
                pillar_id = pillar_by_position.get(match["positionId"])
                if pillar_id:
                    by_pillar[pillar_id][direction] += 1

            key_votes.append({
                "billId": vote["billId"],
                "billTitle": bill["title"],
                "vote": vote["vote"],
                "billAlignment": alignment,
                "directionRelativeToPlatform": direction,
                "date": vote["date"],
                "stage": vote.get("stage", ""),
                "matchedPositions": [m["positionId"] for m in bill.get("matches", [])],
            })

        scorable = with_count + against_count
        alignment_rate = round(with_count / scorable, 3) if scorable else None

        scorecards.append({
            "officialId": official_id,
            "totalVotes": len(votes),
            "scorableVotes": scorable,
            "withPlatform": with_count,
            "againstPlatform": against_count,
            "noted": noted_count,
            "alignmentRate": alignment_rate,
            "byPillar": [
                {
                    "pillarId": pid,
                    "pillarName": pillar_names.get(pid, pid),
                    "withPlatform": counts["with"],
                    "againstPlatform": counts["against"],
                }
                for pid, counts in sorted(by_pillar.items())
            ],
            "keyVotes": sorted(key_votes, key=lambda v: v["date"], reverse=True),
        })

    output = {
        "$comment": OUTPUT_COMMENT,
        "lastComputed": datetime.now(timezone.utc).isoformat(),
        "scorecards": scorecards,
    }
    SCORECARDS_PATH.write_text(json.dumps(output, indent=2) + "\n")

    rated = sum(1 for s in scorecards if s["alignmentRate"] is not None)
    print(
        f"Computed scorecards for {len(scorecards)} officials "
        f"({rated} with at least one scorable vote). Wrote {SCORECARDS_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
