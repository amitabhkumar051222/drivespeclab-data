#!/usr/bin/env python3
"""Build DriveSpecLab's database-first vehicle catalog.

The generated catalog is the public data layer for search, filters, compare,
model detail pages, upcoming-model status and change tracking. It is independent
of Blogger editorial posts.

Inputs:
  data/db/part-01.txt ... part-05.txt
  data/v4/*.json
Outputs:
  data/catalog/cars.json
  data/catalog/upcoming.json
  data/catalog/change-log.json
  data/compare/cars.json

Missing specifications are never guessed. A field is published only when it is
present in the verified source data.
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
CATALOG_DIR = ROOT / "data" / "catalog"
COMPARE_DIR = ROOT / "data" / "compare"
CARS_OUT = CATALOG_DIR / "cars.json"
UPCOMING_OUT = CATALOG_DIR / "upcoming.json"
CHANGELOG_OUT = CATALOG_DIR / "change-log.json"
COMPARE_OUT = COMPARE_DIR / "cars.json"

STATUS_BLOCKERS = ("discontinued", "not currently sold", "no current official product page")
UPCOMING_WORDS = ("upcoming", "expected", "announced", "future model", "coming soon", "pre-production")


def norm(s: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def slug(s: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def route_brand(brand: str) -> str:
    return {"Land Rover": "Land-Rover", "Tata Motors": "Tata"}.get(brand, brand)


def model_url(brand: str, model: str) -> str:
    return f"/search/label/{quote(route_brand(brand))}#usmodel={quote(model)}"


def latest_year(v: object) -> str:
    years = re.findall(r"20\d{2}", str(v or ""))
    return years[-1] if years else ""


def current_status(side: dict | None) -> bool:
    text = str((side or {}).get("status", "")).lower()
    return not any(x in text for x in STATUS_BLOCKERS)


def upcoming_status(side: dict | None) -> bool:
    text = " ".join(str((side or {}).get(k, "")) for k in ("status", "market", "pricing_note")).lower()
    return any(x in text for x in UPCOMING_WORDS)


def body_group(raw: object) -> str:
    v = str(raw or "").lower()
    if re.search(r"suv|crossover", v): return "SUV / Crossover"
    if "sedan" in v: return "Sedan"
    if re.search(r"pickup|truck", v): return "Pickup / Truck"
    if re.search(r"hatchback|wagon|liftback", v): return "Hatchback / Wagon"
    if re.search(r"sports|coupe|convertible", v): return "Sports / Coupe"
    if re.search(r"van|minivan", v): return "Van / Minivan"
    return str(raw or "Other")


def fuel_types(power: object) -> list[str]:
    p = str(power or "").lower()
    out: list[str] = []
    if re.search(r"plug-in|phev", p): out.append("Plug-in Hybrid")
    if "hybrid" in p and "Plug-in Hybrid" not in out: out.append("Hybrid")
    if re.search(r"battery electric|\belectric\b|\bbev\b", p): out.append("Electric")
    if "hydrogen" in p or "fuel-cell" in p: out.append("Hydrogen")
    if "diesel" in p: out.append("Diesel")
    if re.search(r"gas|gasoline|turbo|v6|v8|i4|four-cylinder|six-cylinder", p): out.append("Gas")
    return out or ["Gas"]


def parse_price(v: object) -> int | None:
    if isinstance(v, (int, float)):
        return int(v) if v > 0 else None
    m = re.search(r"\$?\s*([0-9][0-9,]{3,})", str(v or ""))
    if not m: return None
    try: return int(m.group(1).replace(",", ""))
    except ValueError: return None


def money(v: int | None) -> str:
    return f"${v:,.0f}" if v else ""


def base_model(x: list) -> dict:
    row = {
        "name": x[0] if len(x) > 0 else "", "year": x[1] if len(x) > 1 else "",
        "body": x[2] if len(x) > 2 else "", "powertrain": x[3] if len(x) > 3 else "",
        "drivetrain": x[4] if len(x) > 4 else "", "seating": x[5] if len(x) > 5 else "",
        "price": x[6] if len(x) > 6 else "", "key_detail": x[7] if len(x) > 7 else "",
    }
    if len(x) > 8 and isinstance(x[8], dict): row.update(x[8])
    return row


def load_db() -> dict:
    raw = "".join((DB_DIR / f"part-{i:02d}.txt").read_text(encoding="utf-8") for i in range(1, 6))
    return json.loads(raw)


def load_sidecars() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(V4_DIR.glob("*.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        if obj.get("brand"): out[obj["brand"]] = obj
    return out


def side_for(sidecar: dict | None, name: str) -> dict:
    models = (sidecar or {}).get("models", {}) or {}
    if name in models: return models[name] or {}
    key = norm(name)
    for k, v in models.items():
        if norm(k) == key: return v or {}
    return {}


def trim_price(side: dict) -> int | None:
    vals = [parse_price(t.get("msrp")) for t in side.get("trims", []) or []]
    vals = [v for v in vals if v]
    return min(vals) if vals else None


def common_trim(side: dict, keys: tuple[str, ...]) -> str:
    vals: list[str] = []
    for t in side.get("trims", []) or []:
        v = next((str(t[k]).strip() for k in keys if t.get(k)), "")
        if v and v not in vals: vals.append(v)
    return " / ".join(vals[:4]) + (" / …" if len(vals) > 4 else "")


def image_for(base: dict, side: dict) -> str:
    return str(side.get("image") or base.get("image") or "")


def clean_gallery(side: dict) -> list[str]:
    g = side.get("gallery")
    if not isinstance(g, list): return []
    out: list[str] = []
    for x in g:
        u = str(x or "").strip()
        if u and u not in out: out.append(u)
    return out[:12]


def first(side: dict, *keys: str) -> object:
    for key in keys:
        v = side.get(key)
        if v not in (None, "", [], {}): return v
    return None


def dimensions_text(side: dict) -> object:
    v = first(side, "dimensions")
    if v: return v
    parts = []
    for label, key in (("L", "length_in"), ("W", "width_in"), ("H", "height_in"), ("WB", "wheelbase_in")):
        if side.get(key) not in (None, ""): parts.append(f"{label} {side[key]} in")
    return " • ".join(parts) if parts else None


def efficiency_text(side: dict) -> object:
    v = first(side, "efficiency", "mpg_combined", "mpge_combined", "mild_hybrid_mpg_combined")
    if v is None: return None
    if side.get("mpge_combined") == v: return f"{v} MPGe combined"
    if side.get("mpg_combined") == v or side.get("mild_hybrid_mpg_combined") == v: return f"{v} mpg combined"
    return v


def range_text(side: dict) -> object:
    v = first(side, "range_miles", "range_miles_up_to", "epa_range_miles", "epa_range_miles_up_to", "phev_electric_range_miles", "electric_range")
    if v is None: return None
    return f"{v} miles" if isinstance(v, (int, float)) else v


def public_details(side: dict, sidecar: dict | None) -> dict:
    details = {
        "engine": first(side, "engine", "motor", "powertrain"),
        "horsepower": first(side, "horsepower", "mild_hybrid_horsepower", "phev_horsepower", "power"),
        "torque": first(side, "torque", "torque_lb_ft"),
        "transmission": first(side, "transmission"),
        "acceleration": first(side, "zero_to_60_sec", "acceleration_0_60", "accel"),
        "efficiency": efficiency_text(side),
        "range": range_text(side),
        "charging": first(side, "charging", "charging_kw", "dc_fast_charging", "charge_time"),
        "dimensions": dimensions_text(side),
        "cargo": first(side, "cargo", "cargo_cu_ft", "cargo_volume_cu_ft"),
        "towing": first(side, "towing_lbs_up_to", "towing_lbs", "max_towing_lbs", "towing"),
        "payload": first(side, "payload_lbs", "payload"),
        "technology": first(side, "technology", "tech", "infotainment"),
        "safety": first(side, "safety", "adas", "driver_assistance"),
        "warranty": first(side, "warranty") or (sidecar or {}).get("warranty"),
    }
    return {k: v for k, v in details.items() if v not in (None, "", [], {})}


def selected_specs(side: dict) -> dict:
    keys = (
        "horsepower", "mild_hybrid_horsepower", "phev_horsepower", "torque_lb_ft",
        "mpg_combined", "mpge_combined", "epa_range_miles", "epa_range_miles_up_to",
        "range_miles", "range_miles_up_to", "electric_range", "battery_kwh", "charging_kw",
        "towing_lbs", "towing_lbs_up_to", "payload_lbs", "cargo_cu_ft", "zero_to_60_sec",
        "acceleration_0_60", "length_in", "width_in", "height_in", "wheelbase_in",
    )
    return {k: side[k] for k in keys if side.get(k) not in (None, "")}


def synthetic_model(name: str, side: dict) -> dict:
    return {
        "name": name, "year": side.get("year", ""), "body": side.get("body", "Vehicle"),
        "powertrain": side.get("powertrain") or common_trim(side, ("powertrain",)),
        "drivetrain": side.get("drivetrain") or side.get("default_drive") or common_trim(side, ("drivetrain", "default_drive")),
        "seating": side.get("seats", ""), "price": money(trim_price(side)),
        "key_detail": side.get("status", "Current U.S. model"), "_synthetic": True,
    }


def merged_models(brand_pack: list, sidecar: dict | None) -> list[tuple[dict, dict]]:
    out: list[tuple[dict, dict]] = []
    seen: set[str] = set()
    for raw in (brand_pack[4] if len(brand_pack) > 4 else []):
        base = base_model(raw)
        name = str(base.get("name") or "").strip()
        if not name: continue
        side = side_for(sidecar, name)
        seen.add(norm(name))
        if side and not current_status(side): continue
        out.append((base, side))
    for name, side in ((sidecar or {}).get("models", {}) or {}).items():
        if norm(name) in seen or not current_status(side): continue
        out.append((synthetic_model(name, side), side))
    return out


def make_row(brand: str, base: dict, side: dict, sidecar: dict | None) -> dict:
    name = str(base.get("name") or "").strip()
    price_num = trim_price(side) or parse_price(base.get("price"))
    power = str(side.get("powertrain") or base.get("powertrain") or common_trim(side, ("powertrain",)))
    drive = str(side.get("drivetrain") or side.get("default_drive") or base.get("drivetrain") or common_trim(side, ("drivetrain", "default_drive")))
    body = str(side.get("body") or base.get("body") or "Vehicle")
    seating = str(side.get("seats") or side.get("seating_capacity") or base.get("seating") or "")
    year = latest_year(side.get("year") or base.get("year"))
    status = str(side.get("status") or "Current U.S. retail model")
    source = str(side.get("source") or (sidecar or {}).get("source") or "")
    verified = str(side.get("verified_on") or (sidecar or {}).get("verified_on") or (sidecar or {}).get("updated") or "")
    trims = side.get("trims", []) or []
    gallery = clean_gallery(side)
    image = image_for(base, side) or (gallery[0] if gallery else "")
    details = public_details(side, sidecar)

    row = {
        "id": f"spec-{slug(brand)}-{slug(name)}", "brand": brand, "model": name, "year": year,
        "market": "US", "status": status, "upcoming": upcoming_status(side), "body": body,
        "body_group": body_group(body), "powertrain": power, "fuel_types": fuel_types(power),
        "drivetrain": drive, "seating": seating, "starting_price": price_num,
        "starting_price_text": money(price_num) or str(base.get("price") or ""),
        "trim_count": len(trims),
        "trims": [{
            "name": str(t.get("name") or ""), "msrp": parse_price(t.get("msrp")),
            "powertrain": str(t.get("powertrain") or ""),
            "drivetrain": str(t.get("drivetrain") or t.get("default_drive") or ""),
        } for t in trims],
        "key_detail": str(base.get("key_detail") or side.get("pricing_note") or ""),
        "image": image, "gallery": gallery, "gallery_count": len(gallery), "source": source,
        "verified_on": verified, "specs": selected_specs(side), "details": details,
        "url": model_url(brand, name), "route_type": "database-hash",
    }
    row["data_quality"] = {
        "official_source": bool(source), "verified_date": bool(verified), "trims": bool(trims),
        "gallery_6": len(gallery) >= 6, "detail_fields": len(details),
    }
    row["search_text"] = " ".join(str(row.get(k, "")) for k in ("brand", "model", "year", "body", "body_group", "powertrain", "drivetrain", "status", "key_detail")).lower()
    return row


def facets(cars: list[dict]) -> dict:
    def vals(key: str) -> list[str]: return sorted({str(c.get(key) or "") for c in cars if c.get(key)})
    fuels = sorted({x for c in cars for x in c.get("fuel_types", [])})
    return {
        "brands": vals("brand"), "body_groups": vals("body_group"), "fuel_types": fuels,
        "years": sorted({c["year"] for c in cars if c.get("year")}, reverse=True),
        "price_bands": [
            {"label": "Under $30k", "min": 0, "max": 30000}, {"label": "$30k–$50k", "min": 30000, "max": 50000},
            {"label": "$50k–$75k", "min": 50000, "max": 75000}, {"label": "$75k–$100k", "min": 75000, "max": 100000},
            {"label": "$100k+", "min": 100000, "max": None},
        ],
    }


def snapshot(cars: list[dict]) -> dict[str, dict]:
    return {f"{c['brand']}|{c['model']}": {"year": c.get("year"), "price": c.get("starting_price"), "status": c.get("status"), "trim_count": c.get("trim_count")} for c in cars}


def update_changelog(old_cars: list[dict], new_cars: list[dict], now: str) -> list[dict]:
    old, new = snapshot(old_cars), snapshot(new_cars)
    changes: list[dict] = []
    for key in sorted(set(old) | set(new)):
        brand, model = key.split("|", 1)
        if key not in old:
            changes.append({"detected_at": now, "type": "model_added", "brand": brand, "model": model, "new": new[key]}); continue
        if key not in new:
            changes.append({"detected_at": now, "type": "model_removed", "brand": brand, "model": model, "old": old[key]}); continue
        for field in ("year", "price", "status", "trim_count"):
            if old[key].get(field) != new[key].get(field):
                changes.append({"detected_at": now, "type": f"{field}_changed", "brand": brand, "model": model, "field": field, "old": old[key].get(field), "new": new[key].get(field)})
    previous: list[dict] = []
    if CHANGELOG_OUT.exists():
        try: previous = json.loads(CHANGELOG_OUT.read_text(encoding="utf-8")).get("changes", [])
        except Exception: previous = []
    seen = {(c.get("type"), c.get("brand"), c.get("model"), str(c.get("old")), str(c.get("new"))) for c in previous}
    merged = previous[:]
    for c in changes:
        sig = (c.get("type"), c.get("brand"), c.get("model"), str(c.get("old")), str(c.get("new")))
        if sig not in seen: merged.append(c); seen.add(sig)
    return merged[-1000:]


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db, sides = load_db(), load_sidecars()
    cars: list[dict] = []
    for brand, pack in (db.get("b") or {}).items():
        sidecar = sides.get(brand)
        for base, side in merged_models(pack, sidecar): cars.append(make_row(brand, base, side, sidecar))
    cars.sort(key=lambda x: (x["brand"].lower(), x["model"].lower()))
    upcoming = [c for c in cars if c.get("upcoming")]
    old_cars: list[dict] = []
    if CARS_OUT.exists():
        try: old_cars = json.loads(CARS_OUT.read_text(encoding="utf-8")).get("cars", [])
        except Exception: old_cars = []

    payload = {"generated": now, "architecture": "database-first", "route_type": "database-hash", "count": len(cars), "upcoming_count": len(upcoming), "facets": facets(cars), "cars": cars}
    compare_payload = {"generated": now, "architecture": "database-first", "count": len(cars), "cars": [{
        "id": c["id"], "brand": c["brand"], "model": c["model"], "year": c["year"], "body": c["body_group"],
        "powertrain": c["powertrain"], "drivetrain": c["drivetrain"], "seating": c["seating"],
        "starting_price": c["starting_price_text"], "trim_count": c["trim_count"], "verified_on": c["verified_on"],
        "source": c["source"], "url": c["url"], "route_type": "database-hash", "specs": c["specs"], "details": c["details"],
    } for c in cars]}

    CATALOG_DIR.mkdir(parents=True, exist_ok=True); COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    CARS_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    UPCOMING_OUT.write_text(json.dumps({"generated": now, "count": len(upcoming), "cars": upcoming}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CHANGELOG_OUT.write_text(json.dumps({"generated": now, "changes": update_changelog(old_cars, cars, now)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COMPARE_OUT.write_text(json.dumps(compare_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Database catalog: {len(cars)} cars; upcoming: {len(upcoming)}")


if __name__ == "__main__": main()
