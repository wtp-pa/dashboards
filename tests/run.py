#!/usr/bin/env python3
"""
Run all WTPPPA dashboard tests.

  python3 tests/run.py            # all data tests
  python3 tests/run.py --integration   # also run API integration tests

Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITE = ROOT / "elected_officials"


def discover(prefix: str) -> list[Path]:
    return sorted(p for p in SUITE.glob(f"{prefix}_*.py") if p.is_file())


def run_one(path: Path) -> bool:
    name = path.stem
    print(f"\n→ {name}")
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        print(f"  ERROR: could not load {path}", file=sys.stderr)
        return False
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        if hasattr(module, "main"):
            module.main()
        return True
    except AssertionError:
        return False
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False


def main() -> int:
    integration = "--integration" in sys.argv
    results: list[tuple[str, bool]] = []
    start = time.time()

    for p in discover("test"):
        results.append((p.name, run_one(p)))

    if integration:
        for p in discover("integration"):
            results.append((p.name, run_one(p)))

    elapsed = time.time() - start
    failed = [n for n, ok in results if not ok]
    passed = [n for n, ok in results if ok]
    print(f"\n{'=' * 50}")
    print(f"{len(passed)} passed, {len(failed)} failed in {elapsed:.1f}s")
    for n in failed:
        print(f"  ✗ {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
