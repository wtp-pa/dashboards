#!/usr/bin/env python3
"""
Fetch the most recent PA General Assembly bills from the OpenStates API and
write them to data/legislation/bills.json.

Auth: requires the OPENSTATES_API_KEY environment variable. Get a free key
at https://openstates.org/accounts/profile/. Locally, export the var; in
GitHub Actions, set the OPENSTATES_API_KEY repo secret.

Output schema (per bill in bills.json):
    id, chamber, title, sponsor, status, lastAction, url, summary

This script does NOT compute platform matches — that's match_bills.py's job.
Run them in order:

    python pipeline/legislation/fetch_bills.py
    python pipeline/legislation/match_bills.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "legislation" / "bills.json"
API_BASE = "https://v3.openstates.org/bills"
JURISDICTION = "pa"
SESSION = "2025-2026"  # OpenStates session identifier for PA
SESSION_LABEL = "2025-2026 Regular Session"  # human-readable; used in bills.json for the dashboard
PER_PAGE = 20  # OpenStates v3 caps at 20 with non-default sort
MAX_PAGES = 25  # cap to ~500 bills per run; tune as needed
REQUEST_DELAY_SEC = 6.0  # OpenStates free tier — empirically requires generous spacing

# Bill prefixes whose chamber we infer (PA pattern).
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
    classification = person.get("classification", "")
    party_hint = ""
    entity = person.get("entity_type")
    if entity == "person" and person.get("person") and person["person"].get("party"):
        party_hint = f" ({person['person']['party'][0]})"
    chamber = bill.get("from_organization", {}).get("classification") if isinstance(bill.get("from_organization"), dict) else None
    chamber_label = "Sen." if chamber == "upper" else ("Rep." if chamber == "lower" else "")
    label = f"{chamber_label} {name}".strip()
    return f"{label}{party_hint}".strip()


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


def fetch_page(api_key: str, page: int) -> dict:
    params = [
        ("jurisdiction", JURISDICTION),
        ("session", SESSION),
        ("sort", "latest_action_desc"),
        ("per_page", str(PER_PAGE)),
        ("page", str(page)),
        # OpenStates v3 requires `include` to be repeated, not comma-joined.
        ("include", "sponsorships"),
        ("include", "abstracts"),
        ("include", "sources"),
    ]
    headers = {"X-API-KEY": api_key, "User-Agent": "wtp-pa-legislation-watch/1.0"}
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            resp = requests.get(API_BASE, params=params, headers=headers, timeout=60)
            if resp.status_code == 429:
                # Honor server-suggested cooldown if present, else escalate.
                wait = int(resp.headers.get("Retry-After", "")) if resp.headers.get("Retry-After", "").isdigit() else 10 * (attempt + 1)
                print(f"  rate-limited, sleeping {wait}s before retry...", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.HTTPError) as e:
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def main() -> int:
    api_key = os.environ.get("OPENSTATES_API_KEY")
    if not api_key:
        print("OPENSTATES_API_KEY env var is required.", file=sys.stderr)
        print("Get a free key at https://openstates.org/accounts/profile/.", file=sys.stderr)
        return 2

    bills: list[dict] = []
    seen_ids: set[str] = set()
    pages_fetched = 0

    for page in range(1, MAX_PAGES + 1):
        data = fetch_page(api_key, page)
        results = data.get("results", []) or []
        if not results:
            break

        for raw in results:
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
                "status": status,
                "lastAction": last_action,
                "url": _bill_url(raw),
                "summary": _summary(raw),
            })

        pages_fetched += 1
        pagination = data.get("pagination") or {}
        if pagination.get("page", page) >= pagination.get("max_page", page):
            break
        time.sleep(REQUEST_DELAY_SEC)

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
    print(f"Fetched {len(bills)} bills across {pages_fetched} page(s). Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
