"""
Name normalization shared between fetch_officials and fetch_votes.

Goal: turn "Lisa M. Boscola" and "Lisa Boscola" into the same key so we can
match an OpenStates record to an officials.json entry without forcing the
editor to copy initials exactly. Strips honorifics, single-letter middle
initials, and collapses whitespace; lowercases for case-insensitive lookup.
"""

from __future__ import annotations

import re

_HONORIFICS = re.compile(
    r"\b(senator|sen\.|representative|rep\.|hon\.|the honorable)\b",
    re.IGNORECASE,
)
# Single uppercase letter followed by a period AND a word boundary on the
# left + a whitespace/end on the right. The naive `\b[A-Z]\.\b` fails on
# "M." followed by a space because there's no word boundary between two
# non-word characters (`.` and ` `).
_MIDDLE_INITIAL = re.compile(r"\b[A-Z]\.(?=\s|$)")
_WHITESPACE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    if not name:
        return ""
    n = _HONORIFICS.sub("", name)
    n = _MIDDLE_INITIAL.sub("", n)
    n = _WHITESPACE.sub(" ", n).strip().lower()
    return n
