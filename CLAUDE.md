# CLAUDE.md — WTP-PA Dashboards Monorepo

> Read this first. You're picking up a portfolio of civic accountability dashboards built by Christina (`@ChristinaSCivics`) for the **We The People Party of Pennsylvania**. The first dashboard (Budget Watch) is live; the next two — **Legislation Tracker** and **Elected Officials Watch** — are about to be built.

## Where you are

- **Local dir**: `/Users/xtina/Projects/WTP/dashboards/`
- **GitHub repo**: <https://github.com/wtp-pa/dashboards>
- **Live site**: <https://dashboards.wtpppa.org>
- **Memory dir**: `/Users/xtina/.claude/projects/-Users-xtina-Projects-WTP/memory/` — read this on startup. It contains user profile, GitHub identities, brand info, project history, and behavioral feedback from prior sessions. Critical context lives there.

## Current state (May 12, 2026)

**Live** at `https://dashboards.wtpppa.org/`:
- `/` — portfolio landing
- `/budget` (+ `/budget/about`, `/budget/widget`) — full PA Budget Watch dashboard

**Pre-release** — render in build, listed on the landing page with `pre-release` status, but a gold "PRE-RELEASE" banner sits on top and pages are `noindex` until officers sign off:
- `/legislation` (+ `/legislation/about`) — Live OpenStates feed, keyword + TF-IDF matcher with per-match evidence, editorial alignment in `manual_review.json`. **No Claude API in the loop.** Gated by `config.legislation.officersApprovedData`.
- `/elected-officials` (+ `/elected-officials/[id]`) — Real OpenStates data flowing as of 2026-04-29: **251 PA legislators, 21,999 votes across 205 officials, full scorecards.** The original demo data (4 hand-seeded senators) is gone — `votes.json:demoData` is `false` and the auto-flip portion of the banner is satisfied. What's still gating "live" is `config.electedOfficials.officersApprovedData` (manual gate, awaiting officer review). Do **not** flip it without explicit user confirmation that officers have signed off.

**Coming soon** (placeholder card, no routes):
- `/local` — Local Impact

See `docs/roadmap.md` for detailed phase status.

### How the gates work

There are two layered flags driving the pre-release UX:

1. **`votes.json:demoData`** (automatic) — set to `false` by `fetch_votes.py` once real OpenStates votes are written. Already flipped.
2. **`config.{electedOfficials,legislation}.officersApprovedData`** in `src/config.ts` (manual) — flip to `true` only after WTPPPA officers have reviewed the live-data dashboard and approved it for public consumption.

When the banner disappears, also drop the `<meta name="robots" content="noindex" />` lines on the affected pages and switch the corresponding `portfolio.projects[].status` to `"live"`.

## Open work — pick this up next

Most of the foundational EO work that this file used to describe is done. What's left:

1. **Wait for officer sign-off**, then promote both `/legislation` and `/elected-officials` to live: flip both `officersApprovedData` flags in `src/config.ts`, drop `<meta name="robots" content="noindex" />` from the four affected pages, switch the corresponding `portfolio.projects[].status` to `"live"`.
2. **Expand `data/elected-officials/zip-districts.json`** beyond the small hand-curated set toward full coverage (PASDA boundaries → ZIP overlay, or a precomputed source). The runtime fallback (OpenStates `/people.geo` at the county centroid) covers gaps, but a precomputed map is faster and more reliable.
3. **`/local` (Local Impact)** — still a portfolio placeholder. Phase 4 candidate.

