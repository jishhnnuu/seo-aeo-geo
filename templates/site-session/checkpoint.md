# Checkpoint (day 30 and day 60)

A go or no-go decision for the site against the scorecard. Same paths and rules as `weekly.md`.

1. If this month has no snapshot yet, record one (`snapshot --month <n>`) with the scorecard metrics.
2. Run `linkbuilding.py scorecard --campaign <camp>` and `status`.
3. For every failed check, apply its corrective action now where it is within the routine's rules, or queue it for the
   owner with the exact step.
4. Write `<site>/.seo/checkpoint-day<d>.md`: the scorecard table, verdict, what changed, what is queued.
5. Decide and report (under 200 words):
   - **Day 30:** on track, or what changes for days 31 to 60. Say plainly whether brand search, live links and reply
     rate passed, and whether search impressions are moving yet.
   - **Day 60:** whether to keep the midweek sprint (recommend keeping it only if replies and the prospect backlog
     justify it, and wait for the owner's yes before disabling anything), and whether this playbook is ready to roll
     out to the next sites unchanged, or what to adjust first.
6. Commit `<site>/.seo/`, push, append `<date> checkpoint day <d>: <verdict>` to `runs.md`.
