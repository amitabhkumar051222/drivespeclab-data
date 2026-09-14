#!/usr/bin/env python3
"""Generate Blogger import packs and SEO manifests from DriveSpecLab's verified DB.

Inputs (repo-relative):
  data/db/part-01.txt ... part-05.txt
  data/v4/*.json
Outputs:
  dist/blogger-model-pages-all.atom.xml
  dist/blogger-import-by-brand/*.atom.xml
  dist/model-pages-manifest.csv
  data/seo/model-routes-predicted.json
  dist/SEO_MODEL_PAGES_README.txt

The generated posts are deliberately back-dated so they do not bury current editorial
content on the Blogger homepage. Actual Blogger URLs must be crawled after import before
brand/model links are switched away from the existing #usmodel routes.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "data" / "db"
V4_DIR = ROOT / "data" / "v4"
DIST = ROOT / "dist"
BRAND_DIST = DIST / "blogger-import-by-brand"
SEO_DIR = ROOT / "data" / "seo"
SITE = "https://www.drivespeclab.com"
GEN_DATE = "2026-09-14"
PUBLISH_BASE = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

OFFICIAL_DOMAINS = {
    "Toyota":"toyota.com","Honda":"automobiles.honda.com","Ford":"ford.com",
    "Chevrolet":"chevrolet.com","Nissan":"nissanusa.com","Hyundai":"hyundaiusa.com",
    "Kia":"kia.com","Volkswagen":"vw.com","Tesla":"tesla.com","BMW":"bmwusa.com",
    "Mercedes-Benz":"mbusa.com","Audi":"audiusa.com","Porsche":"porsche.com",
    "Lexus":"lexus.com","Volvo":"volvocars.com","Subaru":"subaru.com",
    "Mazda":"mazdausa.com","Jeep":"jeep.com","Land Rover":"landroverusa.com",
    "Genesis":"genesis.com","BYD":"bydglobal.com","GMC":"gmc.com",
    "Ram":"ramtrucks.com","Mahindra":"auto.mahindra.com","Tata Motors":"cars.tatamotors.com",
}

SKIP_DETAIL_FIELDS = {
    "year","source","trims","status","pricing_note","image","gallery","market",
    "phev_source","verified_on","source_policy"
}

LABEL_OVERRIDES = {
    "horsepower":"Horsepower",
    "mild_hybrid_horsepower":"Mild-hybrid horsepower",
    "phev_horsepower":"Plug-in-hybrid horsepower",
    "torque_lb_ft":"Torque",
    "epa_range_miles":"EPA range",
    "epa_range_miles_up_to":"EPA range (up to)",
    "range_miles":"Range",
    "range_miles_up_to":"Range (up to)",
    "electric_range":"Electric range",
    "phev_electric_range_miles":"Plug-in electric range",
    "mpg_combined":"Combined MPG",
    "mild_hybrid_mpg_combined":"Mild-hybrid combined MPG",
    "phev_mpg_combined":"Plug-in-hybrid combined MPG",
    "mpge_combined":"Combined MPGe",
    "phev_mpge_combined":"Plug-in-hybrid combined MPGe",
    "battery_kwh":"Battery capacity",
    "charging_kw":"Peak DC charging",
    "towing_lbs":"Towing capacity",
    "payload_lbs":"Payload capacity",
    "cargo_cu_ft":"Cargo volume",
    "zero_to_60_sec":"0–60 mph",
    "acceleration_0_60":"0–60 mph",
    "seating_capacity":"Seating capacity",
}


def norm(s: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def current_status(side: dict | None) -> bool:
    x = str((side or {}).get("status", "")).lower()
    blockers = ("discontinued", "not currently sold", "no current official product page")
    return not any(b in x for b in blockers)


def latest_year(value: object) -> str:
    years = re.findall(r"20\d{2}", str(value or ""))
    return years[-1] if years else "2026"


def money(v: object) -> str:
    if v is None or v == "":
        return "Not published"
    try:
        n = float(v)
        if n > 0:
            return "${:,.0f}".format(n)
    except Exception:
        pass
    return str(v)


def lowest_msrp(side: dict | None):
    vals = []
    for t in (side or {}).get("trims", []) or []:
        try:
            n = float(t.get("msrp"))
            if n > 0:
                vals.append(n)
        except Exception:
            pass
    return min(vals) if vals else None


def display_value(v: object) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (int, float)):
        return f"{v:g}" if isinstance(v, float) else str(v)
    if isinstance(v, list):
        return " • ".join(display_value(x) for x in v if display_value(x))
    if isinstance(v, dict):
        bits = []
        for k, x in v.items():
            val = display_value(x)
            if val:
                bits.append(f"{pretty_label(k)}: {val}")
        return " • ".join(bits)
    return str(v)


def pretty_label(key: str) -> str:
    if key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[key]
    return key.replace("_", " ").strip().title()


def base_model(x: list) -> dict:
    z = {
        "name": x[0] if len(x) > 0 else "",
        "year": x[1] if len(x) > 1 else "",
        "body": x[2] if len(x) > 2 else "",
        "power": x[3] if len(x) > 3 else "",
        "drive": x[4] if len(x) > 4 else "",
        "seats": x[5] if len(x) > 5 else "",
        "price": x[6] if len(x) > 6 else "",
        "key": x[7] if len(x) > 7 else "",
    }
    if len(x) > 8 and isinstance(x[8], dict):
        z.update(x[8])
    return z


def load_db() -> dict:
    pieces = []
    for n in range(1, 6):
        p = DB_DIR / f"part-{n:02d}.txt"
        pieces.append(p.read_text(encoding="utf-8"))
    return json.loads("".join(pieces))


def load_sidecars() -> dict[str, dict]:
    out = {}
    for p in sorted(V4_DIR.glob("*.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        brand = obj.get("brand")
        if brand:
            out[brand] = obj
    return out


def unpack_brands(db: dict) -> dict[str, dict]:
    out = OrderedDict()
    for brand, b in db.get("b", {}).items():
        out[brand] = {
            "source": b[0] if len(b) > 0 else "",
            "warranty": b[1] if len(b) > 1 else "",
            "note": b[2] if len(b) > 2 else "",
            "status": b[3] if len(b) > 3 else "Current U.S. retail lineup",
            "models": [base_model(x) for x in (b[4] if len(b) > 4 else [])],
        }
    return out


def side_for(sidecar: dict | None, name: str) -> dict | None:
    if not sidecar:
        return None
    models = sidecar.get("models", {}) or {}
    if name in models:
        return models[name]
    n = norm(name)
    for k, v in models.items():
        if norm(k) == n:
            return v
    return None


def common_trim_value(side: dict | None, keys: tuple[str, ...]) -> str:
    vals = []
    for t in (side or {}).get("trims", []) or []:
        v = ""
        for k in keys:
            if t.get(k):
                v = str(t.get(k))
                break
        if v:
            vals.append(v)
    uniq = []
    for v in vals:
        if v not in uniq:
            uniq.append(v)
    if not uniq:
        return ""
    return uniq[0] if len(uniq) == 1 else " / ".join(uniq[:3]) + (" / …" if len(uniq) > 3 else "")


def synthetic_model(name: str, side: dict) -> dict:
    lp = lowest_msrp(side)
    return {
        "name": name,
        "year": side.get("year", ""),
        "body": side.get("body", "Vehicle"),
        "power": side.get("powertrain") or common_trim_value(side, ("powertrain",)) or "",
        "drive": side.get("drive") or common_trim_value(side, ("drivetrain", "default_drive")) or "",
        "seats": side.get("seats", ""),
        "price": money(lp) if lp else "",
        "key": side.get("status", "Current U.S. model; official trim pricing shown where published."),
        "_synthetic": True,
    }


def merged_models(brand_obj: dict, sidecar: dict | None) -> list[tuple[dict, dict | None]]:
    out = []
    seen = set()
    for m in brand_obj.get("models", []):
        s = side_for(sidecar, m["name"])
        seen.add(norm(m["name"]))
        if s and not current_status(s):
            continue
        out.append((m, s))
    for name, s in ((sidecar or {}).get("models", {}) or {}).items():
        if norm(name) in seen or not current_status(s):
            continue
        out.append((synthetic_model(name, s), s))
    return out


def slugify(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def blogger_title(year: str, brand: str, model: str) -> str:
    return f"{year} {brand} {model} Specs, Price & Trims"


def predicted_path(title: str) -> str:
    # Prediction only. Blogger remains the source of truth after import.
    slug = slugify(title)
    return f"/2026/08/{slug}.html"


def official_domain(brand: str) -> str:
    return OFFICIAL_DOMAINS.get(brand, "")


def fallback_image(brand: str, model: str, year: str, slot: int) -> str:
    domain = official_domain(brand)
    terms = [
        "front three-quarter exterior studio",
        "side profile exterior",
        "rear three-quarter exterior rear view",
        "dashboard cockpit infotainment interior",
        "front seats cabin interior",
        "rear seats cabin interior",
    ]
    q = f"site:{domain} {year} {brand} {model} {terms[slot]}" if domain else f"{year} {brand} {model} {terms[slot]}"
    host = [1,2,2,4,1,3][slot]
    return f"https://tse{host}.mm.bing.net/th?q={quote(q)}&w=1200&h=760&c=7&rs=1&p=0&o=5&dpr=1.25&pid=1.7&mkt=en-US&cc=US"


def images_for(brand: str, model: dict, side: dict | None, year: str) -> list[str]:
    vals = []
    for src in [model.get("image"), (side or {}).get("image")]:
        if src and src not in vals:
            vals.append(src)
    for arr in [model.get("gallery"), (side or {}).get("gallery")]:
        if isinstance(arr, list):
            for src in arr:
                if src and src not in vals:
                    vals.append(src)
    while len(vals) < 6:
        vals.append(fallback_image(brand, model["name"], year, len(vals)))
    return vals[:6]


def html_table(rows: list[tuple[str, str]], cls: str = "dsl-seo-table") -> str:
    body = "".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in rows if v not in (None, "")
    )
    return f"<table class=\"{cls}\"><tbody>{body}</tbody></table>" if body else ""


def verified_rows(side: dict | None) -> list[tuple[str, str]]:
    rows = []
    for k, v in (side or {}).items():
        if k in SKIP_DETAIL_FIELDS or k.startswith("_"):
            continue
        val = display_value(v)
        if not val:
            continue
        if len(val) > 500:
            continue
        rows.append((pretty_label(k), val))
    return rows


def trim_html(side: dict | None) -> str:
    trims = (side or {}).get("trims", []) or []
    if not trims:
        return "<p>Official U.S. trim-level pricing was not published in the verified source set for this model.</p>"
    rows = []
    for t in trims:
        cfg = []
        for key in ("powertrain","drivetrain","default_drive","transmission","default_cab","cab"):
            if t.get(key) and str(t.get(key)) not in cfg:
                cfg.append(str(t.get(key)))
        status = t.get("status")
        if status:
            cfg.append(str(status))
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(t.get('name','')))}</strong></td>"
            f"<td>{html.escape(money(t.get('msrp')))}</td>"
            f"<td>{html.escape(' • '.join(cfg) if cfg else 'Configuration varies by trim')}</td>"
            "</tr>"
        )
    note = ""
    if (side or {}).get("pricing_note"):
        note = f"<p class=\"dsl-seo-note\">{html.escape(str(side['pricing_note']))}</p>"
    return (
        "<div class=\"dsl-seo-scroll\"><table class=\"dsl-seo-trims\"><thead><tr>"
        "<th>Trim / configuration</th><th>Starting MSRP</th><th>Powertrain / configuration</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>" + note
    )


def model_intro(brand: str, m: dict, s: dict | None, year: str, start_price: str) -> str:
    body = m.get("body") or "vehicle"
    power = m.get("power") or common_trim_value(s, ("powertrain",))
    drive = m.get("drive") or common_trim_value(s, ("drivetrain", "default_drive"))
    bits = [f"The {year} {brand} {m['name']} is listed in the current U.S. lineup as a {body.lower()}."]
    if power:
        bits.append(f"Verified configurations include {power}.")
    if drive:
        bits.append(f"Available drivetrain information includes {drive}.")
    if start_price and start_price != "Not published":
        bits.append(f"The lowest verified starting MSRP in the current source set is {start_price}.")
    bits.append("This page consolidates the current manufacturer-sourced trim pricing and specification data available in the DriveSpecLab database without estimating unpublished prices.")
    return " ".join(bits)


def vehicle_schema(brand: str, m: dict, s: dict | None, year: str, start_price: str, predicted: str, source: str) -> dict:
    obj = {
        "@context": "https://schema.org",
        "@type": "Vehicle",
        "name": f"{year} {brand} {m['name']}",
        "brand": {"@type":"Brand", "name": brand},
        "model": m["name"],
        "vehicleModelDate": year,
        "bodyType": m.get("body") or None,
        "fuelType": m.get("power") or None,
        "sameAs": source or None,
        "dateModified": GEN_DATE,
    }
    lp = lowest_msrp(s)
    if lp:
        obj["offers"] = {
            "@type":"Offer",
            "priceCurrency":"USD",
            "price": round(float(lp), 2),
            "availability":"https://schema.org/InStock",
            "url": source or None,
        }
    return {k:v for k,v in obj.items() if v not in (None, "")}


def breadcrumb_schema(brand: str, title: str, predicted: str) -> dict:
    return {
        "@context":"https://schema.org",
        "@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":SITE+"/"},
            {"@type":"ListItem","position":2,"name":brand,"item":SITE+"/search/label/"+quote(brand.replace(" ","-"))},
            {"@type":"ListItem","position":3,"name":title},
        ],
    }

POST_CSS = """
<style>
.dsl-seo-model-page{max-width:1060px;margin:20px auto 44px;color:#17202a;font-family:Arial,Segoe UI,sans-serif;line-height:1.62}.dsl-seo-hero{padding:24px;border:1px solid #dfe6ee;border-radius:20px;background:linear-gradient(135deg,#fff,#f3f8fd);box-shadow:0 10px 28px rgba(15,34,58,.07)}.dsl-seo-kicker{font-size:11px;font-weight:900;letter-spacing:.8px;color:#0b5ea8;text-transform:uppercase}.dsl-seo-model-page h1{font-size:clamp(30px,5vw,46px);line-height:1.08;margin:6px 0 8px;color:#111820}.dsl-seo-price{font-size:22px;font-weight:900;color:#0b4c8b}.dsl-seo-chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.dsl-seo-chips span{font-size:11px;font-weight:800;border:1px solid #dce7f2;background:#fff;border-radius:999px;padding:6px 9px}.dsl-seo-sec{margin-top:14px;padding:18px;border:1px solid #e1e8f0;border-radius:16px;background:#fff}.dsl-seo-sec h2{font-size:22px;margin:0 0 10px}.dsl-seo-table,.dsl-seo-trims{width:100%;border-collapse:collapse}.dsl-seo-table tr+tr,.dsl-seo-trims tr+tr{border-top:1px solid #edf1f5}.dsl-seo-table th,.dsl-seo-table td,.dsl-seo-trims th,.dsl-seo-trims td{padding:10px 7px;text-align:left;vertical-align:top;font-size:13px}.dsl-seo-table th{width:34%;color:#66768a}.dsl-seo-trims th{font-size:11px;color:#66768a;text-transform:uppercase}.dsl-seo-trims td:nth-child(2){font-weight:900;white-space:nowrap}.dsl-seo-scroll{overflow-x:auto}.dsl-seo-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.dsl-seo-gallery figure{margin:0;aspect-ratio:16/10;overflow:hidden;border-radius:12px;background:#edf3f8;position:relative}.dsl-seo-gallery img{width:100%;height:100%;object-fit:cover}.dsl-seo-gallery figcaption{position:absolute;left:7px;bottom:7px;padding:4px 7px;border-radius:999px;background:rgba(7,29,63,.86);color:#fff;font-size:9px;font-weight:900}.dsl-seo-note{padding:10px 12px;background:#f7f9fc;border-radius:10px;color:#5f6f82}.dsl-seo-source{display:inline-flex;padding:10px 13px;border-radius:10px;background:#f5b800;color:#111!important;text-decoration:none!important;font-weight:900}.dsl-seo-meta{color:#66768a;font-size:12px}.dsl-seo-related a{display:inline-block;margin:5px 7px 5px 0;padding:7px 9px;border:1px solid #dce7f2;border-radius:999px;text-decoration:none}@media(max-width:650px){.dsl-seo-gallery{grid-template-columns:repeat(2,1fr)}.dsl-seo-hero,.dsl-seo-sec{padding:15px}.dsl-seo-table th{width:42%}}
</style>
""".strip()


def post_html(brand: str, brand_obj: dict, m: dict, s: dict | None, siblings: list[str]) -> tuple[str, dict]:
    year = latest_year((s or {}).get("year") or m.get("year"))
    title = blogger_title(year, brand, m["name"])
    predicted = predicted_path(title)
    lp = lowest_msrp(s)
    start_price = money(lp) if lp else (m.get("price") or "Not published")
    source = (s or {}).get("source") or m.get("source") or brand_obj.get("source") or ""
    imgs = images_for(brand, m, s, year)

    overview = [
        ("Model year", year),
        ("Body style", m.get("body", "")),
        ("Powertrain", m.get("power", "") or common_trim_value(s, ("powertrain",))),
        ("Drivetrain", m.get("drive", "") or common_trim_value(s, ("drivetrain", "default_drive"))),
        ("Seating", m.get("seats", "")),
        ("Starting MSRP", start_price),
    ]
    details = verified_rows(s)
    gallery = "".join(
        f"<figure><img loading=\"lazy\" decoding=\"async\" referrerpolicy=\"no-referrer\" src=\"{html.escape(src, quote=True)}\" alt=\"{html.escape(year+' '+brand+' '+m['name']+' '+('exterior' if i<3 else 'interior')+' view')}\"><figcaption>{'Exterior' if i<3 else 'Interior'}</figcaption></figure>"
        for i, src in enumerate(imgs)
    )
    rel = "".join(
        f"<a href=\"{SITE}/search/label/{quote(brand.replace(' ','-'))}#usmodel={quote(x)}\">{html.escape(brand+' '+x)}</a>"
        for x in siblings[:8] if x != m["name"]
    )
    status = (s or {}).get("status") or m.get("key") or brand_obj.get("status") or ""
    warranty = brand_obj.get("warranty") or ""
    source_policy = ((s or {}).get("source_policy") or "")
    sidecar_note = (s or {}).get("pricing_note") or ""
    verified_on = GEN_DATE

    v_schema = vehicle_schema(brand, m, s, year, start_price, predicted, source)
    b_schema = breadcrumb_schema(brand, title, predicted)
    schema_html = (
        "<script type=\"application/ld+json\">" + json.dumps(v_schema, ensure_ascii=False, separators=(",",":")) + "</script>"
        "<script type=\"application/ld+json\">" + json.dumps(b_schema, ensure_ascii=False, separators=(",",":")) + "</script>"
    )

    content = f"""
{POST_CSS}
<article class="dsl-seo-model-page" data-dsl-key="{html.escape(brand+'|'+m['name'], quote=True)}" data-dsl-brand="{html.escape(brand, quote=True)}" data-dsl-model="{html.escape(m['name'], quote=True)}" data-dsl-year="{year}">
  <header class="dsl-seo-hero">
    <div class="dsl-seo-kicker">DriveSpecLab verified U.S. vehicle database</div>
    <h1>{html.escape(title)}</h1>
    <div class="dsl-seo-price">{html.escape(start_price)}</div>
    <div class="dsl-seo-chips">
      {''.join('<span>'+html.escape(str(x))+'</span>' for x in [m.get('body'),m.get('power'),m.get('drive'),(str(m.get('seats'))+' seats' if m.get('seats') else '')] if x)}
    </div>
    <p>{html.escape(model_intro(brand,m,s,year,start_price))}</p>
    <div class="dsl-seo-meta">Verified/compiled: {verified_on}. MSRP excludes taxes, registration, dealer charges and destination unless the manufacturer source states otherwise.</div>
  </header>

  <section class="dsl-seo-sec"><h2>Overview</h2>{html_table(overview)}{('<p class="dsl-seo-note">'+html.escape(status)+'</p>') if status else ''}</section>
  <section class="dsl-seo-sec"><h2>{html.escape(brand+' '+m['name'])} exterior & interior</h2><div class="dsl-seo-gallery">{gallery}</div></section>
  {('<section class="dsl-seo-sec"><h2>Official verified specifications</h2>'+html_table(details)+'</section>') if details else ''}
  <section class="dsl-seo-sec"><h2>Trims & starting MSRP</h2>{trim_html(s)}</section>
  {('<section class="dsl-seo-sec"><h2>Warranty</h2><p>'+html.escape(warranty)+'</p></section>') if warranty else ''}
  <section class="dsl-seo-sec"><h2>Source & verification</h2>
    <p>DriveSpecLab uses current U.S. manufacturer material for this model. Unpublished prices are left unpublished rather than estimated.</p>
    {('<p class="dsl-seo-note">'+html.escape(sidecar_note)+'</p>') if sidecar_note else ''}
    {('<p class="dsl-seo-note">'+html.escape(source_policy)+'</p>') if source_policy else ''}
    {('<a class="dsl-seo-source" href="'+html.escape(source, quote=True)+'" rel="nofollow noopener" target="_blank">Official U.S. source ↗</a>') if source else ''}
  </section>
  <section class="dsl-seo-sec dsl-seo-related"><h2>More {html.escape(brand)} models</h2><p><a href="{SITE}/search/label/{quote(brand.replace(' ','-'))}">View the full {html.escape(brand)} U.S. lineup</a></p>{rel}</section>
</article>
{schema_html}
""".strip()
    meta = {
        "brand": brand,
        "model": m["name"],
        "year": year,
        "title": title,
        "predicted_path": predicted,
        "source": source,
        "verified_on": verified_on,
        "starting_price": start_price,
    }
    return content, meta


def atom_entry(meta: dict, content: str, index: int) -> str:
    pub = PUBLISH_BASE + timedelta(minutes=index)
    upd = datetime(2026, 9, 14, 4, 30, tzinfo=timezone.utc) + timedelta(seconds=index)
    key = f"{meta['brand']}|{meta['model']}|{meta['year']}"
    pid = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:15], 16)
    title = xml_escape(meta["title"])
    content_escaped = xml_escape(content)
    brand = xml_escape(meta["brand"])
    return f"""  <entry>
    <id>tag:blogger.com,1999:blog-0.post-{pid}</id>
    <published>{pub.isoformat().replace('+00:00','Z')}</published>
    <updated>{upd.isoformat().replace('+00:00','Z')}</updated>
    <category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#post"/>
    <category scheme="http://www.blogger.com/atom/ns#" term="Vehicle Database"/>
    <category scheme="http://www.blogger.com/atom/ns#" term="{brand}"/>
    <category scheme="http://www.blogger.com/atom/ns#" term="Specifications"/>
    <title type="text">{title}</title>
    <content type="html">{content_escaped}</content>
    <author><name>DriveSpecLab</name></author>
    <app:control><app:draft>no</app:draft></app:control>
  </entry>"""


def atom_feed(entries: list[str]) -> str:
    updated = "2026-09-14T04:30:00Z"
    return "\n".join([
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://purl.org/atom/app#" xmlns:thr="http://purl.org/syndication/thread/1.0">',
        "  <id>tag:blogger.com,1999:blog-0</id>",
        "  <title type=\"text\">DriveSpecLab SEO Vehicle Model Pages</title>",
        f"  <updated>{updated}</updated>",
        "  <author><name>DriveSpecLab</name></author>",
        *entries,
        "</feed>",
        "",
    ])


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    BRAND_DIST.mkdir(parents=True, exist_ok=True)
    SEO_DIR.mkdir(parents=True, exist_ok=True)

    db = load_db()
    brands = unpack_brands(db)
    sidecars = load_sidecars()

    all_entries = []
    manifest = []
    routes = {}
    global_idx = 0
    per_brand_counts = {}

    brand_names = list(brands.keys())
    for b in sidecars:
        if b not in brand_names:
            brand_names.append(b)

    for brand in brand_names:
        brand_obj = brands.get(brand, {"source":"","warranty":"","note":"","status":"","models":[]})
        sidecar = sidecars.get(brand)
        pairs = merged_models(brand_obj, sidecar)
        siblings = [m["name"] for m, _ in pairs]
        brand_entries = []
        for m, s in pairs:
            content, meta = post_html(brand, brand_obj, m, s, siblings)
            entry = atom_entry(meta, content, global_idx)
            all_entries.append(entry)
            brand_entries.append(entry)
            manifest.append(meta)
            routes[f"{brand}|{m['name']}"] = {
                "brand": brand,
                "model": m["name"],
                "year": meta["year"],
                "title": meta["title"],
                "predicted_path": meta["predicted_path"],
                "url_status": "predicted-before-import",
            }
            global_idx += 1
        per_brand_counts[brand] = len(brand_entries)
        if brand_entries:
            (BRAND_DIST / f"{slugify(brand)}.atom.xml").write_text(atom_feed(brand_entries), encoding="utf-8")

    (DIST / "blogger-model-pages-all.atom.xml").write_text(atom_feed(all_entries), encoding="utf-8")
    with (DIST / "model-pages-manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["brand","model","year","title","predicted_path","starting_price","source","verified_on"])
        w.writeheader()
        w.writerows(manifest)
    (SEO_DIR / "model-routes-predicted.json").write_text(json.dumps({
        "generated": GEN_DATE,
        "note": "Predicted Blogger paths only. Crawl the live site after import before switching production links.",
        "count": len(routes),
        "routes": routes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    active_brands = sum(1 for v in per_brand_counts.values() if v)
    empty_brands = [k for k,v in per_brand_counts.items() if not v]
    readme = f"""DriveSpecLab SEO Model Page Import Pack\n===================================\n\nGenerated: {GEN_DATE}\nModel posts generated: {len(manifest)}\nBrands with at least one current model: {active_brands}\nNo-current-U.S.-lineup brand cases: {', '.join(empty_brands) if empty_brands else 'None'}\n\nFiles\n-----\n- blogger-model-pages-all.atom.xml : all generated model posts in one Blogger Atom import.\n- blogger-import-by-brand/          : smaller per-brand import files.\n- model-pages-manifest.csv          : QA manifest.\n- ../data/seo/model-routes-predicted.json : predicted paths, NOT production routing yet.\n\nImportant production rule\n-------------------------\nDo not switch DriveSpecLab brand/model buttons from #usmodel routes to the predicted paths until the Blogger import has completed and the live sitemap has been crawled. Blogger is the source of truth for the final permalink.\n\nPublishing strategy\n-------------------\nThe generated posts use August 2026 publication timestamps so they do not bury September 2026 editorial posts on the homepage. Each post is labeled Vehicle Database, Specifications, and the brand name.\n\nAfter import\n------------\n1. Confirm a few imported model pages in Blogger.\n2. Crawl the live sitemap to collect the real URLs.\n3. Build a production model-routes.json from real URLs.\n4. Update the V6.14 theme so brand cards and related-model links point to the real SEO pages while retaining #usmodel as a fallback.\n"""
    (DIST / "SEO_MODEL_PAGES_README.txt").write_text(readme, encoding="utf-8")

    print(json.dumps({
        "posts": len(manifest),
        "active_brands": active_brands,
        "empty_brands": empty_brands,
        "per_brand": per_brand_counts,
    }, indent=2))


if __name__ == "__main__":
    main()
