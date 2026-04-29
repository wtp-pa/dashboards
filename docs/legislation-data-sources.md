# Legislation Watch — data source decision record

## What we use

| Source | What it gives us | Refresh |
|---|---|---|
| **OpenStates v3 API** (`/bills`) | bill identifier, title, sponsor, status, latest action date, OpenStates URL, source links | weekly via GitHub Actions cron |

That's the entire data surface. From it we derive everything else (cleaned titles, pillar matches, stance scoring, etc.).

## What we deliberately *don't* use, and why

We investigated several paths to enrich each bill with plain-English description (a "what does this bill actually do?" sentence beyond the legalese title) and chose to stop. Documented here so a future session doesn't burn time re-discovering the same dead-ends.

### OpenStates `abstracts` field — empty for PA

```bash
curl -H "X-API-KEY: …" 'https://v3.openstates.org/bills?jurisdiction=pa&include=abstracts' | jq '.results[].abstracts'
# → []  (every bill)
```

PA doesn't supply abstracts upstream. OpenStates supports the field but PA legislative IT doesn't populate it. Verified for both the list endpoint and the single-bill detail endpoint.

### OpenStates `subject` tags — empty for PA

Same story. The taxonomy exists in the API; PA doesn't populate it.

### OpenStates `versions` — only PDF links

Each bill has one or more `versions` entries pointing to printed-PDF URLs. We could download the PDFs and OCR/extract text, but that's heavy infrastructure for marginal lift.

### palegis.us bill pages — JS-rendered SPA + 403s to non-browser User-Agents

```bash
curl -sL 'https://www.palegis.us/legislation/bills/2025/sr276' | grep -oE '"(short_?title|description|summary|memo)"[^,]+'
# → returns "403 Forbidden" page when no browser UA
# → with browser UA: only the meta description boilerplate; bill data is hydrated client-side
```

The SPA's underlying API is not publicly documented. Sponsor memos exist (linked from each bill page) but are PDF documents, not embedded text. Bypassing this would require:

- A headless-Chrome scraper (Playwright/Puppeteer) running in the GitHub Actions cron
- ~200 MB of additional CI dependencies
- Fragile against any UI change on palegis.us
- Implicit acceptance that we're scraping a site whose 403s suggest they'd rather we didn't

### legis.state.pa.us — legacy site, being phased out

The older server-rendered HTML version of palegis.us. Probably easier to scrape, but it's already deprecated and could vanish without notice. Building on it would mean rebuilding when it goes.

## The decision (2026-04-29)

**Stay on titles-only.** Reasons:

1. The dashboard's value is narrowing 4,000 bills down to ~50 that touch the platform. Title-quality is sufficient for that.
2. We've intentionally framed alignment as "auto-detected, low-confidence by default" — the system isn't claiming to read every bill, so we don't need richer text to be honest about what we know.
3. Building a scraper for richer text trades $0/month for ongoing maintenance burden against an upstream that's actively un-cooperative.
4. If officers actually use the dashboard and tell us titles aren't enough, we revisit with that signal in hand.

## The civic angle

This whole investigation surfaced a real transparency gap: PA bills are technically public, but their *meaning* is obscured by legal-amendment-style titles ("An Act amending the act of June 28, 1995, in section 12, further providing for…") with no obligation on the legislature to publish a plain-English summary in a structured, machine-readable form. The sponsor-memo PDFs exist but live behind a JS-rendered SPA that returns 403s to non-browser clients.

A citizen who wants to know what a given bill actually does has to:

1. Find the bill on a SPA that doesn't work without JavaScript
2. Click through to a PDF
3. Read 2-10 pages of cross-references to other acts

That's worth saying out loud on the methodology page — and it's a future advocacy lever for WTPPPA: PA could mandate plain-English summaries on bill listings, like several other states do. We've documented the data shape we'd need; if the law changes, the pipeline change to consume it is one afternoon's work.

## Re-evaluation triggers

Reopen this question if any of the following change:

- OpenStates announces PA abstracts are now populated (would show up in `?include=abstracts`)
- palegis.us publishes a public API or RSS feed
- Officers report titles are too sparse to make alignment calls during review
- A scraper-based competitor dashboard launches and pressures us to match
