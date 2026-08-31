---
name: seo
description: "Comprehensive SEO analysis for any website or business type. Full site audits, single-page analysis, technical SEO (crawlability, indexability, Core Web Vitals with INP), schema markup, content quality (E-E-A-T), image optimization, sitemap analysis, and GEO for AI Overviews/ChatGPT/Perplexity. Industry detection for SaaS, e-commerce, local, publishers, agencies. Triggers on: SEO, audit, schema, Core Web Vitals, sitemap, E-E-A-T, AI Overviews, GEO, technical SEO, content quality, page speed."
user-invocable: true
argument-hint: "[command] [url]"
license: MIT
metadata:
  author: jishhnnuu
  version: "1.5.2"
  category: seo
---

# SEO: Universal SEO Analysis Skill

**Invocation:** `/seo $1 $2` where `$1` is the command and `$2` is the URL or argument.

**Runtime:** Run bundled Python tools through `claude-seo run <script.py>`. Plugin
installs expose this command automatically. Repository users run
`./bin/claude-seo`; manual installers rewrite the command to the isolated
launcher path. Never invoke bundled scripts with a bare Python interpreter.

Comprehensive SEO analysis across all industries (SaaS, local services,
e-commerce, publishers, agencies). Orchestrates 27 sub-skills (23 core + 1 growth-loop onboarding + 1 framework
integration + 2 extension mirrors), 18 audit sub-agents, 2 site-wide
review agents, 1 confirmed-fix writer, 1 content writer, and 5 growth-loop
agents. A separate optional Firecrawl
extension is also installable (see "Optional Extensions" below).

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/seo audit <url>` | Full website audit with parallel subagent delegation |
| `/seo page <url>` | Deep single-page analysis |
| `/seo sitemap <url or generate>` | Analyze or generate XML sitemaps |
| `/seo schema <url>` | Detect, validate, and generate Schema.org markup |
| `/seo images <url or optimize>` | Image SEO: on-page audit, SERP analysis, file optimization |
| `/seo technical <url>` | Technical SEO audit (9 categories) |
| `/seo content <url>` | E-E-A-T and content quality analysis |
| `/seo content-brief <topic or url>` | Generate detailed SEO content brief with target keywords, outline, internal links |
| `/seo geo <url>` | AI Overviews / Generative Engine Optimization |
| `/seo plan <business-type>` | Strategic SEO planning |
| `/seo programmatic [url\|plan]` | Programmatic SEO analysis and planning |
| `/seo competitor-pages [url\|generate]` | Competitor comparison page generation |
| `/seo local <url>` | Local SEO analysis (GBP, citations, reviews, map pack) |
| `/seo maps [command] [args]` | Maps intelligence (geo-grid, GBP audit, reviews, competitors) |
| `/seo hreflang [url]` | Hreflang/i18n SEO audit and generation |
| `/seo google [command] [url]` | Google SEO APIs (GSC, PageSpeed, CrUX, Indexing, GA4) |
| `/seo backlinks <url>` | Backlink profile analysis (free: Moz, Bing, CC; premium: DataForSEO) |
| `/seo cluster <seed-keyword>` | SERP-based semantic clustering and content architecture |
| `/seo sxo <url>` | Search Experience Optimization: page-type analysis, user stories, personas |
| `/seo drift baseline <url>` | Capture SEO baseline for change monitoring |
| `/seo drift compare <url>` | Compare current state to stored baseline |
| `/seo drift history <url>` | Show drift history over time |
| `/seo ecommerce <url>` | E-commerce SEO: product schema, marketplace intelligence |
| `/seo firecrawl [command] <url>` | Full-site crawling and site mapping (extension) |
| `/seo dataforseo [command]` | Live SEO data via DataForSEO (extension) |
| `/seo image-gen [use-case] <description>` | AI image generation for SEO assets (extension) |
| `/seo onboard [url]` | Set up the autonomous Growth Loop on a website's repo |
| `/seo flow [stage] [url\|topic]` | FLOW framework: evidence-led prompts for Find, Leverage, Optimize, Win, or Local stages |
| `/seo setup` | Explicitly create or refresh the isolated Python runtime and Chromium |
| `/seo doctor` | Check runtime readiness without changing the system |

## Runtime Setup

Run setup only when the user explicitly invokes `/seo setup` or explicitly asks
to repair dependencies. Execute `claude-seo setup`, report core and Chromium
status separately, and do not fall back to global or user package installation.
For diagnosis, execute `claude-seo doctor --json`; its output intentionally omits
absolute paths and environment values. If any `claude-seo run` command reports
that setup is required, suggest `/seo setup` and do not improvise a `pip install`.

## Pre-Flight Capability Check (mandatory, before ANY analysis command starts)

**Never silently settle for whatever free-tier/lab-only method happens to be
configured, and never ask about it mid-audit either.** Do exactly one
capability scan and exactly one confirmation, both before any crawling,
fetching, or analysis begins — not zero (silently defaulting to basic) and
not several (interrupting the audit repeatedly).

1. **Scan what's actually available** — run these, don't guess from memory:
   - `claude-seo run google_auth.py --tier` — API key (PSI/CrUX lab+field
     data), service account (GSC/Indexing), GA4 property
   - `claude-seo run backlinks_auth.py --tier` — Moz/Bing backlink APIs
   - Check `~/.claude/skills/` for installed extension directories:
     `seo-ahrefs`, `seo-dataforseo`, `seo-firecrawl`, `seo-profound`,
     `seo-seranking`, `seo-bing`, `seo-unlighthouse`, `seo-screaming-frog`
   - Check env vars relevant to live checks: `GEMINI_API_KEY`,
     `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY` (live AI
     citation checking — see seo-geo), `GOOGLE_CSE_API_KEY`/`GOOGLE_CSE_ID`
     (voice-search live check)
   - If you're aware of a materially better data source or method for this
     specific audit than what's configured or than this repo's hardcoded
     default path — a newer API, a free tier the user likely qualifies for,
     a more accurate technique — surface it here too. Don't silently use the
     lesser default, and don't wait until after the audit starts to mention it.

2. **Present one consolidated summary and ask once.** Table format: what's
   configured (and therefore what quality of data the audit will use for
   it), what's missing (and exactly what it would upgrade), and a one-line
   setup pointer for each gap. Example shape:

   | Capability | Status | If missing, audit uses instead |
   |---|---|---|
   | PSI/CrUX real-user field data | ✅ configured / ❌ not set | Lab-only Lighthouse via Unlighthouse (no real-user LCP/INP/CLS) |
   | Backlink index | ✅ Ahrefs / ⚠️ free-tier (Moz/Bing/CC) only | Smaller, slower-refreshed link graph |
   | Live AI-citation check | ✅ N provider(s) / ❌ none | GEO score stays proxy-only (no live citation) |

   End with one question: proceed now with what's configured, or pause to
   add any of the missing pieces first? Wait for that single answer, then
   run the entire audit through to completion without further permission
   stops for capability choices already covered by this checklist.

3. **Once confirmed, always use the best available method — automatically.**
   If a capability is configured, use it; don't fall back to its free/basic
   sibling out of habit. Concretely: if `GOOGLE_API_KEY` is set, use real
   PSI+CrUX field data, not Unlighthouse-only; if `seo-ahrefs` is installed,
   prefer it over the free Moz/Bing/Common-Crawl combination for backlink
   depth; if any of `GEMINI_API_KEY`/`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/
   `PERPLEXITY_API_KEY` are set, run `live_citation_check.py` against all
   configured providers, not just whichever is free; if `seo-screaming-frog`
   is installed and the site is large, prefer it over the ~500-page cap.

