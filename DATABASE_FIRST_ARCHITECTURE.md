# DriveSpecLab database-first architecture

DriveSpecLab's vehicle database is independent of Blogger posts.

## Canonical vehicle data

- Base model families: `data/db/part-01.txt` … `part-05.txt`
- Verified brand/model sidecars: `data/v4/*.json`
- Front-end catalog: `data/catalog/cars.json`
- Upcoming index: `data/catalog/upcoming.json`
- Price/model change log: `data/catalog/change-log.json`
- Comparison index: `data/compare/cars.json`

## Routing

Every database model uses the existing dynamic route:

`/search/label/<brand>#usmodel=<model>`

No Blogger post is required for a vehicle to exist in the database.

## Blogger posts

Blogger posts are editorial content only: reviews, comparisons, buying guides, news and selected long-form SEO articles. Bulk model-page publishing is not part of the database architecture.

## Updates

Official-source pages are monitored separately. A detected web-page change does not blindly overwrite a price. Verified database edits regenerate catalog/search/compare files automatically and the change log records price/year/status/trim-count changes.
