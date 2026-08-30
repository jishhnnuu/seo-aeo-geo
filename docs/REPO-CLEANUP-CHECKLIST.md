# Repo cleanup checklist

> **Status: done.** Everything below was applied when the Growth Loop was
> added (see `docs/GROWTH-LOOP.md`). It is kept as a record of what was
> changed and why, and as the reference for the values the per-site
> template uses. The only item still open is the public/private decision
> at the bottom, which is yours to make.

This repo is a fork/merge of `AgriciDaniel/claude-seo` (plus three other
MIT projects — see `NOTICE.md`; that attribution is required and stays).
Several rebrand steps the upstream README asks for were left unfinished.
They mattered because the per-site workflow template references this
repo's name and marketplace name directly. What was changed:

- [x] **`.claude-plugin/marketplace.json`**: `name` was
      `"agricidaniel-claude-seo"` and `owner.name` was `"AgriciDaniel"`.
      Now `"jishnu-seo-aeo-geo"` / `"Jishnu"`. This is the marketplace
      name the growth-loop workflow installs from.
- [x] **`.claude-plugin/plugin.json`**: `name` was already
      `"claude-seo-unified"` (which the workflow template assumes), but
      `homepage` and `repository` were blank. Both now point at
      `https://github.com/jishhnnuu/seo-aeo-geo`.
- [x] **`README.md`**: the Installation and Uninstall sections carried
      literal `<owner>/claude-seo-unified` placeholders. All replaced with
      `jishhnnuu/seo-aeo-geo`, and the clone-directory names corrected to
      match. Provenance, NOTICE, and Community Contributors references to
      the upstream projects were deliberately left alone — that
      attribution is required.
- [x] **`CLAUDE.md`**: the "Repository Topology (public + private)"
      section described the upstream author's two-remote (`origin` +
      `aimh`) setup, which does not apply here. Replaced with a short note
      that this repo has a single `origin` remote and a normal `main`
      release flow.
- [ ] Decide whether you want this repo **public** (required for anyone
      else's `claude-code-action` to install it as a plugin from a public
      URL without extra auth, and for unlimited free GitHub Actions
      minutes on this repo specifically) or **private** (fine too — your
      own growth-loop workflows in your website repos can still install a
      private plugin repo, they just need a token with read access to it).

These are the values now baked into
`templates/site-repo/.github/workflows/seo-growth-loop.yml`, so a freshly
copied template needs no substitution:

```
plugin_marketplaces: "https://github.com/jishhnnuu/seo-aeo-geo.git"
plugins: "claude-seo-unified@jishnu-seo-aeo-geo"
```

If you ever rename the marketplace in `.claude-plugin/marketplace.json`,
update both lines in the template (they appear once per job, four times in
all) to match.
