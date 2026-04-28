# CLAUDE.md — WTP-PA Dashboards Monorepo

> Read this first. You're picking up a portfolio of civic accountability dashboards built by Christina (`@ChristinaSCivics`) for the **We The People Party of Pennsylvania**. The first dashboard (Budget Watch) is live; the next two — **Legislation Tracker** and **Elected Officials Watch** — are about to be built.

## Where you are

- **Local dir**: `/Users/xtina/Projects/WTP/wtp-budget-watch/` (the directory name is historical; the GitHub repo is now `wtp-pa/dashboards`. Optionally rename locally to match.)
- **GitHub repo**: <https://github.com/wtp-pa/dashboards>
- **Live site**: <https://dashboards.wtpppa.org>
- **Memory dir**: `/Users/xtina/.claude/projects/-Users-xtina-Projects-WTP/memory/` — read this on startup. It contains user profile, GitHub identities, brand info, project history, and behavioral feedback from prior sessions. Critical context lives there.

## Current state (April 28, 2026)

**Live** at `https://dashboards.wtpppa.org/`:
- `/` — portfolio landing with project cards
- `/budget` — full PA Budget Watch dashboard (live deficit ticker, revenue/spending breakdowns, federal context, cliff scenarios, personal impact calculator with multi-year projector, Rainy Day countdown, latest IFO publications, methodology page)
- `/budget/about` — methodology / how-this-works
- `/budget/widget` — compact embed widget for Squarespace

**Coming soon** (placeholder cards on the landing page, no routes yet):
- `/legislation` — Legislation Tracker
- `/elected-officials` — Elected Officials Watch (renamed from "Legislator Scorecards")
- `/local` — Local Impact

See `docs/roadmap.md` for detailed phase status.

## Your immediate task (most likely)

Christina is opening a new Claude Code window to start work on **Legislation Tracker** and **Elected Officials Watch**. Both projects slot into this monorepo at `/legislation` and `/elected-officials` following the same pattern as `/budget`.

Before scaffolding either:

1. **Read `docs/roadmap.md`** for the planned scope of each project
2. **Confirm the WTP-PA platform document** exists somewhere accessible — both projects depend on it as the basis for scoring. Christina mentioned having one but may need to share it. Ask if you don't see it in `shared-docs/` (private sibling repo at `~/Projects/WTP/shared-docs/`) or in this repo's `docs/`.
3. **Confirm the WTP-PA Anthropic API billing account exists** (NOT personal billing). The legislation/officials projects fundamentally need Claude API for platform-alignment scoring. This is a hard block — see `feedback_no_personal_funded_apis.md` in memory. If billing isn't ready, the pipeline can be built with stub responses for now, but no actual API calls until billing exists.
4. **Pick one bill or one official** to test the scoring on first. Score one well end-to-end before scaling.

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
- `.github/workflows/data-pipeline.yml` — weekly Monday cron that runs all Python scrapers and commits JSON updates

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
