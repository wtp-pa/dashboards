"""
Integration: verify a few canonical PA addresses resolve through the
geocoder + OpenStates pipeline and return real PA state reps that exist
in our roster. Skipped when OPENSTATES_API_KEY is not set.

Hits external APIs (Census, Nominatim, OpenStates). Slow.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_true, env, load, need_api_key  # noqa: E402

KEY = env("OPENSTATES_API_KEY")

CANONICAL = [
    # (query, expected senator district, expected rep district, friendly label)
    ("100 Market St, Harrisburg, Pennsylvania", "SD-15", "HD-103", "PA Capitol area"),
    ("4400 Forbes Ave, Pittsburgh, Pennsylvania", "SD-43", "HD-23", "Carnegie Museum"),
    ("16801, Pennsylvania, USA", "SD-25", "HD-82", "ZIP 16801 (State College)"),
]


def census_geocode(addr: str):
    q = urllib.parse.urlencode({"address": addr, "benchmark": "Public_AR_Current", "format": "json"})
    url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{q}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        m = (data.get("result") or {}).get("addressMatches") or []
        if m:
            c = m[0].get("coordinates") or {}
            return c.get("y"), c.get("x")
    except Exception:
        return None
    return None


def nominatim_geocode(addr: str):
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(addr)}&format=json&limit=1&countrycodes=us"
    req = urllib.request.Request(url, headers={"User-Agent": "wtpppa-tests/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None
    return None


def people_geo(lat: float, lng: float):
    url = f"https://v3.openstates.org/people.geo?lat={lat}&lng={lng}&apikey={KEY}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read()).get("results") or []


def main() -> None:
    print("integration_address_lookup.py")
    if need_api_key():
        return
    officials = load("data/elected-officials/officials.json")["officials"]
    by_district = {(o["chamber"], o["district"]): o for o in officials}
    for addr, exp_sd, exp_hd, label in CANONICAL:
        coords = census_geocode(addr) or nominatim_geocode(addr)
        assert_true(coords is not None, f"{label}: geocoder returned a point")
        if coords is None:
            continue
        lat, lng = coords
        people = people_geo(lat, lng)
        # Filter to state-level officeholders by org_classification.
        state_reps = [p for p in people if (p.get("current_role") or {}).get("org_classification") in ("upper", "lower")]
        sds = [p for p in state_reps if (p.get("current_role") or {}).get("org_classification") == "upper"]
        hds = [p for p in state_reps if (p.get("current_role") or {}).get("org_classification") == "lower"]
        assert_true(len(sds) >= 1, f"{label}: at least one state senator")
        assert_true(len(hds) >= 1, f"{label}: at least one state rep")

        # Confirm the expected districts appear (boundary points may yield multiple).
        sd_districts = {f"SD-{(p.get('current_role') or {}).get('district', '')}" for p in sds}
        hd_districts = {f"HD-{(p.get('current_role') or {}).get('district', '')}" for p in hds}
        assert_true(exp_sd in sd_districts, f"{label}: expected senator district {exp_sd} in {sd_districts}")
        assert_true(exp_hd in hd_districts, f"{label}: expected rep district {exp_hd} in {hd_districts}")

        # Each returned state rep should also exist in our roster.
        for p in state_reps:
            cr = p.get("current_role") or {}
            chamber = "Senate" if cr.get("org_classification") == "upper" else "House"
            district = ("SD-" if chamber == "Senate" else "HD-") + str(cr.get("district") or "")
            assert_true((chamber, district) in by_district, f"{label}: {p.get('name', '?')} ({chamber} {district}) is in roster")
        time.sleep(2)  # be polite to OpenStates


if __name__ == "__main__":
    main()
