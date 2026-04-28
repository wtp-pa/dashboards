# WTP-PA Dashboards

Civic accountability dashboards for the **We The People Party of Pennsylvania**. A monorepo for all WTP-PA tracking tools — currently hosting **PA Budget Watch**, with placeholders for Legislation Tracker, Legislator Scorecards, and Local Impact Dashboard.

**Live:**
- Portfolio landing: <https://dashboards.wtpppa.org/>
- PA Budget Watch: <https://dashboards.wtpppa.org/budget>
- Embed widget for Squarespace: <https://dashboards.wtpppa.org/budget/widget>

The dashboards are embedded in editorial pages on the main party site at <https://www.wtpppa.org> (under the "Watch" navigation). The Squarespace pages own all narrative copy; this repo owns the data and live components.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Astro 6 + React 19 islands + Tailwind 4 + TypeScript (strict) |
| Data store | JSON files in `data/` — versioned in git, no database |
| Data pipeline | Python 3.12 scripts in `pipeline/`, scheduled by GitHub Actions |
| Hosting | GitHub Pages (free, no vendor lock-in beyond GitHub itself) |

See `CONTRIBUTING.md` for stack rationale and the decision log.

## Local development

Requires Node 22+ (for the site) and Python 3.12+ (for the data pipeline).

```bash
# Install JS deps
npm install

# Run the dev server
npm run dev          # → http://localhost:4321

# Build for production
npm run build
npm run preview
```

For the data pipeline:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt

# Run the IFO publications scraper
python pipeline/fetch_ifo.py
```

## Deploying

**Auto-deploy on push to `main`.** The `.github/workflows/pages-deploy.yml` workflow builds Astro and deploys to GitHub Pages whenever `main` updates. Custom domain `dashboards.wtpppa.org` is configured via `public/CNAME`.

To manually trigger a deploy: GitHub repo → **Actions** → **Deploy to GitHub Pages** → **Run workflow**.

To check deploy status: <https://github.com/wtp-pa/dashboards/actions>.

## Data pipeline

`.github/workflows/data-pipeline.yml` runs every Monday at 06:00 UTC. It executes the Python scrapers, commits any updated JSON files in `data/`, and pushes to `main` — which triggers a fresh site deploy. The dashboard updates automatically when source data changes; no human in the loop unless a scraper breaks.

A scheduled health-check agent runs on **2026-05-18** to verify the IFO scraper is still functioning. If the scraper has gone stale (likely because IFO restructured their HTML), the agent will diagnose and open a PR with a fix.

## Common edits

| To change | Edit |
|---|---|
| Brand colors | `src/config.ts` AND `src/styles/global.css` (keep them in sync) |
| Party metadata (name, taglines, socials) | `src/config.ts` |
| Portfolio project list (add/remove/launch a project) | `src/config.ts` (`portfolio.projects` array) |
| Seed data (deficit projections, key stats, etc.) | `data/*.json` |
| Federal funds approximations | `data/federal-funds.json` |
| Pipeline schedule (e.g., daily instead of weekly) | `.github/workflows/data-pipeline.yml` cron |
| Adding a new project | See **Adding a new dashboard** below |

After any edit: `git push`. GitHub Actions handles the deploy.

## Adding a new dashboard

The portfolio is structured for new projects to slot in:

1. Add the project to `src/config.ts` (`portfolio.projects` array) with `status: 'coming-soon'`
2. Create `src/pages/<slug>/index.astro` for the full dashboard
3. Create `src/pages/<slug>/widget.astro` for the Squarespace embed
4. Add data files to `data/` (project-specific JSON)
5. Add scrapers to `pipeline/` if needed; wire into `.github/workflows/data-pipeline.yml`
6. Once shippable, flip `status: 'live'` in config
7. Create a corresponding Squarespace page under wtpppa.org/watch/

## Project layout

```
dashboards/
├── src/
│   ├── pages/
│   │   ├── index.astro              # portfolio landing (/)
│   │   └── budget/
│   │       ├── index.astro          # full PA Budget Watch (/budget)
│   │       └── widget.astro         # embed widget (/budget/widget)
│   ├── components/
│   │   ├── DeficitClock.tsx
│   │   ├── PersonalImpactCalculator.tsx
│   │   ├── RainyDayCountdown.tsx
│   │   ├── BudgetBreakdown.astro
│   │   ├── FederalContext.astro
│   │   └── IFOPublications.astro
│   ├── lib/
│   │   ├── format.ts                # currency / number formatters
│   │   └── fiscal.ts                # PA fiscal-year math
│   ├── styles/global.css            # Tailwind + brand color tokens
│   └── config.ts                    # all metadata (party, brand, projects)
├── data/                            # JSON, committed to git
│   ├── projections.json             # IFO 5-year structural deficit projections
│   ├── key-stats.json               # quick stats
│   ├── population.json              # Census PA totals
│   ├── revenue-sources.json         # General Fund revenue by category
│   ├── spending-by-category.json    # Spending by category
│   ├── federal-funds.json           # Federal flows + cliff scenarios
│   └── ifo-publications.json        # Auto-updated by scraper, weekly
├── pipeline/                        # Python data pipeline
│   ├── fetch_ifo.py                 # Scrapes ifo.state.pa.us publications
│   ├── fetch_openbookpa.py          # Stub
│   ├── fetch_census.py              # Stub
│   ├── requirements.txt
│   └── README.md
├── .github/workflows/
│   ├── pages-deploy.yml             # Builds + deploys site on push to main
│   └── data-pipeline.yml            # Weekly cron for scrapers
├── public/
│   ├── CNAME                        # GitHub Pages custom domain
│   └── wtp-logo.png                 # WTP-PA logo asset
├── docs/spec.md                     # PA Budget Watch original spec + Phase 4
└── CONTRIBUTING.md                  # Stack rationale, decision log, dont-do list
```

## Status

Currently live in `/budget`:
- Live deficit clock (FY 2025-26 accrued, ticking)
- Revenue + spending stacked-bar breakdowns
- Federal dependency section with cliff-risk scenarios
- Personal impact calculator (household-size-based)
- Rainy Day Fund countdown
- Latest IFO publications card (auto-refreshed weekly)

Planned (per `docs/spec.md` Phase 4):
- Budget vs. actual variance dashboard
- Top-vendor spending leaderboard
- Contract scrutiny (sole-source flags, no-bid awards)
- Spending citation trails

## License

MIT — see [LICENSE](./LICENSE).

## Built by

[We The People Party of Pennsylvania](https://www.wtpppa.org)
