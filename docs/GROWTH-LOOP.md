# The Growth Loop: autonomous SEO/AEO/GEO for any site

This extends `claude-seo-unified` (25 audit sub-skills, 18 read-only
sub-agents, one confirmed-fix writer) with five new agents —
`seo-planner`, `seo-tester`, `seo-publisher`, `seo-outreach`,
`seo-resolver` — and a GitHub Actions workflow that runs the whole thing on a schedule, so a site
gets planned, audited, fixed, written for, tested, published, and
(re-)submitted to search engines with very little manual input, and
without ever stalling on a missing human answer.

## Two repos, two jobs

- **This repo (`seo-aeo-geo`)** is the *engine*: a generic agent team, and
  nothing else. It holds no website's URL, config, credentials, or list of
  managed sites — it is the same repo whether you run one website or fifty.
  The per-site files a new website needs live under `templates/site-repo/`;
  copying that folder into a website's repo is the entire "plug and play"
  step.
- **Each website's own repo** gets two additions from that template:
  `seo-config.yml` (business/platform config) and
  `.github/workflows/seo-growth-loop.yml` (the schedule). Everything else
  — the audit logic, the agents, the scripts — comes from installing this
  plugin as a dependency.

## Where things actually run (read this if you're unsure where to start)

Three different surfaces are involved, and they do different jobs:

