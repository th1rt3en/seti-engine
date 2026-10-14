"""Resolve each base and alien card into readable full card text: repo data (effects, mission, end-game, texts) merged with the
owner's corrections from the card tracker.

Usage: python resolve_cards.py <repo>/packages/common/src <verification-snapshot.json> <out.json>

Each resolved card has:
  id, name, group, cost, cost_type, income, sector, free_action,
  repo_effects: list of readable strings (from the repo's effect data, in card order),
  owner_additions: list of readable strings (from the owner's notes, parsed where possible),
  owner_note: the note verbatim, status: complete | owner-corrected | needs-owner-reading.
"""
import json
import os
import re
import sys

SRC, SNAP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LOC = os.path.join(SRC, '..', 'locales', 'en')
L = {}
for f in ('seti.json', 'common.json'):
    def walk(o, p=''):
        for k, v in o.items():
            kk = p + '.' + k if p else k
            if isinstance(v, dict): walk(v, kk)
            else: L[kk] = v
    walk(json.load(open(os.path.join(LOC, f), encoding='utf-8')))

# ---- tiny expression parser for the repo's effect DSL ----
TOK = re.compile(r"\s*(?:(//[^\n]*)|('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`)|(-?\d+(?:\.\d+)?)|([A-Za-z_$][\w$.]*)|([()\[\]{},:]))")


def tokenize(s):
    pos, out = 0, []
    while pos < len(s):
        m = TOK.match(s, pos)
        if not m:
            pos += 1
            continue
        pos = m.end()
        if m.group(1): continue
        if m.group(2): out.append(('s', m.group(2)[1:-1]))
        elif m.group(3): out.append(('n', float(m.group(3)) if '.' in m.group(3) else int(m.group(3))))
        elif m.group(4): out.append(('i', m.group(4)))
        else: out.append(('p', m.group(5)))
    return out


class P:
    def __init__(self, toks): self.t, self.i = toks, 0
    def peek(self): return self.t[self.i] if self.i < len(self.t) else (None, None)
    def nxt(self): v = self.peek(); self.i += 1; return v
    def expr(self):
        k, v = self.peek()
        if k == 'p' and v == '[':
            self.nxt(); a = []
            while self.peek() != ('p', ']') and self.peek()[0]:
                a.append(self.expr())
                if self.peek() == ('p', ','): self.nxt()
            self.nxt(); return ('arr', a)
        if k == 'p' and v == '{':
            self.nxt(); d = {}
            while self.peek() != ('p', '}') and self.peek()[0]:
                key = self.nxt()[1]
                if self.peek() == ('p', ':'): self.nxt(); d[key] = self.expr()
                if self.peek() == ('p', ','): self.nxt()
            self.nxt(); return ('obj', d)
        if k in ('s', 'n'): self.nxt(); return (k, v)
        if k == 'i':
            self.nxt()
            if v == 'as' and self.peek() == ('i', 'any'): self.nxt(); return self.expr() if False else ('skip', None)
            if self.peek() == ('p', '('):
                self.nxt(); args = []
                while self.peek() != ('p', ')') and self.peek()[0]:
                    args.append(self.expr())
                    if self.peek() == ('p', ','): self.nxt()
                self.nxt()
                return ('call', v, args)
            return ('id', v)
        self.nxt(); return ('skip', None)


def parse_list(text):
    p = P(tokenize(text)); items = []
    while p.peek()[0]:
        e = p.expr()
        if e[0] == 'skip' and p.peek()[0] == 'i' and p.peek()[1] == 'any': p.nxt()
        if e[0] != 'skip': items.append(e)
        if p.peek() == ('p', ','): p.nxt()
        elif p.peek() == ('i', 'as'): p.nxt(); p.nxt()
    return items


PH = {'score': 'VP', 'publicity': 'publicity', 'energy': 'energy', 'data': 'data', 'move': 'movement', 'credit': 'credit'}
PHX = {'sample': 'sample', 'any-signal': 'signal in any sector', 'yellow-trace': 'yellow trace', 'red-trace': 'pink trace', 'blue-trace': 'blue trace', 'any-trace': 'trace of any color',
       'orbit-or-land-count': 'orbiter or lander', 'land-count': 'lander', 'orbit-count': 'orbiter', 'income': 'income', 'exofossil': 'exofossil', 'use-exofossil': 'spend an exofossil',
       'energy-income': 'energy income card', 'credit-income': 'credit income card', 'card-income': 'card income card', 'draw-card-1': '1 card from the deck', 'any-card-1': '1 card from the row or the deck',
       'yellow-signal': 'signal in a yellow sector', 'red-signal': 'signal in a red sector', 'blue-signal': 'signal in a blue sector', 'fulfill-sample': 'delivered sample',
       'fulfill-sector-yellow': 'win in a yellow sector', 'fulfill-sector-red': 'win in a red sector', 'fulfill-sector-blue': 'win in a blue sector', 'fulfill-sector-black': 'win in a black sector',
       'fulfill-sector-any': 'win in a sector', 'computer-tech': 'computer tech', 'probe-tech': 'probe tech', 'scan-tech': 'telescope tech', 'any-tech': 'tech'}


