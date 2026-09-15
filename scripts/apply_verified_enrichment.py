#!/usr/bin/env python3
"""Apply small verified enrichment patches over V4 sidecars in CI/build workspaces.

Files in data/enrichment are intentionally additive. They are used for carefully
verified priority-model facts that should not require rewriting an entire brand
sidecar. The script never derives or guesses vehicle values.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
PATCH_DIR = ROOT / "data" / "enrichment"


def merge_patch(base: dict, patch: dict) -> dict:
    out = dict(base)
    for key, value in (patch.get("brand_fields") or {}).items():
        out[key] = value

    models = dict(out.get("models") or {})
    for name, extra in (patch.get("models") or {}).items():
        merged = dict(models.get(name) or {})
        merged.update(extra or {})
        models[name] = merged
    out["models"] = models
    return out


def main() -> None:
    if not PATCH_DIR.exists():
        print("No verified enrichment directory; nothing to apply.")
        return

    applied = 0
    for patch_path in sorted(PATCH_DIR.glob("*.json")):
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        target = str(patch.get("target") or "").strip()
        brand = str(patch.get("brand") or "").strip()
        if not target or not brand:
            raise ValueError(f"Enrichment patch needs target and brand: {patch_path.name}")

        base_path = V4 / target
        if not base_path.exists():
            raise FileNotFoundError(f"Target V4 sidecar does not exist: {target}")
        base = json.loads(base_path.read_text(encoding="utf-8"))
        if base.get("brand") != brand:
            raise ValueError(
                f"Brand mismatch for {patch_path.name}: patch={brand!r}, base={base.get('brand')!r}"
            )

        merged = merge_patch(base, patch)
        base_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        applied += 1
        print(f"Applied verified enrichment: {brand} ({patch_path.name})")

    print(f"Applied {applied} verified enrichment patch(es).")


if __name__ == "__main__":
    main()
