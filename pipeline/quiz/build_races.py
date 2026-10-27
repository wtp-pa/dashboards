#!/usr/bin/env python3
"""
Merge researched candidate positions into data/quiz/races.json.

  python3 pipeline/quiz/build_races.py data/quiz/research/gov.json data/quiz/research/house-*.json

Inputs are research notes: gov = {candidates:[...]}, house = {races:[{district,
counties, candidates:[...]}]}. Positions without a source URL are downgraded
to "unknown" here — the fairness rule is "sourced or skipped".
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "quiz" / "races.json"
STANCES = {"agree", "disagree", "mixed", "unknown"}
PARTY = {"D": "Democratic", "R": "Republican", "L": "Libertarian", "G": "Green", "I": "Independent"}


def party(p: str) -> str:
    p = PARTY.get(p, p)
    return p.split(" (")[0]  # drop research annotations like "Independent (Forward Party endorsed)"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def first_url(s: str | None) -> str | None:
    m = re.search(r"https?://[^\s;,)]+", s or "")
    return m.group(0) if m else None


# The votes available on these issues bundle unrelated things (SAVE America
# Act = proof of citizenship + photo ID; H.R. 7008 = stock limits + Voter ID
# Act), so a vote alone doesn't set a stance here — for either party.
BUNDLED_VOTE_ISSUES = {"voter-id", "term-limits"}


def clean_position(p: dict, issue: str) -> dict:
    stance = p.get("stance") if p.get("stance") in STANCES else "unknown"
    source = first_url(p.get("source"))
    if issue in BUNDLED_VOTE_ISSUES and (p.get("summary") or "").lower().startswith(("per record", "record-based")):
        source = None
    out: dict = {"stance": stance if source else "unknown"}
    if p.get("summary"):
        out["summary"] = p["summary"]
    if source:
        out["source"] = source
        if p.get("sourceDate") and p["sourceDate"] != "undated":
            out["sourceDate"] = p["sourceDate"]
    rec = p.get("record") or {}
    rec_src = first_url(rec.get("source"))
    if rec.get("summary") and rec_src:
        out["record"] = {"summary": rec["summary"], "source": rec_src}
    return out


def candidate(c: dict) -> dict:
    return {
        "id": slug(c["name"]),
        "name": c["name"] + (f" / {c['runningMate'].split(' (')[0]}" if c.get("runningMate") else ""),
        "party": party(c["party"]),
        "incumbent": bool(c.get("incumbent")),
        "positions": {k: clean_position(v, k) for k, v in (c.get("positions") or {}).items()},
    }


def district_id(d) -> str:
    n = int(re.search(r"\d+", str(d)).group(0))
    return f"pa-{n:02d}"


def main(paths: list[str]) -> None:
    races: list[dict] = []
    gov = json.loads(Path(paths[0]).read_text())
    races.append({
        "id": "gov",
        "office": "Governor & Lt. Governor",
        "level": "state",
        "candidates": [candidate(c) for c in gov["candidates"]],
    })
    house: dict[str, dict] = {}
    for p in paths[1:]:
        for r in json.loads(Path(p).read_text())["races"]:
            rid = district_id(r["district"])
            # Later files add candidates to a district (e.g. a minor-party
            # ballot check) rather than replacing it.
            race = house.setdefault(rid, {
                "id": rid,
                "office": f"U.S. House — PA-{int(rid[3:])}",
                "level": "federal",
                "counties": [],
                "candidates": [],
            })
            counties = r.get("counties") or []
            race["counties"] = race["counties"] or ([counties] if isinstance(counties, str) else counties)
            race["candidates"] += [
                candidate(c) for c in r["candidates"] if c.get("ballotStatus", "confirmed") == "confirmed"
            ]
    races += [house[k] for k in sorted(house)]
    OUT.write_text(json.dumps({"lastChecked": date.today().isoformat(), "races": races}, indent=1) + "\n")
    print(f"wrote {OUT} — {len(races)} races, {sum(len(r['candidates']) for r in races)} candidates")


if __name__ == "__main__":
    main(sys.argv[1:])
