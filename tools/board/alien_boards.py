"""Base-game alien species boards and tokens (Anomalies, Centaurians, Exertians, Mascamites, 'Oumuamua).

Sources: assets/alien-board-*.png, token images in assets/, rule sheets docs/rules/SETI_Alien_rule_sheets_(EN).pdf, rulebook p.20.
Fill rule (rulebook p.20): when a player gains a life trace they mark ANY empty space of the matching color; the order of spaces is
a position, not a fill order. "Higher" matters only for Anomalies (the highest marked space in a column wins an anomaly) and for
the Exertian tiers (danger per marker). Columns are listed here from the top of the board downwards, as printed.

Run: python tools/board/alien_boards.py  (writes docs/spec/data/alien-boards.json and docs/spec/board-alien-species.md)
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def vp(n): return {'t': 'vp', 'n': n}
def pub(n): return {'t': 'publicity', 'n': n}
def credit(n): return {'t': 'credit', 'n': n}
def energy(n): return {'t': 'energy', 'n': n}
def data(n): return {'t': 'data', 'n': n}
def card(n=1): return {'t': 'card_any', 'n': n}
def alien_card(n=1): return {'t': 'alien_card', 'n': n}
def exo(n): return {'t': 'exofossil', 'n': n}
def trace_any(n=1): return {'t': 'trace', 'kind': 'any', 'n': n}
def sig_oum(n=1): return {'t': 'signal_oumuamua', 'n': n}


def sp(rewards, cost=None, repeat=False, tier=None, note=None):
    d = {'rewards': rewards}
    if cost: d['cost'] = cost
    if repeat: d['repeat'] = True
    if tier: d['tier'] = tier
    if note: d['note'] = note
    return d


def cols(spaces_by_color):
    return [{'color': c, 'spaces': s} for c, s in spaces_by_color.items()]


SAME3 = lambda spaces: {'pink': spaces, 'yellow': spaces, 'blue': spaces}

SPECIES = {
    'anomalies': {
        'title': 'Anomalies', 'image': 'ab_anomalies',
        'columns': cols(SAME3([sp([vp(2)], repeat=True, note='top capsule: always available; a later marker sits above earlier ones'), sp([vp(3)]), sp([vp(2), pub(1)]), sp([vp(2), alien_card()]), sp([vp(4), alien_card()])])),
        'tokens': [
            {'name': 'Anomaly token, pink column', 'sides': [[credit(1)], [vp(4)]], 'column': 'pink'},
            {'name': 'Anomaly token, yellow column', 'sides': [[card(1)], [pub(2)]], 'column': 'yellow'},
            {'name': 'Anomaly token, blue column', 'sides': [[data(1)], [energy(1)]], 'column': 'blue'}],
    },
    'centaurians': {
        'title': 'Centaurians', 'image': 'ab_centaurians',
        'columns': cols(SAME3([sp([vp(6)], cost=[data(1)], repeat=True, note='top capsule: pay 1 data each time'), sp([vp(15)], cost=[data(3)]), sp([vp(5)]), sp([vp(3), alien_card()]), sp([vp(5), alien_card()])])),
        'message_rewards': [[trace_any(1)], [alien_card(1), energy(1)], [pub(3)], [vp(8)]],
        'message_note': 'Four reward hexes across the top. When a player reaches their message milestone they choose one available hex and cover it with their message tile.',
        'tokens': [{'name': 'Message tile (+15), one per player color', 'colors': ['white', 'green', 'purple', 'orange'], 'note': 'Four player colors are shown in the supplied tiles; the physical game has 4 message tiles.'}],
    },
    'exertians': {
        'title': 'Exertians', 'image': 'ab_exertians',
        'columns': cols({
            'pink': [sp([vp(3), pub(1)], tier=1), sp([vp(4), credit(1)], tier=2), sp([vp(5), credit(1)], tier=2), sp([vp(7), credit(1)], tier=3), sp([vp(9), credit(1)], tier=3)],
            'yellow': [sp([vp(3), pub(1)], tier=1), sp([vp(1), energy(1), card(1)], tier=2), sp([vp(2), energy(1), card(1)], tier=2), sp([vp(4), energy(1), card(1)], tier=3), sp([vp(6), energy(1), card(1)], tier=3)],
            'blue': [sp([vp(3), pub(1)], tier=1), sp([vp(1), data(1), pub(1)], tier=2), sp([vp(2), data(1), pub(1)], tier=2), sp([vp(4), data(1), pub(1)], tier=3), sp([vp(6), data(1), pub(1)], tier=3)]}),
        'tier_danger': {'1': 1, '2': 2, '3': 3},
        'banner': 'Danger (one-tenth of total points lost by the player with the most danger), see ALIEN-EXE-07.',
        'tokens': [{'name': 'Milestone tiles (2)', 'note': 'Placed 20 and 40 points ahead of the leading player. The second tile costs 1 credit to use (rule sheet).'}],
    },
    'mascamites': {
        'title': 'Mascamites', 'image': 'ab_mascamites',
        'columns': cols({
            'pink': [sp([vp(4)]), sp([vp(5)]), sp([vp(3), alien_card()]), sp([vp(5), alien_card()])],
            'yellow': [sp([vp(4)]), sp([vp(5)]), sp([vp(3), alien_card()]), sp([vp(5), alien_card()])],
            'blue': [sp([], note='6 empty "sample" spaces (check mark with a sample picture): each gets a delivered sample token face up and then gives that token\'s reward'),
                     sp([], note='the designated space where the one face-up sample token starts'), sp([vp(3), alien_card()]), sp([vp(5), alien_card()])]}),
        'tokens': [{'name': 'Sample tokens (7), faces', 'sides': [[pub(3)], [vp(7)], [vp(3), card(1)], [data(2)], [energy(2)], [credit(2)], [{'t': 'card_random', 'n': 2}]],
                    'note': 'Seven sample tokens with different faces and one common back (spider). The face "2 ?" is read as 2 random cards.'}],
    },
    'oumuamua': {
        'title': "'Oumuamua", 'image': 'ab_oumuamua',
        'columns': cols(SAME3([sp([vp(6)], cost=[exo(1)], repeat=True, note='top capsule: pay 1 exofossil each time'), sp([vp(2), exo(1)]), sp([vp(3), alien_card()]), sp([vp(3), alien_card(), exo(1)]), sp([vp(25)], cost=[exo(4)])])),
        'planet_like': {'orbit': [vp(10), exo(1), sig_oum(1)], 'first_orbiter': [alien_card()], 'land': [vp(9), exo(2)], 'first_lander_data': [3, 2, 1],
                        'note': 'The top of the board: orbit rewards, a first-orbiter bonus (1 alien card), lander rewards and three first-lander data spaces, as for a planet (ALIEN-OUM-05).'},
        'tile': {'data_tokens': 3, 'slot_rewards': {'first_marker': [vp(1)], 'third_marker': [vp(2)]}, 'on_completion': 'each contributor gains 1 exofossil; the tile is refilled with no markers left'},
        'tokens': [{'name': 'Exofossil tokens (17)', 'note': 'unlimited supply'}],
    },
}


def txt(r):
    t, n = r['t'], r.get('n', 1)
    s = 's' if n > 1 else ''
    return {'vp': '%d VP' % n, 'publicity': '%d publicity' % n, 'credit': '%d credit%s' % (n, s), 'energy': '%d energy' % n, 'data': '%d data' % n,
            'card_any': '%d card%s' % (n, s), 'card_random': '%d random card%s' % (n, s), 'alien_card': '%d alien card%s' % (n, s), 'exofossil': '%d exofossil%s' % (n, s),
            'trace': '%d life trace%s of any kind' % (n, s), 'signal_oumuamua': '%d signal in a sector with \'Oumuamua or on its tile' % n}[t]


def line(rs): return ', '.join(txt(r) for r in rs) or '(none)'


def main():
    os.makedirs(os.path.join(ROOT, 'docs', 'spec', 'data'), exist_ok=True)
    json.dump(SPECIES, open(os.path.join(ROOT, 'docs', 'spec', 'data', 'alien-boards.json'), 'w', encoding='utf-8'), indent=1)
    L = ['# Alien species boards, base game (draft, owner check in progress)\n',
         'Transcribed from `assets/alien-board-*.png` and the token images, with the rule sheets (`docs/rules/SETI_Alien_rule_sheets_(EN).pdf`). Data in `data/alien-boards.json`; generated by `tools/board/alien_boards.py`.\n',
         '- **ALIEN-DATA-10** Every species board has three columns (pink = scanning trace, yellow = landing trace, blue = analyzing trace). A player who gains a life trace marks ANY empty space of the matching color and gains its reward (rulebook p.20, LIFE-04). Position matters only where stated: Anomalies (highest marked space wins) and the Exertian tiers (danger).',
         '- **ALIEN-DATA-11** A space with a cost (a cost shown with a red cross) can only be marked by a player who pays it (Centaurians: data from the pool, Oumuamua: exofossils). A space marked "top capsule" can be marked any number of times by any player, paying the cost each time.',
         '- **ALIEN-DATA-12** The "alien card" icon means gain 1 card of this species (draw from the top of its deck or take the face-up card, ALIEN-05). Tucking, hand limit and free-action rules are those of normal cards.',
         '- **ALIEN-DATA-13** The overflow spaces (3 VP each, any kind of trace) and the three discovery spaces are on the planetary board (BOARD-40), not on the species boards.\n']
    for key, s in SPECIES.items():
        L.append('## %s\n' % s['title'])
        L.append('| Column | Spaces from the top of the board down |\n|---|---|')
        for c in s['columns']:
            parts = []
            for i, x in enumerate(c['spaces'], 1):
                t = line(x['rewards'])
                if x.get('cost'): t += ' (pay %s)' % line(x['cost'])
                if x.get('repeat'): t += ' [top capsule]'
                if x.get('tier'): t += ' [tier %d, danger %d]' % (x['tier'], s['tier_danger'][str(x['tier'])])
                parts.append('%d. %s' % (i, t))
            L.append('| %s | %s |' % (c['color'], '; '.join(parts)))
        if 'message_rewards' in s:
            L.append('\nMessage rewards (top hexes): ' + ' | '.join(line(r) for r in s['message_rewards']) + '. ' + s['message_note'])
        if 'planet_like' in s:
            p = s['planet_like']
            L.append('\nPlanet-like part: orbit %s; first orbiter %s; land %s; first landers get data %s. %s' % (line(p['orbit']), line(p['first_orbiter']), line(p['land']), ', '.join(map(str, p['first_lander_data'])), p['note']))
            t = s['tile']
            L.append("\n'Oumuamua tile: %d data tokens in its slot; first marker %s, third marker %s; %s." % (t['data_tokens'], line(t['slot_rewards']['first_marker']), line(t['slot_rewards']['third_marker']), t['on_completion']))
        for t in s['tokens']:
            sides = ''
            if 'sides' in t:
                sides = ' Faces: ' + ' / '.join(line(x) for x in t['sides']) + '.'
            L.append('\nToken: %s.%s %s' % (t['name'], sides, t.get('note', '')))
        L.append('')
    open(os.path.join(ROOT, 'docs', 'spec', 'board-alien-species.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('ok')


if __name__ == '__main__':
    main()
