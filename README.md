# PA Budget Watch

Interactive budget accountability dashboard for the **We The People Party of Pennsylvania**. Tracks PA's structural deficit, spending, and (Phase 4) line-item budget-vs-actual variance.

Inspired by usdebtclock.org but for PA state finances — and with editorial framing that aligns with WTP-PA's fiscal accountability platform.

> **Status:** scaffold complete; Phase 1 (deficit clock + key stats) not yet built. Landing page is a "this project lives" placeholder using seed data from the spec.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Astro 6 + React 19 islands + Tailwind 4 + TypeScript (strict) |
| Data store | JSON files in `data/` — versioned in git, no database |
| Data pipeline | Python 3.12 scripts in `pipeline/`, scheduled by GitHub Actions |
| Hosting | Vercel free tier (demo); iframe-embeddable on the WTP-PA Squarespace site later |

**Why this stack instead of Next.js + Supabase + Vercel cron** (the spec's original proposal): the workload is mostly-static, public, and slow-moving. Supabase free-tier projects pause after 1 week of inactivity (bad for a niche civic tool). Putting cron in Next.js API routes couples data fetching to web hosting. Python is the right tool for parsing IFO Excel files and scraping PA Treasury. JSON in git gives a free audit trail. See `docs/spec.md` for the full rationale.

## Local development

Requires Node 22+ and (for the pipeline) Python 3.12+.

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
python pipeline/fetch_ifo.py   # all fetchers are stubs for now
```

## Project layout

```
wtp-budget-watch/
├── src/
│   ├── pages/index.astro       # landing page
│   ├── components/             # React islands (charts, clock, calculator)
│   ├── styles/global.css       # Tailwind + brand color tokens
│   ├── lib/                    # shared TS utilities
│   └── config.ts               # brand + party metadata (edit when forking)
├── data/                       # JSON output from pipeline (committed)
│   ├── projections.json        # IFO 5-year structural deficit projections
│   ├── key-stats.json          # quick stats (deficit per family, depletion dates)
│   └── population.json         # Census PA population/households
├── pipeline/                   # Python data fetchers
│   ├── fetch_ifo.py
│   ├── fetch_openbookpa.py
│   ├── fetch_census.py
│   ├── requirements.txt
│   └── README.md
├── .github/workflows/
│   └── data-pipeline.yml       # monthly cron + manual trigger
├── docs/spec.md                # full project spec including Phase 4
├── public/wtp-logo.png         # WTP-PA logo
└── README.md
```

## Deploy to Vercel (demo)

1. Sign up at vercel.com using your **civic GitHub account** (not your personal or business account)
2. Click **New Project**, import `wtp-pa/wtp-budget-watch`
3. Vercel auto-detects Astro — no config needed
4. Deploy → get a URL like `wtp-budget-watch-xyz.vercel.app`
5. Share that URL with party officers for the demo

To embed on the wtpppa.org Squarespace site later: add a Code Block with `<iframe src="https://your-vercel-url" width="100%" height="600">`. No migration needed.

## Forking for another state party

This project is open-source so other state parties can adapt it for their state's budget data.

Edit:

1. **`src/config.ts`** — your party name, colors, socials, logo
2. **`data/*.json`** — your state's projections, stats, population
3. (eventually) **`pipeline/`** — fetchers for your state's official data sources

The architecture stays the same.

## License

MIT — see [LICENSE](./LICENSE).

## Built by

[We The People Party of Pennsylvania](https://www.wtpppa.org)
