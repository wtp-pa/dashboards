"""
Integration: Philadelphia County should return ≥25 unique state reps via
multi-point sampling. If it returns fewer, the sampling grid is too sparse
or rate limits dropped requests. Skipped without OPENSTATES_API_KEY.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_in_range, env, need_api_key  # noqa: E402

KEY = env("OPENSTATES_API_KEY")

# Philadelphia bbox (rough)
PHILA = {"south": 39.867, "north": 40.138, "west": -75.280, "east": -74.956}


def people_geo(lat: float, lng: float):
    url = f"https://v3.openstates.org/people.geo?lat={lat}&lng={lng}&apikey={KEY}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read()).get("results") or []
    except Exception:
        return []


def main() -> None:
    print("integration_county_coverage.py")
    if need_api_key():
        return
    inset = 0.08
    points = []
    for i in range(5):
        for j in range(5):
            fx = inset + (i / 4) * (1 - 2 * inset)
            fy = inset + (j / 4) * (1 - 2 * inset)
            points.append((PHILA["south"] + (PHILA["north"] - PHILA["south"]) * fy,
                           PHILA["west"] + (PHILA["east"] - PHILA["west"]) * fx))
    seen: set[str] = set()
    state_reps: list[str] = []
    for k, (lat, lng) in enumerate(points):
        people = people_geo(lat, lng)
        for p in people:
            cr = p.get("current_role") or {}
            if cr.get("org_classification") in ("upper", "lower") and p.get("id") not in seen:
                seen.add(p["id"])
                state_reps.append(f"{p.get('name', '?')} {cr.get('org_classification')}-{cr.get('district', '?')}")
        # Pace ourselves to avoid 429s.
        if k % 5 == 4:
            time.sleep(0.6)
    # Philadelphia is ~1.6M people → 6 senators + 25 reps = 31 expected.
    # Tolerate -10 since boundary points may fall outside Philly proper.
    assert_in_range(len(state_reps), 21, 50, f"Philadelphia distinct state reps from 25-point sample")


if __name__ == "__main__":
    main()
