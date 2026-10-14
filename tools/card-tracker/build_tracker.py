"""Build the card tracker page.

Usage: python build_tracker.py <cards.json> <art-meta.json> <art-urls.json> <template.html> <out.html>

cards.json comes from extract_cards.py, art-meta.json from the art staging step (sheet sizes),
art-urls.json maps staged art file names to the artifact's stored asset urls.
"""
import json
import re
import sys

cards_p, meta_p, urls_p, tpl_p, out_p = sys.argv[1:6]
cards = json.load(open(cards_p, encoding='utf-8'))
import os
rw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rival-rewrite.json')
RW = json.load(open(rw_path, encoding='utf-8')) if os.path.exists(rw_path) else {}
cd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'spec', 'data', 'card-definitions.json')
RES = {(c['group'], c['id']): c['repo_effects'] for c in json.load(open(cd_path, encoding='utf-8'))} if os.path.exists(cd_path) else {}
meta = json.load(open(meta_p, encoding='utf-8'))
urls = json.load(open(urls_p, encoding='utf-8'))

GROUPS = [
    ('base', 'Base game', 'Main deck', 'Cards 1 to 138'),
    ('alien-base', 'Base game', 'Alien species cards', 'Anomalies, Centaurians, Exertians, Mascamites, Oumuamua'),
    ('base-solo-rival-action', 'Base game', 'Solo rival action cards', 'S.1 to S.19. Rewritten from the card art; please check each reading against the card'),
    ('expansion-promo-se-en', 'Promo', 'SE EN promo cards', 'SE EN 01 and SE EN 02: promo cards, not part of the base deck or the expansion; optional at game start. The group key keeps its old name so saved checks stay attached'),
    ('expansion-main-deck', 'Expansion', 'New main-deck cards', '42 cards'),
    ('expansion-alien', 'Expansion', 'Glyphids and Amoeba cards', 'Alien species cards'),
    ('expansion-arkhos-exploration', 'Expansion', 'Arkhos exploration cards', 'Repo has only stubs; no images'),
    ('expansion-arkhos-security', 'Expansion', 'Arkhos security cards', 'Repo has no printed text; no images'),
    ('expansion-organization', 'Expansion', 'Organizations', '11 asymmetric organizations'),
    ('expansion-quick-start', 'Expansion', 'Quick start cards', '21 cards (repo calls them prelude cards); no images'),
]
RIVAL_HELP = (
    '<ul>'
    '<li><b>Turn:</b> reveal the top card, do the first action that is possible, top to bottom. The arrow at the top decides ties: pointing left means the leftmost option, right means the rightmost.</li>'
    '<li><b>Analyze:</b> only when the rival computer is full. Clear it, take the card benefit (3 VP on some cards), gain the life trace on the rival board, move pool data into the computer, then discard a computer tech for 3 VP and 1 progress.</li>'
    '<li><b>Launch:</b> place a probe on Earth and gain the publicity shown. Skipped if a probe is already on Earth.</li>'
    '<li><b>Tech:</b> pay 6 publicity (skipped if the rival has less), or no cost where the card shows none. Rotate the solar system. The tech is the one the progress track points to, if it has a 2-point tile.</li>'
    '<li><b>Probe:</b> move from Earth to the first listed planet reachable in the shown number of moves. Then try to discard a probe tech to land on a moon; else take the first orbiter or first lander space; if both or neither are free, use the preference on the card (left icon first).</li>'
    '<li><b>Telescope:</b> mark the signals shown (Earth sector, card row), plus one extra card-row signal by discarding a telescope tech.</li>'
    '<li><b>Progress arrow with a 1:</b> advance the progress marker 1 space.</li>'
    '<li><b>S.3 and S.4:</b> if the 1st or 2nd alien species is discovered, replace the card with that species card (S.15 to S.19) and resolve it.</li>'
    '</ul>')
REF = {'base-solo-rival-action': 'ref-rival-actions.webp'}


def clean_enum(v):
    return v.split('.')[-1].lower() if v else None


