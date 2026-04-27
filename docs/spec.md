# PA Budget Watch — Claude Code Project Spec

## What This Is

An interactive, embeddable budget accountability dashboard for the We The People (WTP) Party of Pennsylvania's website. Think usdebtclock.org but for PA state finances — a "deficit pin" for the web that makes Pennsylvania's fiscal crisis visceral, shareable, and impossible to ignore.

**Repo name:** `pa-budget-watch`

## Why This Matters

- PA has a **$3.9 billion structural deficit** in FY 2025-26, projected to grow to **$6.7 billion** in FY 2026-27 (per the Independent Fiscal Office)
- General Fund spending has grown **50% since FY 2018-19**, outpacing revenue growth by $5 billion
- The General Fund balance is projected to hit zero in FY 2025-26; the Rainy Day Fund could be drained by FY 2026-27
- Medicaid/Long-Term Living costs are growing **3x faster than revenue**
- No interactive, branded, state-level PA deficit tool exists from any political party or independent org — government portals (PennWATCH, OpenBookPA) show raw data with no narrative framing; the Commonwealth Foundation publishes great analysis but only as static blog posts/PDFs

## Tech Stack

> **Note:** This stack was revised during planning. The original spec proposed Next.js + Supabase + Vercel cron routes — those were re-evaluated against the actual workload (slow-moving data, fully public, no user accounts/writes) and replaced with the choices below. See the project README for rationale.

| Layer | Choice | Why |
|---|---|---|
| Framework | **Astro 6+ with React islands** | Static-first matches workload; ships less JS by default; islands for interactive parts (clock, calculator, charts) |
| Data store | **JSON files in repo** (`data/*.json`) | Data is small (KB), public, slow-moving; versioned and auditable in git; no SaaS dependency or cold-starts |
| Data pipeline | **Python scripts run by GitHub Actions cron** | Right tool for Excel parsing/scraping; decoupled from web hosting; logs and audit trail built into GitHub |
| Hosting | **Vercel (free tier)** for demo; iframe-embeddable in Squarespace | Free for low traffic; transferable to party-owned account later |
| Styling | **Tailwind CSS 4** | Fast, themeable, brand tokens centralized in `global.css` + `config.ts` |
| Charts | **Recharts + `d3-hierarchy`** for treemap | Standard React charts; D3 only where Recharts is weak |
| Frontend language | **TypeScript (strict)** | Type safety for financial data |
| Pipeline language | **Python 3.12** | Excel parsing (openpyxl), scraping (beautifulsoup), pandas for normalization |

**Target cost: $0/month** on free tiers.

## Data Sources (Priority Order)

### 1. PA Independent Fiscal Office (IFO) — Primary
- **What:** Monthly General Fund revenue actuals vs. estimates, fiscal outlook projections, structural deficit tracking
- **URL:** https://www.ifo.state.pa.us/
- **Data page:** https://www.ifo.state.pa.us/data.cfm (historical General Fund revenues as downloadable Excel/CSV)
- **Format:** Excel/CSV downloads + PDF reports
- **Automation approach:** Scheduled scraper checks the IFO data page monthly for updated files; parse Excel with a library like `xlsx`; store parsed data in Supabase
- **Key datasets:**
  - Historical General Fund Revenues (by tax type, by month)
  - Monthly revenue reports (actual vs. estimate)
  - Fiscal Outlook 5-year projections (revenue, expenditure, deficit)
  - Structural deficit briefs

### 2. PA Treasury — OpenBookPA
- **What:** Current fiscal year expenditures by department/fund, General Fund balance, vendor payments
- **URL:** https://www.patreasury.gov/openbookpa/
- **Format:** Web-rendered charts; underlying data may be scrapeable or available via hidden API endpoints (investigate during build)
- **Automation approach:** Check for API endpoints behind the OpenBookPA charts; if none, scrape key summary numbers on a schedule
- **Key datasets:**
  - Total expenditures by department
  - General Fund balance (current vs. prior year)
  - Revenue by classification

### 3. PA Open Data Portal (data.pa.gov) — Supplementary
- **What:** Various state datasets on Socrata platform with SODA API
- **URL:** https://data.pa.gov/
- **API:** Socrata/SODA REST API — JSON responses, no auth required for public datasets
- **Automation approach:** Direct API calls, easiest to automate
- **Usage:** Look for budget/finance datasets; this is the most developer-friendly source but may not have the fiscal headline numbers — cross-reference during build

### 4. Commonwealth Foundation — Reference/Context
- **What:** "Deficit Watch" monthly analysis, structural deficit breakdowns, spending growth analysis
- **URL:** https://commonwealthfoundation.org/research/ (search "deficit watch")
- **Format:** Blog posts with embedded data points
- **Usage:** Not for automated data ingestion — use as editorial reference for framing, key stats, and narrative context. Cite where appropriate. Their analysis aligns with WTP's fiscal accountability message.

