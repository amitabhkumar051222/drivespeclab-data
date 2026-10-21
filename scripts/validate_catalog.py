#!/usr/bin/env python3
"""Reject corrupt or inconsistent outputs before any public catalog commit."""
import json
from pathlib import Path


def validate(root):
    data = json.loads((root / 'data/catalog/cars.json').read_text())
    compare = json.loads((root / 'data/compare/cars.json').read_text())
    cars = data['cars']
    if not cars or data['count'] != len(cars):
        raise ValueError('Empty catalog or incorrect count')
    ids = [c['id'] for c in cars]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate stable model IDs')
    indexed = {c['id']: c for c in compare['cars']}
    if len(indexed) != len(compare['cars']) or set(indexed) != set(ids):
        raise ValueError('Comparison and catalog model IDs differ')
    for c in cars:
        if not c.get('brand') or not c.get('model'):
            raise ValueError('Missing model identity')
        price = c.get('starting_price')
        if price is not None and (isinstance(price, bool) or not isinstance(price, (float,int)) or price <= 0):
            raise ValueError(f"Invalid price for {c['id']}")
        trims = [t['msrp'] for t in c.get('trims', []) if t.get('msrp') is not None]
        if trims and min(trims) != price:
            raise ValueError(f"Starting price/trim mismatch for {c['id']}")
        other = indexed[c['id']]
        for field in ['year', 'source', 'verified_on', 'details']:
            if c.get(field) != other.get(field):
                raise ValueError(f"Comparison mismatch: {c['id']} {field}")
        if c['starting_price_text'] != other['starting_price']:
            raise ValueError(f"Comparison price mismatch: {c['id']}")
        if c.get('source') and not c['source'].startswith('https://'):
            raise ValueError(f"Invalid source URL: {c['id']}")
    print(f'Validated {len(cars)} model records and matching comparison rows')

if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
