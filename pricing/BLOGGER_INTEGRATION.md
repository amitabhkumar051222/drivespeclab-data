# Safe Blogger integration (not yet deployed)

The adapter at `pricing/lookup.js` supports `DSLPricing.fetchPrice({brand,model,year,trim})` on Blogger pages. It loads the JSON feed from **main**, not this PR branch.

**Do not embed it in production until this pull request is merged and all records intended for public display are reviewed.**

Example (after merging):
```html
<script src="https://cdn.jsdelivr.net/gh/amitabhkumar051222/drivespeclab-data@main/pricing/lookup.js"></script>
<script>
DSLPricing.fetchPrice({brand:"Toyota",model:"Camry",year:2026,trim:"LE"})
  .then(function(item) {
    if (!item) { console.log("Verified price unavailable"); return; }
    console.log(item.msrp_usd, item.destination_usd, item.msrp_source);
  })
  .catch(function() { console.log("Price feed temporarily unavailable"); });
</script>
```

Records in the current starter are `needs_reverification`, so the adapter deliberately returns null for them.

Never use `msrp_usd` as a final dealer OTD price. Full OTD needs taxable selling price, precise registration address/county, relevant tax rules, vehicle type/weight, and dealer quote.

Tests: `node pricing/lookup.test.cjs` and `python pricing/validate.py`.
