#!/usr/bin/env python3
"""
Build static PA ZIP→districts and county→districts lookup tables.

Why: the U.S. Census Bureau's geographies API returns SLDU/SLDL
correctly but does NOT send CORS headers, so browser fetches are
blocked. Solution: do all the Census calls server-side here, ship the
result as static JSON, and make the EO page resolve ZIP and county
lookups locally with no runtime API needed.

Pipeline:
  1. Download Census 2020 Gazetteer files (ZCTA centroids + county
     centroids).
  2. Filter to PA (state code 42).
  3. For each PA ZIP: hit Census /geographies/coordinates at the
     centroid → record SD-N and HD-N.
  4. For each PA county: hit Census /geographies/coordinates at a 5×5
     grid sampled across the county bbox → record union of districts.
  5. Write data/elected-officials/zip-districts.json and
     data/elected-officials/county-districts.json.

Run locally (one-shot, no env vars required):
    python3 pipeline/elected-officials/build_static_geo.py

Re-run when PA redistricting happens (every 10 years) or when Census
publishes a new Current_Current vintage.
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ZIP_OUTPUT = REPO_ROOT / "data" / "elected-officials" / "zip-districts.json"
COUNTY_OUTPUT = REPO_ROOT / "data" / "elected-officials" / "county-districts.json"

GAZ_ZCTA_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_zcta_national.zip"
GAZ_COUNTY_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip"
CENSUS_COORDS = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"

PA_STATE_FIPS = "42"
USER_AGENT = "wtpppa-dashboard-build/1.0"


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def census_districts(lat: float, lng: float) -> list[str]:
    """Return ['SD-N', 'HD-N'] for a coordinate, or [] on failure."""
    params = urllib.parse.urlencode({
        "x": str(lng),
        "y": str(lat),
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    })
    try:
        data = json.loads(fetch(f"{CENSUS_COORDS}?{params}", timeout=30))
    except Exception:
        return []
    g = (data.get("result") or {}).get("geographies") or {}
    out = []
    for key in ("2024 State Legislative Districts - Upper", "2022 State Legislative Districts - Upper"):
        items = g.get(key) or []
        if items and items[0].get("SLDU"):
            out.append(f"SD-{int(items[0]['SLDU'])}")
            break
    for key in ("2024 State Legislative Districts - Lower", "2022 State Legislative Districts - Lower"):
        items = g.get(key) or []
        if items and items[0].get("SLDL"):
            out.append(f"HD-{int(items[0]['SLDL'])}")
            break
    return out


def parse_gazetteer_zip(zip_bytes: bytes) -> list[dict]:
    """Parse a Census gazetteer .zip, return list of dict rows."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        # First .txt inside is the data file.
        name = next(n for n in z.namelist() if n.endswith(".txt"))
        with z.open(name) as f:
            text = f.read().decode("utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        return []
    headers = [h.strip() for h in lines[0].split("\t")]
    rows = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def main() -> int:
    print("[1/4] Downloading Census 2020 ZCTA gazetteer…", file=sys.stderr)
    zcta_rows = parse_gazetteer_zip(fetch(GAZ_ZCTA_URL))
    print(f"      {len(zcta_rows)} ZCTAs total", file=sys.stderr)

    # PA ZCTAs are 5-digit codes starting with 15–19, but the gazetteer
    # has no state code on ZCTAs (they cross state lines). Filter by
    # the prefix as a heuristic; we'll trust Census to confirm location.
    pa_zips = [r for r in zcta_rows if r.get("GEOID", "")[:2] in ("15", "16", "17", "18", "19")]
    print(f"      {len(pa_zips)} ZCTAs starting with 15-19 (likely PA)", file=sys.stderr)

    print("[2/4] Querying Census /coordinates per ZIP centroid…", file=sys.stderr)
    print("      (no rate limit known — pacing at ~5/sec to be polite)", file=sys.stderr)
    zip_to_districts: dict[str, dict] = {}
    skipped = 0
    for i, row in enumerate(pa_zips):
        try:
            zcta = row.get("GEOID", "")
            lat = float(row.get("INTPTLAT", "0"))
            lng = float(row.get("INTPTLONG", "0"))
        except Exception:
            skipped += 1
            continue
        if not zcta or not lat or not lng:
            skipped += 1
            continue
        districts = census_districts(lat, lng)
        # Only keep if we got both Senate + House and both are PA-like
        # (this filters non-PA ZIPs that happened to share a 15-19 prefix).
        senate = next((d for d in districts if d.startswith("SD-")), None)
        house = next((d for d in districts if d.startswith("HD-")), None)
        if senate and house:
            zip_to_districts[zcta] = {"senate": senate, "house": house, "lat": lat, "lng": lng}
        else:
            skipped += 1
        if (i + 1) % 100 == 0:
            print(f"      {i+1}/{len(pa_zips)} processed, kept {len(zip_to_districts)}", file=sys.stderr)
        time.sleep(0.2)

    print(f"      Final: {len(zip_to_districts)} PA ZIPs, {skipped} skipped (non-PA or no SLD)", file=sys.stderr)

    zip_doc = {
        "$comment": (
            "Pre-built PA ZIP → state legislative district lookup. "
            "Built by pipeline/elected-officials/build_static_geo.py from Census "
            "2020 ZCTA Gazetteer + Census geographies API. Re-run after "
            "redistricting (next ~2032). Schema: zips[ZIP] = {senate, house, lat, lng}."
        ),
        "lastBuilt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "U.S. Census Bureau (Gazetteer 2020 + Geographies API Current_Current)",
        "zips": zip_to_districts,
    }
    ZIP_OUTPUT.write_text(json.dumps(zip_doc, indent=2) + "\n")
    print(f"      Wrote {ZIP_OUTPUT}", file=sys.stderr)

    print("[3/4] Downloading Census 2020 county gazetteer…", file=sys.stderr)
    county_rows = parse_gazetteer_zip(fetch(GAZ_COUNTY_URL))
    pa_counties = [r for r in county_rows if r.get("USPS", "") == "PA"]
    print(f"      {len(pa_counties)} PA counties", file=sys.stderr)

    print("[4/4] Sampling districts per county centroid (5x5 bbox grid)…", file=sys.stderr)
    county_to_districts: dict[str, dict] = {}
    for i, row in enumerate(pa_counties):
        name = row.get("NAME", "").replace(" County", "").strip()
        if not name:
            continue
        try:
            lat = float(row.get("INTPTLAT", "0"))
            lng = float(row.get("INTPTLONG", "0"))
            # Census counties gazetteer doesn't have a bbox; use a fixed
            # ~0.5-degree window around the centroid for sampling. Counties
            # rarely span more than that in PA.
            radius = 0.4
            bbox = {
                "south": lat - radius,
                "north": lat + radius,
                "west": lng - radius,
                "east": lng + radius,
            }
        except Exception:
            continue
        districts: set[str] = set()
        # 5x5 inset grid
        inset = 0.08
        for ix in range(5):
            for iy in range(5):
                fx = inset + (ix / 4) * (1 - 2 * inset)
                fy = inset + (iy / 4) * (1 - 2 * inset)
                px = bbox["west"] + (bbox["east"] - bbox["west"]) * fx
                py = bbox["south"] + (bbox["north"] - bbox["south"]) * fy
                for d in census_districts(py, px):
                    districts.add(d)
                time.sleep(0.15)
        senate = sorted(d for d in districts if d.startswith("SD-"))
        house = sorted(d for d in districts if d.startswith("HD-"))
        county_to_districts[name] = {
            "senate": senate,
            "house": house,
            "lat": lat,
            "lng": lng,
        }
        print(f"      {i+1}/{len(pa_counties)} {name}: {len(senate)} senate, {len(house)} house", file=sys.stderr)

    county_doc = {
        "$comment": (
            "Pre-built PA county → state legislative districts overlap "
            "lookup. Built by pipeline/elected-officials/build_static_geo.py "
            "via 5x5 grid sampling of Census /coordinates per county. "
            "Schema: counties[NAME] = {senate[], house[], lat, lng}."
        ),
        "lastBuilt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "U.S. Census Bureau (Gazetteer 2020 + Geographies API Current_Current)",
        "counties": county_to_districts,
    }
    COUNTY_OUTPUT.write_text(json.dumps(county_doc, indent=2) + "\n")
    print(f"      Wrote {COUNTY_OUTPUT}", file=sys.stderr)

    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
