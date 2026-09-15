#!/usr/bin/env python3
"""Validate DriveSpecLab gallery URLs and production-readiness.

Run after V6 and verified enrichment overlays plus the model-completeness audit.
The script makes small HTTP GET requests (Range when supported), records
reachability/content type, and writes a machine-readable audit plus a compact
Markdown summary.

A model is production-ready only when the completeness audit marks it fully
complete AND it has at least six gallery URLs AND every checked gallery URL is
healthy. Network/CDN failures are reported and never silently accepted.
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
OUT = ROOT / "data" / "audit"
COMPLETENESS = OUT / "model-completeness.json"
TIMEOUT = 12
USER_AGENT = "DriveSpecLabGalleryAudit/1.1 (+https://www.drivespeclab.com/)"


def fetch_status(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Range": "bytes=0-2047",
        },
        method="GET",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            ctype = str(resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            elapsed_ms = round((time.monotonic() - started) * 1000)
            ok = status in (200, 206) and ctype.startswith("image/")
            return {
                "ok": ok,
                "status": status,
                "content_type": ctype,
                "elapsed_ms": elapsed_ms,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": int(exc.code),
            "content_type": str(exc.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower(),
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "error": f"HTTP {exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
        return {
            "ok": False,
            "status": None,
            "content_type": "",
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "error": str(exc),
        }


def load_completeness() -> dict:
    if not COMPLETENESS.exists():
        return {}
    try:
        return json.loads(COMPLETENESS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    gallery_by_model: dict[tuple[str, str], list[str]] = {}
    checks_by_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
    total_models = models_with_gallery = total_urls = healthy_urls = 0

    for path in sorted(V4.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        brand = str(data.get("brand") or path.stem)
        for model_name, model in (data.get("models") or {}).items():
            total_models += 1
            gallery = model.get("gallery")
            if not isinstance(gallery, list) or not gallery:
                continue
            urls = [str(x).strip() for x in gallery if str(x).strip()]
            if not urls:
                continue
            key = (brand, str(model_name))
            gallery_by_model[key] = urls
            models_with_gallery += 1
            for url in urls:
                total_urls += 1
                result = fetch_status(url)
                if result["ok"]:
                    healthy_urls += 1
                row = {
                    "brand": brand,
                    "model": model_name,
                    "url": url,
                    **result,
                }
                checks.append(row)
                checks_by_model[key].append(row)

    broken = [row for row in checks if not row["ok"]]

    completeness = load_completeness()
    completeness_brands = completeness.get("brands") if isinstance(completeness, dict) else {}
    if not isinstance(completeness_brands, dict):
        completeness_brands = {}

    model_health: list[dict] = []
    production_ready: list[dict] = []
    for key, urls in sorted(gallery_by_model.items()):
        brand, model_name = key
        rows = checks_by_model.get(key, [])
        healthy_count = sum(1 for row in rows if row.get("ok"))
        all_healthy = len(rows) == len(urls) and healthy_count == len(urls)

        comp_model = (
            ((completeness_brands.get(brand) or {}).get("models") or {}).get(model_name) or {}
        )
        completeness_pass = bool(comp_model.get("fully_complete"))
        gallery_minimum_pass = len(urls) >= 6
        is_ready = completeness_pass and gallery_minimum_pass and all_healthy

        state = {
            "brand": brand,
            "model": model_name,
            "gallery_urls": len(urls),
            "healthy_urls": healthy_count,
            "all_gallery_urls_healthy": all_healthy,
            "completeness_pass": completeness_pass,
            "gallery_minimum_pass": gallery_minimum_pass,
            "production_ready": is_ready,
        }
        model_health.append(state)
        if is_ready:
            production_ready.append({"brand": brand, "model": model_name})

    audited_current = int(((completeness.get("summary") or {}).get("current_models_audited") or 0)) if isinstance(completeness, dict) else 0
    ready_pct = round((len(production_ready) / audited_current * 100), 1) if audited_current else 0.0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Gallery URLs are checked over HTTP and must return an image content type. "
            "Production-ready requires the model-completeness audit to pass, at least six gallery URLs, "
            "and every checked gallery URL to be healthy. Temporary CDN/network failures are reported "
            "and never converted into valid assets."
        ),
        "summary": {
            "models_scanned": total_models,
            "models_with_gallery": models_with_gallery,
            "gallery_urls_checked": total_urls,
            "healthy_gallery_urls": healthy_urls,
            "unhealthy_gallery_urls": len(broken),
            "healthy_pct": round((healthy_urls / total_urls * 100), 1) if total_urls else 0.0,
            "current_models_audited_for_completeness": audited_current,
            "production_ready_models": len(production_ready),
            "production_ready_pct": ready_pct,
        },
        "production_ready_models": production_ready,
        "model_gallery_health": model_health,
        "checks": checks,
        "unhealthy": broken,
    }
    (OUT / "gallery-health.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    s = report["summary"]
    lines = [
        "# DriveSpecLab Gallery Health & Production Readiness",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"- Models scanned: **{s['models_scanned']}**",
        f"- Models with galleries: **{s['models_with_gallery']}**",
        f"- Gallery URLs checked: **{s['gallery_urls_checked']}**",
        f"- Healthy image URLs: **{s['healthy_gallery_urls']} ({s['healthy_pct']}%)**",
        f"- Unhealthy image URLs: **{s['unhealthy_gallery_urls']}**",
        f"- Production-ready models: **{s['production_ready_models']} / {s['current_models_audited_for_completeness']} ({s['production_ready_pct']}%)**",
        "",
    ]

    if production_ready:
        lines.extend(["## Production-ready models", ""])
        for row in production_ready:
            lines.append(f"- {row['brand']} {row['model']}")
        lines.append("")

    if broken:
        lines.extend(["## Unhealthy URLs", ""])
        for row in broken[:50]:
            detail = row.get("error") or f"HTTP {row.get('status')} / {row.get('content_type')}"
            lines.append(f"- {row['brand']} {row['model']}: {detail} — {row['url']}")
        if len(broken) > 50:
            lines.append(f"- …and {len(broken) - 50} more; see gallery-health.json")
        lines.append("")

    (OUT / "GALLERY_HEALTH.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
