# Contributing

This is a civic project built by a small WTP-PA volunteer team (effectively one technical maintainer + AI assistance). The goal is to keep the project **accessible** so any future technical volunteer can pick it up after a few hours of orientation, and so non-technical admins can update editorial content (which lives in Squarespace) without touching code.

## Stack rationale

We picked these specific technologies for specific reasons. Read this before proposing changes to the stack.

### Why Astro

- **Static-first** matches our workload: dashboards are mostly read-only, public, and slow-moving. Astro's "ship HTML, hydrate islands only when needed" model gives us small bundles and great Lighthouse scores by default.
- **React islands** for interactive components (deficit clock, calculator) without making the whole site a SPA.
- **TypeScript strict** out of the box.
- **Sole-maintainer velocity**: Astro is fast to scaffold, has minimal magic, and is well-supported.

### Why JSON files in `data/` (not a database)

- Our data is small (kilobytes), public, and slow-moving (monthly cadences at most).
- **Committing data to git gives a free audit trail** — `git log data/projections.json` shows when every number changed and who changed it. For an accountability project, that's a feature.
- **No SaaS dependency** = no cold-starts, no billing risk, no auth needed for scrapers, no migration risk.
- Supabase free-tier projects pause after a week of inactivity, which would be bad UX for a niche civic tool.

### Why GitHub Pages (not Vercel/Netlify/Cloudflare Pages)

- **$0**, totally generic — "git push to deploy" is universal
- **Native to GitHub** — same place the code lives, no second dashboard to learn
- **One platform** across the WTP-PA portfolio reduces bottleneck risk
- Custom domains supported (`*.wtpppa.org` subdomains)
- Astro static output runs there unchanged

If a future project needs serverless functions (e.g., Project 3 / legislation scanner with Claude API), revisit. Cloudflare Workers free tier is the most likely answer for that.

### Why Python for the data pipeline

- **Right tool for the job**: parsing Excel from IFO uses `openpyxl`/`pandas`; web scraping uses `requests`+`beautifulsoup4`.
- **Decoupled from the web build** — pipeline runs on GitHub Actions cron, commits JSON, the site rebuilds automatically. No coupling between data refresh and web hosting.

## Decision log

Things we tried, considered, or explicitly rejected — and why.

**Original spec proposed Next.js + Supabase + Vercel cron.** Rejected after analysis (`docs/spec.md` has the rewritten Tech Stack table). The workload is wrong for that stack: no users, no writes, no real-time, no auth. Astro + JSON in repo + cron in GitHub Actions is the simpler fit.

**LLM API integration in budget-watch.** Considered but blocked: WTP-PA doesn't have a party-funded Anthropic account, and we won't put paid API calls on the maintainer's personal billing. LLM features defer to Project 3 (Legislation Scanner) where the funding question gets resolved properly.

**Squarespace as the hosting platform.** Considered for accessibility / single-platform simplicity, but Squarespace is a closed CMS — it can't run Astro builds or serve arbitrary static sites. Resolved as a hybrid: Squarespace owns editorial pages (admin-editable), GitHub Pages hosts the live dashboards, embedded via iframe.

**Separate repos per project (multi-repo).** Considered, but rejected in favor of a monorepo. With a sole maintainer, isolation benefits don't outweigh the cost of N repos × N deploy configs. Monorepo means one place to look, shared brand config, shared component library, and faster ramp on new projects.

**Renaming `repo: wtp-budget-watch` → `dashboards`.** Done at the monorepo migration. GitHub auto-redirects the old URL.

## Don't-do list

These are real failure patterns we've already navigated. Avoid:

- ❌ **Don't propose paid APIs** without confirming party billing first. Personal-account billing for civic infrastructure isn't acceptable.
- ❌ **Don't add Next.js / Supabase / a database / a CMS layer** without strong justification. The current stack was chosen deliberately; bias is toward simplicity.
- ❌ **Don't reach for the "modern default" stack** without per-project justification. Different workloads warrant different choices.
- ❌ **Don't break the open-source forking story for project 1 (the voting platform)**, but for projects 2-4+ (dashboards), forking is aspirational; don't over-engineer for hypothetical other state parties.
- ❌ **Don't add features that admin-friendly Squarespace edits could handle.** If it's editorial copy, it belongs on Squarespace, not in code.
- ❌ **Don't commit changes without reviewing.** Diff carefully — this is the audit trail.

## How to add a new dashboard

See README.md `### Adding a new dashboard` for the recipe. Short version: add a project entry to `src/config.ts`, create `src/pages/<slug>/index.astro` and `src/pages/<slug>/widget.astro`, add data files, optionally add scrapers, and create a Squarespace page under `wtpppa.org/watch/`.

## Testing

We currently rely on:
- **Build-time TypeScript checks** (`npm run build` fails on type errors)
- **Astro's HTML/component validation** at build time
- **Production verification via curl** (after each deploy, fetch `https://dashboards.wtpppa.org/budget` and grep for expected content)
- **The scheduled health-check agent** (verifies the IFO scraper still works)

We don't have a unit-test suite or an integration-test framework. Adding one is fine when there's something subtle to test, but don't add testing infrastructure for its own sake — the components are mostly static rendering of JSON.

## Help / contact

Repo owned by [@ChristinaSCivics](https://github.com/ChristinaSCivics) (civic GitHub account). Issues, PRs, and questions welcome.

For non-technical questions about WTP-PA: <https://www.wtpppa.org>.
