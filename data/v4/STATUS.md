# DriveSpecLab V4 verification status

Updated: 2026-09-13

## V4 sidecars currently committed
- BMW — `data/v4/bmw.json` (21 base model families covered with current official BMW USA model/trim MSRP data; 750e/760i are retained without guessed MSRP where exact current official starting price was not surfaced)
- BYD — `data/v4/byd.json` (U.S. market-status case; no mainstream consumer passenger lineup in scope)
- Chevrolet — `data/v4/chevrolet.json` (current gas, EV, truck/SUV and 2027 Corvette-family pricing covered; unpublished Corvette Grand Sport X 2LT/3LT MSRP values are not estimated)
- Ford — `data/v4/ford.json` (all base model families covered; all 15 current 2027 Super Duty pickup model rows including F-450 Platinum are verified from Ford Build & Price)
- Genesis — `data/v4/genesis.json` (current U.S. G70/G80/G90/GV60/GV60 Magma/GV70/Electrified GV70/GV80/GV80 Coupe pricing covered)
- GMC — `data/v4/gmc.json`
- Honda — `data/v4/honda.json`
- Hyundai — `data/v4/hyundai.json` (base U.S. model families covered with current official trim pricing; latest 2027 Santa Fe/Palisade used; current-listed 2025 KONA Electric added as a sidecar-only model)
- Jeep — `data/v4/jeep.json` (2026 Cherokee Turbo Hybrid added after re-verification)
- Kia — `data/v4/kia.json` (current Telluride, EV6, Carnival, Sorento, EV9, Niro/Niro EV, EV3, Sportage, K5, K4/K4 Hatchback and Seltos pricing covered; unpublished EV9 GT MSRP is not estimated)
- Land Rover — `data/v4/land-rover.json` (Range Rover, Defender, Discovery and Discovery Sport covered)
- Lexus — `data/v4/lexus.json` (current ES/IS/LC/LS/UX/NX/RX/RZ/TX/GX/LX covered; RC retained as discontinued reference)
- Mahindra — `data/v4/mahindra.json` (U.S. market-status case)
- Mazda — `data/v4/mazda.json`
- Mercedes-Benz — `data/v4/mercedes-benz.json` (26 base model families covered across gas, hybrid, PHEV, EV, AMG and Maybach; current Price Coming Soon values remain null rather than estimated)
- Nissan — `data/v4/nissan.json` (12 base model families aligned to current Nissan USA model years/pricing; Versa retained at current listed 2025 model year)
- Ram — `data/v4/ram.json`
- Subaru — `data/v4/subaru.json`
- Tata Motors — `data/v4/tata-motors.json` (U.S. market-status case)
- Tesla — `data/v4/tesla.json` (current Model 3, Model Y and Cybertruck lineup covered; exact Tesla cash prices are used only where surfaced by official Tesla pages, and current Premium/Performance Model Y prices are intentionally left unpublished rather than estimated)
- Toyota — `data/v4/toyota.json` (25 base model families covered; latest currently priced 2027 model years used where Toyota has published retail pricing, with exact grade MSRP rows and no estimates for unpublished future-year prices)
- Volkswagen — `data/v4/volkswagen.json`
- Volvo — `data/v4/volvo.json`

## Loader
- `js/drivespeclab-v4.js`
- Loads the five-part compact V3 base database.
- Loads a brand-specific V4 sidecar when available.
- Uses verified V4 trim MSRP as the displayed starting price.
- Appends current sidecar-only models that are absent from the older base database.
- Hides base models explicitly marked discontinued/not currently sold in the V4 sidecar.
- Exposes `window.DriveSpecLabDB` and dispatches `DriveSpecLabDBReady`.

## Still pending before FINAL READY
Audi and Porsche.

After all brand sidecars are complete: integrate the V4 loader into the latest Blogger XML, migrate homepage Find Your Car/selectors to `window.DriveSpecLabDB`, remove obsolete embedded duplicate database code, validate XML and inline JavaScript, then live-test brand and `#usmodel=` routes.

Do not label the Blogger theme FINAL READY until all required brand sidecars, loader integration, XML validation, and live route tests pass.
