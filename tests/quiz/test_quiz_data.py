"""Fairness guards for data/quiz: every scored position has a source and real option ids."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _helpers import assert_eq, assert_true, load  # noqa: E402


def main() -> None:
    issue_list = load("data/quiz/issues.json")["issues"]
    issues = {i["id"]: {o["id"] for o in i["options"]} for i in issue_list}
    bad_near = [f"{i['id']}:{p}" for i in issue_list for p in i["near"] if not set(p) <= issues[i["id"]]]
    races = load("data/quiz/races.json")["races"]

    unsourced, unknown_ids, dup_ids, bad_opts = [], [], [], []
    for r in races:
        ids = [c["id"] for c in r["candidates"]]
        if len(ids) != len(set(ids)):
            dup_ids.append(r["id"])
        for c in r["candidates"]:
            for iid, p in c["positions"].items():
                if iid not in issues:
                    unknown_ids.append(f"{r['id']}/{c['id']}/{iid}")
                    continue
                if not set(p["options"]) <= issues[iid] or len(p["options"]) > 2:
                    bad_opts.append(f"{r['id']}/{c['id']}/{iid}")
                if p["options"] and not str(p.get("source", "")).startswith("http"):
                    unsourced.append(f"{r['id']}/{c['id']}/{iid}")

    assert_eq(unsourced, [], "every scored position links a source")
    assert_eq(bad_opts, [], "positions use 1-2 real option ids")
    assert_eq(bad_near, [], "near pairs reference real option ids")
    assert_eq(unknown_ids, [], "positions only reference known issue ids")
    assert_eq(dup_ids, [], "candidate ids unique within a race")
    house = [r for r in races if r["level"] == "federal"]
    assert_true(len(house) in (0, 17), f"0 or all 17 House races present ({len(house)})")


if __name__ == "__main__":
    main()