## Orchestration Logic

When the user invokes `/seo audit`, run the Pre-Flight Capability Check
above first, then delegate to subagents in parallel:
1. Detect business type (SaaS, local, ecommerce, publisher, agency, other)
2. Spawn subagents: seo-technical, seo-content, seo-schema, seo-sitemap, seo-performance, seo-visual, seo-geo
3. If Google API credentials detected (`claude-seo run google_auth.py --check`), also spawn seo-google agent
4. If local business detected, also spawn seo-local agent
5. If local business detected AND DataForSEO MCP available, also spawn seo-maps agent
6. If backlink APIs detected (`claude-seo run backlinks_auth.py --check`), also spawn seo-backlinks agent
7. If Firecrawl MCP available, use `firecrawl_map` to discover all site URLs before analysis
8. If content strategy signals detected (blog, pillar pages, topic clusters), also spawn seo-cluster agent
9. If e-commerce detected, also spawn seo-ecommerce agent
10. If drift baseline exists for this URL (`claude-seo run drift_history.py <url>`), also spawn seo-drift agent
11. Always include seo-sxo in full audits (search experience applies to all sites)
12. Collect results and generate unified report with SEO Health Score (0-100)
13. **Synthesize via the 10-principle framework** (see "Synthesis Methodology" below), walk PERCEIVE → ANALYZE → VALIDATE → ACT before bucketing findings into Critical / High / Medium / Low
14. Create prioritized action plan with dependency sequencing + falsifiability per recommendation
15. **Offer PDF report**: "Generate a professional PDF report? Use `/seo google report full`"

