#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog"
SEO = ROOT / "data" / "seo"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    brands = load(CATALOG / "brand-registry-live.json")
    us = load(CATALOG / "cars.json")
    global_ref = load(CATALOG / "global-cars-live.json")
    routes = load(SEO / "model-routes-live.json")

    rows = brands.get("brands") or []
    us_brands = [b for b in rows if b.get("market_group") == "US"]
    global_brands = [b for b in rows if b.get("market_group") != "US"]
    global_names = {b.get("name") for b in global_brands}

    assert len(rows) == 25, f"Expected 25 brands, found {len(rows)}"
    assert len(us_brands) == 22, f"Expected 22 U.S. brands, found {len(us_brands)}"
    assert global_names == {"BYD", "Tata Motors", "Mahindra"}, global_names
    assert all(not b.get("include_in_us_finder") for b in global_brands)
    assert all(c.get("include_in_us_finder") is False for c in (global_ref.get("cars") or []))

    live_routes = [r for r in (routes.get("routes") or {}).values() if isinstance(r, dict) and r.get("url_status") == "live"]
    generated = us.get("generated") or brands.get("generated") or global_ref.get("generated")

    manifest = {
        "generated": generated,
        "version": 1,
        "brand_count": len(rows),
        "us_brand_count": len(us_brands),
        "global_brand_count": len(global_brands),
        "us_model_count": len(us.get("cars") or []),
        "global_reference_model_count": len(global_ref.get("cars") or []),
        "live_model_route_count": len(live_routes),
        "feeds": {
            "brands": "data/catalog/brand-registry-live.json",
            "us_models": "data/catalog/cars.json",
            "global_models": "data/catalog/global-cars-live.json",
            "live_routes": "data/seo/model-routes-live.json",
        },
        "rules": [
            "U.S. catalog remains primary for DriveSpecLab.",
            "BYD, Tata Motors and Mahindra stay in a separate Global/India section unless verified U.S. retail availability changes.",
            "Theme reads live GitHub feeds with jsDelivr fallback so catalog changes do not require Blogger theme edits.",
            "Dedicated Blogger model pages override database hash routes through model-routes-live.json.",
        ],
    }
    out = CATALOG / "catalog-manifest-live.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("brand_count", "us_brand_count", "global_brand_count", "us_model_count", "global_reference_model_count", "live_model_route_count")}, indent=2))


if __name__ == "__main__":
    main()
