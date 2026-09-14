#!/usr/bin/env python3
"""Conservative post-processing for DriveSpecLab's generated database catalog.

Removes false-positive upcoming flags and avoids guessing a fuel type when an official
source only says a future model is electrified without publishing the actual system.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / 'data' / 'catalog' / 'cars.json'
UPCOMING = ROOT / 'data' / 'catalog' / 'upcoming.json'

EXPLICIT = ('upcoming','expected','launch planned','planned for','announced for','future model','coming soon','pre-production')


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


def main() -> None:
    data = json.loads(CARS.read_text(encoding='utf-8'))
    cars = data.get('cars') or []
    for c in cars:
        p = str(c.get('powertrain') or '').lower()
        if 'electrified' in p and not any(x in p for x in ('hybrid','electric','bev','phev','gas','diesel')):
            c['fuel_types'] = []
        c['upcoming'] = clean_upcoming(c)
    upcoming = [c for c in cars if c.get('upcoming')]
    data['upcoming_count'] = len(upcoming)
    CARS.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    UPCOMING.write_text(json.dumps({'generated': data.get('generated'), 'count': len(upcoming), 'cars': upcoming}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Conservative catalog post-process: upcoming', len(upcoming))

if __name__ == '__main__':
    main()