### 5. U.S. Census / BLS — Supplementary
- **What:** PA population, household count (for per-family/per-capita calculations)
- **API:** Census API (free, key required)
- **Usage:** Calculate "deficit per PA family" and "deficit per taxpayer" figures

## Features to Build

### View 1: The Deficit Counter (Hero)
The marquee feature — a live-ticking counter showing PA's structural deficit growing in real time.

**How it works:**
- Take the IFO's annual structural deficit projection (e.g., $3.9B for FY 2025-26)
- Calculate a per-second growth rate based on the projected deficit expansion over the fiscal year
- Display as a large, animated, ticking number (like usdebtclock.org)
- Below the counter, show contextual stats:
  - **Per PA family of 4:** ~$1,500 (IFO's own figure for what it would cost to close the deficit)
  - **Per PA taxpayer:** calculated from deficit / number of tax filers
  - **Per second:** the deficit growth rate
  - **Days until Rainy Day Fund depletion:** countdown based on IFO projections

**Design notes:**
- This should feel urgent but credible — not alarmist conspiracy, but "these are the state's own numbers"
- Include a small "Source: PA Independent Fiscal Office" attribution
- Make it embeddable as an iframe snippet (provide embed code on the page)
- Dark background, large typography, the number is the star
- Shareable — generate an OG image with the current number for social media cards

### View 2: Where Your Money Goes (Spending Breakdown)
Interactive treemap or sunburst chart showing General Fund expenditures by department/category.

**Data source:** OpenBookPA expenditures by department + IFO spending breakdown

**Features:**
- Click/tap into categories to drill down (e.g., Human Services → Medicaid → Long-Term Living)
- Show year-over-year growth percentage for each category
- Highlight the fastest-growing categories (Medicaid, education) vs. revenue growth
- Toggle between current year and historical comparison (3-5 year trend)

**Key editorial callouts to surface:**
- Medicaid spending has grown 71% since 2018 (more than $5 billion increase)
- Long-Term Living growing 3x faster than revenue
- School districts holding $6.78 billion in reserves while state education funding increased $4.1B in 4 years
- $1.49 billion spent on corporate welfare programs

### View 3: Revenue vs. Spending Gap Tracker
Monthly line chart showing cumulative revenue vs. cumulative spending for the current fiscal year.

**Data source:** IFO monthly revenue reports + OpenBookPA expenditures

**Features:**
- Two lines: revenue (green) and spending (red)
- The gap between them filled/shaded in red — this IS the deficit, made visual
- Monthly data points with hover tooltips showing actual numbers
- Overlay the IFO's official revenue estimate as a dashed line so viewers can see if collections are above or below expectations
- Historical toggle to compare current FY to prior years

### View 4: Personal Impact Calculator
Interactive tool where PA residents enter basic info to see their personal stake.

**Inputs:**
- Household size (dropdown: 1, 2, 3, 4, 5+)
- County (dropdown — all 67 PA counties)
- Approximate household income range (bracket selector, not exact amount — privacy friendly)

**Outputs:**
- "Your family's share of the deficit: $X"
- "If the deficit were closed by tax increases, your family could pay an additional $X/year"
- "Your county receives $X in state funding" (if data available)
- Shareable card with their result

## Data Pipeline Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Sources    │     │  Next.js API      │     │  Supabase       │
│                  │     │  Routes (Cron)    │     │  (Postgres)     │
│  - IFO (Excel)   │────▶│                  │────▶│                 │
│  - OpenBookPA    │     │  /api/cron/       │     │  budget_data    │
│  - data.pa.gov   │     │  fetch-revenue    │     │  revenue_monthly│
│  - Census API    │     │  fetch-spending   │     │  spending_dept  │
│                  │     │  fetch-population │     │  projections    │
└─────────────────┘     └──────────────────┘     │  snapshots      │
                                                  └────────┬────────┘
                                                           │
                                                  ┌────────▼────────┐
                                                  │  Frontend       │
                                                  │  Components     │
                                                  │                 │
                                                  │  - DeficitClock │
                                                  │  - SpendingMap  │
                                                  │  - GapTracker   │
                                                  │  - Calculator   │
                                                  └─────────────────┘
```

### Cron Schedule
- **Daily:** Deficit counter interpolation (calculated client-side from stored projection data)
- **Monthly:** Fetch new IFO revenue report when published (~first week of each month)
- **Quarterly:** Refresh spending breakdown from OpenBookPA
- **Annually:** Update fiscal outlook projections, population data, per-family calculations

### Database Schema (Supabase)

```sql
-- Monthly revenue actuals from IFO
CREATE TABLE revenue_monthly (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fiscal_year text NOT NULL,          -- e.g., '2025-26'
  month_num int NOT NULL,             -- 1-12 (July=1 for PA fiscal year)
  month_name text NOT NULL,
  total_revenue_actual bigint,        -- in cents to avoid float issues
  total_revenue_estimated bigint,
  revenue_by_type jsonb,              -- { "personal_income_tax": 1234567890, "sales_tax": ... }
  variance bigint,                    -- actual minus estimated
  source_url text,
  fetched_at timestamptz DEFAULT now(),
  UNIQUE(fiscal_year, month_num)
);

-- Spending by department/category from OpenBookPA
CREATE TABLE spending_department (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fiscal_year text NOT NULL,
  department text NOT NULL,
  fund text DEFAULT 'General Fund',
  total_appropriation bigint,
  total_expenditure bigint,
  subcategories jsonb,                -- nested breakdown if available
  source_url text,
  fetched_at timestamptz DEFAULT now(),
  UNIQUE(fiscal_year, department, fund)
);

-- IFO projections and deficit data
CREATE TABLE fiscal_projections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  projection_date date NOT NULL,      -- when the IFO published this
  fiscal_year text NOT NULL,
  projected_revenue bigint,
  projected_expenditure bigint,
  projected_deficit bigint,
  general_fund_balance bigint,
  rainy_day_fund_balance bigint,
  source_url text,
  notes text,
  fetched_at timestamptz DEFAULT now()
);

