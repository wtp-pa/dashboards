#!/usr/bin/env python3
"""
Fetch real PA roll-call votes from OpenStates and write to
data/elected-officials/votes.json — replacing the hand-seeded DEMO data.

Strategy:
  - Pull all PA bills with `include=votes` for the current session via the
    shared OpenStatesClient.
  - For each vote_event, look up each per-legislator vote and keep only the
    ones for officials we currently track in officials.json (matched by
    openstatesId when present, falling back to a normalized-name match).
  - Normalize OpenStates' option strings to {yea, nay, abstain, absent}.
  - Refuse to overwrite demo data with empty real data — if the run produces
    zero votes, print a warning and leave votes.json untouched. Keeps the
    DEMO banner visible until real data is actually available.

Required env: OPENSTATES_API_KEY

Run:
    python pipeline/elected-officials/fetch_votes.py

Pipeline ordering (in .github/workflows/data-pipeline.yml):
    fetch_bills.py → match_bills.py → fetch_votes.py → score_officials.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# So `python pipeline/elected-officials/fetch_votes.py` resolves the shared module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline._shared.openstates import OpenStatesClient, OpenStatesError  # noqa: E402
from pipeline._shared.names import normalize_name  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OFFICIALS_PATH = REPO_ROOT / "data" / "elected-officials" / "officials.json"
VOTES_PATH = REPO_ROOT / "data" / "elected-officials" / "votes.json"

JURISDICTION = "pa"
SESSION = "2025-2026"
MAX_PAGES = 25  # ~500 bills; same cap as fetch_bills.py for consistency

# Map OpenStates vote option strings → our canonical 4 values.
_OPTION_MAP = {
    "yes": "yea",
    "yea": "yea",
    "aye": "yea",
    "no": "nay",
    "nay": "nay",
    "abstain": "abstain",
    "present": "abstain",
    "not voting": "abstain",
    "absent": "absent",
    "excused": "absent",
}


def _normalize_id(identifier: str) -> str:
    return identifier.replace(" ", "").upper()


def _normalize_option(opt: str) -> str | None:
    return _OPTION_MAP.get((opt or "").strip().lower())


def _build_official_index(officials: list[dict]) -> dict[str, str]:
    """
    Returns a lookup that maps OpenStates voter_id (and normalized voter name)
    → our officialId. Includes both keys so name-only matches still work.
    """
    idx: dict[str, str] = {}
    for o in officials:
        oid = o["id"]
        if o.get("openstatesId"):
            idx[o["openstatesId"]] = oid
        if o.get("name"):
            idx[normalize_name(o["name"])] = oid
    return idx


def _vote_event_iter(bill: dict) -> list[dict]:
    """OpenStates calls them `votes` on the bill object."""
    return bill.get("votes") or []


def _date_only(iso: str) -> str:
    if not iso:
        return ""
    return iso.split("T", 1)[0]


def main() -> int:
    if not OFFICIALS_PATH.exists():
        print(f"officials.json missing at {OFFICIALS_PATH}", file=sys.stderr)
        return 1
    officials_doc = json.loads(OFFICIALS_PATH.read_text())
    official_idx = _build_official_index(officials_doc.get("officials", []))
    if not official_idx:
        print("No officials in officials.json — nothing to attach votes to.", file=sys.stderr)
        return 1

    try:
        client = OpenStatesClient.from_env()
    except OpenStatesError as e:
        print(str(e), file=sys.stderr)
        return 2

    collected: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()  # (billId, officialId, vote_event_id)

    for bill in client.paginate(
        "/bills",
        params={"jurisdiction": JURISDICTION, "session": SESSION, "sort": "latest_action_desc"},
        include=("votes",),
        max_pages=MAX_PAGES,
    ):
        bill_id = _normalize_id(bill.get("identifier", ""))
        if not bill_id:
            continue
        for event in _vote_event_iter(bill):
            event_id = event.get("id") or event.get("identifier") or ""
            stage = event.get("motion_text") or event.get("identifier") or ""
            event_date = _date_only(event.get("start_date") or "")
            for v in (event.get("votes") or []):
                voter_id = v.get("voter_id") or ""
                voter_name = v.get("voter_name") or ""
                official_id = official_idx.get(voter_id) or official_idx.get(normalize_name(voter_name))
                if not official_id:
                    continue
                option = _normalize_option(v.get("option") or "")
                if not option:
                    continue
                key = (bill_id, official_id, event_id)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                collected.append({
                    "billId": bill_id,
                    "officialId": official_id,
                    "vote": option,
                    "date": event_date,
                    "stage": stage,
                })

    if not collected:
        print(
            "Fetched 0 real votes — leaving votes.json untouched so the DEMO banner stays up. "
            "This is expected until OpenStates returns vote data for tracked officials.",
            file=sys.stderr,
        )
        return 0

    output = {
        "$comment": (
            "PA roll-call votes per official, fetched from OpenStates v3 API. "
            "officialId references officials.json; billId references "
            "data/legislation/bills.json. vote ∈ {yea, nay, abstain, absent}. "
            "Refreshed weekly by GitHub Actions."
        ),
        "demoData": False,
        "lastFetched": datetime.now(timezone.utc).isoformat(),
        "source": "https://openstates.org/pa/",
        "votes": collected,
    }
    VOTES_PATH.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote {len(collected)} real votes for {len({v['officialId'] for v in collected})} official(s) → {VOTES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
