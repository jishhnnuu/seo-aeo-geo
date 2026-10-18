# Midweek run (Thursday, first 60 days)

A short link-building and indexing run that doubles the outreach rhythm during the first 60 days. Same paths and rules
as `weekly.md`. Keep it small: no on-site changes unless an indexing problem needs a fix.

1. Append `<date> midweek: started` to `<site>/.seo/runs.md`.
2. `linkbuilding.py due --campaign <camp>`: draft the follow-ups that are due and refresh the export.
3. Prepare the next batch from approved prospects (contact, hook, `draft`, `export`). List new prospects that need
   the owner's approval.
4. Verify any link the owner logged as won since Monday (`verify`), and check that pages shipped on Monday are indexed
   (`scripts/gsc_inspect.py`). Queue a request-indexing item for any that are not.
5. Commit `<site>/.seo/`, push, append `<date> midweek: done`.
6. Report in under 120 words: follow-ups to send, emails ready, approvals waiting, new links verified, indexing
   problems, and the "needs you" list with minutes per item.
