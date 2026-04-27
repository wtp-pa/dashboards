#!/usr/bin/env python3
"""
Scrape the PA Independent Fiscal Office homepage for the most recent publications.

Source: https://www.ifo.state.pa.us/

Output: data/ifo-publications.json (top 5 most recent publications across all categories)

Run locally:
    python pipeline/fetch_ifo.py

Run via GitHub Actions: see .github/workflows/data-pipeline.yml
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

IFO_HOME = "https://www.ifo.state.pa.us/"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "ifo-publications.json"
MAX_PUBLICATIONS = 5
USER_AGENT = "wtp-budget-watch/0.1 (+https://github.com/wtp-pa/wtp-budget-watch)"

DATE_PATTERN = re.compile(
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
)
RELEASE_PATTERN = re.compile(r"/releases/\d+/[^/]+/?$")
SUFFIX_NOISE = re.compile(r"\s*-\s*opens in a new tab\s*$", re.IGNORECASE)


def parse_date(text: str) -> str | None:
    """Parse 'April 23, 2026' style dates into ISO 'YYYY-MM-DD'."""
    text = text.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def clean_title(text: str) -> str:
    return SUFFIX_NOISE.sub("", text).strip()


def extract_publication(card) -> dict | None:
    """Extract a single publication record from a `div.featured-details` card."""
    title_div = card.find(class_="featured-title")
    if not title_div:
        return None

    # Find the release link inside the title div.
    release_anchor = next(
        (
            a
            for a in title_div.find_all("a", href=True)
            if RELEASE_PATTERN.search(a["href"].strip())
        ),
        None,
    )
    if not release_anchor:
        return None

    title = clean_title(release_anchor.get_text(strip=True))
    if not title:
        return None
    url = urljoin(IFO_HOME, release_anchor["href"].strip())

    # Date: find the first "Month DD, YYYY" pattern in the card.
    card_text = card.get_text(" ", strip=True)
    date_match = DATE_PATTERN.search(card_text)
    date_iso = parse_date(date_match.group(0)) if date_match else None

    # PDF: any anchor inside the card with .pdf href.
    pdf_anchor = next(
        (a for a in card.find_all("a", href=True) if a["href"].lower().endswith(".pdf")),
        None,
    )
    pdf_url = urljoin(IFO_HOME, pdf_anchor["href"].strip()) if pdf_anchor else None

    # Summary: take text after the date string (if found), else the longest chunk.
    summary: str | None = None
    if date_match:
        after_date = card_text[date_match.end():].strip()
        if len(after_date) > 30:
            summary = after_date[:280] + ("…" if len(after_date) > 280 else "")
    if not summary:
        chunks = [t for t in card.stripped_strings if len(t) > 30]
        if chunks:
            summary = max(chunks, key=len)[:280]

    return {
        "title": title,
        "date": date_iso,
        "url": url,
        "pdfUrl": pdf_url,
        "summary": summary,
    }


def scrape_publications() -> list[dict]:
    resp = requests.get(IFO_HOME, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cards = soup.find_all(class_="featured-details")
    seen_urls: set[str] = set()
    publications: list[dict] = []
    for card in cards:
        pub = extract_publication(card)
        if not pub or not pub["date"] or pub["url"] in seen_urls:
            continue
        seen_urls.add(pub["url"])
        publications.append(pub)

    publications.sort(key=lambda p: p["date"], reverse=True)
    return publications[:MAX_PUBLICATIONS]


def write_output(publications: list[dict]) -> None:
    payload = {
        "schemaVersion": 1,
        "lastUpdated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "name": "PA Independent Fiscal Office",
            "url": IFO_HOME,
        },
        "publications": publications,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[fetch_ifo] wrote {len(publications)} publications → {OUTPUT_PATH}")


def main() -> int:
    try:
        pubs = scrape_publications()
    except requests.RequestException as exc:
        print(f"[fetch_ifo] HTTP error: {exc}", file=sys.stderr)
        return 1

    if not pubs:
        print(
            "[fetch_ifo] no publications found — IFO HTML structure may have changed",
            file=sys.stderr,
        )
        return 1

    write_output(pubs)
    for p in pubs:
        print(f"  {p['date']} · {p['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
