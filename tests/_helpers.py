"""Shared helpers for the test suite. No external deps."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def load(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text())


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)
    print(f"  PASS: {msg}")


def assert_eq(got, want, msg: str) -> None:
    if got != want:
        print(f"  FAIL: {msg} — got {got!r}, want {want!r}", file=sys.stderr)
        raise AssertionError(f"{msg} — got {got!r}, want {want!r}")
    print(f"  PASS: {msg} ({got!r})")


def assert_in_range(value, lo, hi, msg: str) -> None:
    if value < lo or value > hi:
        print(f"  FAIL: {msg} — got {value}, expected in [{lo}, {hi}]", file=sys.stderr)
        raise AssertionError(f"{msg} — got {value}, expected in [{lo}, {hi}]")
    print(f"  PASS: {msg} ({value})")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def need_api_key() -> bool:
    """Skip integration tests if no OpenStates key. Returns True if we should skip."""
    if not env("OPENSTATES_API_KEY"):
        print("  SKIP: OPENSTATES_API_KEY not set, skipping integration test")
        return True
    return False
