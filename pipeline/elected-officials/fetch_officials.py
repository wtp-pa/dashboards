#!/usr/bin/env python3
"""
Refresh and expand the PA legislator records in
data/elected-officials/officials.json against current OpenStates data.

What it does:
  - Refreshes OpenStates-derived fields on existing entries
    (openstatesId, photoUrl, currentTermStart/End).
  - Adds new entries for every PA legislator returned from /people that
    isn't already in the file. The full roster is ~253 (50 senators +
    203 representatives), so the file grows to that size after a fresh
    run.

Editor-curated fields are NEVER overwritten on existing entries:
  - id (slug), counties, region, currentTermStart/End if OpenStates
    doesn't supply them.

For new entries, counties[] starts empty and region is null. An editor
can populate them later for richer card display; the dashboard handles
missing values gracefully.

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

# OpenStates uses full party names; we normalize to single-letter abbreviations
# to keep the badge column compact.
_PARTY_MAP = {
    "republican": "R",
    "democratic": "D",
    "democrat": "D",
    "independent": "I",
}


def _year_of(iso: str | None) -> int | None:
    if not iso:
        return None
    m = re.match(r"(\d{4})", iso)
    return int(m.group(1)) if m else None


def _slug_for(name: str, chamber: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    prefix = "sen" if chamber == "Senate" else "rep"
    return f"{prefix}-{base}"


def _party_letter(raw: str) -> str:
    return _PARTY_MAP.get((raw or "").strip().lower(), (raw or "")[:1].upper() or "I")


def _district_label(raw: str | int | None, chamber: str) -> str:
    if raw is None or raw == "":
        return ""
    prefix = "SD" if chamber == "Senate" else "HD"
    return f"{prefix}-{raw}"


def _term_dates_default(chamber: str, district_str: str) -> tuple[int | None, int | None]:
    """
    Best-effort term dates when OpenStates doesn't supply them. Based on PA
    cycle parity (Senate odd districts elect in non-presidential even years
    [2018, 2022, 2026...], even districts in presidential years [2020, 2024,
    2028...]; 4-year terms). PA House: all elected every even year, 2-year
    terms.

    PA elections are in November; terms begin December (or January). Until
    that November we treat the most-recent past cycle as the current term;
    after November of an election year, swing to the next term.
    """
    today = datetime.now(timezone.utc)
    year = today.year
    pre_election = today.month < 11
    digits = re.search(r"(\d+)", district_str or "")

    def last_cycle(start_year: int, every: int) -> int | None:
        # Walk back to most-recent past election year of this cycle.
        if year < start_year:
            return None
        candidate = year - ((year - start_year) % every)
        if candidate == year and pre_election:
            # This year IS a cycle year, but the election hasn't happened
            # yet — current term is from the PREVIOUS cycle.
            candidate -= every
        return candidate if candidate >= start_year else None

    if chamber == "House":
        # House: 2-year term, sworn in year after election.
        # Election year 2022 → term 2023–2024.
        cy = last_cycle(2018, 2)
        if cy is None:
            return None, None
        return cy + 1, cy + 2
    if not digits:
        return None, None
    n = int(digits.group(1))
    # Senate: 4-year term, sworn in year after election.
    # Election year 2022 → term 2023–2026.
    cy = last_cycle(2022, 4) if n % 2 == 1 else last_cycle(2020, 4)
    if cy is None:
        return None, None
    return cy + 1, cy + 4



def _build_new_record(person: dict) -> dict | None:
    name = (person.get("name") or "").strip()
    if not name:
        return None
    current = person.get("current_role") or {}
    org = current.get("org_classification") or ""
    chamber = "Senate" if org == "upper" else ("House" if org == "lower" else "")
    if not chamber:
        return None
    district_str = _district_label(current.get("district"), chamber)
    start = _year_of(current.get("start_date"))
    end = _year_of(current.get("end_date"))
    if start is None or end is None:
        d_start, d_end = _term_dates_default(chamber, district_str)
        start = start if start is not None else d_start
        end = end if end is not None else d_end
    return {
        "id": _slug_for(name, chamber),
        "name": name,
        "title": current.get("title") or ("Senator" if chamber == "Senate" else "Representative"),
        "chamber": chamber,
        "district": district_str,
        "party": _party_letter(person.get("party") or ""),
        "openstatesId": person.get("id"),
        "url": (person.get("links") or [{}])[0].get("url", "") if person.get("links") else "",
        "photoUrl": person.get("image") or None,
        "counties": [],
        "region": None,
        "currentTermStart": start,
        "currentTermEnd": end,
    }


def _ensure_unique_slug(slug: str, existing_ids: set[str]) -> str:
    if slug not in existing_ids:
        return slug
    i = 2
    while f"{slug}-{i}" in existing_ids:
        i += 1
    return f"{slug}-{i}"


def main() -> int:
    if not OFFICIALS_PATH.exists():
        print(f"officials.json missing at {OFFICIALS_PATH}", file=sys.stderr)
        return 1

    doc = json.loads(OFFICIALS_PATH.read_text())
    officials = doc.get("officials", []) or []

    try:
        client = OpenStatesClient.from_env()
    except OpenStatesError as e:
        print(str(e), file=sys.stderr)
        return 2

    name_index: dict[str, dict] = {}
    id_index: dict[str, dict] = {}
    fetched: list[dict] = []
    for person in client.paginate("/people", params={"jurisdiction": JURISDICTION}):
        if not isinstance(person, dict):
            continue
        fetched.append(person)
        norm = normalize_name(person.get("name") or "")
        if norm:
            name_index[norm] = person
        if person.get("id"):
            id_index[person["id"]] = person

    updated = 0
    matched_openstates_ids: set[str] = set()
    for o in officials:
        match = None
        if o.get("openstatesId") and o["openstatesId"] in id_index:
            match = id_index[o["openstatesId"]]
        if not match:
            match = name_index.get(normalize_name(o.get("name") or ""))
        if not match:
            continue
        matched_openstates_ids.add(match.get("id") or "")

        current_role = match.get("current_role") or {}
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

    existing_slugs = {o.get("id") for o in officials if o.get("id")}
    added = 0
    for person in fetched:
        ocd = person.get("id")
        if ocd in matched_openstates_ids:
            continue
        record = _build_new_record(person)
        if not record:
            continue
        record["id"] = _ensure_unique_slug(record["id"], existing_slugs)
        existing_slugs.add(record["id"])
        officials.append(record)
        added += 1

    doc["lastFetched"] = datetime.now(timezone.utc).isoformat()
    doc.pop("lastFetchedNote", None)
    doc["officials"] = officials
    OFFICIALS_PATH.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"Refreshed {updated} existing officials, added {added} new (total now {len(officials)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
