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

## Private site repo, public engine repo

That is the right way round, and it is what the templates assume.

The engine repo (this one) is **public** and holds no credentials — only
templates with placeholder values. Each website's repo can be **private** and
holds all the real secrets. A workflow running in a private repo clones a
public plugin repo with no authentication at all, so nothing about the private
side needs to be loosened. The reverse arrangement — a private engine repo —
would need every site repo to carry a token just to install the plugin, which
is why it is not the default.

Four things change when the site repo is private, and three of them cost money
or silence:

**Actions minutes are metered.** Public repos get unlimited minutes; private
repos get 2,000/month on Free and 3,000 on Pro. This loop runs roughly ten
agent jobs a week. Every job in the template sets `timeout-minutes: 45` so a
single hung run cannot eat a fifth of the month, and a `concurrency` group
stops two runs overlapping — but watch **Settings → Billing** for the first
few weeks and adjust the cron frequency if you are burning through it. When
the quota runs out, workflows simply stop; GitHub does not warn you loudly.

**There are no organization secrets on a personal account.** GitHub has
repository and environment secrets, and organization secrets — but no
account-level ones. If your repos live under your own username, set the shared
credentials on each site repo. If they live in an organization, organization
secrets work, though on *private* repos that needs a Team plan (on public
repos it works on Free).

**Scheduled workflows are disabled after 60 days of repo inactivity.** The
loop commits to `reports/` every week, which counts as activity, so it keeps
itself alive as long as it is actually running. A loop that has been failing
silently for two months will also stop being scheduled.

**Private repos cannot use GitHub Pages on the Free plan.** If that is how the
site is served, the repo has to be public or the plan upgraded.

## The PAT, and why the loop stalls without it

This is the single most likely reason a correctly-installed loop does nothing.

GitHub will not start a workflow run from an event created with the built-in
`GITHUB_TOKEN`. It is a deliberate anti-recursion rule. The `build` job opens
a pull request; `test-and-publish` runs `on: pull_request`. If that PR is
opened with `GITHUB_TOKEN`, **the test job never runs** — the pull request sits
open forever, nothing tests it, `seo-publisher` never gets its passing verdict,
and nothing reaches the site. The Actions tab shows green runs the whole time,
because the jobs that did run succeeded.

The fix is a fine-grained personal access token, scoped to the site repo, with
**Contents, Pull requests and Issues set to read/write**, saved as the
`GROWTH_LOOP_PAT` secret. Create it at
<https://github.com/settings/personal-access-tokens/new>. The workflow falls
back to `GITHUB_TOKEN` when it is absent, so audits and reports keep working —
and the Monday job puts a missing PAT at the top of
`reports/HUMAN-INBOX.md` rather than letting it go unnoticed.

Set an expiry you will actually renew. When the token expires the loop returns
to exactly the stall above, so treat the renewal date as a real calendar item.

## Merging is not deploying

`seo-publisher` merges to your deploy branch. Whether that reaches the live
site depends on how the site is hosted:

- **Vercel, Netlify, Cloudflare Pages, Render, Amplify** — these deploy from
  their own webhooks, which fire on any push regardless of which token made
  it. These work with no extra setup.
- **GitHub Pages, or any deploy that is itself a GitHub Actions workflow** —
  subject to the same restriction as above. A merge made with `GITHUB_TOKEN`
  will not trigger your deploy workflow. With `GROWTH_LOOP_PAT` configured it
  will, because the merge is then attributed to that token.
- **A CMS (WordPress, Shopify, Webflow)** — nothing is deployed from git at
  all; `seo-publisher` calls the platform's API directly using the per-site
  CMS credentials.

Set `site.deploy_branch` and `site.platform` in `seo-config.yml` so the
publisher knows which of these it is doing, and verify the first cycle by hand
before trusting it unattended.

## What "unattended" actually means here

Once `CLAUDE_CODE_OAUTH_TOKEN` and `GROWTH_LOOP_PAT` are set, nothing needs
your laptop, your session, or your attention. GitHub's schedulers fire the
workflow, the runners are GitHub's, and the agents commit, open, test, merge
and submit on their own. Scheduled cron on GitHub can fire late under load —
minutes to occasionally an hour — which does not matter for a weekly cadence.

### The preflight gate

Every trigger runs `preflight` first, and all four other jobs depend on it. It
uses `scripts/preflight_check.py`, which proves each credential by making a real
call with it — checking that an environment variable is set proves nothing.

It reports three states, deliberately kept distinct:

- **WORKING** — a live call succeeded.
- **UNAUTHORIZED** — the credential exists and was refused. This is a permission
  grant, not a missing key, and is usually a two-minute fix. Collapsing it into
  "not configured" is how a 403 goes unnoticed for a month.
- **ABSENT** — nothing configured. The report says what each absence costs, so
  the trade-off is visible rather than silent.

Only one condition is fatal: a missing `GROWTH_LOOP_PAT`, because without it
nothing can ever be published and the loop would burn 45 minutes a cycle
producing changes that never ship. Everything else degrades the run rather than
stopping it — a weaker audit beats no audit. The full table lands in the run's
GitHub Actions summary, so a glance at the Actions tab tells you what the loop
can currently see.

### The weekly report

A fifth scheduled job runs Monday 09:00 UTC, after the audit has landed, and
writes `reports/WEEKLY-REPORT.md`: the numbers first (impressions, clicks,
average position, CTR — this week against last), then a one-paragraph verdict
quoting the outcome-review rung the planner recorded, then what actually
shipped, what is next, and what needs you. Under 400 words, written to be read
on a phone by someone who has not opened the repo all week.

It is delivered two ways:

- **Always** — as a *new comment* on a pinned issue titled "Growth Loop:
  weekly report", assigned to the repo owner. GitHub emails that comment to
  you. This needs no setup and no extra credentials. It is a comment rather
  than a body edit for exactly the reason given above: an edit notifies nobody.
- **Optionally** — as a real formatted email, if you set `SMTP_USERNAME`,
  `SMTP_PASSWORD` and `REPORT_EMAIL_TO` (plus `SMTP_SERVER` / `SMTP_PORT` if
  you are not on Gmail). For Gmail, `SMTP_PASSWORD` must be an
  [App Password](https://myaccount.google.com/apppasswords) — never the account
  password, which would also not work with 2FA on. The mail step is
  `continue-on-error`, so a bounced or misconfigured mailbox degrades the
  report to the GitHub comment rather than failing the run.

The report deliberately leads with traffic rather than with work done. A cycle
that shipped everything planned and moved no metric was a failed cycle, and
this is where that has to be visible.

### How you find out when something breaks

Three channels, none of which need you to go looking:

- **A job fails** — GitHub emails the repo owner when a *scheduled* workflow
  fails. This covers the big ones: an expired `CLAUDE_CODE_OAUTH_TOKEN`, an
  expired `GROWTH_LOOP_PAT`, a revoked service account, exhausted Actions
  minutes.
- **Something needs you** — items marked `NOTIFY` in
  `reports/HUMAN-INBOX.md` trigger one mentioning comment on the pinned issue.
  This matters because **editing an issue body notifies nobody**: without the
  comment, a blocker raised in week three would sit unread indefinitely. The
  issue is also assigned to the repo owner on creation, which notifies too.
- **Nothing at all for weeks** — that is itself the signal. A healthy loop
  commits to `reports/` every Monday. If the last commit there is a month old,
  the schedule stopped: check Actions, then billing.

Two things still want a human roughly monthly: the pinned
`Growth Loop: needs your input` issue, and the billing page.

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
