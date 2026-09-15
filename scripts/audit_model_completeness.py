#!/usr/bin/env python3
"""Audit DriveSpecLab model-page data completeness.

A section is complete when it has a verified value, or when the model explicitly
marks that section as not applicable / not published by the official source.
Missing values are never inferred. Gallery completeness remains a separate hard
requirement of six verified images.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
OUT = ROOT / "data" / "audit"

ALIASES = {
    "engine": ["engine", "powertrain", "motor"],
    "horsepower": ["horsepower", "mild_hybrid_horsepower", "phev_horsepower", "power"],
    "torque": ["torque", "torque_lb_ft"],
    "transmission": ["transmission"],
    "efficiency": [
        "efficiency", "mpg_combined", "mpg_combined_up_to", "mpge_combined",
        "mild_hybrid_mpg_combined", "mpg_city_highway", "mpg_city_highway_combined",
        "mpge_city_highway_combined",
    ],
    "range": [
        "range_miles", "range_miles_up_to", "epa_range_miles", "epa_range_miles_up_to",
        "phev_electric_range_miles", "electric_range",
    ],
    "dimensions": ["dimensions", "length_in", "width_in", "height_in", "wheelbase_in"],
    "cargo": ["cargo", "cargo_cu_ft", "cargo_cu_ft_up_to", "cargo_volume_cu_ft", "bed_lengths"],
    "towing": ["towing_lbs_up_to", "towing_lbs", "towing", "max_towing_lbs"],
    "technology": ["technology", "tech", "infotainment"],
    "safety": ["safety", "adas", "driver_assistance"],
    "warranty": ["warranty"],
}

SECTIONS = [
    "engine", "horsepower", "torque", "transmission", "efficiency", "range",
    "dimensions", "cargo", "towing", "technology", "safety", "warranty",
]


def populated(value: object) -> bool:
    return value not in (None, "", [], {})


def has_any(model: dict, keys: list[str], brand: dict) -> bool:
    for key in keys:
        if populated(model.get(key)):
            return True
        if key == "warranty" and populated(brand.get("warranty")):
            return True
    return False


def explicit_resolution(model: dict, section: str) -> str | None:
    for key, label in (("not_applicable", "not_applicable"), ("not_published", "not_published")):
        values = model.get(key) or []
        if isinstance(values, str):
            values = [values]
        if section in {str(x).strip().lower() for x in values}:
            return label
    return None


def section_state(model: dict, section: str, brand: dict) -> str:
    if has_any(model, ALIASES[section], brand):
        return "verified"
    resolution = explicit_resolution(model, section)
    if resolution:
        return resolution
    return "missing"


def gallery_count(model: dict) -> int:
    gallery = model.get("gallery")
    if isinstance(gallery, list):
        return len({str(x).strip() for x in gallery if str(x).strip()})
    return 1 if populated(model.get("image")) else 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Missing fields are reported only; no values are guessed. Explicit not-applicable "
            "or official-source-not-published states resolve a section without inventing a value."
        ),
        "brands": {},
        "summary": {},
    }

    total = full_gallery = complete_specs = fully_complete = 0
    missing_gallery: list[str] = []
    incomplete_specs: list[dict] = []
    policy_resolved = 0

    for path in sorted(V4.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        brand_name = data.get("brand") or path.stem
        brand_result = {
            "models": {},
            "counts": {"models": 0, "gallery_6": 0, "spec_complete": 0, "fully_complete": 0},
        }

        for name, model in (data.get("models") or {}).items():
            status = str(model.get("status") or "").lower()
            if any(x in status for x in ("discontinued", "not currently sold", "no current official product page")):
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

            states = {section: section_state(model, section, data) for section in SECTIONS}
            missing_sections = [section for section, state in states.items() if state == "missing"]
            resolved_by_policy = [
                section for section, state in states.items() if state in ("not_applicable", "not_published")
            ]
            policy_resolved += len(resolved_by_policy)
            spec_ok = not missing_sections
            if spec_ok:
                complete_specs += 1
                brand_result["counts"]["spec_complete"] += 1
            else:
                incomplete_specs.append({"brand": brand_name, "model": name, "missing": missing_sections})

            source_present = bool(model.get("source"))
            trims_present = bool(model.get("trims"))
            full = gallery_ok and spec_ok and source_present and trims_present
            if full:
                fully_complete += 1
                brand_result["counts"]["fully_complete"] += 1

            brand_result["models"][name] = {
                "gallery_count": gc,
                "gallery_complete": gallery_ok,
                "section_states": states,
                "missing_spec_sections": missing_sections,
                "policy_resolved_sections": resolved_by_policy,
                "source_present": source_present,
                "trims_present": trims_present,
                "fully_complete": full,
            }

        report["brands"][brand_name] = brand_result

    def pct(value: int) -> float:
        return round((value / total * 100), 1) if total else 0.0

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
        "sections_resolved_as_not_applicable_or_not_published": policy_resolved,
    }
    report["missing_gallery"] = missing_gallery
    report["incomplete_specs"] = incomplete_specs

    (OUT / "model-completeness.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

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
        f"- Sections explicitly resolved as not applicable/not published: **{s['sections_resolved_as_not_applicable_or_not_published']}**",
        "",
        "## Policy",
        "Missing values remain missing until verified from an official manufacturer source. Explicit not-applicable or official-source-not-published states are tracked separately and never converted into guessed values.",
        "",
    ]
    (OUT / "MODEL_COMPLETENESS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
