#!/usr/bin/env python3
"""Apply verified V6 enhancement data over V4 brand sidecars in-place.

This is intended for CI/build workspaces. It does not guess values and does not
replace V4 trims/MSRP unless a V6 field explicitly supplies a replacement.
Generated catalog/audit outputs can therefore consume richer verified details
without forcing the repository to duplicate complete brand files.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
V6 = ROOT / "data" / "v6"


def merge_brand(base: dict, patch: dict) -> dict:
    out = dict(base)
    if patch.get("verified_on"):
        out["verified_on"] = patch["verified_on"]
    if patch.get("source_policy"):
        out["source_policy"] = patch["source_policy"]
    models = dict(out.get("models") or {})
    for name, extra in (patch.get("models") or {}).items():
        merged = dict(models.get(name) or {})
        merged.update(extra or {})
        models[name] = merged
    out["models"] = models
    return out


def main() -> None:
    if not V6.exists():
        print("No V6 enhancement directory; nothing to apply.")
        return
    applied = 0
    for patch_path in sorted(V6.glob("*.json")):
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        brand = patch.get("brand")
        if not brand:
            continue
        base_path = V4 / patch_path.name
        if base_path.exists():
            base = json.loads(base_path.read_text(encoding="utf-8"))
            if base.get("brand") and base.get("brand") != brand:
                raise ValueError(f"Brand mismatch: {base_path.name}")
        else:
            base = {"brand": brand, "market": patch.get("market", "United States"), "models": {}}
        merged = merge_brand(base, patch)
        base_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        applied += 1
        print(f"Applied V6 overlay: {brand}")
    print(f"Applied {applied} V6 brand overlay(s).")


if __name__ == "__main__":
    main()
