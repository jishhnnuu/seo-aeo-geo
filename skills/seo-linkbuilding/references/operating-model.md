# Link Building Operating Model (portfolio edition)

How to run link building across many sites, your own and clients', with little or no spend. Loaded by
`seo-linkbuilding` when the question is strategy, budget, sequencing or multi-site operations rather than one campaign.
Per-campaign mechanics are in [prospect-discovery.md](prospect-discovery.md), [outreach-playbook.md](outreach-playbook.md)
and [site-readiness.md](site-readiness.md).

## The thesis

Links are the outcome of four things, in this order of importance: a reason to link (the asset), relevance (the right
people), a pitch that respects the editor's time, and follow-through. A long list of domains is the cheapest and least
valuable of the four. Money buys speed and data. It does not buy links that last.

## What a one-time data export can and cannot do

A single month of access to a commercial link index (Ahrefs, Semrush, DataForSEO) can produce, per sector: the sites
that rank for the sector's main searches, the referring domains of the top five of them, their broken inbound links
and their best-linked pages. That is raw material, typically tens of thousands of rows.

It cannot produce a finished list:

- **Vetting is the bottleneck.** Each candidate still needs relevance, editorial standards, outbound-link and contact
  checks. Plan on a vetted library of a few hundred per sector at most, reading three pages per site.
- **It decays.** Ratings and traffic move monthly, sites die, editors leave. Treat a stored library as dated, re-check
  liveness before each use and re-vet yearly.
- **Terms of use apply.** Read the provider's terms before storing exports long term or sharing them with clients.
  Keep exports internal, and keep the stable parts (platforms, patterns, rules), not the volatile numbers.
- **The connected Ahrefs account must include API access.** In October 2026 the account connected to this session
  returned "Insufficient plan" on every call, including the free domain-rating lookup.

So the reusable asset is a sector library of vetted pools plus the repeatable discovery recipe, not a frozen
list of 1,000 domains reused unchanged for every client.

## Free data stack (what to use when there is no budget)

| Need | Free source | Limits |
|------|-------------|--------|
| Own links, own broken links | Google Search Console Links report, Ahrefs Webmaster Tools, Bing Webmaster Tools | Verified own sites only |
| Authority proxy for any domain | Moz API free tier, Open PageRank, Common Crawl web graph (`commoncrawl_graph.py`) | Different scales; triangulate, never trust one |
| Popularity proxy | Tranco top-sites ranking | Top sites only |
| Who links to a competitor | Common Crawl hyperlink graph (domain level) | Quarterly, no anchors, heavy download |
| Competitors and SERP layout | Manual search plus `serp` research via WebSearch | Slow, fine for 5 competitors |
| Contact route | The site's own contact, about and author pages; schema.org contact points | Public information only |
| Link still live | `verify_backlinks.py` | Needs JavaScript pages checked by hand |

Three free proxies that agree are a better filter than one paid number that may be wrong.

## Contact checking without a paid tool

Checks that are safe and free: find the named editor or author on the site's own pages, take only a publicly listed
address, confirm the address's domain accepts mail (an MX record exists), and prefer a named person over a role
address. Do not guess patterns such as firstname.lastname. Do not probe mailboxes with SMTP tests: they are unreliable
and can damage the sending reputation. The real verification is the first 20 to 30 sends, where a bounce rate above
about 5 percent means stop and fix the list.

## Sequencing for a portfolio

1. **Triage every site (week 0).** Industry, geography, stage, existing links, linkable assets, money pages. Capture a
   baseline: referring domains, Search Console clicks and impressions for target pages.
2. **Readiness first.** A site with no asset and no About page gets fixes before outreach, not after.
3. **Foundation links (weeks 1 to 2).** Entity, citation, profile and directory listings from the sector library.
   These are quick, high acceptance, and set up the entity signals AI answer engines read.
4. **Relationship links (the engine, weeks 2 onward).** In order of return per hour:
   unlinked mentions, then partners, suppliers and customers, then expert quotes (two or three a week), then
   resource pages and broken links, then one data or research asset per quarter pitched to 20 to 30 named people,
   then a small number of guest contributions on genuinely editorial sites.
5. **Measure and compound (monthly).** Compare each batch with its baseline and the planning estimate. Kill the
   tactics that fail, double the ones that work.

## Plays by industry

| Industry | Best free plays | Watch out for |
|----------|-----------------|---------------|
| SaaS and B2B | Software directories and review sites, integration partner pages, benchmark data, free tool, expert quotes | Directory spam; chasing generic "guest post" |
| E-commerce | Supplier and maker pages, product review and gift-guide editors, local press, original test data | Affiliate-heavy sites, thin guides |
| Local service | Citations, chamber and association pages, local press, sponsorships, supplier pages, cost guides | Inconsistent name, address and phone |
| Agency | Case studies the client co-promotes, client site mentions, industry surveys, podcasts | Linking only to your own client sites |
| Healthcare, legal, finance | Professional directories, association membership, credentialed expert quotes, reviewed guides | Weak credentials; claims without sources; strict advertising rules |
| Real estate | Local market data, neighbourhood guides, local press, partner trades | Duplicate listings content |
| Publisher | Data stories, source directories, syndication partners that canonical back | Syndication without canonical |
| Nonprofit | Funder and partner pages, impact data, community resource pages, volunteer-site listings | Dormant partner pages |

## Portfolio rules that protect everyone

- **One suppression list across all clients.** Someone who declined for client A is not pitched for client B next week.
- **Contact frequency cap.** At most one pitch per site per month across the whole portfolio.
- **Sector pools, not one giant list.** Each client draws the best-matched prospects from its sector pool.
- **No cross-linking for ranking.** Your own sites and clients' sites do not link to each other to pass authority.
- **Disclosure.** Every paid placement is labelled and uses `rel="sponsored"`.

## Spend ladder

| Level | Spend | What it adds |
|-------|-------|--------------|
| 0 | None, time only | Everything above. Roughly 4 to 6 hours a week per site in the first quarter |
| 1 | One month of a link-index tool in a burst | Competitor referring-domain exports for every sector and client at once |
| 2 | A contact-lookup tool, if bounce rates justify it | Faster named-contact finding |
| 3 | Disclosed sponsorship, a wire release | Brand reach and AI citation value, not rankings; judge on traffic and leads |

## How success is judged

Four levels: the link exists, search tools count it, the linked page moved, and it paid back in leads or traffic. Expect
the first earned links from outreach in weeks 4 to 8 and measurable movement from month 2 to 4. A campaign with no
baseline cannot be judged, so record one first.