1. **A Claude Code session attached to this repo (one-time, per setup
   task)** — used to make and commit changes to the repo itself: adding
   the new agent files, fixing the repo's leftover branding, and later,
   the one-time per-site install step (copying the template into a new
   website's repo). This is *you* directing a session interactively; it
   is not what runs the loop day to day.
2. **GitHub Actions, inside each website's own repo (ongoing, unattended)**
   — this is what actually runs the loop. Once `seo-growth-loop.yml` and
   its secrets are in place, GitHub fires it on the cron schedule whether
   or not any chat session, Claude Code window, or Cowork tab is open.
   There is no persistent "session" to keep alive — each scheduled run is
   a fresh, self-contained job.
3. **A periodic digest back to you (optional, recommended)** — since
   nothing above proactively tells you anything happened, a low-frequency
   Claude scheduled task reads the `reports/` folder and the pinned
   "needs your input" issue across your sites and summarizes them in chat.
   It finds those sites by the GitHub topic `seo-growth-loop`, which the
   onboarding step adds to each managed repo — so the list of your websites
   lives on the websites' own repos, never in this engine repo.

## The eight agents

| Agent | Where it lives | What it does | Can write to |
|---|---|---|---|
| **seo-planner** | this repo, `agents/seo-planner.md` | Strategist. Prioritizes quick wins first (striking-distance keywords, low-CTR pages, indexing blockers), then sequences everything else against real GSC/GA4 data. Runs the non-blocking escalation protocol. | `reports/ROADMAP.md`, `reports/CONTENT-CALENDAR.md`, `reports/KPI-TRACKER.md`, `reports/HUMAN-INBOX.md` |
| **seo-audit + 18 sub-agents** | this repo, existing | Diagnostician. Technical, content/E-E-A-T, schema, performance, GEO/AI-search, local, backlinks, drift, e-commerce — parallel, read-only. | nothing (read-only) |
| **seo-fixer-writer + content agents** | this repo, existing + content briefs | Implementer. Applies AUTO-tier fixes and drafts content from the planner's roadmap, on a branch. | a feature branch only |
| **seo-outreach** | this repo, `agents/seo-outreach.md` | Off-page/growth specialist. Citations and directory submissions (automated where legitimate), linkable-asset proposals, broken-link-building prospecting, journalist-request drafting. Never sends anything itself; queues one-click drafts. | `reports/OUTREACH-LOG.md`, queue items to `reports/HUMAN-INBOX.md` |
| **seo-tester** | this repo, `agents/seo-tester.md` | QA lead. Pre-publish gate (build, links, schema, drift regression, performance, content quality) and post-publish verification. | `reports/TEST-REPORT.md` only |
| **seo-publisher** | this repo, `agents/seo-publisher.md` | Release engineer. Merges/deploys only after a fresh `VERDICT: PASS`, platform-aware. | the deploy branch/CMS, gated |
| **seo-resolver** | this repo, `agents/seo-resolver.md` | The unblocker. Any agent that would fail, skip, or escalate must call it first. Runs a mandatory seven-rung solution ladder, holds binding decision authority for the cycle, and broadcasts every fix so nothing is ever re-solved. | `reports/RESOLUTIONS.md`, plus whatever the fix itself requires |
| **Distribution step** | existing scripts (`indexnow_submit.py`, `indexing_notify.py`) + `seo-tester` Phase 2 | Pings Bing/Yandex/Seznam/Naver via IndexNow, requests Google re-crawl via Search Console when configured, watches for impression/click regressions. | `reports/DISTRIBUTION-LOG.md` |

## How nothing ever blocks — the resolver protocol

No agent in this system is allowed to fail, skip a task, or ask the human
for anything on its own. Every one of them must hand the problem to
`seo-resolver` first. That is enforced in each agent's own file, not left
to judgment.

The resolver then runs a **seven-rung ladder**, and may not declare
anything human-required until every rung has been attempted *and logged*:

1. **Read the real error** — the actual log, status code, validator
   message. Most escalations are a misdiagnosis of a clear error.
2. **Retry differently** — other parameters, rendered instead of raw, a
   backoff, a smaller batch, a different merge base.
3. **Another route to the same outcome** — this plugin ships overlapping
   capabilities on purpose; if CrUX is unavailable, Lighthouse answers the
   same question; if Moz is down, Bing and Common Crawl remain.
4. **Decompose** — do the part that can be done now, completely.
5. **Substitute at lower fidelity** — a weaker but valid answer, marked as
   such, beats no answer.
6. **Defer with a changed approach** — retry next cycle by a *different*
   method, never the same attempt on a loop.
7. **Reduce to the smallest human atom** — only now, and only the single
   irreducible physical action (receive a code, click send), with
   everything around it already prepared so it takes under a minute.

It also holds **binding decision authority**: when agents disagree or a
choice has no clear winner, it decides, logs the reasoning and what would
reverse it, and the loop moves. A logged, reversible decision that keeps
the system running beats a correct hesitation that stops it.

Every resolution is written to `reports/RESOLUTIONS.md`, which every agent
reads before starting — so a problem solved once is never worked twice,
and a fix that applies portfolio-wide gets proposed for promotion into the
engine repo's shared agent instructions.

Two things the resolver may never do, no matter how blocked it is: weaken
a safety gate (disabling the tester, flipping to `ungated`, bypassing
`VERDICT: PASS`, force-pushing, silencing a failing check), or resolve
toward a black-hat tactic. If the only available "fix" is removing a
safeguard, that is a rung-7 human item, not a fix.

Whatever does survive all seven rungs lands in `reports/HUMAN-INBOX.md`,
which the Monday run syncs to one pinned GitHub issue (`Growth Loop: needs
your input`). It is a queue, never a gate — everything not structurally
dependent on it ships on schedule regardless.

The only thing this system will never do automatically: buy/exchange
links, post to community platforms (Reddit/Quora/forums) on your behalf,
or send an email without a human clicking send — these are refused
outright (link schemes) or drafted-and-queued (everything else), because
automating them either risks a Google penalty or your own account
standing on the target platform.

## Gated vs. ungated publishing

`seo-publisher` refuses to ship anything without a fresh `VERDICT: PASS`
from `seo-tester`. That's the approval gate standing in for a human click
— you don't press approve, but a bad auto-write still can't reach a live
site. Set `autonomy.mode: gated` (default, recommended) or `ungated`
(skips the test gate — available since you asked for zero manual
involvement, but start gated and watch what the Tester actually catches
for a month before relaxing it) in each site's `seo-config.yml`.

## Setup, in order

**Once, ever** — the engine side is already in place in this repo: the
five agents under `agents/`, the `seo-onboard` skill, and `templates/`.
The rebrand steps this depended on are recorded in
[REPO-CLEANUP-CHECKLIST.md](REPO-CLEANUP-CHECKLIST.md). The one remaining
manual step is `/install-github-app` in a Claude Code session on this repo,
choosing **create a long-lived token with your Claude subscription** rather
than a separate API key, so scheduled runs draw on the existing
subscription instead of per-token API billing. It saves the secret as
`CLAUDE_CODE_OAUTH_TOKEN` — set it as a GitHub *organization* secret and
every site repo inherits it.

**Per website** — open a Claude Code session on *that website's* repo and
just say what you want: "optimize this website", "set up SEO here", "I
want this site ranking". The `seo-onboard` skill triggers on plain
language; no command has to be typed or remembered. It asks any genuinely
unanswerable question once, upfront, then runs to completion without
interrupting: copies the template in, detects the framework and build
command, installs every credential as that repo's GitHub secrets (reading
them from wherever they already are, so no key is handled by hand), tags
the repo with the `seo-growth-loop` topic, and triggers the first audit.

Nothing about a website is ever written into this engine repo.

## What this cannot do for you

- It cannot buy domain trust or backlinks — those take months regardless
  of tooling. See the realistic 0–3 / 3–6 / 6–12 month framing in
  `agents/seo-planner.md`. What genuinely can move inside 30 days:
  indexing-blocker fixes, CTR gains on already-ranking pages, and
  striking-distance keywords (position 11-20) crossing to page 1 —
  `seo-planner` prioritizes exactly these first for this reason.
- It cannot automate anything that requires a human fact: legal/
  compliance sign-off, a verification code only the account owner
  receives, a payment method. It queues these without blocking anything
  else.
- It is not free in the sense of "zero ongoing cost" — GitHub Actions
  minutes and your Claude subscription's usage are the two real costs,
  and both are usage you likely already have.
