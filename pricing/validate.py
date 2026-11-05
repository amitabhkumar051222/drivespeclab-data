#!/usr/bin/env python3
"""Fail CI on malformed or misleading pricing entries. Never invent prices."""
import json
from datetime import date
from pathlib import Path
BASE = Path(__file__).resolve().parent
prices = json.loads((BASE / "vehicle-prices.json").read_text(encoding="utf-8"))
rules = json.loads((BASE / "tax-rules.json").read_text(encoding="utf-8"))
assert prices["schema_version"] == rules["schema_version"] == 1
seen = set()
for p in prices["records"]:
    key = (p["brand"], p["model"], p["model_year"], p["trim"])
    assert key not in seen, "duplicate trim: " + repr(key)
    seen.add(key)
    assert type(p["msrp_usd"]) in (int, float) and p["msrp_usd"] > 0
    assert p["destination_usd"] is None or (type(p["destination_usd"]) in (int, float) and p["destination_usd"] >= 0)
    assert p["status"] in {"verified", "needs_reverification", "retired"}
    assert p["msrp_source"].startswith("https://")
    if p["destination_usd"] is not None:
        assert p["destination_source"] and p["destination_source"].startswith("https://")
    if p["status"] == "verified":
        assert p["verified_on"], "verified records require verified_on"
        assert date.fromisoformat(p["verified_on"]) <= date.today()
for rule in rules["rules"]:
    assert len(rule["state"]) == 2
    assert 0 <= rule["rate"] <= 0.2
    assert rule["source"].startswith("https://")
print(f"PASS: {len(prices['records'])} price rows and {len(rules['rules'])} rule rows validated (not independently price-verified).")
