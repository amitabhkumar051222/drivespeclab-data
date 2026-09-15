#!/usr/bin/env python3
"""Daily official-source change detector for DriveSpecLab.

This intentionally does NOT auto-publish guessed prices. It fingerprints official source
pages referenced by verified sidecars, the 25-brand registry and the Global/India catalog.
When a source materially changes, it records the URL in a pending-review report so verified
catalog updates can be applied without silently inventing prices or specifications.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4_DIR = ROOT / "data" / "v4"
CATALOG_DIR = ROOT / "data" / "catalog"
REGISTRY = CATALOG_DIR / "brand-registry-live.json"
GLOBAL = CATALOG_DIR / "global-cars-live.json"
STATE = ROOT / "data" / "monitor" / "official-source-fingerprints.json"
PENDING = ROOT / "data" / "monitor" / "pending-source-changes.json"


def clean_text(raw: bytes, content_type: str) -> str:
    s = raw.decode("utf-8", "ignore")
    if "html" in content_type.lower() or "<html" in s[:500].lower():
        s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
        s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
        s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:2_000_000]


def add_url(urls: dict[str, dict], url: str, meta: dict) -> None:
    if not isinstance(url, str) or not url.startswith("https://"):
        return
    if url not in urls:
        urls[url] = meta


def collect_urls() -> dict[str, dict]:
    urls: dict[str, dict] = {}

    # Existing verified U.S. sidecars.
    for p in V4_DIR.glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        brand = d.get("brand") or p.stem
        if d.get("source"):
            add_url(urls, d["source"], {"brand": brand, "model": "", "kind": "brand"})
        for model, m in (d.get("models") or {}).items():
            for key in ("source", "phev_source"):
                if m.get(key):
                    add_url(urls, m[key], {"brand": brand, "model": model, "kind": "model"})

    # 25-brand official lineup registry, including BYD/Tata/Mahindra.
    if REGISTRY.exists():
        d = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for b in d.get("brands") or []:
            add_url(urls, b.get("official_lineup_url", ""), {
                "brand": b.get("name", ""),
                "model": "",
                "kind": "brand-registry",
                "market": b.get("market_label", ""),
            })

    # Global/India reference models may have model-specific official sources.
    if GLOBAL.exists():
        d = json.loads(GLOBAL.read_text(encoding="utf-8"))
        for c in d.get("cars") or []:
            add_url(urls, c.get("source", ""), {
                "brand": c.get("brand", ""),
                "model": c.get("model", ""),
                "kind": "global-model",
                "market": c.get("market", ""),
            })

    return urls


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DriveSpecLabSourceWatch/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            raw = r.read(2_500_000)
            ctype = r.headers.get("Content-Type", "")
            text = clean_text(raw, ctype)
            return int(getattr(r, "status", 200)), hashlib.sha256(text.encode()).hexdigest()
    except Exception:
        return 0, ""


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"sources": {}}
    old_sources = old.get("sources") or {}
    current = {}
    changes = []

    for url, meta in collect_urls().items():
        status, fp = fetch(url)
        prev = old_sources.get(url) or {}
        row = {**meta, "status": status, "fingerprint": fp, "checked_at": now}
        current[url] = row
        if fp and prev.get("fingerprint") and fp != prev.get("fingerprint"):
            changes.append({"url": url, **meta, "previous_fingerprint": prev.get("fingerprint"), "new_fingerprint": fp, "detected_at": now})

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"generated": now, "count": len(current), "sources": current}, indent=2) + "\n", encoding="utf-8")
    PENDING.write_text(json.dumps({"generated": now, "count": len(changes), "changes": changes}, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(current)} official URLs across the 25-brand architecture; material fingerprint changes: {len(changes)}")


if __name__ == "__main__":
    main()