-- Point-in-time snapshots for the deficit clock
CREATE TABLE deficit_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date date NOT NULL,
  structural_deficit bigint NOT NULL,
  deficit_per_capita bigint,
  deficit_per_family bigint,
  pa_population int,
  pa_households int,
  source text,
  created_at timestamptz DEFAULT now()
);

-- Key stats for display (admin-editable fallback)
CREATE TABLE key_stats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stat_key text UNIQUE NOT NULL,      -- e.g., 'current_deficit', 'rainy_day_balance'
  stat_value text NOT NULL,
  stat_label text,
  source_citation text,
  updated_at timestamptz DEFAULT now()
);
```

## Pages / Routes

- `/` — Hero deficit counter + summary stats + navigation to other views
- `/spending` — Spending breakdown treemap/sunburst
- `/revenue` — Revenue vs. spending gap tracker
- `/calculator` — Personal impact calculator
- `/about` — Methodology, data sources, update schedule, link to GitHub
- `/embed` — Instructions + iframe/script snippet for embedding on other sites
- `/api/cron/fetch-revenue` — Cron endpoint for IFO data
- `/api/cron/fetch-spending` — Cron endpoint for OpenBookPA data
- `/api/data/[dataset]` — Public JSON API for the cached data (so others can use it too)

## Design Direction

**Aesthetic:** Serious, credible, data-journalism feel — think ProPublica or The Marshall Project, not conspiracy blog. Dark mode default with high-contrast data. The numbers should feel like a newsroom ticker.

**Typography:** Use a monospace or tabular-lining font for the deficit counter (numbers need to not jump around as digits change). Clean sans-serif for body text.

**Color palette:**
- Background: near-black or very dark navy
- Deficit/negative numbers: red-orange (#E53E3E or similar)
- Revenue/positive: green (#38A169 or similar)
- Accent: WTP party branding color (make this a CSS variable for easy theming)
- Text: white/light gray on dark

**Branding:**
- WTP logo in header/footer
- "Built by We The People Party of PA" in footer
- "Data sourced from the PA Independent Fiscal Office and PA Treasury" — always visible
- All brand elements (colors, logo, party name) stored in a single `config.ts` for easy theming by other orgs

**Responsive:** Mobile-first. The deficit counter must look great on a phone screen — it's the most likely thing to be screenshotted and shared.

**Social sharing:**
- OG meta tags that show the current deficit number in the preview card
- A "Share this" button that generates a tweet/post with the current number
- The OG image should auto-update (use Vercel OG image generation)

## Embed Strategy

The widget should be embeddable on the WTP website and anywhere else. Provide:
1. **iframe embed** — simplest, works anywhere: `<iframe src="https://pa-budget-watch.vercel.app/embed/clock" width="100%" height="400">`
2. **Script tag embed** — for more integration: loads the React component into a target div
3. Multiple embed sizes: full dashboard, deficit clock only, mini badge (like the federal debt clock badge widgets)

## Open Source Considerations

- MIT license
- All party-specific config in `config.ts` (party name, colors, logo URL, state name)
- Data source URLs and scraper configs in a separate `data-sources.ts` so other states can swap in their own
- README with: what this is, live demo link, setup instructions, how to adapt for another state, data source documentation
- One-click Vercel deploy button in README

## Build Order (Suggested Phases)

### Phase 1: Foundation + Deficit Clock
1. Scaffold Next.js project with TypeScript, Tailwind, Supabase client
2. Set up Supabase schema (tables above)
3. Seed the database with current IFO data (manual initial load is fine):
   - Current structural deficit: $3.9B (FY 2025-26)
   - Projected deficit: $6.7B (FY 2026-27), $8.4B by FY 2029-30
   - PA population: ~13 million
   - PA households: ~5.1 million
   - Deficit per family of 4: ~$1,500
4. Build the deficit counter component with animated ticking
5. Build the home page with counter + key stats
6. Set up OG image generation
7. Deploy to Vercel

### Phase 2: Spending Breakdown + Gap Tracker
1. Build the data fetcher cron jobs (IFO revenue, OpenBookPA spending)
2. Build the spending treemap/sunburst visualization
3. Build the revenue vs. spending line chart
4. Add historical data toggle

### Phase 3: Calculator + Embed + Polish
1. Build the personal impact calculator
2. Build embed page with iframe/script snippets
3. Add social sharing features
4. Write the /about methodology page
5. Polish responsive design
6. Open source README and deploy button

### Phase 4: Accountability Layer (post-MVP)

Beyond making the deficit visceral, this layer makes the tool an actual watchdog. The data sources for this exist already (OpenBookPA, PennWATCH, PA eMarketplace, enacted budget PDFs) — the work is reconciliation, not access.

**Features to build:**
- **Budget vs. actual variance dashboard** — each line item's enacted appropriation vs. actual spend; overruns and underspends ranked
- **Top variances leaderboard** — top 10/20 line items where actual differs most from budget
- **Vendor spending leaderboard** — largest recipients of state payments by department, with year-over-year changes
- **Contract scrutiny** — new contract awards, sole-source flags, no-bid awards (from PA eMarketplace)
- **Fund balance tracker** — restricted/special funds with idle balances (extends the "school districts holding $6.78B in reserves" angle)
- **YoY line-item changes** — which specific programs grew or shrank, ranked
- **Spending citation trails** — click a number → see the actual source document or transaction it came from. Major credibility win for an accountability tool.

**The hard part is reconciliation:** line-item codes in enacted budget PDFs don't always cleanly map to expenditure codes in OpenBookPA. Building the mapping is real forensic work — expect to spend more time on data normalization than UI.

**Editorial standards needed:** judgments like "what counts as overspending vs. legitimate emergency reallocation" are the WTP point-of-view. Capture standards in a doc in `shared-docs/` so future editorial decisions are consistent.

## Key Reference Data Points (Seed Data)

Use these verified figures from IFO and Commonwealth Foundation reports to seed the initial database:

| Metric | Value | Source |
|---|---|---|
| FY 2025-26 structural deficit | $3.9 billion | IFO Budget Brief, Feb 2026 |
| FY 2026-27 projected deficit (no policy changes) | $6.7 billion | IFO Budget Brief, Feb 2026 |
| FY 2029-30 projected deficit | $8.4 billion | IFO Fiscal Outlook |
| FY 2025-26 General Fund spending | $50.09 billion | Enacted budget, Nov 2025 |
| FY 2025-26 General Fund net revenue | ~$45.3 billion | IFO/Commonwealth Foundation |
| General Fund spending growth since FY 2018-19 | 50% | IFO |
| Medicaid spending growth since 2018 | 71% (~$5B increase) | Commonwealth Foundation |
| Long-Term Living growth rate vs. revenue | 3x faster | IFO projection |
| School district reserves | $6.78 billion | Commonwealth Foundation |
| Rainy Day Fund balance | ~$7 billion | PA Treasury |
| Projected General Fund balance depletion | FY 2025-26 | IFO |
| Projected Rainy Day Fund depletion | FY 2026-27 | IFO |
| Deficit cost per family of 4 | ~$1,500 | IFO / Commonwealth Foundation |
| PA population | ~13 million | Census |
| Corporate welfare spending | $1.49 billion | Commonwealth Foundation |

## Non-Goals (Avoid Scope Creep)

- This is NOT a general-purpose data portal — it's an accountability tool with a point of view
- No user accounts or login (fully public)
- No real-time API connections to Treasury systems (we cache and refresh on schedule)
- No legislative tracking or bill analysis (different tool)
- No federal budget data (stay focused on PA state)
- Don't build a CMS — key stats can be updated via Supabase dashboard directly or via the admin seed script
