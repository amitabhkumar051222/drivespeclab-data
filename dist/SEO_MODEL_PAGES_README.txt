DriveSpecLab SEO Model Page Import Pack
===================================

Generated: 2026-09-14
Model posts generated: 279
Brands with at least one current model: 22
No-current-U.S.-lineup brand cases: BYD, Mahindra, Tata Motors

Files
-----
- blogger-model-pages-all.atom.xml : all generated model posts in one Blogger Atom import.
- blogger-import-by-brand/          : smaller per-brand import files.
- model-pages-manifest.csv          : QA manifest.
- ../data/seo/model-routes-predicted.json : predicted paths, NOT production routing yet.

Important production rule
-------------------------
Do not switch DriveSpecLab brand/model buttons from #usmodel routes to the predicted paths until the Blogger import has completed and the live sitemap has been crawled. Blogger is the source of truth for the final permalink.

Publishing strategy
-------------------
The generated posts use August 2026 publication timestamps so they do not bury September 2026 editorial posts on the homepage. Each post is labeled Vehicle Database, Specifications, and the brand name.

After import
------------
1. Confirm a few imported model pages in Blogger.
2. Crawl the live sitemap to collect the real URLs.
3. Build a production model-routes.json from real URLs.
4. Update the V6.14 theme so brand cards and related-model links point to the real SEO pages while retaining #usmodel as a fallback.
