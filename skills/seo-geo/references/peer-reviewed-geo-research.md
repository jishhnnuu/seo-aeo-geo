<!-- Added for this repo. Not sourced from any of the four merged upstream projects — written from primary sources found during a review of the wider Claude-Code-SEO-tool ecosystem. See /NOTICE.md. -->

# GEO scoring: the peer-reviewed foundation

This plugin's passage-citability guidance elsewhere in `skills/seo-geo/`
(the "134-167 word self-contained answer block" heuristic, brand-mention
correlations, platform-citation behavior) comes from industry studies —
useful, but `directional` confidence at best per this repo's tiering. This
file grounds the GEO scoring model in two sources with a materially higher
evidence bar: one peer-reviewed academic paper, and one large-sample
empirical study with a published methodology. Where the two sections
disagree in specifics, prefer this file — `established`/methodologically
transparent beats `directional`/vendor-blog per this repo's own confidence
discipline.

## Source 1: the GEO paper (KDD 2024)

Aggarwal, Murahari, et al., "GEO: Generative Engine Optimization,"
ACM SIGKDD 2024 — <https://arxiv.org/abs/2311.09735>. This is the paper
that coined the term "Generative Engine Optimization" and the one most
GEO tooling traces back to, directly or through several removes.

**Findings this plugin should apply directly:**

- **Claim density target: 4+ extractable facts/statistics/measurements
  per 100 words.** Score a passage's claim density explicitly rather than
  relying on a subjective "feels information-dense" judgment.
- **Optimal sentence length: 15-20 words average.** Shorter sentences with
  concrete nouns parse more reliably for extraction than long, clause-heavy
  ones — this converges with the Dejan grounding-chunk finding below
  (~15.5 words), which is a genuine cross-validation between an academic
  paper and an independent empirical study, worth noting to a user because
  it's stronger evidence than either alone.
- **Extractability-focused optimization measured a 40% improvement in AI
  citation rate** in the paper's own test set. Tag this specific figure
  `directional` even though the source is peer-reviewed — one paper's test
  set is not the same as a replicated, cross-platform result, and this
  repo's confidence-tier discipline (`schema/finding.schema.json`) doesn't
  waive that standard just because the source is academic rather than a
  vendor blog.

## Source 2: Dejan AI grounding research (2025)

Empirical analysis of 7,060 queries and 2,275 pages —
<https://dejan.ai/blog/how-big-are-googles-grounding-chunks/> and
<https://dejan.ai/blog/googles-ranking-signals/>. Published methodology,
large sample, specific to Google's AI grounding behavior rather than GEO
in general — treat as strong evidence for Google AI Overviews/AI Mode
specifically, `directional` for other platforms until someone runs the
equivalent study against them.

**The "grounding budget" framework — a sharper mental model than "get
cited or don't":**

- Google allocates roughly a **~2,000-word total grounding budget** across
  all sources cited for a single AI answer. Getting cited isn't binary —
  it's competing for a *share* of that fixed budget against every other
  source Google pulls in for the same query.
- **Rank #1 source gets ~531 words (28% of the budget). Rank #5 gets ~266
  words (13%).** This is a genuinely different framing from "get cited or
  don't" — it means the practical goal for a page already earning
  citations is to grow its *share* of the budget, which the same
  extractability/frontloading work as above still serves, but the target
  metric (word share, not binary presence) is more actionable for
  reporting progress over time.
- **Average extraction chunk: 15.5 words** — the number the GEO paper's
  15-20 word sentence-length target above independently converges with.
- **Content-length sweet spot, empirically observed:** pages under 1,000
  words get pulled into ~61% of eligible AI answers; pages over 3,000
  words drop to ~13%. This is a real finding worth surfacing to a user
  writing long-form content for AI visibility specifically — it argues for
  a focused, well-structured 800-1,500 word page over a comprehensive
  3,000+ word one when AI-citation share (not just ranking) is the goal.
  It does **not** mean shorter is always better for classic SEO ranking,
  where comprehensiveness can still help — flag both sides so the user
  isn't led to gut a page's depth chasing the wrong metric.

## How to apply this without contradicting the rest of the plugin

- Where `skills/seo-geo/SKILL.md`'s existing "134-167 word self-contained
  answer block" guidance and this file's "15-20 word sentences, 4+
  claims/100 words" guidance both apply, they're compatible — a 134-167
  word answer block written in 15-20 word sentences with 4+ claims easily
  fits both. Frame them as the same target at two different granularities
  (block-level vs. sentence-level), not as competing numbers.
- Where the content-length sweet spot here (800-1,500 words, or even
  under 1,000) conflicts with a page's classic-SEO comprehensiveness
  needs, say so explicitly in the report rather than picking one silently
  — this is a real GEO-vs-SEO tension, not a case where one number is
  simply wrong.
- Cross-check any specific percentage this file cites against
  `tracked-statistics-2026.md` before including it in a report — that
  file's job is catching exactly this kind of number going stale.

## Further primary sources worth reading for deeper GEO/AEO grounding

Surfaced during the same review that produced this file; not yet
individually verified/integrated the way the two sources above are, so
treat citations from these as `directional` pending a closer read:

- SE Ranking's AI Mode optimization study —
  <https://seranking.com/blog/how-to-optimize-for-ai-mode/>
- Growth Memo, "The science of how AI pays attention" —
  <https://www.growth-memo.com/p/the-science-of-how-ai-pays-attention>
- Ahrefs, content freshness and AI citation study —
  <https://ahrefs.com/blog/do-ai-assistants-prefer-to-cite-fresh-content/>
- Conductor AEO/GEO benchmarks report —
  <https://www.conductor.com/academy/aeo-geo-benchmarks-report/>
- AirOps, "Structuring Content for LLMs" —
  <https://www.airops.com/report/structuring-content-for-llms>
