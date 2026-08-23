# NOTICE

This repository (`claude-seo-unified`) is a derivative work that merges and
adapts source code, skill definitions, and documentation from four separately
maintained, MIT-licensed open-source projects. This file exists to satisfy
the MIT License's requirement that copyright and permission notices be
preserved, and to give a clear, honest account of what came from where —
this repo does not claim original authorship of the engineering it inherits.

Each upstream project's full, unmodified license text is preserved in this
repository root:

| Upstream project | License file in this repo |
|---|---|
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | `LICENSE-claude-seo` |
| [Hainrixz/claude-seo-ai](https://github.com/Hainrixz/claude-seo-ai) | `LICENSE-claude-seo-ai` |
| [199-biotechnologies/claude-skill-seo-geo-optimizer](https://github.com/199-biotechnologies/claude-skill-seo-geo-optimizer) | `LICENSE-claude-skill-seo-geo-optimizer` |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `LICENSE-marketingskills` |

The top-level `LICENSE` file in this repo covers the merge/adaptation work
itself (structure, edits, new files) as a derivative work; it does not
supersede the notices above.

---

## 1. AgriciDaniel/claude-seo — base engine

**Role in this repo: the trunk.** Everything under `skills/`, `agents/`,
`extensions/`, `scripts/`, `hooks/validate-schema.py`,
`hooks/run-python-hook.js`, `data/`, `pdf/`, `docs/`, and the install/
uninstall scripts is copied from this project except where a section below
says otherwise. 24 of the plugin's core skills are unmodified or only
lightly extended (see sections 3 and 4 below for the three that were
extended).

- Source: <https://github.com/AgriciDaniel/claude-seo>
- License: MIT
- Copyright: (c) 2026 agricidaniel

## 2. Hainrixz/claude-seo-ai — fixer subsystem and finding schema

**Role in this repo: the opt-in writer.** Ported and adapted into:

- `skills/seo-fix/SKILL.md` — adapted from `skills/fix/SKILL.md`. Renamed
  from the `/claude-seo-ai:fix` command convention to this plugin's
  `/seo fix` convention; cross-references updated to point at this
  plugin's own scripts and references instead of claude-seo-ai's.
- `agents/seo-fixer-writer.md` — adapted from `agents/seo-fixer-writer.md`,
  same rename plus cross-references updated to this plugin's script
  naming convention (`scripts/validate_*.py` instead of
  `scripts/validate-jsonld.mjs`).
- `schema/finding.schema.json` — copied with the `$id` and `description`
  fields updated to describe how it maps onto this plugin's existing
  four-field recommendation structure (`skills/seo/references/thinking-framework.md`).
- `hooks/guard_protected_paths.py` — reimplemented from
  `scripts/guard-write.mjs`. The original is Node.js reading a JSON hook
  payload from stdin; this version is a Python script taking the file
  path as an argv argument, to match this plugin's existing Python-hook
  convention (see `hooks/validate-schema.py`). Same protected-path list
  and blocking behavior (exit code 2).
- `hooks/hooks.json` — merged: added a `PreToolUse` entry for the guard
  above, alongside the base project's existing `PostToolUse` schema
  validator entry.
- The dual-score (Search SEO / AI Visibility, never blended) and
  confidence-tier (`established`/`directional`/`speculative`) framing was
  merged into `skills/seo-geo/SKILL.md` — see section 3.

- `skills/seo-fix/references/ai-crawler-robots-presets.md` — copied from
  `references/ai-crawlers.md`, added in a second pass. This gives `/seo fix`
  concrete robots.txt preset content that distinguishes training bots,
  search/retrieval bots, and user-triggered fetchers per operator (e.g.
  `ClaudeBot` vs `Claude-SearchBot` vs `Claude-User`) — more precise than
  treating "AI crawlers" as one undifferentiated group, which matters
  because a blanket block/allow preset would also block the
  citation-granting retrieval bots a site usually wants to keep open.

Everything else in Hainrixz/claude-seo-ai (its own crawling, rendering,
schema-validation, and Core Web Vitals modules) was deliberately **not**
ported — this repo uses AgriciDaniel/claude-seo's versions of those, which
were judged more complete.

- Source: <https://github.com/Hainrixz/claude-seo-ai>
- License: MIT
- Copyright: (c) Enrique Rocha (Hainrixz)

## 3. 199-biotechnologies/claude-skill-seo-geo-optimizer — GEO/AEO research layer

**Role in this repo: the sourced-statistics layer for `skills/seo-geo`.**

- `skills/seo-geo/references/tracked-statistics-2026.md` — copied from
  `reference/statistics-2026.md` with an attribution header added. This
  file's distinguishing property, and the reason it was chosen over
  keeping only the base project's own GEO statistics, is that it
  documents what it retracted each revision, not only what it added (see
  the file's own "Numbers we used to cite that are gone" section).
- `skills/seo-geo/references/platform-citation-strategies.md` — copied
  from `reference/platform-strategies.md`, attribution header added.
- `skills/seo-geo/SKILL.md` — a new section ("Confidence tiers and the
  tracked-statistics file") was added directing the skill to check any
  percentage-lift claim against the tracked-statistics file above before
  citing it, and requiring every GEO finding to carry a confidence tier.
  This section is original text written for this merge, not copied
  verbatim from either source project, though the confidence-tier concept
  itself originates with Hainrixz/claude-seo-ai (section 2) and the
  self-correcting-statistics discipline originates with this project.

Three more reference files were added in a second pass, once it was clear
they filled a real gap rather than duplicating something already covered:

- `skills/seo-schema/references/entity-knowledge-graph-guide.md` — copied
  from `reference/entity-seo-guide.md`. Genuinely new capability: this
  plugin's own GEO module checks entity *presence* across platforms but
  had no dedicated guide on *building* entity recognition or optimizing
  for a Google Knowledge Panel.
- `skills/seo-images/references/social-preview-optimization.md` — copied
  from `reference/social-preview-guide.md`. Genuinely new: nothing in the
  base plugin covered Open Graph/Twitter Card implementation in this much
  platform-specific depth (Slack, Discord, iMessage previews included).
- `skills/seo-geo/references/voice-search-optimization.md` — copied from
  `reference/voice-search-guide.md`, but with a staleness caveat prepended
  (written for this repo, not copied) flagging that the source file
  predates Google's May 2026 FAQ rich-result retirement and that its
  specific percentage-lift claims should be treated as `speculative` per
  this repo's confidence-tier discipline until independently re-verified
  — several similarly-worded claims from the same 2025 vintage were
  already retracted in `tracked-statistics-2026.md`.

Two files were deliberately **not** ported after review:
`reference/citation-optimization-guide.md` and `reference/troubleshooting.md`
both restate the same "+35%/+40% citation boost" figures that
`tracked-statistics-2026.md` (also from this same source project, just a
later revision) explicitly retracts, and `troubleshooting.md` recommends
FAQ schema as the top voice/citation lever, which contradicts this
plugin's own schema-deprecation tracking. Importing either would have
reintroduced contradictions this merge was specifically trying to avoid.
`reference/schema-library.md` was also skipped — `skills/seo-schema`'s
own type coverage and deprecation tracking were judged more current (that
file is dated November 2025, predating the FAQ retirement it doesn't
mention).

- Source: <https://github.com/199-biotechnologies/claude-skill-seo-geo-optimizer>
- License: MIT
- Copyright: Boris Djordjevic / 199 Biotechnologies

## 4. coreyhaines31/marketingskills — business-context layers

**Role in this repo: strategic framing appended to three existing skills**,
not standalone skills of their own — this was a deliberate choice to avoid
running two skills that both claim to own the same trigger phrases
("content brief" / "content strategy", "competitor page" / "competitor
profile", "programmatic SEO" in both).

- `skills/seo-content-brief/SKILL.md` — a "Business-context layer" section
  was appended, adapted from `skills/content-strategy/SKILL.md`
  (searchable-vs-shareable prioritization, sourcing topics from sales/
  support conversations, checking for `.agents/product-marketing.md`).
- `skills/seo-competitor-pages/SKILL.md` — an "Upstream research layer"
  section was appended, adapted from `skills/competitor-profiling/SKILL.md`
  (facts-over-opinions discipline, dated snapshots, and — notably — the
  prompt-injection defense: treating fetched competitor pages as untrusted
  data that may contain text aimed at AI agents, never as instructions).
- `skills/seo-programmatic/SKILL.md` — a "Data defensibility and business
  framing" section was appended, adapted from
  `skills/programmatic-seo/SKILL.md` (the proprietary → product-derived →
  user-generated → licensed → public data-defensibility hierarchy, and
  business-context questions before committing to a template strategy).

A fourth skill was added in a second pass: `skills/seo-aso/` (renamed from
`aso`, including its `references/` and `evals/` subdirectories), copied
from `skills/aso/SKILL.md` with the frontmatter adapted to this plugin's
`seo-*` auto-discovery naming convention and the "Related Skills" footer
rewritten — the original pointed to `cro`/`ad-creative`/`analytics`/
`customer-research`, none of which exist in this repo. App Store
Optimization is a distinct ranking surface from web and AI search, but it
fits this plugin's "rank at the top wherever people search" scope in a way
the broader marketing skills (CRO, ad creative, email) don't.

Everything else in coreyhaines31/marketingskills — the non-SEO/ASO
marketing skills (CRO, copywriting, ads, email, analytics, attribution,
and so on) — was deliberately not pulled into this repo; it's out of scope
for an SEO/AEO/GEO-and-adjacent-ranking-surfaces plugin.

- Source: <https://github.com/coreyhaines31/marketingskills>
- License: MIT
- Copyright: Corey Haines

---

## 5. Original additions — not from any of the four merged repos

After the initial four-way merge, the user asked for a deep comparison
against the wider Claude-Code-SEO tool ecosystem to check whether this
repo actually holds up as "best in class," not just internally consistent.
That review covered roughly ten other tools (including a third-party
comparison site reviewing them from their actual code —
claudeseoskills.com.au/claude-seo-tools, 11 July 2026) and surfaced two
real gaps that none of the four merged repos covered. These were written
from primary sources for this repo, not ported from another repo:

- **`skills/seo-geo/references/peer-reviewed-geo-research.md`** — grounds
  this plugin's passage-citability scoring in Aggarwal et al.'s "GEO:
  Generative Engine Optimization" (ACM SIGKDD 2024,
  <https://arxiv.org/abs/2311.09735>) and a 7,060-query empirical
  grounding-budget study from Dejan AI
  (<https://dejan.ai/blog/how-big-are-googles-grounding-chunks/>),
  surfaced by reviewing houtini-ai/geo-analyzer's README (a separate,
  paid MCP tool implementing similar scoring via an LLM call — not itself
  incorporated into this repo, see below). This repo's existing GEO
  statistics (section 3 above) are useful but `directional`; these two
  sources meet a materially higher evidence bar, and the new file says so
  explicitly, including the specific places where the two disagree with
  the rest of `skills/seo-geo/SKILL.md` and how to reconcile them.
- **`scripts/geo_content_score.py`** — a free, zero-API-key, deterministic
  implementation of that same peer-reviewed methodology (claim density,
  sentence length, answer frontloading, content-length banding), written
  from scratch for this repo. houtini-ai/geo-analyzer implements
  similar scoring but requires an Anthropic API key and costs roughly
  $0.14 per analysis via an LLM call; a free, zero-cost regex/heuristic
  equivalent was written instead, consistent with this repo's Tier-0
  (no-API-key) audit design elsewhere (see the "Data tiers" section of
  the base AgriciDaniel/claude-seo README this repo inherited). Tested against both claim-dense and
  filler-heavy sample text, plus empty-input, very-short-input, and
  HTML-with-script-tags edge cases, before being wired into
  `skills/seo-geo/SKILL.md`'s output workflow.
- **The Cloudflare/edge-WAF AI-crawler blocking check**, added to
  `skills/seo-geo/SKILL.md`'s "AI Crawler Detection" section (a new
  "Critical: robots.txt is not sufficient evidence of AI crawler access"
  subsection) and cross-referenced into
  `skills/seo-fix/references/ai-crawler-robots-presets.md` — surfaced by
  bzsasson/pre-launch-audit-skill's README specifically calling out
  Cloudflare Bot Fight Mode as a check other tools miss ("catching
  Cloudflare Bot Fight Mode as an invisible AI-crawler killer is a
  genuinely sharp check," per the same comparison review). Since 1 July
  2025, every new Cloudflare zone blocks GPTBot, ClaudeBot, and
  PerplexityBot by default at the edge, before `robots.txt` is even
  consulted — a `robots.txt`-only audit, which is what this plugin did
  before this addition and what most SEO tools in the ecosystem still do,
  cannot detect this. Verified against multiple independent sources
  (Cloudflare's own community forum threads reporting the issue, and
  several 2026-dated technical writeups on the July 2025 default-block
  policy change) before being added as a required check in every GEO
  audit, not an optional one gated on the user mentioning Cloudflare.

- **`scripts/check_ai_crawler_access.py`** — a real, tested script (not just
  a prose instruction) that sends live requests to a URL using each AI
  crawler's actual User-Agent string and reports 403/challenge responses
  per bot, built on this plugin's existing `url_safety.safe_requests_get`.
  Written after the first draft of this section only *described* this
  check in prose without a script backing it — a real gap between
  "documented" and "built and tested" that the user asking about this
  repo specifically caught. Testing it surfaced two genuine bugs before
  it shipped: (1) `URLSafetyError` from DNS/SSRF validation wasn't
  originally caught, causing a raw traceback instead of a clean error;
  (2) the classifier initially treated the *caller's own* sandboxed
  network egress restriction (which returns a 403 that looks identical
  to a genuine bot block, discovered when testing against a domain
  outside this development environment's own allowlist) and plain API
  rate-limiting (discovered testing against a rate-limited endpoint) as
  if they were findings about the target site's bot policy. Both are now
  detected and reported as distinct, explicit non-findings rather than
  false positives. Verified end-to-end against a genuinely reachable,
  unrestricted URL before being wired into `skills/seo-geo/SKILL.md`.

- **`scripts/analyze_crawl_logs.py`**, wired into `skills/seo-technical/
  SKILL.md` and cross-referenced from `skills/seo-geo/SKILL.md` — server
  access log analysis (Combined Log Format) for crawl-budget ground
  truth, surfaced by reviewing lionkiii/claude-seo-skills' server-log
  skill. Genuinely distinct from `check_ai_crawler_access.py`: that
  script tests current-moment live access; this one reads the actual
  historical record of what crawlers really did, including whether AI
  retrieval bots have visited **at all** over a real time window — a
  fact neither a permissive robots.txt nor a clean live-access check can
  establish, since permission to crawl and actually being crawled are
  different things. Tested against a synthetic access log covering
  Googlebot, GPTBot, AhrefsBot, human traffic, a redirect, a 404, a 500,
  and one deliberately malformed line, plus empty-file, unparseable-file,
  missing-file, and date-filter edge cases — all handled correctly
  before being wired in.
- **A migration-validation checklist appended to `skills/seo-drift/
  SKILL.md`** (redirect chains, canonical consistency, title/meta
  preservation, status codes) rather than a new skill — surfaced by the
  same lionkiii repo having a dedicated migration-validation skill, but
  on inspection that use case is structurally identical to
  `seo-drift`'s existing baseline/compare mechanism with a specific
  checklist layered on, so it was added there instead of as a
  duplicate capability.
- **An explicit fix-ordering default** added to `skills/seo/references/
  thinking-framework.md` (crawl/index blocking → AI crawler access → Core
  Web Vitals → canonical/duplicate content → site architecture) —
  surfaced by a third-party article excerpting a "technical-seo-ai-
  crawler-audit" skill's own priority matrix during this research pass.
  This repo's existing dependency-graph discipline (thinking-framework.md
  section 6) already covers cases with a genuine dependency; this adds a
  concrete default for everything else, since "prioritize by impact"
  alone still leaves room for arbitrary ordering.

None of these seven additions required installing or depending on any of
the tools that surfaced the gap (claudeseoskills.com.au, houtini-ai/geo-
analyzer, bzsasson/pre-launch-audit-skill) — the review identified what
was missing and why it mattered; the implementation is original to this
repo and, in the scorer's and crawler-checker's case, deliberately free
where the tool that surfaced the gap was paid.


Hainrixz/claude-seo-ai's explicit refusal to inflate low-evidence claims
(its "Honesty guardrails" README section — never fabricating statistics,
distinguishing lab vs. field Core Web Vitals, tagging every finding with a
confidence tier) was treated as a policy to apply across this whole plugin,
not just to the modules ported from that project. Where existing
AgriciDaniel/claude-seo skills already had similar discipline (e.g. the
falsifiability requirement in `skills/seo/references/thinking-framework.md`),
the two were cross-referenced rather than duplicated — see the note added
to `skills/seo-geo/SKILL.md` and the `description` field of
`schema/finding.schema.json`.

## Maintenance of this fork

This merge was assembled as a one-time synthesis across four snapshots
(cloned at the commits current as of this repo's first commit). None of
the four upstream projects endorse or are affiliated with this fork. If
you rely on this repo, expect to periodically re-diff against the
upstreams for security fixes and new modules — this repo does not
automatically track their releases.