def ph(m):
    k = m.group(1)
    r = re.match(r'(score|publicity|energy|data|move|credit)-(\d+)$', k)
    if r: return '%s %s' % (r.group(2), PH[r.group(1)])
    r = re.match(r'(red|yellow|blue)-trace-(\d+)$', k)
    if r: return '%s %s traces' % (r.group(2), {'red': 'pink'}.get(r.group(1), r.group(1)))
    r = re.match(r'exofossil-(\d+)$', k)
    if r: return '%s exofossils' % r.group(1)
    return PHX.get(k, '{' + k + '}')


def text_of(s):
    s = L.get(s, s)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'\{([a-z0-9\-]+)\}', ph, s)
    return re.sub(r'\s+', ' ', s).strip()


def num(args, d=1):
    return args[0][1] if args and args[0][0] == 'n' else d


def plural(n, w): return '%d %s' % (n, w)


def render(e):
    k = e[0]
    if k == 's': return text_of(e[1])
    if k == 'n': return str(e[1])
    if k == 'id': return e[1].split('.')[-1].lower()
    if k == 'arr': return '; '.join(x for x in (render(a) for a in e[1]) if x)
    if k == 'obj':
        if 'reward' in e[1]: return render(e[1]['reward'])
        return ', '.join('%s=%s' % (a, render(b)) for a, b in e[1].items())
    if k != 'call': return ''
    name, a = e[1].split('.')[-1], e[2]
    n = num(a)
    if name == 'DESC': return text_of(a[0][1]) if a and a[0][0] == 's' else ''
    simple = {'SCORE': '%d VP', 'PUBLICITY': '%d publicity', 'DATA': '%d data', 'CREDIT': '%d credit', 'ENERGY': '%d energy', 'MOVE': '%d movement'}
    if name in simple: return simple[name] % n
    if name == 'CARD_ANY': return '%d card from the row or the deck' % n
    if name == 'CARD': return '%d random card from the deck' % n
    if name == 'ROTATE': return 'rotate the solar system'
    acts = {'LAUNCH': 'launch a probe', 'ORBIT': 'orbit action', 'LAND': 'land action', 'ORBIT_OR_LAND': 'orbit or land action', 'SCAN': 'scan action', 'COMPUTER': 'analyze action'}
    if name in acts: return 'take a %s without paying its cost' % acts[name] if name != 'LAUNCH' else 'launch a probe without paying its cost'
    tech = {'TECH_PROBE': 'probe', 'TECH_SCAN': 'telescope', 'TECH_COMPUTER': 'computer', 'TECH_ANY': 'any'}
    if name in tech: return 'research a %s tech' % tech[name]
    tr = {'TRACE_RED': 'pink', 'TRACE_YELLOW': 'yellow', 'TRACE_BLUE': 'blue', 'TRACE_ANY': 'any'}
    if name in tr: return 'mark %d %s life trace' % (n, tr[name])
    sg = {'SIGNAL_RED': 'red', 'SIGNAL_YELLOW': 'yellow', 'SIGNAL_BLUE': 'blue', 'SIGNAL_BLACK': 'black', 'SIGNAL_ANY': 'any'}
    if name in sg: return 'mark %d signal%s in %s' % (n, 's' if n > 1 else '', 'any sector' if sg[name] == 'any' else 'a %s sector' % sg[name])
    if name == 'SIGNAL_DISPLAY_CARD': return 'discard %d card%s from the row and mark a signal in each matching sector' % (n, 's' if n > 1 else '')
    if name == 'INCOME': return 'tuck a card for income'
    if name == 'EXOFOSSIL': return 'gain %d exofossil' % n
    if name == 'USE_EXOFOSSIL': return 'spend %d exofossil' % n
    if name == 'ADVANCED_15': return 'place your message marker 15 points ahead'
    if name == 'FULFILL_ADVANCED': return 'when you reach the marker'
    if name == 'FULFILL_SAMPLE': return 'deliver a sample'
    if name.startswith('FULFILL_SECTOR_'): return 'win a %s sector%s' % (name[15:].lower().replace('any', ''), ' (x%d)' % n if n > 1 else '')
    cnt = {'ORBIT_OR_LAND_COUNT': 'orbiter or lander', 'ORBIT_COUNT': 'orbiter', 'LAND_COUNT': 'lander'}
    if name in cnt: return cnt[name]
    if name == 'QUICK_MISSION': return 'QUICK MISSION: when %s, gain %s' % (render(a[0]), render(a[1]) if len(a) > 1 else '')
    if name == 'FULL_MISSION':
        circles = render(a[0]) if a and a[0][0] == 'arr' else ''
        req = text_of(a[1][1]) if len(a) > 1 and a[1][0] == 's' else ''
        return 'TRIGGERABLE MISSION: %s circles: %s' % (req, circles)
    if name == 'END_GAME':
        d = render(a[0]) if a else ''
        return 'END OF GAME: %s' % d
    if name == 'MASCAMITES_SAMPLE_DELIVERY': return 'deliver a sample to %s' % (a[0][1].split('.')[-1].lower() if a and a[0][0] == 'id' else '?')
    return '%s(%s)' % (name, ', '.join(render(x) for x in a))


