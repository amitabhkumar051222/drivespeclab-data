# DriveSpecLab price-data foundation

This directory is **not** a complete, automatically refreshed U.S. pricing system.

- `vehicle-prices.json` includes sample reference records with `needs_reverification` status. A price is eligible for public auto-display only after independently checking its official source, setting `verified_on`, and changing status to `verified`.
- `tax-rules.json` stores source-linked reference rules. Texas 6.25% tax does not imply that MSRP is the taxable transaction value. Base registration fees may differ by vehicle and county.
- `validate.py` checks data *structure* every day with GitHub Actions. It **does not** fetch manufacturer sites, update MSRP, validate fee law or calculate a final dealer quote.
- Live Blogger calculator integration should fetch the published JSON via a stable endpoint, filter `status === "verified"`, and display **partial MSRP-based estimates only** unless all transaction-specific fees and taxes have been obtained.
- Prior to production, add model-year coverage, a pricing update procedure, source freshness controls, VIN/vehicle classification, ZIP/county tax rules, titling fees, additional vehicle/electric/heavyweight fees, error-handling, and end-to-end testing.
- Do not overwrite or delete existing car-specification datasets in this repository.