For individual commands, load the relevant sub-skill directly — the
Pre-Flight Capability Check still applies, scoped to what that command
actually uses (e.g. `/seo google` only needs the Google API row).
After any analysis command completes, offer to generate a PDF report via `scripts/google_report.py`.

## Synthesis Methodology

Audits are not just findings, they are findings synthesized into a coherent
strategy. claude-seo uses a 10-principle thinking framework grouped into four
phases: **PERCEIVE** (observe-external · observe-internal · listen),
**ANALYZE** (think · connect-lateral · connect-system), **VALIDATE** (feel ·
accept), **ACT** (create · grow).

Full audits (`/seo audit`, `/seo page`) walk every phase before emitting the
action plan. Narrower commands (`/seo schema`, `/seo images`, etc.) pass at
least THINK + ACCEPT before emitting (sound first principle, surfaced
falsifiability). The Critical / High / Medium / Low priority buckets are the
**output** of validation, not a substitute for it.

Full methodology + per-principle SEO mapping: `references/thinking-framework.md`.

Each emitted recommendation should carry:
- The first-principle observation it rests on (THINK)
- The dependency on / unblock relationship to other recommendations (CONNECT-system)
- An explicit "how would we know this failed?" check (ACCEPT)
- A leading indicator the user can monitor without re-running the audit (GROW)

## Industry Detection

Detect business type from homepage signals:
- **SaaS**: pricing page, /features, /integrations, /docs, "free trial", "sign up"
- **Local Service**: phone number, address, service area, "serving [city]", Google Maps embed --> auto-suggest `/seo local` for deeper analysis
- **E-commerce**: /products, /collections, /cart, "add to cart", product schema
- **Publisher**: /blog, /articles, /topics, article schema, author pages, publication dates
- **Agency**: /case-studies, /portfolio, /industries, "our work", client logos

## Quality Gates

Read `references/quality-gates.md` for thin content thresholds per page type.
Hard rules:
- WARNING at 30+ location pages (enforce 60%+ unique content)
- HARD STOP at 50+ location pages (require user justification)
- Never recommend HowTo schema (deprecated Sept 2023)
- FAQ schema: Google retired FAQ rich results for ALL sites on May 7, 2026 (no SERP feature anymore; supersedes the Aug 2023 gov/health restriction). Flag existing FAQPage at Info (not Critical); do not claim confirmed AI/LLM citation benefit; do not recommend removal; do not recommend new FAQPage for Google SERP benefit; use QAPage for genuine user Q&A
- All Core Web Vitals references use INP, never FID

## Reference Files

Load these on-demand as needed (do NOT load all at startup):
- `references/cwv-thresholds.md`: Current Core Web Vitals thresholds and measurement details
- `references/schema-types.md`: All supported schema types with deprecation status
- `references/eeat-framework.md`: E-E-A-T evaluation criteria (Sept 2025 QRG update)
- `references/quality-gates.md`: Content length minimums, uniqueness thresholds
- `references/local-seo-signals.md`: Local ranking factors, review benchmarks, citation tiers, GBP status
- `references/local-schema-types.md`: LocalBusiness subtypes, industry-specific schema and citation sources

Maps-specific references (loaded by seo-maps skill, not at startup):
- `references/maps-geo-grid.md`, `references/maps-gbp-checklist.md`, `references/maps-api-endpoints.md`, `references/maps-free-apis.md`

## Scoring Methodology

### SEO Health Score (0-100)
Weighted aggregate of all categories:

| Category | Weight |
|----------|--------|
| Technical SEO | 22% |
| Content Quality | 23% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Performance (CWV) | 10% |
| AI Search Readiness | 10% |
| Images | 5% |

### Priority Levels
- **Critical**: Blocks indexing or causes penalties (immediate fix required)
- **High**: Significantly impacts rankings (fix within 1 week)
- **Medium**: Optimization opportunity (fix within 1 month)
- **Low**: Nice to have (backlog)

## Sub-Skills

This skill orchestrates 27 sub-skills (23 core + 1 growth-loop onboarding +
1 framework integration + 2 extension mirrors). The orchestrator itself (`seo`)
lives in `skills/` too, but does not orchestrate itself, so it is not
enumerated below.

