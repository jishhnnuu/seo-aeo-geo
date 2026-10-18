# Outreach Playbook

How first contact, follow-up and closing work in `seo-linkbuilding`, and why. Loaded at steps 6 to 8.
The email templates themselves are in `scripts/linkbuilding.py` (`render_draft`) so they are tested; this
file explains the principles so drafts can be improved without breaking the gates.

## The gate

Nothing is drafted for a prospect the owner has not approved, and nothing is sent by the tooling. The owner
approves the shortlist (`linkbuilding.py approve`), the draft step refuses incomplete prospects, and the export
is a mail-merge CSV the owner sends from their own mailbox. Sending automatically from a cold domain damages
deliverability for the whole business, and a mistake cannot be recalled.

## What makes a first email work

1. **A specific reason it is addressed to this person.** The `hook` must reference something on their page
   that only someone who read it would know. "Love your content" and "great article" are rejected by the script.
   - Weak: "I came across your site and thought you might like our guide."
   - Strong: "Your list of accounts payable tools stops at 2021 and skips anything for businesses under ten staff."
2. **One useful thing, one link.** Name what the asset is in a sentence, link it once. No attachments.
3. **No ask beyond the obvious.** The editor decides. Do not pressure, flatter or offer money for a link.
4. **Short.** Under about 120 words. The script flags longer drafts.
5. **Honest sender.** Real name, real title, the company, a postal address if the campaign has one, and a
   one-line opt-out. This is a legal requirement in many places and a trust signal everywhere.
6. **A subject that says what it is.** Under 60 characters, no tricks, no "Re:" prefix on a first message.

## Cadence

| Day | Action |
|-----|--------|
| 0 | First email |
| 6 | One short follow-up |
| 14 | Final note, no pressure |
| 21 | Close as no response |

`linkbuilding.py due` lists what is owed. Do not send more than two follow-ups. Someone who declines, or asks to
stop, goes on the suppression list (`log --event declined`) and is never contacted again, on any page of that site.

## Volume

Start with 20 to 30 emails, not 100. Read every reply. Fix the hook, the asset or the target type, then widen.
Typical outcomes for cold pitches to relevant editors are low single digits to roughly 15 percent depending on the
tactic (see `types` in `skills/seo-linkbuilding/data/library.json`). Unlinked mentions and partner pages convert best, broken-link
and guest pitches worst. Replace the planning estimates with the campaign's own rates as soon as there are 20 sends.

Send a handful a day from a real mailbox on the business's own domain, in plain text, without tracking pixels at
first. Use one person's name consistently. Stop and investigate if bounces exceed about 5 percent.

## Handling replies

| Reply | What to do |
|-------|------------|
| "Yes, added" | Log `won` with the live URL. Verify it. Thank them. |
| "Yes, if you pay" | Decline politely. If you want the exposure anyway, treat it as a disclosed sponsored placement and expect `rel="sponsored"`. |
| "Link to us in return" | Decline. Reciprocal link swaps are a link scheme. A genuine mutual mention in real content is fine. |
| "Can you change X?" | Reasonable edits to your own asset are fine. Never agree to exact-match anchor text. |
| "No" or no reply after 21 days | Log it. Do not argue. |
| "Stop" | Log `unsubscribed`. The domain and the address are suppressed. |

## Law and platform rules

- **US (CAN-SPAM):** accurate sender and subject, a postal address, and an opt-out honoured promptly.
- **EU and UK (GDPR, PECR):** corporate addresses are generally contactable for relevant business proposals, but
  named individuals and sole traders are personal data. Keep the list small, relevant and documented, and honour
  objections immediately.
- **Contact data:** use publicly listed business addresses. Never guess an address from a pattern and never use a
  purchased list.
- **Communities:** never auto-post to Reddit, Quora, forums or comment sections. Participate as a person, disclose
  your affiliation, and follow each community's rules.

## After a link is won

Record the live URL (`log --event won --link-url ...`). `linkbuilding.py due` schedules verification at 30, 90 and
180 days. A link that disappears is logged as lost. Judge results with the four levels in the report's Measurement
section: exists, counted, moved something, paid back.
