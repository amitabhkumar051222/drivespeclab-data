# DriveSpecLab V4 verification status

Updated: 2026-09-13

## V4 sidecars currently committed
- Jeep — `data/v4/jeep.json`
- Mazda — `data/v4/mazda.json`
- Ram — `data/v4/ram.json`
- Subaru — `data/v4/subaru.json`
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
Toyota, Volkswagen, Ford, Honda, Chevrolet, Nissan, Hyundai, Kia, Tesla, BMW, Mercedes-Benz, Audi, Porsche, Lexus, Land Rover, Genesis, GMC.

BYD, Mahindra and Tata Motors remain special market-status cases because they do not have a mainstream current U.S. retail passenger-vehicle lineup in the base project scope.

Do not label the Blogger theme FINAL READY until all required brand sidecars, loader integration, XML validation, and live route tests pass.