**Defer (don't pre-extract):**
- The TF-IDF/keyword matcher in `match_bills.py` — likely useful for a future candidate tool, but premature extraction is harder to undo than late extraction.
- Editorial-review generalization beyond bills — EO scoring is mechanical (yea/nay × aligned/opposed); only add `data/elected-officials/manual_review.json` when an editor actually wants to override a vote interpretation.
- A self-service editorial admin (Decap CMS, custom CLI, etc.) — Christina is sole editor; JSON-via-PR is fine until that changes.

## Cross-window git hygiene — important

Christina sometimes runs **two Claude Code windows in parallel** on this repo (one per dashboard). On 2026-04-28, the legislation window committed with `git add -A` and accidentally pulled untracked elected-officials files into a "Legislation: live OpenStates feed" commit (93f842d). Files survived but the EO work is misattributed. **The `feedback_no_git_add_all.md` memory rule must be honored** — stage specific paths only. If you see untracked files in another dashboard's directory, those belong to the other window.

## File-structure conventions for new projects

The monorepo is set up so adding `legislation/` and `elected-officials/` is mostly a copy-paste of the budget pattern:

```
src/pages/legislation/
  index.astro       # full Legislation Tracker dashboard
  widget.astro      # compact embed widget
  about.astro       # (optional) methodology page

src/pages/elected-officials/
  index.astro
  widget.astro
  about.astro

src/components/                   # currently flat — budget components live here
  DeficitClock.tsx                # generic enough to reuse if needed
  PersonalImpactCalculator.tsx    # budget-specific
  ...
  legislation/                    # NEW — project-specific components
    BillCard.tsx
    ScoreBadge.tsx
    ...
  elected-officials/              # NEW
    OfficialCard.tsx
    VoteHistory.tsx
    ...
  shared/                         # (CREATE THIS once components actually need to be shared)
    SiteHeader.astro
    SiteFooter.astro
    ShareRow.astro

data/
  projections.json                # budget-specific
  ifo-publications.json           # budget-specific (auto-updated)
  ...
  legislation/                    # NEW — bills, scores, platform doc
    bills.json
    scores.json
    platform.md (or .json)
  elected-officials/              # NEW
    officials.json
    votes.json
    scores.json

pipeline/                         # currently flat for budget scrapers
  fetch_ifo.py                    # budget-specific
  fetch_openbookpa.py             # budget-specific (stub)
  fetch_census.py                 # budget-specific (stub)
  legislation/                    # NEW
    fetch_bills.py                # scrape PA General Assembly
    score_bills.py                # call Claude API to score against platform
    requirements.txt
  elected-officials/              # NEW
    fetch_officials.py            # scrape officials list
    fetch_votes.py                # voting records
    score_officials.py
    requirements.txt
```

When you create the first new project, also create the `src/components/<slug>/` and `data/<slug>/` and `pipeline/<slug>/` subdirs even if mostly empty — establishes the pattern so the next project follows it cleanly.

If a component genuinely needs to be shared across projects (e.g., site header), promote it to `src/components/shared/` rather than duplicating.

## Stack — locked, do not propose changes without strong justification

| Layer | Choice |
|---|---|
| Frontend | Astro 6 + React 19 islands + Tailwind 4 + TypeScript (strict) |
| Data store | JSON files in `data/`, versioned in git, no database |
| Data pipeline | Python 3.12 in `pipeline/`, scheduled by GitHub Actions cron |
| Hosting | GitHub Pages (auto-deploy on push to `main` via `.github/workflows/pages-deploy.yml`) |
| Custom domain | `dashboards.wtpppa.org` (CNAME in `public/CNAME`) |

For Legislation Tracker / Elected Officials Watch specifically:
- The static dashboard pages live on GitHub Pages alongside `/budget`
- The serverless API for Claude API calls (if needed at runtime, not just build-time) needs **Cloudflare Workers free tier** — GitHub Pages doesn't run server code. Decide at scaffolding time whether to call Claude API at build-time-only (cheap, simpler) or runtime (needs Workers).
- **Default to build-time scoring** — score bills/officials in the GitHub Actions cron, commit results to JSON. Only add runtime API if you need user-typed queries (e.g., "ask the dashboard" feature) which is currently blocked anyway.

## User constraints — these are firm

1. **$0/month operating cost.** No paid Supabase, no paid Vercel, no paid LLM credits beyond what WTP-PA itself funds. The user will not put paid API calls on personal billing — see `feedback_no_personal_funded_apis.md` in memory.
2. **Sole maintainer.** Christina is the only engineer. Stack and decisions optimize for solo velocity. Open-source forking is aspirational, not load-bearing.
3. **Bottleneck-resistant.** The CEO has explicitly flagged concerns about IT bottlenecks (Libertarian Party cautionary tale). Editorial content should live in code where possible (NOT Squarespace — Squarespace UI is too painful for her). Documentation should be strong enough for handoff.
4. **Don't reach for default LLM-suggested stacks** without per-project justification. Past sessions have flagged "vibe coding" pushback — see `feedback_stack_bias.md` in memory.

## Brand

Pulled from wtpppa.org Squarespace Site Styles:
- Navy `#15184E` — primary brand
- Sky `#7EC7DA` — primary accent
- Indigo `#2E3279` — secondary accent
- Cream `#F5F2E8` — body text warmth
- Gold `#D4B962` — logo-stripe color, kept available
- Red `#C8262C` — deficit/danger
- Page bg `#08091F`, surface `#1B1F5E` (lifted slightly from brand navy for elevation)
- Font: **Poppins** loaded from Google Fonts via `src/styles/global.css`

Dark mode is the dashboard's permanent design choice — visual contrast with the light wtpppa.org site reinforces "this is the data view," not editorial. Don't propose switching to light mode without an explicit user request.

The official brand kit was matched directly from Squarespace Site Styles screenshots; if officers later provide a more polished kit (SVG logo, exact PSD, official font specs), update `src/config.ts` and `src/styles/global.css` together.

## Identity (for git config and PRs)

- Civic GitHub identity: `ChristinaSCivics` / `kennedy24chesco@gmail.com`
- Per-repo `git config user.name`/`user.email` are already pinned in this clone — verify with `git config user.email` if in doubt
- Christina maintains separate work and business GitHub identities (jupiterdigitalcs); never propose using anything other than the civic identity for WTP-PA work

## What NOT to do

- ❌ Don't propose paid APIs (Claude, OpenAI, etc.) without confirming WTP-PA billing exists
- ❌ Don't reach for Next.js / Supabase / a database / a CMS layer without strong project-specific justification
- ❌ Don't migrate frameworks (Astro stays)
- ❌ Don't propose hosting on Vercel (we migrated to GitHub Pages for vendor neutrality)
- ❌ Don't try to host code on Squarespace — it's a closed CMS, won't run Astro
- ❌ Don't propose embedding editorial copy in Squarespace pages — Christina rejected that workflow as too painful
- ❌ Don't auto-commit; ask first
- ❌ Don't add `text-white/N` for body text — use `text-wtp-cream/N` for warmth (consistent with current code)
- ❌ Don't add features beyond what's asked. Sole-maintainer velocity > completeness.

## Open Issues / TODOs

- **Logo SVG**: Christina couldn't extract from Squarespace asset library. Current `public/wtp-logo.png` is a converted WebP. If she ever gets the source SVG, swap it in.
- **Brand kit refinement**: colors are eyeballed from Squarespace screenshots. If officially supplied, replace `APPROXIMATE` references in `src/config.ts` and update `src/styles/global.css`.
- **Vercel parallel deployment** at `wtp-budget-watch.vercel.app` is still active as a fallback. Disconnect when GitHub Pages deploy has been stable for a few weeks.
- **`legislation-scanner` repo** (separate, originally created as standalone) is now obsolete. The Legislation Tracker work has moved into this monorepo. The standalone repo can be archived once the monorepo version exists.

## Useful files when getting oriented

- `README.md` — public-facing project overview
- `CONTRIBUTING.md` — stack rationale, decision log, don't-do list
- `docs/roadmap.md` — phase tracking for budget + planned work for legislation/elected-officials/local
- `docs/spec.md` — original PA Budget Watch spec (with stack revision and Phase 4 added)
- `src/config.ts` — single source of truth for party metadata, brand, project list
- `src/styles/global.css` — Tailwind theme tokens
- `.github/workflows/pages-deploy.yml` — GH Pages build/deploy
- `.github/workflows/data-pipeline.yml` — **weekly** Monday cron for free, rate-limit-free sources (IFO, OpenBookPA, Census)
- `.github/workflows/data-pipeline-openstates.yml` — **monthly** (1st of month) cron for OpenStates-backed data (bills, officials, votes, scoring). Split out 2026-05 because weekly polling chronically tripped 429s on the free tier; PA roll-call activity is bursty enough that monthly matches the actual rhythm. Use `workflow_dispatch` on this workflow to refresh on demand around big floor action (budget season, end-of-session sprints).

## Scheduled agents

- **2026-05-18 13:00 UTC** — IFO scraper health-check (one-shot remote agent). Reads `data/ifo-publications.json`, cross-checks against IFO's live site, opens a PR with a fix if the scraper has gone stale. Routine ID: `trig_01PkEc1TFeSnTaEpthqE5qks`.

## Quick wins to verify the project still works

```bash
# Local dev
npm install
npm run dev   # → http://localhost:4321

# Build
npm run build

# Test the scraper
pip install -r pipeline/requirements.txt
python pipeline/fetch_ifo.py

# Trigger a fresh deploy
git push    # GH Pages auto-deploys on push to main
```

If anything is broken at startup, start with `git status` and `git log --oneline -10` to see what landed recently. The most recent significant work was the brand polish + CTA + compounding projector + methodology page (commit before this handoff).

Good luck.