def balanced(text, start):
    d, i, instr = 0, start, None
    while i < len(text):
        c = text[i]
        if instr:
            if c == '\\': i += 1
            elif c == instr: instr = None
        elif c in '\'"`': instr = c
        elif c in '([{': d += 1
        elif c in ')]}':
            d -= 1
            if d == 0: return i
        i += 1
    return -1


def objects(text, marker):
    i = text.index(marker); i = text.index('= [', i) + 2
    out, j = [], i + 1
    d = 0; instr = None; start = None
    while j < len(text):
        c = text[j]
        if instr:
            if c == '\\': j += 1
            elif c == instr: instr = None
        else:
            if c in '\'"`': instr = c
            elif c == '/' and text[j + 1] == '/': j = text.index('\n', j)
            elif c == '/' and text[j + 1] == '*': j = text.index('*/', j) + 1
            elif c == '{':
                if d == 0: start = j
                d += 1
            elif c == '}':
                d -= 1
                if d == 0: out.append(text[start:j + 1])
            elif c == ']' and d == 0: break
        j += 1
    return out


def field(b, name):
    m = re.search(r'^\s{4}' + name + r':\s*(.+?),?\s*$', b, re.M)
    return m.group(1).strip() if m else None


def effects_of(b):
    m = re.search(r'^\s{4}effects:\s*\[', b, re.M)
    if not m: return []
    s = m.end() - 1
    e = balanced(b, s)
    return parse_list(b[s + 1:e])


def clean_enum(v): return v.split('.')[-1].lower() if v else None


def fa_block(b):
    m = re.search(r'^\s{4}freeAction:\s*\[', b, re.M)
    if not m: return None
    st = m.end() - 1
    return b[st:balanced(b, st) + 1]


def fa_text(v):
    if not v: return None
    items = re.findall(r'type:\s*[A-Za-z]+\.([A-Z_]+),\s*value:\s*(\d+)', v)
    return ', '.join('%s %s' % (n, t.lower().replace('_', ' ')) for t, n in items) or v


# ---- owner notes ----
NOTE = [
    (r'^(\d+)\s*(publicity|data|credit|energy)$', lambda m: '%s %s' % (m.group(1), m.group(2))),
    (r'^gain (\d+) (publicity|data|credit|energy)$', lambda m: '%s %s' % (m.group(1), m.group(2))),
    (r'^(\d+)\s*(?:random )?(?:card|cards)(?: any)?$', lambda m: '%s card from the row or the deck' % m.group(1)),
    (r'^draw (\d+)(?: any)?$', lambda m: '%s card from the row or the deck' % m.group(1)),
    (r'^move (\d+)$', lambda m: '%s movement' % m.group(1)),
    (r'^(\d+) scan action$', lambda m: 'take a scan action without paying its cost'),
    (r'^scan action$', lambda m: 'take a scan action without paying its cost'),
    (r'^(\d+) launch action$', lambda m: 'launch a probe without paying its cost'),
    (r'^then land.*$', lambda m: 'then land (after movement)'),
    (r'^(\d+) rotate$', lambda m: 'rotate the solar system'),
    (r'^(\d+) (blue|pink|orange|any|any color) tech(?:nology)?$', lambda m: 'research a %s tech' % {'blue': 'computer', 'pink': 'telescope', 'orange': 'probe', 'any': 'any', 'any color': 'any'}[m.group(2)]),
    (r'^(?:mark )?(\d+) (blue|pink|yellow|any) (?:life )?trace$', lambda m: 'mark %s %s life trace' % (m.group(1), m.group(2))),
    (r'^mark (\d+) signals?$', lambda m: 'mark %s signal%s' % (m.group(1), 's' if m.group(1) != '1' else '')),
    (r'^scan (\d+) from display cards$', lambda m: 'discard %s card%s from the row and mark a signal in each matching sector' % (m.group(1), 's' if m.group(1) != '1' else '')),
    (r'^(\d+) exofossil$', lambda m: 'gain %s exofossil' % m.group(1)),
    (r'^(\d+) any trace$', lambda m: 'mark %s trace of any color' % m.group(1)),
]


