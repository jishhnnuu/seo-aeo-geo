# Prospect Discovery

How to build a site-specific shortlist of about 100 link opportunities that are
relevant, live and worth an editor's time. Loaded by `seo-linkbuilding` at step 4.
The scoring and screening rules live in `scripts/linkbuilding.py`; this file covers
where candidates come from and how to qualify them before they reach the script.

A list of 100 is a target, not a quota. If fewer than 100 clear the bar, report the
shortfall and run more discovery. Never lower the bar to fill the list.

## Sources, in the order they usually pay off

| Source | Opportunity type | Cost | Typical yield |
|--------|------------------|------|---------------|
| Evergreen library for the industry (`linkbuilding.py library`) | local_citation, directory_listing, review_platform, brand_profile, product_launch | free or fee | 20 to 45 per site |
| Unlinked brand mentions | unlinked_mention | free | 0 to 30, depends on how known the brand is |
| Competitor link gap | competitor_gap | free | 15 to 60 raw, 5 to 20 after qualifying |
| Resource and curated-list pages | resource_page | free | 10 to 40 |
| Partners, suppliers, customers, members | partner_page | free | 5 to 25 |
| Expert-quote platforms | expert_quote | free tier | ongoing, 1 to 4 a month |
| Broken links on relevant pages | broken_link | free | 5 to 20 |
| Data or research pitch | digital_pr | free, needs an asset | 5 to 15 per asset |
| Disclosed sponsored placements, press wires | sponsored_placement, press_release | paid | as needed, for brand and AI visibility |

## Step by step

1. **Library.** `claude-seo run linkbuilding.py library --campaign <dir>` adds industry-matched
   sources. Set `--capabilities` at init so app-store entries appear only if the site ships an app,
   extension or plugin.
2. **Unlinked mentions.** Search the brand name and common variants excluding the site itself, for example
   `"Brand Name" -site:brand.com`. Open each result and confirm the page mentions the brand without linking.
   Record the page URL as `their_page_url`. These convert best because the writer already knows the brand.
3. **Competitor gap.** Pick 3 to 5 organic competitors from the SERPs for the target keywords (not just business
   competitors). Pull referring domains for each from the best available source, in this order: DataForSEO,
   Ahrefs MCP (if the plan allows it), Moz, Bing Webmaster (own site only), Common Crawl. Keep domains that link to
   two or more competitors and not to the site. Export to CSV with columns `domain, dr, da, traffic, notes` and run
   `linkbuilding.py ingest --source competitor_gap --type competitor_gap`. Label the metrics source in `metrics_source`.
4. **Resource pages.** Search patterns such as `"{topic}" "useful resources"`, `"{topic}" "recommended tools"`,
   `intitle:resources "{topic}"`, `"{topic}" inurl:links`. Keep pages that list external sites on the topic and were
   updated in the last two years. Ingest as `resource_page` with the page URL, the contact and a specific hook.
5. **Partners and customers.** Pages that list suppliers, integrations, members, sponsors or case studies where
   the site already has a real relationship. Ingest as `partner_page` with the `relationship` field filled.
6. **Broken links.** On the resource pages from step 4, check the outbound links. A dead link on a relevant page is
   a legitimate reason to write, but only if the site has a page that truly replaces it. Ingest as `broken_link`
   with `broken_url`, `their_page_url`, `asset_url` and `asset_summary`.
7. **Liveness.** `linkbuilding.py check-live --campaign <dir>` drops parked, suspended and dead domains.
8. **Screen.** `linkbuilding.py screen`, then read the rejection breakdown. If a rejection looks wrong, check the
   domain by hand before overriding; the rules are in `skills/seo-linkbuilding/data/blocklist.json`.

## Qualification checklist (do this for every prospect that survives screening)

- Open three recent pages. Is the topic genuinely close to the site's? Relevance outranks authority.
- Does the site have named authors, an About page, a working contact route and a real social presence?
- Is there organic traffic in a country that matters to the client? A high rating with almost no traffic is a
  warning, not a bargain.
- Skim one article. Count external links. A page with a long list of unrelated outbound links is a link farm.
- Search `site:domain.com`. A site that is barely indexed is not worth the effort.
- Run `claude-seo run domain_history.py <domain>` for finalists. A decade-old domain that recently changed topic
  or owner is often an expired domain re-registered for its history.
- Does the listing use seller language such as "guest post service", "dofollow guaranteed", "instant publish" or
  quotes a price per link? If so it is a seller, not an editor. Treat as paid and disclosed, or skip it.

## Metrics: what to trust

DR, DA and traffic figures from a seller are claims. Tool figures from different vendors disagree by design. Always
record the source, prefer tool data you pulled yourself, and use the numbers to rank prospects, never to promise
results. The report labels every metric with its source.

## What to do with paid guest-post sheets

Do not buy from them. Three uses are legitimate:

- **Blocklist.** Domains that appear across several seller sheets, or that show gambling, adult or piracy content,
  fake `.edu` lookalikes, identical DA/DR across unrelated sites, or topic-hopping content farms, are in
  `skills/seo-linkbuilding/data/blocklist.json`. Add new ones as you meet them.
- **Seller-listed demotion.** A real publisher that also sells posts is not a free prospect. The script treats
  every domain in `seller_listed_domains.txt` as paid and disclosed only.
- **Direct buying of disclosed sponsorship.** A few real publishers in these sheets (regional newspapers, national
  news sites) run labelled sponsored sections. If you want brand exposure there, ask their advertising desk
  directly, get the price in writing and expect `rel="sponsored"`. See [Google's guidance on qualifying outbound
  links](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links).

## .edu links

Real university pages that earn a link on merit (research collaboration, a scholarship the business funds for a
real reason, a faculty citation) are valuable. Hunting for `.edu` pages that anyone can edit, such as learning-system
profile pages and student portfolios, is not. Lookalike domains such as `*.edu.co.bz` are commercial domains and
carry no educational authority. The script excludes them.
