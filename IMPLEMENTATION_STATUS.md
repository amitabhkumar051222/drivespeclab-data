# DriveSpecLab consistency update — 21 October 2026

## Implemented

- The existing external V4 script loads `js/catalog-consistency.js` on home and model pages. No Blogger theme replacement is required for this adapter.
- Homepage cards, finder and homepage comparison consume catalog price and year together. Brand prefixes are not repeated in display names; stable IDs and model keys remain intact.
- Search reacts to typing and filter selection. Transmission data is carried from catalog details. Unknown fuel types are not classified as gasoline.
- Homepage comparison exposes source/date and detailed model-family specifications plus a trim selector. A trim selection only changes fields recorded for that trim; family performance figures remain explicitly qualified.
- Internal version labels and the model-hero placeholder are removed; duplicate model navigation is consolidated.
- Three existing model articles (RAV4, CR-V, Tucson) were retrieved and marked with a link check. Matching model-year cards link to them. Other models keep their working database routes until their article links are confirmed. This does not create new articles or change canonical tags.
- The build runs in an isolated temporary workspace, validates IDs/prices/compare alignment, and only writes changed output. It does not advance verification dates or rewrite unchanged files just to update a timestamp.
- Source monitoring retains the last successful fingerprint on failure and retains pending review items across runs. Effective catalog sources are monitored alongside brand sidecars.

## Validation

Python regression tests cover unknown/mixed fuel classifications, display identity, transmission propagation, failed-source recovery and persistent pending changes. A Node DOM test covers homepage price/year, SEO route, names, transmission, input search, trim price and idempotent rendering. Integration was also exercised against the captured live homepage and its existing inline scripts.

## Limits and remaining editorial work

The site contains both repository records and older theme-embedded additions. The adapter preserves those additions, prioritizes repository records for matching models, and does not certify their accuracy. All-brand specification completion requires field-by-field official-source research. The pre-existing completeness report lists 30 fully complete models out of 278 audited sidecar models; the generated catalog contains 279 entries. Those are different audit populations, not a claim that all catalog models are complete.

Manufacturer page-change detection is automatic; accepting new prices/specifications remains a reviewed enrichment operation. There is no universal official vehicle-price API connected. Failed source checks never turn into new prices.

Blogger article content, bulk publishing, theme markup replacement and Search Console indexing requests require their respective write access. Do not import the legacy bulk Atom pack as a shortcut: existing model articles must be checked for duplication first.

## Operations

Run `python scripts/update_car_database.py --check` for a dry run, then without `--check` to write validated generated outputs. Daily existing build/monitor schedules remain in place. Run `npm ci && npm test` and `python -m unittest discover -s tests -v` for regressions. Resolve a source-monitor item only after reviewing its official page and updating the relevant enrichment file; remove that URL from the pending list in the same reviewed change.

Rollback the adapter by reverting the loader appended to `js/drivespeclab-v4.js`. Existing theme search and comparison remain available without it.
