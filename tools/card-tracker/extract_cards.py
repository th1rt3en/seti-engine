import json, re, sys, os
SRC = sys.argv[1]  # packages/common/src
LOC = os.path.join(SRC, '..', 'locales', 'en')

def load_locale():
    flat = {}
    def walk(o, p=''):
        for k, v in o.items():
            key = f'{p}.{k}' if p else k
            if isinstance(v, dict): walk(v, key)
            else: flat[key] = v
    for f in ('seti.json', 'common.json'):
        walk(json.load(open(os.path.join(LOC, f), encoding='utf-8')))
    return flat
L = load_locale()
FLAV = json.load(open(os.path.join(LOC, 'flavorText.json'), encoding='utf-8'))

def top_objects(text, start_marker):
    """yield source text of each top-level {...} inside the first array after start_marker"""
    i = text.index(start_marker)
    i = text.index('= [', i) + 2
    depth = 0; out = []; j = i + 1
    instr = None
    start = None
    while j < len(text):
        c = text[j]
        if instr:
            if c == '\\': j += 1
            elif c == instr: instr = None
        else:
            if c in '\'"`': instr = c
            elif c == '/' and text[j+1] == '/':
                j = text.index('\n', j)
            elif c == '/' and text[j+1] == '*':
                j = text.index('*/', j) + 1
            elif c == '{':
                if depth == 0: start = j
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0: out.append(text[start:j+1])
            elif c == ']' and depth == 0: break
        j += 1
    return out

def field(block, name):
    m = re.search(r'^\s{4}' + name + r':\s*(.+?),?\s*$', block, re.M)
    return m.group(1).strip() if m else None

def strip_q(s):
    return s.strip("'\"") if s else s

def resolve_keys(block):
    keys = set(re.findall(r"'([A-Za-z0-9_.\-]+\.[A-Za-z0-9_.\-]+)'", block))
    res = {}
    for k in sorted(keys):
        if k in L: res[k] = L[k]
    return res

def card(block, group, species=None):
    cid = strip_q(field(block, 'id'))
    name = strip_q(field(block, 'name')) or ''
    name_en = L.get(name, name)
    price = field(block, 'price')
    income = field(block, 'income')
    sector = field(block, 'sector')
    alien = field(block, 'alien')
    fa = re.search(r'^\s{4}freeAction:\s*(\[.*?\]),\s*$', block, re.M | re.S)
    eff = re.search(r'^\s{4}effects:\s*\[(.*?)^\s{4}\],', block, re.M | re.S)
    pos = re.search(r"position:\s*\{\s*src:\s*'([^']+)',\s*row:\s*(\d+),\s*col:\s*(\d+)", block)
    img = re.search(r"^\s+image:\s*'([^']+)'", block, re.M)
    desc = re.search(r"^\s{4}description:\s*(.+?),?\s*$", block, re.M)
    return dict(group=group, id=cid, name=name_en, nameKey=name if name != name_en else None,
                price=price, income=income, sector=sector, alien=alien,
                freeAction=(fa.group(1).replace('\n', ' ') if fa else None),
                effectsRaw=re.sub(r'\n\s+', ' ', eff.group(1)).strip() if eff else None,
                description=strip_q(desc.group(1)) if desc else None,
                pos=[pos.group(1), int(pos.group(2)), int(pos.group(3))] if pos else None,
                img=img.group(1) if img else None,
                text=resolve_keys(block),
                flavor=FLAV.get(cid) if isinstance(FLAV.get(cid), str) else None)

cards = []
def read(f): return open(os.path.join(SRC, 'data', f), encoding='utf-8').read()
for b in top_objects(read('baseCards.ts'), '_baseCards'):
    cards.append(card(b, 'base'))
for b in top_objects(read('alienCards.ts'), 'const _alienCards'):
    c = card(b, 'alien-base'); cards.append(c)
for b in top_objects(read('spaceAgencyCards.ts'), '_spaceAgencyCards'):
    cards.append(card(b, 'expansion-main-deck'))
for b in top_objects(read('spaceAgencyAliens.ts'), '_spaceAgencyAliens'):
    cards.append(card(b, 'expansion-alien'))
json.dump(cards, open(sys.argv[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter((c['group'], (c['alien'] or '').replace('EAlienType.', '')) for c in cards))
print(len(cards), 'cards;', sum(1 for c in cards if not c['id']), 'missing id')

# ---- additional groups ----
def raw_block(block):
    return re.sub(r'\s+', ' ', block).strip()
extra = []
for b in top_objects(read('organizations.ts'), 'export const ORGANIZATIONS'):
    nm = strip_q(field(b, 'name'))
    extra.append(dict(group='expansion-organization', id=strip_q(field(b, 'id')), name=nm, raw=raw_block(b), img=(re.search(r"image:\s*'([^']+)'", b) or [None,None])[1], text=resolve_keys(b)))
for b in top_objects(read('preludeCards.ts'), 'export const preludeCards'):
    extra.append(dict(group='expansion-quick-start', id=strip_q(field(b, 'id')), name='Quick start ' + strip_q(field(b, 'id')), raw=raw_block(b), text=resolve_keys(b)))
for b in top_objects(read('rivalActionCards.ts'), 'export const'):
    extra.append(dict(group='base-solo-rival-action', id=strip_q(field(b, 'id')), name='Rival action ' + strip_q(field(b, 'id')), raw=raw_block(b), text=resolve_keys(b)))
ark = read('arkhosCards.ts')
for kind, var in (('exploration', 'ARKHOS_EXPLORATION_CARD_IDS'), ('security', 'ARKHOS_SECURITY_CARD_IDS')):
    ids = [f'ARKHOS.EXPLORATION.{n}' for n in range(1, 10)] if kind == 'exploration' else [f'AIcard{n:02d}' for n in range(1, 13)]
    for k, i in enumerate(ids):
        extra.append(dict(group='expansion-arkhos-' + kind, id=i, name=f'Arkhos {kind} {i}', raw=('Repo has only a stub for this card: effect ids are "UNMAPPED"; no rules text.' if kind == 'exploration' else f'trace color group {["pink","yellow","blue"][k//4]}; cost 2 credits; effect text is a generic per-color description, not the printed card text'), text={}))
for c in cards:
    c['raw'] = None
allc = cards + extra
for c in allc:
    if c['group'] == 'base' and not c['id'].isdigit():
        c['group'] = 'expansion-promo-se-en'
json.dump(allc, open(sys.argv[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(Counter(c['group'] for c in allc), len(allc))
