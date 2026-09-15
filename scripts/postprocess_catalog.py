#!/usr/bin/env python3
"""Conservative post-processing for DriveSpecLab's generated database catalog.

This pass keeps the public catalog honest and readable:
- removes false-positive upcoming flags;
- never invents a fuel type or specification;
- exposes verified enhancement aliases that are present in the V4/V6 overlay;
- adds units to numeric capability/spec values;
- keeps the comparison index aligned with the public catalog.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / 'data' / 'catalog' / 'cars.json'
UPCOMING = ROOT / 'data' / 'catalog' / 'upcoming.json'
COMPARE = ROOT / 'data' / 'compare' / 'cars.json'
V4 = ROOT / 'data' / 'v4'

EXPLICIT = ('upcoming','expected','launch planned','planned for','announced for','future model','coming soon','pre-production')


def norm(v: object) -> str:
    return re.sub(r'[^a-z0-9]', '', str(v or '').lower())


def clean_upcoming(c: dict) -> bool:
    text = ' '.join(str(c.get(k) or '') for k in ('status','market')).lower()
    price = c.get('starting_price')
    year = str(c.get('year') or '')
    if any(x in text for x in EXPLICIT):
        if 'current' in text and price:
            return False
        return True
    try:
        return bool(year and int(year) > datetime.now(timezone.utc).year and not price)
    except Exception:
        return False


def first(d: dict, *keys: str):
    for k in keys:
        v = d.get(k)
        if v not in (None, '', [], {}):
            return v, k
    return None, ''


def unit(v: object, suffix: str) -> object:
    if isinstance(v, (int, float)):
        n = f'{v:g}'
        return f'{n} {suffix}'
    return v


def clean_efficiency(v: object) -> object:
    if not isinstance(v, str):
        return v
    s = v.strip()
    low = s.lower()
    if low.endswith(' mpg combined') and 'mpg' in low[:-13]:
        return s[:-13].rstrip()
    if low.endswith(' mpge combined') and 'mpge' in low[:-14]:
        return s[:-14].rstrip()
    return s


def sidecar_models() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for p in V4.glob('*.json'):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        brand = str(d.get('brand') or '')
        for model, values in (d.get('models') or {}).items():
            out[(norm(brand), norm(model))] = values or {}
    return out


def enrich_details(c: dict, side: dict) -> None:
    d = c.setdefault('details', {})

    # Preserve already-generated verified values, but normalize units.
    for key, suffix in (
        ('horsepower', 'hp'), ('torque', 'lb-ft'), ('range', 'miles'),
        ('cargo', 'cu ft'), ('towing', 'lb'), ('payload', 'lb'),
        ('charging', 'kW'), ('acceleration', 'sec'), ('ground_clearance', 'in'),
    ):
        if key in d:
            d[key] = unit(d[key], suffix)
    if 'efficiency' in d:
        d['efficiency'] = clean_efficiency(d['efficiency'])

    aliases = {
        'acceleration': ('zero_to_60', 'zero_to_60_sec', 'acceleration_0_60', 'accel'),
        'drivetrain_detail': ('drivetrain_detail',),
        'ground_clearance': ('ground_clearance_in_up_to', 'ground_clearance_in'),
        'cargo': ('cargo_cu_ft_up_to', 'cargo_cu_ft', 'cargo_volume_cu_ft'),
        'towing': ('towing_lbs_up_to', 'towing_lbs', 'max_towing_lbs'),
        'payload': ('payload_lbs',),
    }
    suffixes = {
        'acceleration': 'sec', 'ground_clearance': 'in', 'cargo': 'cu ft',
        'towing': 'lb', 'payload': 'lb',
    }
    for target, keys in aliases.items():
        if d.get(target) not in (None, ''):
            continue
        v, _ = first(side, *keys)
        if v not in (None, ''):
            d[target] = unit(v, suffixes.get(target, '')) if target in suffixes else v

    if d.get('efficiency') in (None, ''):
        v, key = first(
            side, 'mpg_combined_up_to', 'mpg_city_highway', 'mpg_city_highway_combined',
            'mpge_city_highway_combined', 'mpg_combined', 'mpge_combined',
            'mild_hybrid_mpg_combined', 'efficiency'
        )
        if v not in (None, ''):
            if isinstance(v, (int, float)):
                d['efficiency'] = f'{v:g} MPGe combined' if 'mpge' in key else f'{v:g} mpg combined'
            else:
                d['efficiency'] = clean_efficiency(v)

    if d.get('range') in (None, ''):
        v, _ = first(side, 'range_miles', 'range_miles_up_to', 'epa_range_miles', 'epa_range_miles_up_to', 'phev_electric_range_miles', 'electric_range')
        if v not in (None, ''):
            d['range'] = unit(v, 'miles')

    if d.get('charging') in (None, ''):
        v, key = first(side, 'charging', 'charging_kw', 'dc_fast_charging', 'charge_time')
        if v not in (None, ''):
            d['charging'] = unit(v, 'kW') if key == 'charging_kw' else v

    # Keep data-quality counts in sync with the final public detail object.
    q = c.setdefault('data_quality', {})
    q['detail_fields'] = len([v for v in d.values() if v not in (None, '', [], {})])


def main() -> None:
    data = json.loads(CARS.read_text(encoding='utf-8'))
    cars = data.get('cars') or []
    sides = sidecar_models()

    for c in cars:
        p = str(c.get('powertrain') or '').lower()
        if 'electrified' in p and not any(x in p for x in ('hybrid','electric','bev','phev','gas','diesel')):
            c['fuel_types'] = []
        c['upcoming'] = clean_upcoming(c)
        enrich_details(c, sides.get((norm(c.get('brand')), norm(c.get('model'))), {}))

    upcoming = [c for c in cars if c.get('upcoming')]
    data['upcoming_count'] = len(upcoming)
    CARS.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    UPCOMING.write_text(json.dumps({'generated': data.get('generated'), 'count': len(upcoming), 'cars': upcoming}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    if COMPARE.exists():
        compare = json.loads(COMPARE.read_text(encoding='utf-8'))
        by_id = {c.get('id'): c for c in cars}
        for row in compare.get('cars') or []:
            full = by_id.get(row.get('id'))
            if full:
                row['details'] = full.get('details', {})
                row['specs'] = full.get('specs', {})
                row['verified_on'] = full.get('verified_on', row.get('verified_on'))
                row['source'] = full.get('source', row.get('source'))
        COMPARE.write_text(json.dumps(compare, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    print('Conservative catalog post-process: upcoming', len(upcoming), 'cars', len(cars))

if __name__ == '__main__':
    main()
