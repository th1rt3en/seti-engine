"""Copy the confirmed spec data into the engine package (services/engine/src/seti_engine/data).

Run from the repo root: python tools/engine/sync_data.py
The engine only reads these copies; the sources of truth are docs/spec/data/*.json (owner-confirmed).
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
SPEC = os.path.join(ROOT, 'docs', 'spec', 'data')
OUT = os.path.join(ROOT, 'services', 'engine', 'src', 'seti_engine', 'data')
os.makedirs(OUT, exist_ok=True)

for name in ('solar-system.json', 'stars.json', 'planets.json', 'tech-board.json', 'player-board.json', 'gold-tiles.json', 'alien-boards.json',
             'solo-boards.json', 'objectives.json', 'rival-action-cards.json', 'expansion-organizations.json', 'expansion-quick-start.json', 'expansion-arkhos.json', 'expansion-glyphids.json', 'expansion-amoeba.json'):
    with open(os.path.join(SPEC, name), encoding='utf-8') as f:
        data = json.load(f)
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=True)


def enum(v):
    return v.split('.')[-1].lower() if v else None


# Static card facts: id -> {name, deck, cost, income, sector}. Effects are not here: card effects are implemented in code per card.
extracted = json.load(open(os.path.join(ROOT, 'tools', 'card-tracker', 'cards-extracted.json'), encoding='utf-8'))
cards = {}
for c in extracted:
    if c['group'] not in ('base', 'alien-base', 'expansion-promo-se-en'):
        continue
    cid = c['id'].replace(' ', '_')
    deck = 'base' if c['group'] == 'base' else 'promo' if c['group'] == 'expansion-promo-se-en' else 'alien'
    alien = enum(c.get('alien')) if c.get('alien') else None
    fa = [[enum(t), int(v)] for t, v in re.findall(r'type:\s*[A-Za-z]+\.([A-Z_]+),\s*value:\s*(\d+)', c.get('freeAction') or '')]
    cards[cid] = {'free': fa, 'name': c['name'], 'deck': deck, 'species': alien, 'cost': int(c['price']) if c.get('price') not in (None, '') else 0,
                  'income': enum(c.get('income')), 'sector': enum(c.get('sector'))}
assert sum(1 for v in cards.values() if v['deck'] == 'base') == 138
with open(os.path.join(OUT, 'cards.json'), 'w', encoding='utf-8') as f:
    json.dump(cards, f, indent=1, sort_keys=True)
print('synced', len(os.listdir(OUT)), 'files;', len(cards), 'cards')
