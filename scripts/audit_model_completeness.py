#!/usr/bin/env python3
"""Audit DriveSpecLab model-page data completeness.

Checks V4 brand sidecars against the fields used by the universal Tucson-style
model page. Produces a machine-readable JSON report plus a compact Markdown
summary. This script does not invent or infer missing vehicle data.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
OUT = ROOT / "data" / "audit"

CORE_FIELDS = [
    "year", "source", "trims",
    "engine", "horsepower", "torque", "transmission",
    "mpg_combined", "mpge_combined", "range_miles", "range_miles_up_to",
    "dimensions", "cargo", "towing_lbs_up_to",
    "technology", "safety", "warranty",
]

# Alternative keys accepted for a section to count as populated.
ALIASES = {
    "engine": ["engine", "powertrain"],
    "horsepower": ["horsepower", "mild_hybrid_horsepower", "phev_horsepower", "power"],
    "torque": ["torque", "torque_lb_ft"],
    "transmission": ["transmission"],
    "efficiency": ["mpg_combined", "mpge_combined", "mild_hybrid_mpg_combined", "efficiency"],
    "range": ["range_miles", "range_miles_up_to", "epa_range_miles", "epa_range_miles_up_to", "phev_electric_range_miles"],
    "dimensions": ["dimensions", "length_in", "width_in", "height_in", "wheelbase_in"],
    "cargo": ["cargo", "cargo_cu_ft", "cargo_volume_cu_ft"],
    "towing": ["towing_lbs_up_to", "towing", "max_towing_lbs"],
    "technology": ["technology", "tech", "infotainment"],
    "safety": ["safety", "adas", "driver_assistance"],
    "warranty": ["warranty"],
}

SECTIONS = [
    "engine", "horsepower", "torque", "transmission", "efficiency", "range",
    "dimensions", "cargo", "towing", "technology", "safety", "warranty",
]


def has_any(model: dict, keys: list[str], brand: dict) -> bool:
    for key in keys:
        v = model.get(key)
        if v not in (None, "", [], {}):
            return True
        if key == "warranty":
            v = brand.get("warranty")
            if v not in (None, "", [], {}):
                return True
    return False


def gallery_count(model: dict) -> int:
    g = model.get("gallery")
    if isinstance(g, list):
        return len([x for x in g if x])
    return 1 if model.get("image") else 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "Missing fields are reported only; no values are guessed.",
        "brands": {},
        "summary": {},
    }

    total = full_gallery = complete_specs = fully_complete = 0
    missing_gallery = []
    incomplete_specs = []

    for path in sorted(V4.glob("*.json")):
        if path.name == "STATUS.md":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        brand_name = data.get("brand") or path.stem
        brand_result = {"models": {}, "counts": {"models": 0, "gallery_6": 0, "spec_complete": 0, "fully_complete": 0}}

        for name, model in (data.get("models") or {}).items():
            status = str(model.get("status") or "").lower()
            if any(x in status for x in ["discontinued", "not currently sold", "no current official product page"]):
                continue

            total += 1
            brand_result["counts"]["models"] += 1
            gc = gallery_count(model)
            gallery_ok = gc >= 6
            if gallery_ok:
                full_gallery += 1
                brand_result["counts"]["gallery_6"] += 1
            else:
                missing_gallery.append(f"{brand_name} {name}")

            missing_sections = [sec for sec in SECTIONS if not has_any(model, ALIASES[sec], data)]
            spec_ok = len(missing_sections) == 0
            if spec_ok:
                complete_specs += 1
                brand_result["counts"]["spec_complete"] += 1
            else:
                incomplete_specs.append({"brand": brand_name, "model": name, "missing": missing_sections})

            full = gallery_ok and spec_ok and bool(model.get("source")) and bool(model.get("trims"))
            if full:
                fully_complete += 1
                brand_result["counts"]["fully_complete"] += 1

            brand_result["models"][name] = {
                "gallery_count": gc,
                "gallery_complete": gallery_ok,
                "missing_spec_sections": missing_sections,
                "source_present": bool(model.get("source")),
                "trims_present": bool(model.get("trims")),
                "fully_complete": full,
            }

        report["brands"][brand_name] = brand_result

    def pct(n: int) -> float:
        return round((n / total * 100), 1) if total else 0.0

    report["summary"] = {
        "current_models_audited": total,
        "models_with_6_gallery_images": full_gallery,
        "gallery_complete_pct": pct(full_gallery),
        "models_with_complete_spec_sections": complete_specs,
        "spec_complete_pct": pct(complete_specs),
        "fully_complete_models": fully_complete,
        "fully_complete_pct": pct(fully_complete),
        "models_missing_full_gallery": len(missing_gallery),
        "models_with_incomplete_specs": len(incomplete_specs),
    }
    report["missing_gallery"] = missing_gallery
    report["incomplete_specs"] = incomplete_specs

    (OUT / "model-completeness.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    s = report["summary"]
    lines = [
        "# DriveSpecLab Model Data Completeness",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"- Current models audited: **{s['current_models_audited']}**",
        f"- 6-image gallery complete: **{s['models_with_6_gallery_images']} ({s['gallery_complete_pct']}%)**",
        f"- Core spec sections complete: **{s['models_with_complete_spec_sections']} ({s['spec_complete_pct']}%)**",
        f"- Fully complete for universal model page: **{s['fully_complete_models']} ({s['fully_complete_pct']}%)**",
        "",
        "## Policy",
        "Missing values remain missing until verified from an official U.S. manufacturer source. No guessed specs or prices are added by this audit.",
        "",
    ]
    (OUT / "MODEL_COMPLETENESS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
