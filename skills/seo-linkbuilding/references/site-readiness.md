# Site Readiness for Link Building

What a website must have before outreach is worth doing, and how to change it when it does not. Loaded at step 2
and when writing the report's Site Readiness section. The automated checks are in `linkbuilding.py readiness`.

Link building multiplies what a site already offers. A site with nothing worth citing will get a low reply rate
from outreach however good the emails are, which is why readiness comes first.

## The checks and why each matters

| Check | Why an editor or Google cares |
|-------|-------------------------------|
| HTTPS, indexable, canonical, mobile viewport | Editors check on a phone; links to a noindex or duplicate URL are wasted |
| Organization or LocalBusiness schema with `sameAs` | Lets mentions and profiles resolve to one entity, which also feeds AI answer engines |
| Contact route, About page naming real people | Editors will not link to an anonymous site |
| Named authors with credentials | Trust signal for editors and an E-E-A-T signal for search |
| Blog or resources hub | A home for linkable pages |
| A linkable asset | The reason anyone would link at all. This is the heaviest check |
| Privacy and terms | Signals a real business |
| Phone and address (local only) | Citations must match the site exactly |

## Linkable assets: what earns links

People link to things that save them work or give them a fact to cite. In rough order of reliability:

1. **Original data.** A survey, benchmark, or analysis of your own anonymised numbers, with the method stated and the
   dataset downloadable. Writers cite statistics.
2. **A free tool or calculator** that answers a question people actually search for.
3. **A definitive guide** that is clearly better than what ranks today: current, specific, with original images.
4. **A template or checklist** people can use immediately.
5. **A named expert** with credentials who has said something quotable. Pages about people earn links when the people
   are cited.
6. **Local value** for local businesses: cost guides with real quotes, community resources, event pages.

Industry-specific starting ideas are in `ASSET_IDEAS` in `scripts/linkbuilding.py` and appear in the report.

## Make the asset easy to cite

- A stable, short URL that will not change.
- Visible author, publication date and last-updated date.
- Key figures stated in plain sentences near the top, not buried in an image.
- A "how to cite" line, downloadable data, and an embed code for charts where that fits.
- Not gated behind a form. Nobody links to a page they cannot read.
- Server-rendered or pre-rendered. Content that exists only after JavaScript runs is invisible to many checkers.

## Route the value inside the site

Link assets earn links to themselves. Pass that strength on by linking from the asset to the pages that sell or
serve, with descriptive anchors, and from related articles back to the asset. Check coverage with `/seo audit`.

## Anchor text

Aim for mostly branded and plain-URL anchors, as in the distribution targets in `seo-backlinks`. Never ask a site for an
exact-match keyword anchor. Editors choose the anchor, and over-optimised anchors are a pattern spam classifiers look for.

## What to stop doing

- Footer or sidebar "link to us" blocks and sitewide sponsored links.
- Thin location pages and mass-produced AI articles built to attract links. They do not earn them.
- Buying undisclosed dofollow links, link exchanges and private blog networks. Google treats these as link spam.
  See [Google's spam policies](https://developers.google.com/search/docs/essentials/spam-policies#link-spam).

## Timeline and honest expectations

| Window | What realistically happens |
|--------|----------------------------|
| Weeks 0 to 2 | Fix readiness items, build or choose the asset, complete profile and citation listings |
| Weeks 2 to 6 | First outreach batch of 20 to 30, learn from replies |
| Months 2 to 4 | First earned links land; measurement shows early movement on linked pages |
| Months 4 to 6 | Compounding: earlier links get discovered, new content starts attracting links unprompted |

Rankings depend on far more than links. Treat link building as one lever, measured against its own baseline.
