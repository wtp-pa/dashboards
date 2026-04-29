#!/usr/bin/env python3
"""
Score each PA bill in data/legislation/bills.json against the WTP-PA platform
positions in data/legislation/platform.json.

Two stages per bill:

  1. Topic detection — does this bill *touch* a platform plank?
     Combines keyword regex (precise) with TF-IDF cosine similarity (catches
     paraphrasing). Produces a list of `matches`, each with a score and an
     evidence string for the drill-down.

  2. Auto-alignment — for each topic match, does the bill move *with* WTP-PA
     or *against* it? Counts hits of `stanceVerbs.aligned` and
     `stanceVerbs.opposed` (defined per-position in platform.json) in the
     bill text. The dominant direction wins; clean wins get high confidence,
     mixed signals get low.

The bill-level `autoAlignment` is the alignment of its strongest match. UI
maps this to a badge:

    likely-aligned   — clear stance verbs in the supported direction
    likely-opposed   — clear stance verbs in the opposed direction
    topic-only       — bill touches a plank but no stance signal
    (manual override from manual_review.json beats all of the above)

Direction calls are still a heuristic, not truth. Confidence < 0.6 means
"go read the bill." Manual reviews override automation.

Run locally:
    python pipeline/legislation/match_bills.py
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


def stance_hits(text: str, verbs: list[str]) -> list[str]:
    """Return the list of stance verbs from `verbs` that appear in `text`."""
    return [v for v in verbs if keyword_pattern(v).search(text)]


def detect_alignment(text: str, position: dict) -> tuple[str, float, dict]:
    """Decide if a bill is moving with or against this position.

    Returns (alignment, confidence, evidence) where:
      alignment  - 'likely-aligned' | 'likely-opposed' | 'topic-only'
      confidence - 0.0..1.0
      evidence   - {'aligned': [...verbs...], 'opposed': [...verbs...]}
    """
    verbs = position.get("stanceVerbs") or {}
    aligned_hits = stance_hits(text, verbs.get("aligned", []))
    opposed_hits = stance_hits(text, verbs.get("opposed", []))

    if not aligned_hits and not opposed_hits:
        return "topic-only", 0.0, {"aligned": [], "opposed": []}

    if aligned_hits and not opposed_hits:
        # 1 verb hit → 0.7 conf; 2+ → 0.85; 3+ → 0.95
        confidence = min(0.95, 0.55 + 0.15 * len(aligned_hits))
        return "likely-aligned", confidence, {"aligned": aligned_hits, "opposed": []}

    if opposed_hits and not aligned_hits:
        confidence = min(0.95, 0.55 + 0.15 * len(opposed_hits))
        return "likely-opposed", confidence, {"aligned": [], "opposed": opposed_hits}

    # Mixed signals — bill mentions both directions. Decide by majority but
    # at low confidence; UI should treat these as "needs review".
    diff = len(aligned_hits) - len(opposed_hits)
    if diff > 0:
        return "likely-aligned", 0.4, {"aligned": aligned_hits, "opposed": opposed_hits}
    if diff < 0:
        return "likely-opposed", 0.4, {"aligned": aligned_hits, "opposed": opposed_hits}
    # Equal hits in both directions.
    return "topic-only", 0.3, {"aligned": aligned_hits, "opposed": opposed_hits}


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

    positions_by_id = {p["id"]: p for p in positions}

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

        # Stance detection — for each topic match, decide alignment.
        for match in match_by_position.values():
            position = positions_by_id[match["positionId"]]
            alignment, confidence, evidence = detect_alignment(haystack, position)
            match["autoAlignment"] = alignment
            match["autoConfidence"] = round(confidence, 2)
            match["alignedVerbs"] = evidence["aligned"]
            match["opposedVerbs"] = evidence["opposed"]

        ranked = sorted(match_by_position.values(), key=lambda m: m["score"], reverse=True)
        bill["matches"] = ranked[:MAX_MATCHES_PER_BILL]
        bill["matchedPositions"] = [m["positionId"] for m in bill["matches"]]

        # Bill-level auto-alignment = the strongest signal across its matches.
        # Pick the match with the highest autoConfidence; ties broken by topic
        # match score.
        if bill["matches"]:
            best = max(bill["matches"], key=lambda m: (m["autoConfidence"], m["score"]))
            bill["autoAlignment"] = best["autoAlignment"]
            bill["autoConfidence"] = best["autoConfidence"]
        else:
            bill["autoAlignment"] = None
            bill["autoConfidence"] = 0.0

    bills_doc["lastMatched"] = datetime.now(timezone.utc).isoformat()
    bills_doc["tfidfThreshold"] = TFIDF_THRESHOLD
    BILLS_PATH.write_text(json.dumps(bills_doc, indent=2) + "\n")

    matched_count = sum(1 for b in bills if b["matches"])
    keyword_count = sum(1 for b in bills for m in b["matches"] if m["mechanism"] == "keyword")
    tfidf_count = sum(1 for b in bills for m in b["matches"] if m["mechanism"] == "tfidf")
    aligned_auto = sum(1 for b in bills if b.get("autoAlignment") == "likely-aligned")
    opposed_auto = sum(1 for b in bills if b.get("autoAlignment") == "likely-opposed")
    topic_only = sum(1 for b in bills if b.get("autoAlignment") == "topic-only")
    print(
        f"Scored {len(bills)} bills against {len(positions)} platform positions. "
        f"{matched_count} matched at least one plank "
        f"({keyword_count} keyword hits, {tfidf_count} TF-IDF hits). "
        f"Auto-alignment: {aligned_auto} likely-aligned, {opposed_auto} likely-opposed, {topic_only} topic-only. "
        f"Wrote {BILLS_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
