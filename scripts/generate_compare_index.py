#!/usr/bin/env python3
"""Generate a compact comparison index from DriveSpecLab DB + verified sidecars.

The result is safe for front-end use and prefers confirmed live SEO URLs when available,
otherwise preserving the existing brand/#usmodel route.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "data" / "db"
V4_DIR = ROOT / "data" / "v4"
LIVE_ROUTES = ROOT / "data" / "seo" / "model-routes-live.json"
OUT = ROOT / "data" / "compare" / "cars.json"


def norm(s: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def route_brand(b: str) -> str:
    if b == "Land Rover":
        return "Land-Rover"
    if b == "Tata Motors":
        return "Tata"
    return b


def base_model(x: list) -> dict:
    z = {
        "name": x[0] if len(x) > 0 else "",
        "year": x[1] if len(x) > 1 else "",
        "body": x[2] if len(x) > 2 else "",
        "powertrain": x[3] if len(x) > 3 else "",
        "drivetrain": x[4] if len(x) > 4 else "",
        "seating": x[5] if len(x) > 5 else "",
        "price": x[6] if len(x) > 6 else "",
        "key_detail": x[7] if len(x) > 7 else "",
    }
    if len(x) > 8 and isinstance(x[8], dict):
        z.update(x[8])
    return z


def load_db() -> dict:
    return json.loads("".join((DB_DIR / f"part-{i:02d}.txt").read_text(encoding="utf-8") for i in range(1, 6)))


def load_sidecars() -> dict[str, dict]:
    out = {}
    for p in V4_DIR.glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("brand"):
            out[d["brand"]] = d
    return out


def side_for(sidecar: dict | None, model: str) -> dict:
    models = (sidecar or {}).get("models", {}) or {}
    if model in models:
        return models[model] or {}
    n = norm(model)
    for k, v in models.items():
        if norm(k) == n:
            return v or {}
    return {}


def live_routes() -> dict:
    if not LIVE_ROUTES.exists():
        return {}
    return (json.loads(LIVE_ROUTES.read_text(encoding="utf-8")).get("routes") or {})


def trim_price(side: dict) -> str:
    vals = []
    for t in side.get("trims", []) or []:
        try:
            v = float(t.get("msrp"))
            if v > 0:
                vals.append(v)
        except Exception:
            pass
    return f"${min(vals):,.0f}" if vals else ""


def fallback_url(brand: str, model: str) -> str:
    return f"/search/label/{quote(route_brand(brand))}#usmodel={quote(model)}"


def main() -> None:
    db = load_db()
    sides = load_sidecars()
    routes = live_routes()
    rows = []

    for brand, pack in (db.get("b") or {}).items():
        sidecar = sides.get(brand)
        for raw in (pack[4] if len(pack) > 4 else []):
            m = base_model(raw)
            name = str(m.get("name") or "").strip()
            if not name:
                continue
            side = side_for(sidecar, name)
            live = routes.get(f"{brand}|{name}") or {}
            trims = side.get("trims", []) or []
            rows.append({
                "id": "spec-" + re.sub(r"[^a-z0-9]+", "-", f"{brand}-{name}".lower()).strip("-"),
                "brand": brand,
                "model": name,
                "year": str(side.get("year") or m.get("year") or ""),
                "body": str(side.get("body") or m.get("body") or ""),
                "powertrain": str(side.get("powertrain") or m.get("powertrain") or ""),
                "drivetrain": str(side.get("drivetrain") or side.get("default_drive") or m.get("drivetrain") or ""),
                "seating": str(side.get("seats") or m.get("seating") or ""),
                "starting_price": trim_price(side) or str(m.get("price") or ""),
                "trim_count": len(trims),
                "verified_on": str(side.get("verified_on") or ""),
                "source": str(side.get("source") or (sidecar or {}).get("source") or ""),
                "url": str(live.get("url") or fallback_url(brand, name)),
                "url_status": "live" if live.get("url") else "hash-fallback",
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(rows),
        "cars": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compare index: {len(rows)} cars -> {OUT}")


if __name__ == "__main__":
    main()
