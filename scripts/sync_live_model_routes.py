#!/usr/bin/env python3
"""Sync confirmed Blogger model URLs into data/seo/model-routes-live.json.

Reads the public Blogger JSON feed and the generated model-page manifest. Only exact
post-title matches are accepted as live. Missing posts remain absent so the production
Blogger theme can safely fall back to its existing #usmodel routes.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dist" / "model-pages-manifest.csv"
OUT = ROOT / "data" / "seo" / "model-routes-live.json"
SITE = "https://www.drivespeclab.com"
FEED = SITE + "/feeds/posts/default?alt=json&max-results=500"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DriveSpecLabRouteSync/1.0 (+https://www.drivespeclab.com/)"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def feed_posts() -> dict[str, str]:
    data = fetch_json(FEED)
    out: dict[str, str] = {}
    for e in (data.get("feed", {}).get("entry") or []):
        title = str((e.get("title") or {}).get("$t") or "").strip()
        href = ""
        for link in e.get("link") or []:
            if link.get("rel") == "alternate" and link.get("href"):
                href = str(link["href"])
                break
        if title and href.startswith(SITE + "/"):
            out[title] = href
    return out


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    if not MANIFEST.exists():
        print(f"Manifest missing: {MANIFEST}", file=sys.stderr)
        return 2

    posts = feed_posts()
    rows = load_manifest()
    routes: dict[str, dict[str, str]] = {}

    for row in rows:
        title = str(row.get("title") or "").strip()
        url = posts.get(title)
        if not url:
            continue
        brand = str(row.get("brand") or "").strip()
        model = str(row.get("model") or "").strip()
        if not brand or not model:
            continue
        routes[f"{brand}|{model}"] = {
            "brand": brand,
            "model": model,
            "year": str(row.get("year") or ""),
            "title": title,
            "url": url,
            "url_status": "live",
            "verified_on": datetime.now(timezone.utc).date().isoformat(),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "live-only-hybrid",
        "note": "Only exact title matches from the live Blogger feed are included. Theme falls back to hash routes for all other models.",
        "count": len(routes),
        "routes": routes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Live SEO routes: {len(routes)} / {len(rows)} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