def parse_note(note):
    adds, unparsed = [], []
    for line in note.split('\n'):
        l = line.strip().strip('.')
        l = re.sub(r'^(missing (?:instant )?effect|missing quick mission)\s*:?\s*', '', l, flags=re.I).strip(' ,')
        if not l: continue
        if re.search(r'danger|endgame|e\.ADVANCED|mark \d+ \w+ traces? ->', line, re.I):
            adds.append(('raw', line.strip())); continue
        for part in [x.strip() for x in l.split(',') if x.strip()]:
            for pat, fn in NOTE:
                m = re.match(pat, part, re.I)
                if m: adds.append(('ok', fn(m))); break
            else:
                unparsed.append(part); adds.append(('raw', part))
    return adds, unparsed


def main():
    snap = json.load(open(SNAP, encoding='utf-8'))['rows']
    notes = {(r['group'], r['id']): r for r in snap}
    out = []
    for fname, marker, group in (('baseCards.ts', '_baseCards', 'base'), ('alienCards.ts', 'const _alienCards', 'alien-base')):
        text = open(os.path.join(SRC, 'data', fname), encoding='utf-8').read()
        for b in objects(text, marker):
            cid = field(b, 'id').strip("'\"")
            if group == 'base' and not cid.isdigit(): continue
            nm = field(b, 'name').strip("'\"")
            nm = L.get(nm, nm)
            effs = [x for x in (render(e) for e in effects_of(b)) if x]
            desc = field(b, 'description')
            if desc and desc.strip("'\"") and desc.strip("'\"") != '':
                effs.append(text_of(desc.strip("'\"")))
            # texts referenced outside the effects array (e.g. end-game keys given as description or special)
            for k in re.findall(r"'((?:desc|sa\.desc|et)[\w.\-]*)'", b):
                t = text_of(k)
                if t and t not in effs and k in L and not any(t == x or t in x for x in effs): effs.append(t)
            fa = fa_text(fa_block(b))
            r = notes.get((group, cid))
            adds, unparsed = ([], [])
            status = 'complete'
            if r and r['status'] == 'difference':
                adds, unparsed = parse_note(r['note'])
                status = 'owner-corrected' if not unparsed else 'needs-owner-reading'
            elif not r:
                status = 'unchecked'
            joined = ' | '.join(effs).lower()
            fixed = []

            def norm(t):
                t = t.lower()
                t = re.sub(r'^(missing )?(instant )?(effect|quick mission)\s*:\s*', '', t).strip()
                t = re.sub(r'scan (red|yellow|blue|black)', r'mark 1 signal in a  sector', t)
                t = re.sub(r'draw (\d+)', r' random card', t)
                t = t.replace('gain ', '')
                return t
            for k, t in adds:
                dup = False
                if k == 'ok' and norm(t) in joined: dup = True
                if k == 'raw':
                    names = re.findall(r'e\.([A-Z_0-9]+)\(', t)
                    if names and all(re.search(n, b) for n in names): dup = True
                    nt = norm(t)
                    parts = [x.strip() for x in re.split(r',| and ', nt) if x.strip()]
                    if parts and not re.search(r'danger|endgame', t, re.I):
                        if all(any(re.sub(r'[^a-z0-9 ]', '', q) in re.sub(r'[^a-z0-9 ]', '', joined) for q in [pp]) for pp in parts if not pp.startswith('e.')): dup = True
                    if re.search(r'quick mission', t, re.I) and 'QUICK_MISSION' in b: dup = dup or ('mark 3' in joined and 'mark 1 pink' in joined)
                fixed.append((('dup' if dup else k), t))
            adds = fixed
            out.append({'id': cid, 'group': group, 'name': nm, 'cost': field(b, 'price'), 'cost_type': clean_enum(field(b, 'priceType')) or ('energy' if group == 'alien-base' and False else 'credit'),
                        'income': clean_enum(field(b, 'income')), 'sector': clean_enum(field(b, 'sector')), 'free_action': fa,
                        'repo_effects': effs, 'owner_additions': [{'kind': k, 'text': t} for k, t in adds], 'owner_note': r['note'] if r else '', 'status': status, 'unparsed': unparsed,
                        'pos': None})
    # keep sprite positions
    cards = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cards-extracted.json'), encoding='utf-8'))
    pos = {(c['group'], c['id']): c.get('pos') for c in cards}
    for c in out: c['pos'] = pos.get((c['group'], c['id']))
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    import collections
    print(len(out), collections.Counter(c['status'] for c in out))
    print('unparsed examples:', [c['unparsed'] for c in out if c['unparsed']][:12])


main()
