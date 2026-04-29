#!/usr/bin/env python3
"""
Score each PA bill in data/legislation/bills.json against the WTP-PA platform
positions in data/legislation/platform.json using two complementary signals:

  1. Keyword matching — word-boundary regex against curated keywords per
     position. Precise; produces a "matched keyword" explanation.
  2. TF-IDF cosine similarity — semantic catch-all that handles paraphrasing
     and synonyms. Produces a similarity score + the highest-contributing
     overlapping terms.

A position is recorded for a bill if EITHER signal fires. Each match in the
output records the mechanism (keyword | tfidf) and a human-readable evidence
string for the dashboard drill-down.

This is intentionally NOT an LLM-based scorer. The math is open and the
keyword list is checked into git. Direction calls (aligned vs. opposed) are
not something either signal can infer — those still come from
manual_review.json.

Run locally:
    python pipeline/legislation/match_bills.py

Run via GitHub Actions: see .github/workflows/data-pipeline.yml
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "legislation"
BILLS_PATH = DATA_DIR / "bills.json"
PLATFORM_PATH = DATA_DIR / "platform.json"

# Cosine-similarity threshold above which a TF-IDF hit is recorded as a match.
# Keyword hits are always recorded regardless of TF-IDF score.
TFIDF_THRESHOLD = 0.10

# Cap matches per bill so the drill-down stays focused on the strongest signals.
MAX_MATCHES_PER_BILL = 5
MAX_TERMS_PER_MATCH = 5


# --- Keyword matcher (precise) -------------------------------------------------

@lru_cache(maxsize=None)
def keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Word-boundary regex for a keyword phrase, case-insensitive.

    \\b at each end avoids 'PAC' matching 'impact'. Internal whitespace
    matches one or more whitespace characters so 'school choice' matches
    'school   choice' or 'school\\nchoice'.
    """
    parts = [re.escape(p) for p in keyword.lower().split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b", re.IGNORECASE)


def keyword_hit(text: str, position: dict) -> str | None:
    """Return the first keyword that matches, or None."""
    for keyword in position["keywords"]:
        if keyword_pattern(keyword).search(text):
            return keyword
    return None


# --- TF-IDF matcher (semantic) -------------------------------------------------

# Lightweight Porter-style suffix stripping for stemming. Catches the common
# cases ("midwifery"→"midwif", "voting"→"vote", "firearms"→"firearm") without
# pulling in nltk.
_SUFFIXES = (
    "ational", "tional", "iveness", "ization", "fulness", "ousness",
    "alize", "icate", "ative", "ically", "iciti", "icity", "alism",
    "ation", "ities", "ously", "ment", "able", "ible", "ness", "ance",
    "ence", "less", "ship", "ies", "ied", "ing", "ity", "ous", "ive",
    "ize", "ise", "ed", "es", "er", "ly", "al", "y", "s",
)
_WORD_RE = re.compile(r"[a-z]+")


def _stem(word: str) -> str:
    if len(word) <= 3:
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


# Stem the standard English stop-word list once so the same words don't slip
# through after stemming. Add legislative boilerplate that carries no signal.
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
_BOILERPLATE = {
    "act", "bill", "section", "amend", "amendment", "establish", "provide",
    "require", "law", "code", "title", "chapter", "regulation", "pennsylvania",
    "state", "include", "general", "purpose",
}
_STEMMED_STOPWORDS: frozenset[str] = frozenset(
    {_stem(w) for w in ENGLISH_STOP_WORDS} | {_stem(w) for w in _BOILERPLATE}
)


def stem_tokenize(text: str) -> list[str]:
    return [s for s in (_stem(w) for w in _WORD_RE.findall(text.lower())) if s not in _STEMMED_STOPWORDS]


def position_corpus(position: dict) -> str:
    parts = [position["title"], position["summary"]]
    parts.extend(position["keywords"] * 2)
    return " ".join(parts)


def bill_corpus(bill: dict) -> str:
    return f"{bill.get('title', '')} {bill.get('summary', '')}"


def overlapping_terms(bill_vec, position_vec, vocabulary: list[str], limit: int) -> list[str]:
    """Top terms by contribution to the cosine-similarity dot product."""
    products = bill_vec.toarray()[0] * position_vec.toarray()[0]
    top_indices = products.argsort()[::-1]
    terms: list[str] = []
    for idx in top_indices:
        if products[idx] <= 0:
            break
        terms.append(vocabulary[idx])
        if len(terms) >= limit:
            break
    return terms


# --- Main ---------------------------------------------------------------------

def main() -> int:
    if not BILLS_PATH.exists() or not PLATFORM_PATH.exists():
        print(f"Missing input file. Need {BILLS_PATH} and {PLATFORM_PATH}", file=sys.stderr)
        return 1

    bills_doc = json.loads(BILLS_PATH.read_text())
    platform = json.loads(PLATFORM_PATH.read_text())

    positions: list[dict] = []
    for pillar in platform["pillars"]:
        for position in pillar["positions"]:
            positions.append({**position, "pillar_id": pillar["id"]})

    position_corpora = [position_corpus(p) for p in positions]
    bills = bills_doc["bills"]
    bill_corpora = [bill_corpus(b) for b in bills]

    vectorizer = TfidfVectorizer(
        tokenizer=stem_tokenize,
        token_pattern=None,
        stop_words=None,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    vectorizer.fit(position_corpora + bill_corpora)
    vocabulary: list[str] = vectorizer.get_feature_names_out().tolist()
    position_vectors = vectorizer.transform(position_corpora)
    bill_vectors = vectorizer.transform(bill_corpora)
    sim_matrix = cosine_similarity(bill_vectors, position_vectors)

    for bi, bill in enumerate(bills):
        haystack = bill_corpus(bill)
        match_by_position: dict[str, dict] = {}

        # Keyword pass — high precision.
        for pi, position in enumerate(positions):
            keyword = keyword_hit(haystack, position)
            if keyword:
                match_by_position[position["id"]] = {
                    "positionId": position["id"],
                    "score": round(float(sim_matrix[bi, pi]), 3),
                    "evidence": f'matched keyword "{keyword}"',
                    "mechanism": "keyword",
                    "overlappingTerms": [],
                }

        # TF-IDF pass — semantic recall. Only records matches above threshold,
        # and only for positions not already recorded by the keyword pass.
        for pi, position in enumerate(positions):
            if position["id"] in match_by_position:
                continue
            score = float(sim_matrix[bi, pi])
            if score < TFIDF_THRESHOLD:
                continue
            terms = overlapping_terms(
                bill_vectors[bi], position_vectors[pi], vocabulary, MAX_TERMS_PER_MATCH,
            )
            match_by_position[position["id"]] = {
                "positionId": position["id"],
                "score": round(score, 3),
                "evidence": f'shares terms: {", ".join(terms)}' if terms else f"cosine similarity {score:.2f}",
                "mechanism": "tfidf",
                "overlappingTerms": terms,
            }

        ranked = sorted(match_by_position.values(), key=lambda m: m["score"], reverse=True)
        bill["matches"] = ranked[:MAX_MATCHES_PER_BILL]
        bill["matchedPositions"] = [m["positionId"] for m in bill["matches"]]

    bills_doc["lastMatched"] = datetime.now(timezone.utc).isoformat()
    bills_doc["tfidfThreshold"] = TFIDF_THRESHOLD
    BILLS_PATH.write_text(json.dumps(bills_doc, indent=2) + "\n")

    matched_count = sum(1 for b in bills if b["matches"])
    keyword_count = sum(1 for b in bills for m in b["matches"] if m["mechanism"] == "keyword")
    tfidf_count = sum(1 for b in bills for m in b["matches"] if m["mechanism"] == "tfidf")
    print(
        f"Scored {len(bills)} bills against {len(positions)} platform positions. "
        f"{matched_count} matched at least one plank "
        f"({keyword_count} keyword hits, {tfidf_count} TF-IDF hits). "
        f"Wrote {BILLS_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
