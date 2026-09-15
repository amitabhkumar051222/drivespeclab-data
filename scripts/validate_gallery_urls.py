#!/usr/bin/env python3
"""Validate DriveSpecLab gallery URLs without guessing or rewriting data.

Run after V6 and verified enrichment overlays have been applied. The script makes
small HTTP GET requests (Range when supported), records reachability/content type,
and writes a machine-readable audit plus a compact Markdown summary.

Network failures are reported, not silently converted into valid images. The script
returns success so a temporary CDN outage does not block all catalog publishing;
health regressions remain visible in data/audit/gallery-health.json.
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "data" / "v4"
OUT = ROOT / "data" / "audit"
TIMEOUT = 12
USER_AGENT = "DriveSpecLabGalleryAudit/1.0 (+https://www.drivespeclab.com/)"


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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
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
            models_with_gallery += 1
            for url in urls:
                total_urls += 1
                result = fetch_status(url)
                if result["ok"]:
                    healthy_urls += 1
                checks.append({
                    "brand": brand,
                    "model": model_name,
                    "url": url,
                    **result,
                })

    broken = [row for row in checks if not row["ok"]]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Gallery URLs are checked over HTTP and must return an image content type. "
            "Temporary CDN/network failures are reported and never converted into valid assets."
        ),
        "summary": {
            "models_scanned": total_models,
            "models_with_gallery": models_with_gallery,
            "gallery_urls_checked": total_urls,
            "healthy_gallery_urls": healthy_urls,
            "unhealthy_gallery_urls": len(broken),
            "healthy_pct": round((healthy_urls / total_urls * 100), 1) if total_urls else 0.0,
        },
        "checks": checks,
        "unhealthy": broken,
    }
    (OUT / "gallery-health.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    s = report["summary"]
    lines = [
        "# DriveSpecLab Gallery Health",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"- Models scanned: **{s['models_scanned']}**",
        f"- Models with galleries: **{s['models_with_gallery']}**",
        f"- Gallery URLs checked: **{s['gallery_urls_checked']}**",
        f"- Healthy image URLs: **{s['healthy_gallery_urls']} ({s['healthy_pct']}%)**",
        f"- Unhealthy image URLs: **{s['unhealthy_gallery_urls']}**",
        "",
    ]
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
