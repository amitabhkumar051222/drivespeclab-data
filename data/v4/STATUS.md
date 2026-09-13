# DriveSpecLab V4 verification status

Updated: 2026-09-13

## V4 sidecars currently committed — 25/25 brands
- Audi — `data/v4/audi.json` (15 base model families covered with current official Audi USA / Audi of America pricing; unpublished future pricing remains null rather than estimated)
- BMW — `data/v4/bmw.json` (21 base model families covered with current official BMW USA model/trim MSRP data; exact current prices are not guessed where BMW does not surface them)
- BYD — `data/v4/byd.json` (U.S. market-status case; no mainstream consumer passenger lineup in scope)
- Chevrolet — `data/v4/chevrolet.json` (current gas, EV, truck/SUV and Corvette-family pricing covered; unpublished prices are not estimated)
- Ford — `data/v4/ford.json` (all base model families covered; current Super Duty rows including F-450 Platinum verified from Ford Build & Price)
- Genesis — `data/v4/genesis.json` (current U.S. G70/G80/G90/GV60/GV60 Magma/GV70/Electrified GV70/GV80/GV80 Coupe pricing covered)
- GMC — `data/v4/gmc.json`
- Honda — `data/v4/honda.json`
- Hyundai — `data/v4/hyundai.json` (base U.S. model families covered with current official trim pricing; current-listed KONA Electric retained where applicable)
- Jeep — `data/v4/jeep.json` (current U.S. Jeep model families covered; newly verified Cherokee generation included)
- Kia — `data/v4/kia.json` (current Telluride, EV6, Carnival, Sorento, EV9, Niro/Niro EV, EV3, Sportage, K5, K4/K4 Hatchback and Seltos pricing covered; unpublished MSRP is not estimated)
- Land Rover — `data/v4/land-rover.json` (Range Rover, Defender, Discovery and Discovery Sport families covered)
- Lexus — `data/v4/lexus.json` (current ES/IS/LC/LS/UX/NX/RX/RZ/TX/GX/LX covered; discontinued reference models are explicitly labeled)
- Mahindra — `data/v4/mahindra.json` (U.S. market-status case)
- Mazda — `data/v4/mazda.json`
- Mercedes-Benz — `data/v4/mercedes-benz.json` (base model families covered across gas, hybrid, PHEV, EV, AMG and Maybach; Price Coming Soon values remain null rather than estimated)
- Nissan — `data/v4/nissan.json` (base model families aligned to current Nissan USA model years/pricing; older current-listed model years retained only where Nissan still lists them)
- Porsche — `data/v4/porsche.json` (718, 911, Taycan, Panamera, Macan/Macan Electric and Cayenne/Cayenne Electric families covered with current Porsche USA configurator pricing)
- Ram — `data/v4/ram.json`
- Subaru — `data/v4/subaru.json`
- Tata Motors — `data/v4/tata-motors.json` (U.S. market-status case)
- Tesla — `data/v4/tesla.json` (current Model 3, Model Y and Cybertruck lineup covered; exact Tesla cash prices are used only where surfaced by official Tesla pages, and unpublished variants are not estimated)
- Toyota — `data/v4/toyota.json` (25 base model families covered; latest currently priced model years used where Toyota has published retail pricing, with no estimates for unpublished future-year prices)
- Volkswagen — `data/v4/volkswagen.json`
- Volvo — `data/v4/volvo.json`

## Loader
- `js/drivespeclab-v4.js`
- Loads the five-part compact V3 base database.
- Loads a brand-specific V4 sidecar when available.
- Uses verified V4 trim MSRP as the displayed starting price.
- Appends current sidecar-only models that are absent from the older base database.
- Hides base models explicitly marked discontinued/not currently sold in the V4 sidecar.
- Exposes `window.DriveSpecLabDB` and dispatches `DriveSpecLabDBReady` on brand pages.

## Database phase
- Brand sidecars: COMPLETE (25/25)
- V4 loader: COMMITTED
- Unpublished manufacturer prices: intentionally left null / Price Coming Soon
- No guessed trim MSRP values should be introduced during theme integration.

## Blogger theme integration
- V4 loader reference integrated into the final external-database Blogger XML artifact.
- Old `drivespeclab-db.js` loader reference removed.
- Old embedded `var DB=` database absent.
- Five-part external compact DB bridge retained for homepage Finder compatibility.
- Strict XML parse: PASS.
- Custom inline JavaScript syntax checks: PASS (Blogger-generated dynamic script excluded from static Node check).
- All 25 brand names/shells present in the final XML source.

## Remaining before FINAL READY on the live site
Upload the validated V4 Blogger XML, then live-test the homepage Finder plus representative brand and `#usmodel=` routes (Toyota/RAV4, Honda/CR-V, Ford/F-150, Tesla/Model Y, Land Rover and no-U.S.-lineup brand cases). The theme should only be called fully live/FINAL after those route tests pass.