1. **seo-audit** -- Full website audit with parallel delegation
2. **seo-page** -- Deep single-page analysis
3. **seo-technical** -- Technical SEO (9 categories)
4. **seo-content** -- E-E-A-T and content quality
5. **seo-content-brief** -- Detailed SEO content brief generation (contributed by puneetindersingh)
6. **seo-schema** -- Schema markup detection and generation
7. **seo-images** -- Image optimization, SERP analysis, file optimization
8. **seo-sitemap** -- Sitemap analysis and generation
9. **seo-geo** -- AI Overviews / GEO optimization
10. **seo-plan** -- Strategic planning with templates
11. **seo-programmatic** -- Programmatic SEO analysis and planning
12. **seo-competitor-pages** -- Competitor comparison page generation
13. **seo-hreflang** -- Hreflang/i18n SEO audit, cultural profiles, content parity
14. **seo-local** -- Local SEO (GBP, NAP, citations, reviews, local schema, multi-location)
15. **seo-maps** -- Maps intelligence (geo-grid, GBP audit, reviews, competitor radius)
16. **seo-google** -- Google SEO APIs (GSC, PageSpeed, CrUX, Indexing API, GA4)
17. **seo-backlinks** -- Backlink profile analysis (free: Moz, Bing, CC; premium: DataForSEO)
18. **seo-cluster** -- SERP-based semantic clustering (contributed by Lutfiya Miller)
19. **seo-sxo** -- Search Experience Optimization (contributed by Florian Schmitz)
20. **seo-drift** -- SEO drift monitoring (contributed by Dan Colta)
21. **seo-ecommerce** -- E-commerce SEO intelligence (contributed by Matej Marjanovic)
22. **seo-dataforseo** -- Live SEO data via DataForSEO MCP (extension mirror)
23. **seo-image-gen** -- AI image generation for SEO assets via Gemini (extension mirror)
24. **seo-flow** -- FLOW framework integration (Find -> Leverage -> Optimize -> Win, 41 AI prompts, CC BY 4.0)
25. **seo-onboard** -- Growth Loop setup for a website repo (copies the per-site template in, installs credentials as repo secrets, triggers the first audit)
26. **seo-aso** -- App Store Optimization for App Store / Google Play listings
27. **seo-fix** -- Opt-in fixer for audit findings: dry-run preview by default, writes only after per-change confirmation

### Optional Extensions

