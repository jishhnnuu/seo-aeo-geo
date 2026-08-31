---
name: seo-fix
description: >
  Opt-in fixer for the /seo audit findings. Applies safe, deterministic
  fixes — meta viewport/charset/lang, JSON-LD, robots.txt AI directives,
  hreflang, sitemaps, OG/Twitter cards, image dimensions, canonical,
  llms.txt. Dry-run preview by default; writes only after explicit
  per-change confirmation from the user. Runs only when the user invokes
  `/seo fix` — never auto-triggered by any other skill in this plugin.
disable-model-invocation: true
argument-hint: "<url|path> [--category schema|meta|robots|sitemap|hreflang|alt|canonical|social|llms] [--dry-run]"
allowed-tools: Read, Grep, Glob, Bash, Task
license: MIT
metadata:
  category: seo
  version: "1.8.1"
  provenance: "Ported and adapted from Hainrixz/claude-seo-ai (MIT). See /NOTICE.md."
---

# seo-fix (opt-in writer)

Every other skill in this plugin is **read-only by design** — `/seo audit`,
`/seo technical`, `/seo schema`, `/seo geo`, and the rest only ever produce
findings and reports. `seo-fix` is the single exception, and it is
deliberately walled off: `disable-model-invocation: true` means the model
can **never** trigger it on its own, only the user running `/seo fix`
directly. Writes happen only through the **seo-fixer-writer** subagent (the
one agent in this whole plugin with Write/Edit access) and only after
explicit user confirmation of a previewed diff.

This mirrors the safety model of the upstream project this was ported
from — the goal is that a person can trust `/seo audit` to never touch
their files, full stop, while still having a fast path to apply the
boring, mechanical fixes once they've reviewed them.

## Fixability classes

Every finding this plugin's auditors emit should carry a `fixable` field
(see `schema/finding.schema.json`) with one of three values:

- **AUTO** — deterministic, additive, machine-verifiable, low-semantic-risk.
  May be written, with a diff shown first and confirmation required: meta
  `viewport`/`charset`/`<html lang>`; Tier-1 JSON-LD blocks; `sameAs`/`@id`/
  `dateModified` (only from values the user has confirmed, never invented);
  robots.txt AI-crawler presets (see `references/ai-crawler-robots-presets.md`
  for the actual preset content — it distinguishes training bots,
  search/retrieval bots, and user-triggered fetchers per operator, since a
  blanket "block all AI bots" preset would also block the citation-granting
  retrieval bots a site usually wants to allow) + `Sitemap:` line;
  self-referential canonical; hreflang link sets; OG/Twitter cards; image
  `width`/`height`; XML sitemap entries; `llms.txt` (disclosure-gated — see
  `references/llmstxt-evidence.md` in `skills/seo-geo/references/`, since
  llms.txt carries no citation weight and should never be oversold as one).
- **PROPOSED** — changes prose or meaning; generate a draft diff and require
  per-item accept, never a blanket accept: generated `<title>` and meta
  description, answer-block/TL;DR rewrites, internal-link insertions,
  heading restructuring, generated image alt text. These are editorial
  messaging decisions, not deterministic transforms, even when they look
  mechanical.
- **ADVISORY** — never written by this skill, full stop: content/E-E-A-T
  rewrites, adding statistics/citations/original data, Core Web Vitals or
  performance work, rendering-strategy changes, redirects/status codes,
  link-building, and anything that lives in Merchant Center/GBP backend
  data rather than the site's own files.

If an existing finding from another skill in this plugin doesn't carry a
`fixable` field yet, treat it as `advisory` until that skill is updated —
never guess a finding into `auto` just because it looks simple.

## Workflow

1. Take findings from the most recent `/seo audit` (or run a fresh
   read-only audit first if none exists). Filter to `fixable: auto`, plus
   `fixable: proposed` only if the user has explicitly opted into
   reviewing proposed changes. Honor `--category` to scope the run
   (schema|meta|robots|sitemap|hreflang|alt|canonical|social|llms).
2. For each finding, locate the exact insertion point in the user's files
   and build a **unified diff** (or full new-file content for a new file
   like `/llms.txt`). If a fix needs a real-world input the audit couldn't
   observe — a `sameAs` profile URL, a locale map, a true publish date —
   **ask the user for it**. Never invent a value to fill the gap; an
   invented `dateModified` or fabricated `sameAs` link is worse than no
   fix at all.
3. **Dry-run is the default.** Print every diff, grouped by file, and
   summarize what running `/seo fix` without `--dry-run` would change.
   Write nothing in this step, regardless of how confident the diff looks.
4. Only on explicit user confirmation, delegate to **seo-fixer-writer** to
   apply the change. The user can confirm per-change or in a batch — that
   choice is theirs, not the skill's to assume.

## Safety (hard rules, not guidelines)

- **Dry-run by default.** Writing requires the user to drop `--dry-run`
  and separately confirm.
- **Git-aware.** Refuse to write into a dirty working tree unless the user
  passes `--force`; prefer creating or switching to a dedicated branch
  first. Detect dirtiness via `git status --porcelain`.
- **Backup before first write.** Copy every file to
  `${CLAUDE_PLUGIN_DATA}/backups/<timestamp>/<path>` before modifying it.
- **Idempotent.** Detect existing tags/blocks and update them in place
  rather than duplicating; re-running `/seo fix` after it has already
  applied a change should produce zero new diffs.
- **Re-verify after writing.** Re-run the finding's own
  `verification.assertion` (e.g. the relevant `scripts/validate_*` check)
  and report pass/fail per change — a fix that doesn't re-verify clean is
  reported as failed, not silently left as "written."
- **Scope discipline.** Never touch `.git/`, `.env` or other secrets
  files, lockfiles, or anything outside the project root.
- **No fabrication, ever.** Never write an invented statistic, citation,
  date (including no backdating `dateModified`), credential, or identity
  link. If the fix needs a fact the audit didn't observe, ask — don't
  guess and don't leave a placeholder that looks like real data.
