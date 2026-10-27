"""Fairness guards for data/quiz: every scored stance has a source."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_eq, assert_true, load  # noqa: E402


def main() -> None:
    issues = {i["id"] for i in load("data/quiz/issues.json")["issues"]}
    races = load("data/quiz/races.json")["races"]

    unsourced, unknown_ids, dup_ids = [], [], []
    for r in races:
        ids = [c["id"] for c in r["candidates"]]
        if len(ids) != len(set(ids)):
            dup_ids.append(r["id"])
        for c in r["candidates"]:
            for iid, p in c["positions"].items():
                if iid not in issues:
                    unknown_ids.append(f"{r['id']}/{c['id']}/{iid}")
                if p["stance"] != "unknown" and not str(p.get("source", "")).startswith("http"):
                    unsourced.append(f"{r['id']}/{c['id']}/{iid}")

    assert_eq(unsourced, [], "every non-unknown stance links a source")
    assert_eq(unknown_ids, [], "positions only reference known issue ids")
    assert_eq(dup_ids, [], "candidate ids unique within a race")
    house = [r for r in races if r["level"] == "federal"]
    assert_true(len(house) in (0, 17), f"0 or all 17 House races present ({len(house)})")


if __name__ == "__main__":
    main()
