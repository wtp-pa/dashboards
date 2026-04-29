#!/usr/bin/env python3
"""
Refresh the PA legislator records in data/elected-officials/officials.json
with current OpenStates data — primarily to populate `openstatesId` so
fetch_votes.py can match votes by ID rather than relying on name fuzzing.

Scope: this script only updates officials that already exist in
officials.json. It does NOT expand the roster from 4 senators to all 252
PA legislators. The roster grows when an editor adds a record by hand
(with hand-curated counties/region) and re-runs this script to fill in
the OpenStates-derived fields.

Updated fields:
  - openstatesId   (OpenStates person ID)
  - photoUrl       (people[].image)
  - currentTermStart / currentTermEnd  (current_role.start_date/end_date when present)

Preserved fields (never overwritten):
  - id, name, title, chamber, district, party, counties, region,
    firstElectedYear  ← hand-curated from public records, OpenStates
    doesn't expose first-elected reliably

Required env: OPENSTATES_API_KEY
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline._shared.openstates import OpenStatesClient, OpenStatesError  # noqa: E402
from pipeline._shared.names import normalize_name  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OFFICIALS_PATH = REPO_ROOT / "data" / "elected-officials" / "officials.json"

JURISDICTION = "pa"


def _year_of(iso: str | None) -> int | None:
    if not iso:
        return None
    m = re.match(r"(\d{4})", iso)
    return int(m.group(1)) if m else None


def main() -> int:
    if not OFFICIALS_PATH.exists():
        print(f"officials.json missing at {OFFICIALS_PATH}", file=sys.stderr)
        return 1

    doc = json.loads(OFFICIALS_PATH.read_text())
    officials = doc.get("officials", [])
    if not officials:
        print("No officials in officials.json — nothing to refresh.", file=sys.stderr)
        return 1

    try:
        client = OpenStatesClient.from_env()
    except OpenStatesError as e:
        print(str(e), file=sys.stderr)
        return 2

    # Fetch the full PA roster once. /people is small enough (~252 records)
    # that paginating through it on every run is fine.
    name_index: dict[str, dict] = {}
    id_index: dict[str, dict] = {}
    for person in client.paginate("/people", params={"jurisdiction": JURISDICTION}):
        if not isinstance(person, dict):
            continue
        norm = normalize_name(person.get("name") or "")
        if norm:
            name_index[norm] = person
        if person.get("id"):
            id_index[person["id"]] = person

    updated = 0
    skipped: list[str] = []
    for o in officials:
        match = None
        if o.get("openstatesId") and o["openstatesId"] in id_index:
            match = id_index[o["openstatesId"]]
        if not match:
            match = name_index.get(normalize_name(o.get("name") or ""))
        if not match:
            skipped.append(o.get("name") or o.get("id") or "<unknown>")
            continue

        current_role = match.get("current_role") or {}
        # Update only the OpenStates-derived fields. Don't touch counties /
        # region / firstElectedYear / id — those are editor-curated.
        o["openstatesId"] = match.get("id") or o.get("openstatesId")
        if match.get("image"):
            o["photoUrl"] = match["image"]

        start = _year_of(current_role.get("start_date"))
        end = _year_of(current_role.get("end_date"))
        if start is not None:
            o["currentTermStart"] = start
        if end is not None:
            o["currentTermEnd"] = end

        updated += 1

    doc["lastFetched"] = datetime.now(timezone.utc).isoformat()
    doc.pop("lastFetchedNote", None)
    doc["officials"] = officials
    OFFICIALS_PATH.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"Updated {updated} of {len(officials)} officials from OpenStates.")
    if skipped:
        print(f"  No OpenStates match for: {', '.join(skipped)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
