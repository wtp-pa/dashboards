# WTP-PA Dashboards — Roadmap

A living document of what's live, what's in progress, and what's planned across the dashboard portfolio. Updated as projects ship.

Last updated: 2026-04-29

---

## Portfolio at a glance

| Project | Slug / URL | Status | Notes |
|---|---|---|---|
| **PA Budget Watch** | `/budget` (live) | Phase 1+2 partial live | Live deficit clock, breakdowns, federal context, calculator, IFO publications, methodology |
| **PA Legislation Watch** | `/legislation` (live) | Live | OpenStates feed, keyword+TF-IDF matcher, editorial alignment. No LLM. |
| **PA Elected Officials Watch** | `/elected-officials` | Scaffolded, DEMO data | Pages render with 4 demo senators + synthetic votes. DEMO banner visible. Real OpenStates votes pending; landing card stays `coming-soon` until real data lands. |
| **Local Impact** | `/local` | Coming soon | County-level / district-level fiscal impact |

---

## PA Budget Watch — phase status

### Phase 1 — Foundation + Deficit Clock (✅ live)

- ✅ Live ticking deficit counter (FY 2025-26 accrued, IFO-anchored)
- ✅ Three at-a-glance stat cards ($1,500/family, 71% Medicaid growth, $6.78B school reserves)
- ✅ Personal Impact Calculator (household size + time horizon)
- ✅ Rainy Day Fund countdown
- ✅ Open Graph / Twitter share metadata
- ✅ Twitter/Facebook/Copy-link share buttons in hero

### Phase 2 — How money works (✅ live, partial)

- ✅ Revenue sources stacked-bar breakdown (5 categories, sourced to IFO)
- ✅ Spending category stacked-bar breakdown (5 categories, sourced to Office of the Budget)
- ✅ Plain-language framing paragraphs
- 🟡 Department-level drill-down treemap (planned — needs more granular data)
- 🟡 Revenue vs. spending over time (line chart, planned — needs monthly time-series fetcher)
- 🟡 Year-over-year change tracker for top categories (planned)

### Phase 3 — Federal context + calculators (✅ live)

- ✅ Federal funds breakdown (~$50B flowing into PA, 5 program categories)
- ✅ Cliff scenarios (FMAP cut, ACA expansion repeal, SNAP cost-shift)
- ✅ Compounding multi-year projector in Personal Impact Calculator
- ✅ Methodology page at `/budget/about`
- 🟡 Per-county impact selector (planned — needs county-level data or per-capita approximation)
- 🟡 USAspending.gov live fetcher to replace federal-funds approximations (planned)

### Phase 4 — Accountability layer (planned)

This is where the dashboard becomes a watchdog tool, not just a data viewer. Significant work; sequenced after `legislation` and `elected-officials` projects scaffold.

- 🟡 **Budget vs. actual variance dashboard** — each line item's enacted amount vs. actual spend; overruns ranked
- 🟡 **Top variances leaderboard** — top 10/20 line items where actual differs most from enacted
- 🟡 **Vendor spending leaderboard** — largest recipients of state payments by department, year-over-year
- 🟡 **Contract scrutiny** — sole-source flags, no-bid awards from PA eMarketplace
- 🟡 **Fund balance tracker** — restricted/special funds with idle balances
- 🟡 **Spending citation trails** — click a number → see source document/transaction

Reconciliation between enacted-budget line items (in PDFs from the General Assembly) and actual expenditures (in OpenBookPA) is the hard part. Expect more time on data normalization than UI.

### Live-data infrastructure (cross-cutting)

- ✅ IFO publications scraper — runs weekly via GitHub Actions, commits JSON to repo
- ✅ Scheduled health-check agent (May 18, 2026) to verify scraper still works
- 🟡 IFO monthly revenue parser (Phase 2)
- 🟡 OpenBookPA scraper for current spending (Phase 2-4)
- 🟡 USAspending.gov SODA API fetcher for federal flows (Phase 3 enhancement)
- 🟡 PA eMarketplace scraper for contracts (Phase 4)

---

## Legislation Tracker — planned

The accountability tool that scores PA bills against the WTP-PA platform. Funded by Claude API (pending WTP-PA party billing — not personal account).

Approach (from prior planning):
- Python or TypeScript CLI/script first, no web UI on day 1
- Anthropic API with prompt caching: WTP platform doc as cached prefix; each bill as variable suffix
- SQLite to start, defer Postgres until volume needs it
- Score output: alignment score, reasoning, named sponsors, district impact
- Once scoring works, build `/legislation` dashboard route + widget

Blockers:
- WTP-PA needs its own Anthropic API billing account (don't use personal billing)
- Need the WTP-PA platform document as the canonical text to score against
- Need a sample PA bill for initial testing

Hosting note: when this ships a UI, the static dashboard pages live on GitHub Pages alongside `/budget`. The serverless API endpoint (calling Claude API) needs Cloudflare Workers free tier or similar — GH Pages doesn't run server code.

## Elected Officials Watch — scaffolded with DEMO data

Pages, components, and scoring pipeline all built. Landing page (`/elected-officials/`) has roster, ZIP/county lookup, and per-pillar alignment summary; per-legislator pages (`/elected-officials/[id]/`) show the score, pillar breakdown, and vote history with bill links.

**Live now (in build):**
- ✅ Roster with 4 real PA senators (public roster data only)
- ✅ Synthetic DEMO votes — visible gold banner on every page warns the data is fabricated
- ✅ `pipeline/elected-officials/score_officials.py` — joins votes × bills.matchedPositions × manual_review.alignment → per-pillar scorecards
- ✅ ZIP/county lookup — ~10 demo PA ZIPs covering the 4 senate districts in the seed roster
- ✅ `noindex` meta on all routes; `src/config.ts` portfolio entry pinned to `coming-soon`

**Pending (in order):**
- 🟡 Lift OpenStates client to `pipeline/_shared/openstates.py` (currently lives in `pipeline/legislation/fetch_bills.py:103-172`)
- 🟡 Wire `fetch_officials.py` to OpenStates `/people?jurisdiction=pa`
- 🟡 Wire `fetch_votes.py` to OpenStates `/bills?jurisdiction=pa&include=votes`
- 🟡 Replace `votes.json` with real data; flip `demoData: false`
- 🟡 Expand `zip-districts.json` to all PA ZIPs
- 🟡 Flip `src/config.ts` to `live`, drop `noindex`

**Reuses (do not duplicate):** `data/legislation/platform.json`, `data/legislation/manual_review.json`, `data/legislation/bills.json` are read directly. The legislation matcher's outputs (`bill.matchedPositions`) drive per-pillar attribution.

## Local Impact — planned

County-level / district-level dashboards showing how state policy affects specific PA communities.

Likely scope:
- Per-county fiscal share of the deficit
- Per-county federal funds inflows
- District-by-district legislator alignment with local needs
- "Your county receives $X in state funding; your senator voted Y on the budget"

---

## How phases get shipped

Each phase ships through the same loop:

1. Pull the next data source (or research what's available)
2. Add a Python fetcher in `pipeline/<project>/`
3. Wire to `.github/workflows/data-pipeline.yml`
4. Build the UI components
5. Add to the project's page route
6. Build, commit, push (GH Pages deploys automatically)
7. Verify, iterate

When a project goes from "coming-soon" to "live," flip its `status` in `src/config.ts` so it gets a real link on the portfolio landing page.