def free_action(v):
    if not v:
        return None
    items = re.findall(r'type:\s*[A-Za-z]+\.([A-Z_]+),\s*value:\s*(\d+)', v)
    return ', '.join(f'{n} {t.lower()}' for t, n in items) or v


def art(x):
    if x['group'] == 'base-solo-rival-action':
        m = re.match(r'S\.(\d+)$', x['id'])
        if m:
            n = int(m.group(1)) - 1
            return ['ref-rival-actions.webp', n // 5, n % 5]
    if x.get('pos'):
        src, row, col = x['pos']
        m = re.search(r'/cards/(cards-\d)\.webp$', src)
        if m:
            return ['sheet-' + m.group(1) + '.webp', row, col]
        m = re.search(r'/aliens/([a-z]+)\.webp$', src)
        if m:
            return ['sheet-alien-' + m.group(1) + '.webp', row, col]
    img = x.get('img')
    if img:
        m = re.search(r'space-agency/(\d+)\.webp$', img)
        if m:
            return ['sa-' + m.group(1) + '.webp']
        m = re.search(r'corporations/(.+)\.jpg$', img)
        if m:
            return ['org-' + re.sub(r'[^a-z0-9]+', '-', m.group(1).lower()).strip('-') + '.jpg']
    return None


items = []
sheet_grid = {}
for g, _, _, _ in GROUPS:
    for x in [c for c in cards if c['group'] == g]:
        it = {'g': g, 'id': x['id'], 'n': x['name']}
        if x.get('alien'):
            it['sp'] = clean_enum(x['alien'])
        for k, f in (('p', x.get('price')), ('i', clean_enum(x.get('income'))), ('s', clean_enum(x.get('sector'))), ('f', free_action(x.get('freeAction')))):
            if f:
                it[k] = f
        if x.get('effectsRaw'):
            it['e'] = x['effectsRaw'].rstrip(',')
        if x.get('raw'):
            it['r'] = x['raw'][:1800]
        t = [[k, re.sub(r'<br\s*/?>', ' ', v)] for k, v in (x.get('text') or {}).items()]
        if t:
            it['t'] = t
        if x.get('flavor'):
            it['fl'] = x['flavor']
        if x['group'] == 'base-solo-rival-action' and x['id'] in RW:
            it['rw'] = RW[x['id']]['code']
            it['rwp'] = RW[x['id']]['words']
            it['rwd'] = RW[x['id']]['diff']
            it['rwdir'] = RW[x['id']]['dir']
        if (x['group'], x['id']) in RES:
            it['rs'] = RES[(x['group'], x['id'])]
        a = art(x)
        if a:
            if len(a) == 3:
                gr = sheet_grid.setdefault(a[0], [0, 0])
                gr[0] = max(gr[0], a[1] + 1)
                gr[1] = max(gr[1], a[2] + 1)
            it['a'] = a
        items.append(it)

meta['sheets'].setdefault('ref-rival-actions.webp', {'w': 1867, 'h': 2080})  # half-size copy of the 3735x4160 sheet
sheets = {}
for name, (rows, cols) in sheet_grid.items():
    m = meta['sheets'][name]
    sheets[name] = {'w': m['w'], 'h': m['h'], 'cols': cols, 'rows': rows}
missing = sorted({i['a'][0] for i in items if i.get('a')} - set(urls))
if missing:
    sys.exit('no stored url for: ' + ', '.join(missing))
used = {i['a'][0] for i in items if i.get('a')} | set(REF.values())
data = {
    'groups': [dict({'key': g, 'scope': s, 'label': l, 'note': n}, **({'help': RIVAL_HELP} if g == 'base-solo-rival-action' else {})) for g, s, l, n in GROUPS],
    'items': items,
    'art': {'urls': {k: urls[k] for k in sorted(used)}, 'sheets': sheets, 'refs': REF},
}
s = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(out_p, 'w', encoding='utf-8').write(open(tpl_p, encoding='utf-8').read().replace('/*DATA*/', s))
print(len(items), 'items;', sum(1 for i in items if i.get('a')), 'with art;', len(s), 'bytes of data')
