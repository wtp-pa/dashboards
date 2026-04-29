#!/usr/bin/env python3
"""
Fetch the most recent PA General Assembly bills from the OpenStates API and
write them to data/legislation/bills.json.

Auth: requires the OPENSTATES_API_KEY environment variable. Get a free key
at https://openstates.org/accounts/profile/. Locally, export the var; in
GitHub Actions, set the OPENSTATES_API_KEY repo secret.

HTTP/auth/retry/pagination plumbing lives in pipeline/_shared/openstates.py
so EO fetchers and any future candidate dashboard can share the same client.

Output schema (per bill in bills.json):
    id, chamber, title, sponsor, status, lastAction, url, summary

This script does NOT compute platform matches — that's match_bills.py's job.
Run them in order:

    python pipeline/legislation/fetch_bills.py
    python pipeline/legislation/match_bills.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running this file directly (python pipeline/legislation/fetch_bills.py)
# even though pipeline/_shared isn't on sys.path by default.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline._shared.openstates import OpenStatesClient, OpenStatesError  # noqa: E402

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "legislation" / "bills.json"
JURISDICTION = "pa"
SESSION = "2025-2026"  # OpenStates session identifier for PA
SESSION_LABEL = "2025-2026 Regular Session"  # human-readable; used in bills.json for the dashboard
MAX_PAGES = 25  # cap to ~500 bills per run; tune as needed

_CHAMBER_BY_PREFIX = {
    "HB": "House", "HR": "House", "HCO": "House", "HCR": "House",
    "SB": "Senate", "SR": "Senate", "SCR": "Senate", "SCO": "Senate",
}


def _chamber_from_id(identifier: str) -> str:
    prefix = "".join(c for c in identifier if c.isalpha()).upper()
    return _CHAMBER_BY_PREFIX.get(prefix, "Unknown")


def _normalize_id(identifier: str) -> str:
    """OpenStates uses 'HB 123' with a space; our schema uses 'HB123'."""
    return identifier.replace(" ", "").upper()


def _primary_sponsor(bill: dict) -> str:
    sponsorships = bill.get("sponsorships") or []
    primary = next((s for s in sponsorships if s.get("primary")), None)
    person = primary or (sponsorships[0] if sponsorships else None)
    if not person:
        return "Unknown"
    name = person.get("name") or "Unknown"
    party_hint = ""
    entity = person.get("entity_type")
    if entity == "person" and person.get("person") and person["person"].get("party"):
        party_hint = f" ({person['person']['party'][0]})"
    chamber = bill.get("from_organization", {}).get("classification") if isinstance(bill.get("from_organization"), dict) else None
    chamber_label = "Sen." if chamber == "upper" else ("Rep." if chamber == "lower" else "")
    label = f"{chamber_label} {name}".strip()
    return f"{label}{party_hint}".strip()


def _all_sponsors(bill: dict) -> list[dict]:
    """
    Return the full sponsor list for a bill in a structured shape that lets
    the EO scorer JOIN against officials.json by openstatesId. Drops
    organizational sponsorships (no person ID to match).
    """
    out: list[dict] = []
    for s in bill.get("sponsorships") or []:
        if s.get("entity_type") != "person":
            continue
        person = s.get("person") or {}
        ocd_id = person.get("id")
        out.append({
            "openstatesId": ocd_id,
            "name": s.get("name") or person.get("name") or "",
            "primary": bool(s.get("primary")),
        })
    return out


def _latest_action(bill: dict) -> tuple[str, str]:
    """Return (status_label, iso_date)."""
    description = bill.get("latest_action_description") or "No recent action"
    date = bill.get("latest_action_date") or ""
    if date and "T" in date:
        date = date.split("T", 1)[0]
    return description, date


def _summary(bill: dict) -> str:
    """Prefer the abstract over title for the dashboard summary."""
    abstracts = bill.get("abstracts") or []
    if abstracts:
        text = abstracts[0].get("abstract") or ""
        if text:
            return text.strip()
    return bill.get("title", "")


def _bill_url(bill: dict) -> str:
    """Prefer a palegis.us source link; fall back to the OpenStates bill page."""
    for src in (bill.get("sources") or []):
        url = src.get("url", "")
        if "palegis" in url or "legis.state.pa" in url:
            return url
    return bill.get("openstates_url") or ""


def main() -> int:
    try:
        client = OpenStatesClient.from_env()
    except OpenStatesError as e:
        print(str(e), file=sys.stderr)
        return 2

    bills: list[dict] = []
    seen_ids: set[str] = set()

    for raw in client.paginate(
        "/bills",
        params={"jurisdiction": JURISDICTION, "session": SESSION, "sort": "latest_action_desc"},
        include=("sponsorships", "abstracts", "sources"),
        max_pages=MAX_PAGES,
    ):
        bid = _normalize_id(raw.get("identifier", ""))
        if not bid or bid in seen_ids:
            continue
        seen_ids.add(bid)
        status, last_action = _latest_action(raw)
        bills.append({
            "id": bid,
            "chamber": _chamber_from_id(bid),
            "title": (raw.get("title") or "").strip(),
            "sponsor": _primary_sponsor(raw),
            "sponsors": _all_sponsors(raw),
            "status": status,
            "lastAction": last_action,
            "url": _bill_url(raw),
            "summary": _summary(raw),
        })

    if not bills:
        print("Fetched 0 bills — refusing to overwrite bills.json.", file=sys.stderr)
        return 1

    # Preserve `matches` from the existing file where bill IDs overlap, so the
    # dashboard isn't blank in the gap between fetch and match runs.
    existing_matches: dict[str, list] = {}
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text())
            for b in existing.get("bills", []):
                if "matches" in b:
                    existing_matches[b["id"]] = b["matches"]
        except Exception:
            pass

    for b in bills:
        b["matches"] = existing_matches.get(b["id"], [])
        b["matchedPositions"] = [m["positionId"] for m in b["matches"]]

    output = {
        "$comment": "PA bills fetched from OpenStates v3 API. Match data is computed by pipeline/legislation/match_bills.py. Manual alignment overrides live in data/legislation/manual_review.json. Refreshed weekly by GitHub Actions.",
        "lastFetched": datetime.now(timezone.utc).isoformat(),
        "session": SESSION_LABEL,
        "source": "https://openstates.org/pa/",
        "bills": bills,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Fetched {len(bills)} bills. Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
