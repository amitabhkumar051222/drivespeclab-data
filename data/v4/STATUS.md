# DriveSpecLab V4 verification status

Updated: 2026-09-13

## V4 sidecars currently committed
- BYD — `data/v4/byd.json` (U.S. market-status case; no mainstream consumer passenger lineup in scope)
- Ford — `data/v4/ford.json` (all base model families covered; F-450 Platinum exact Super Duty row still pending final verification)
- Genesis — `data/v4/genesis.json` (current U.S. G70/G80/G90/GV60/GV60 Magma/GV70/Electrified GV70/GV80/GV80 Coupe pricing covered)
- GMC — `data/v4/gmc.json`
- Honda — `data/v4/honda.json`
- Hyundai — `data/v4/hyundai.json` (base U.S. model families covered with current official trim pricing; latest 2027 Santa Fe/Palisade used; current-listed 2025 KONA Electric added as a sidecar-only model)
- Jeep — `data/v4/jeep.json` (2026 Cherokee Turbo Hybrid added after re-verification)
- Land Rover — `data/v4/land-rover.json` (Range Rover, Defender, Discovery and Discovery Sport covered)
- Lexus — `data/v4/lexus.json` (current ES/IS/LC/LS/UX/NX/RX/RZ/TX/GX/LX covered; RC retained as discontinued reference)
- Mahindra — `data/v4/mahindra.json` (U.S. market-status case)
- Mazda — `data/v4/mazda.json`
- Nissan — `data/v4/nissan.json` (12 base model families aligned to current Nissan USA model years/pricing; Versa retained at current listed 2025 model year)
- Ram — `data/v4/ram.json`
- Subaru — `data/v4/subaru.json`
- Tata Motors — `data/v4/tata-motors.json` (U.S. market-status case)
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
Toyota, Chevrolet, Kia, Tesla, BMW, Mercedes-Benz, Audi and Porsche, plus the final Ford Super Duty F-450 Platinum price check.

After all brand sidecars are complete: integrate the V4 loader into the latest Blogger XML, migrate homepage Find Your Car/selectors to `window.DriveSpecLabDB`, remove obsolete embedded duplicate database code, validate XML and inline JavaScript, then live-test brand and `#usmodel=` routes.

Do not label the Blogger theme FINAL READY until all required brand sidecars, loader integration, XML validation, and live route tests pass.
