#!/usr/bin/env python3
"""
Compute per-official platform alignment scorecards from:
  - data/elected-officials/votes.json     — roll-call votes (officialId × billId)
  - data/elected-officials/officials.json — roster
  - data/legislation/bills.json           — bills with matchedPositions
  - data/legislation/manual_review.json   — editor's alignment call per bill
  - data/legislation/platform.json        — pillars, for byPillar grouping

A vote counts toward platform alignment as follows:
    bill alignment = aligned + vote = yea  →  withPlatform
    bill alignment = aligned + vote = nay  →  againstPlatform
    bill alignment = opposed + vote = nay  →  withPlatform
    bill alignment = opposed + vote = yea  →  againstPlatform
    bill alignment = mixed                 →  unscorable
    bill alignment = under-review          →  unscorable
    vote in {abstain, absent}              →  unscorable

Output: data/elected-officials/scorecards.json (overwritten in place).

Run locally:
    python pipeline/elected-officials/score_officials.py

Run via GitHub Actions: see .github/workflows/data-pipeline.yml (eventually).
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

WITH_PLATFORM_RULES = {
    ("aligned", "yea"): "with",
    ("aligned", "nay"): "against",
    ("opposed", "yea"): "against",
    ("opposed", "nay"): "with",
}


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"Missing input file: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def main() -> int:
    officials_doc = load_json(OFFICIALS_PATH)
    votes_doc = load_json(VOTES_PATH)
    bills_doc = load_json(BILLS_PATH)
    manual_review_doc = load_json(MANUAL_REVIEW_PATH)
    platform_doc = load_json(PLATFORM_PATH)

    bills_by_id = {b["id"]: b for b in bills_doc["bills"]}
    reviews = manual_review_doc["reviews"]
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
        unscorable_count = 0
        by_pillar: dict[str, dict[str, int]] = defaultdict(lambda: {"with": 0, "against": 0})
        key_votes: list[dict] = []

        for vote in votes:
            bill = bills_by_id.get(vote["billId"])
            if bill is None:
                unscorable_count += 1
                continue

            review = reviews.get(vote["billId"])
            alignment = review["alignment"] if review else "under-review"
            direction = WITH_PLATFORM_RULES.get((alignment, vote["vote"]))

            if direction is None:
                unscorable_count += 1
                continue

            if direction == "with":
                with_count += 1
            else:
                against_count += 1

            for position_id in bill.get("matchedPositions", []):
                pillar_id = pillar_by_position.get(position_id)
                if pillar_id:
                    by_pillar[pillar_id][direction] += 1

            key_votes.append({
                "billId": vote["billId"],
                "billTitle": bill["title"],
                "vote": vote["vote"],
                "billAlignment": alignment,
                "directionRelativeToPlatform": direction,
                "date": vote["date"],
                "matchedPositions": bill.get("matchedPositions", []),
            })

        scorable = with_count + against_count
        alignment_rate = round(with_count / scorable, 3) if scorable else None

        scorecards.append({
            "officialId": official_id,
            "totalVotes": len(votes),
            "scorableVotes": scorable,
            "withPlatform": with_count,
            "againstPlatform": against_count,
            "unscorable": unscorable_count,
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
        "$comment": SCORECARDS_PATH.read_text().split('"$comment":', 1)[1].split('"', 2)[1] if SCORECARDS_PATH.exists() else "",
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