The following ship in `extensions/` rather than `skills/` and require a separate
installer to activate (see each extension's `install.sh`/`install.ps1`):

All optional extensions are reachable through `/seo` subcommands once
installed: firecrawl, dataforseo, and image-gen, plus `/seo ahrefs`,
`/seo bing`, `/seo profound`, `/seo seranking`, `/seo unlighthouse`, and
`/seo screaming-frog`. Each installs as its own sub-skill, so the model
also auto-routes to their descriptions without the `/seo` prefix.

- **seo-firecrawl** -- Full-site crawling and site mapping via Firecrawl MCP. Install
  via `extensions/firecrawl/install.sh` (Unix) or `extensions/firecrawl/install.ps1`
  (Windows). Once installed, invoke via `/seo firecrawl <command>`.
- **seo-screaming-frog** -- Enterprise-scale crawling (tens of
  thousands to millions of URLs, bulk CSV export, redirect-chain
  mapping) via a Screaming Frog SEO Spider licence you already own.
  Install via `extensions/screaming-frog/install.sh`. Invoke via
  `/seo screaming-frog <url>`.

### Free-tier ceiling vs. paid coverage

Everything in `skills/` and `scripts/` runs with zero paid subscriptions
— free APIs (Moz, Bing Webmaster, Common Crawl, GSC/GA4/PSI/CrUX,
Gemini's free tier), or fully local/deterministic scripts. That ceiling
is real and worth stating plainly rather than pretending it doesn't
exist, so paid users know exactly which extension closes which gap:

| Free-tier ceiling | What it looks like | Extension that removes it |
|---|---|---|
| Crawl depth capped ~500 pages | `seo-audit`'s built-in parallel-subagent crawl | `seo-screaming-frog` (licensed CLI, effectively unlimited) or `seo-firecrawl` (API-driven, JS-heavy sites, no desktop install) |
| No proprietary backlink index | `seo-backlinks` uses Moz/Bing/Common Crawl only — smaller, slower-refreshed link graphs than a funded commercial crawler | `seo-ahrefs` (Ahrefs' own index via official MCP) |
| Single-shot, single-platform live AI citation check | `scripts/live_citation_check.py` running Gemini-only (free tier) | Same script with `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/`PERPLEXITY_API_KEY` set (paid, per-call), or `seo-profound`/`seo-seranking` for continuously-polled, multi-platform time-series instead of on-demand single queries |
| Voice-search eligibility is a featured-snippet proxy, not a real device query | `scripts/voice_search_live_check.py` | No extension closes this — no vendor (free or paid) exposes an API to query a real smart speaker as an end user would. This is a structural product-level gap, not a licensing one. |
| Keyword volume/difficulty/SERP tracking needs a paid data source | GSC gives your own historical query data only | `seo-dataforseo` (keyword volume, difficulty, live SERPs) |

## Subagents

### Audit agents

For parallel analysis during audits (read-only):
- `seo-technical` -- Crawlability, indexability, security, CWV
- `seo-content` -- E-E-A-T, readability, thin content
- `seo-schema` -- Detection, validation, generation
- `seo-sitemap` -- Structure, coverage, quality gates
- `seo-performance` -- Core Web Vitals measurement
- `seo-visual` -- Screenshots, mobile testing, above-fold
- `seo-geo` -- AI crawler access, llms.txt, citability, brand mention signals
- `seo-local` -- GBP signals, NAP consistency, reviews, local schema, industry-specific local factors (conditional: spawned when Local Service detected)
- `seo-maps` -- Geo-grid rank tracking, GBP audit, review intelligence, competitor radius mapping (conditional: spawned when Local Service detected AND DataForSEO MCP available)
- `seo-google` -- CWV field data, URL indexation status, organic traffic trends (conditional: spawned when Google API credentials detected)
- `seo-backlinks` -- Backlink profile data: DA/PA, referring domains, anchor text, toxic links (conditional: spawned when Moz/Bing API keys detected or always for CC domain-level metrics)
- `seo-cluster` -- Semantic clustering analysis (conditional: content strategy detected)
- `seo-sxo` -- Page-type mismatch, user stories, persona scoring (always in full audits)
- `seo-drift` -- Baseline comparison (conditional: drift baseline exists for URL)
- `seo-ecommerce` -- Product schema, marketplace intel (conditional: e-commerce detected)
- `seo-flow` -- FLOW framework prompts (conditional: spawned for content strategy workflows)
- `seo-dataforseo` -- Live SERP, keyword, backlink, local SEO data (extension, optional)
- `seo-image-gen` -- SEO image audit and generation plan (extension, optional)

### Write-capable agent

Never spawned by an audit; used only by the `seo-fix` skill after the user
confirms the diffs:
- `seo-fixer-writer` -- Applies AUTO-class fixes. Backs up first, idempotent, git-aware, re-verifies each change

### Site-wide review agents

Look across the whole site rather than one page, so they see what no
per-page pass can. Run from the growth loop's Monday job:
- `seo-content-performance` -- Per-page Search Console results for everything published, classified by age band and failure mode. Writes the lessons file `seo-writer` reads before drafting, which is what closes the quality loop
- `seo-internal-links` -- Whole-site link graph: orphans, depth, dead ends, anchor dilution, broken cluster structure. Proposes specific link insertions

### Content writer

Drafts pages and articles. Invoked by the growth loop's build step and by
`/seo content-brief` follow-through, never by an audit:
- `seo-writer` -- Researches the live SERP before drafting, writes from concrete specifics, verifies its own claims, runs the humanizer. Writes drafts on a branch only; never publishes

### Growth Loop agents

For the autonomous plan -> audit -> fix -> test -> publish -> distribute loop
(see `docs/GROWTH-LOOP.md`). Not spawned by `/seo audit`; they run from a
site repo's scheduled workflow or from `/seo onboard`:
- `seo-planner` -- Strategist: turns audit + GSC/GA4 signals into a prioritized, dependency-sequenced roadmap, quick wins first. Writes planning docs only
- `seo-resolver` -- The unblocker: mandatory seven-rung solution ladder that every other agent must call before failing, skipping, or escalating; holds binding decision authority for the cycle
- `seo-outreach` -- Off-page authority: citations, directory submissions, linkable-asset proposals, broken-link prospecting. Drafts and queues, never auto-sends. White-hat only
- `seo-tester` -- QA gate: pre-publish checks (build, links, schema, drift, performance) and post-publish verification. No write access; can only pass, fail, and report
- `seo-publisher` -- Release engineer: the only agent allowed to merge, push to a deploy branch, or call a CMS publish API, and only on a fresh `VERDICT: PASS` from `seo-tester`

## Error Handling

| Scenario | Action |
|----------|--------|
| Unrecognized command | List available commands from the Quick Reference table. Suggest the closest matching command. |
| URL unreachable | Report the error and suggest the user verify the URL. Do not attempt to guess site content. |
| Sub-skill fails during audit | Report partial results from successful sub-skills. Clearly note which sub-skill failed and why. Suggest re-running the failed sub-skill individually. |
| Ambiguous business type detection | Present the top two detected types with supporting signals. Ask the user to confirm before proceeding with industry-specific recommendations. |
