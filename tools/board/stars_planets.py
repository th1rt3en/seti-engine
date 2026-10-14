"""Nearby stars (sector boards) and planetary board transcription.

Sources: assets/sector-board-*.png, assets/main-board-assembled.png (planetary board, top part). Read from the art and
cross-checked against the repo (Ender-Wiggin2019/seti, constant/sectorSetup.ts and constant/boardLayout.ts).
The slot capacity of each star was also measured from the cutout length in the image: every slot is 44 px per token
(Kepler 22 221 px = 5, Proxima 267 = 6, Sirius A 266 = 6, Barnard's Star 221 = 5, Procyon 219 = 5, Vega 177 = 4,
61 Virginis 265 = 6, Beta Pictoris 219 = 5).

Run: python tools/board/stars_planets.py  (writes docs/spec/data/stars.json, planets.json and docs/spec/board-stars-and-planets.md)
Reward item types: vp, data, publicity, energy, card_any (row or deck), card_random (top of deck), tuck (income),
signal_planet (signal in a sector with the planet), signal_color, trace (pink, yellow, blue, any).
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def vp(n): return {'t': 'vp', 'n': n}
def data(n): return {'t': 'data', 'n': n}
def pub(n): return {'t': 'publicity', 'n': n}
def energy(n): return {'t': 'energy', 'n': n}
def card_any(n): return {'t': 'card_any', 'n': n}
def card_random(n): return {'t': 'card_random', 'n': n}
def tuck(n=1): return {'t': 'tuck', 'n': n}
def sig_planet(n=1): return {'t': 'signal_planet', 'n': n}
def sig_color(c): return {'t': 'signal_color', 'color': c, 'n': 1}
def trace(kind, n=1): return {'t': 'trace', 'kind': kind, 'n': n}


# Sector boards. Each covers two neighbouring sectors. Drawn here as the board image is shown (a quarter ring in the
# top-right quadrant): 'low' is the star nearer the 3 o'clock edge (lower angle), 'high' the other.
# Capacity: tokens in the data slot. first_win: reward on the first win of the sector. later_win: reward on later wins.
# first_win and later_win are the same when the board prints a single reward capsule and no first-win circle.
BOARDS = [
    {'id': 1, 'image': 'sb1', 'stars': [
        {'name': 'Proxima Centauri', 'color': 'red', 'capacity': 6, 'first_win': [trace('pink')], 'later_win': [trace('pink')], 'slot': 'low'},
        {'name': 'Kepler 22', 'color': 'yellow', 'capacity': 5, 'first_win': [trace('pink')], 'later_win': [vp(3)], 'slot': 'high'}]},
    {'id': 2, 'image': 'sb2', 'stars': [
        {'name': "Barnard's Star", 'color': 'red', 'capacity': 5, 'first_win': [trace('pink')], 'later_win': [vp(3)], 'slot': 'low'},
        {'name': 'Sirius A', 'color': 'blue', 'capacity': 6, 'first_win': [trace('pink')], 'later_win': [trace('pink')], 'slot': 'high'}]},
    {'id': 3, 'image': 'sb3', 'stars': [
        {'name': 'Vega', 'color': 'black', 'capacity': 4, 'first_win': [trace('pink'), vp(2)], 'later_win': [vp(5)], 'slot': 'low'},
        {'name': 'Procyon', 'color': 'blue', 'capacity': 5, 'first_win': [trace('pink')], 'later_win': [vp(3)], 'slot': 'high'}]},
    {'id': 4, 'image': 'sb4', 'stars': [
        {'name': 'Beta Pictoris', 'color': 'black', 'capacity': 5, 'first_win': [trace('pink'), vp(3)], 'later_win': [trace('pink')], 'slot': 'low'},
        {'name': '61 Virginis', 'color': 'yellow', 'capacity': 6, 'first_win': [trace('pink')], 'later_win': [trace('pink')], 'slot': 'high'}]},
]
STAR_COMMON = {
    'each_contributor': [pub(1)],
    'second_position': [vp(2)],
}

PLANETS = {
    'MERCURY': {'order': 1, 'img': 'p_mercury',
                'orbit': [card_random(1), sig_planet(2), tuck(1)], 'first_orbit': [vp(3)],
                'land': [vp(12), trace('yellow')], 'first_land_data': [3], 'moons': {}},
    'VENUS': {'order': 2, 'img': 'p_venus',
              'orbit': [vp(6), tuck(1)], 'first_orbit': [vp(3)],
              'land': [vp(5), trace('yellow')], 'first_land_data': [2], 'moons': {}},
    'MARS': {'order': 3, 'img': 'p_mars',
             'orbit': [card_any(1), sig_planet(1), tuck(1)], 'first_orbit': [vp(3)],
             'land': [vp(6), trace('yellow')], 'first_land_data': [2, 1],
             'moons': {'Phobos and Deimos (one space)': [vp(8), tuck(2)]}},
    'JUPITER': {'order': 4, 'img': 'p_jupiter',
                'orbit': [data(1), sig_planet(1), tuck(1)], 'first_orbit': [vp(3)],
                'land': [vp(7), trace('yellow')], 'first_land_data': [2],
                'moons': {'Io': [vp(10), energy(4)], 'Europa': [vp(7), trace('yellow', 2)],
                          'Callisto': [vp(13), data(4)], 'Ganymede': [vp(12), pub(5)]}},
    'SATURN': {'order': 5, 'img': 'p_saturn',
               'orbit': [pub(2), sig_planet(1), tuck(1)], 'first_orbit': [vp(3)],
               'land': [vp(8), trace('yellow')], 'first_land_data': [2],
               'moons': {'Enceladus': [vp(12), sig_color('red'), sig_color('yellow'), sig_color('blue')],
                         'Titan': [vp(7), trace('any', 2)]}},
    'URANUS': {'order': 6, 'img': 'p_uranus',
               'orbit': [card_random(3), sig_color('black'), vp(8)], 'first_orbit': [vp(3)],
               'land': [vp(9), trace('yellow')], 'first_land_data': [3],
               'moons': {'Titania': [vp(25)]}},
    'NEPTUNE': {'order': 7, 'img': 'p_neptune',
                'orbit': [data(4), sig_color('black'), vp(7)], 'first_orbit': [vp(3)],
                'land': [vp(10), trace('yellow')], 'first_land_data': [3],
                'moons': {'Triton': [vp(26)]}},
}

DISCOVERY = {
    'left_board_slot': {'image': 'p_slotsL', 'discovery_space_each_color': [vp(5), pub(1)], 'overflow_space_each': [vp(3)]},
    'right_board_slot': {'image': 'p_slotsR', 'discovery_space_each_color': [vp(3), pub(1)], 'overflow_space_each': [vp(3)]},
    'note': 'Each of the two alien species slots has three discovery spaces (pink, yellow, blue trace) and three overflow spaces below them.',
}


def txt(r):
    t, n = r['t'], r.get('n', 1)
    return {
        'vp': '%d VP' % n, 'data': '%d data' % n, 'publicity': '%d publicity' % n, 'energy': '%d energy' % n,
        'card_any': '%d card%s from the row or the deck' % (n, 's' if n > 1 else ''),
        'card_random': '%d random card%s from the deck' % (n, 's' if n > 1 else ''),
        'tuck': 'tuck %d card%s for income' % (n, 's' if n > 1 else ''),
        'signal_planet': '%d signal%s in a sector with this planet' % (n, 's' if n > 1 else ''),
        'signal_color': '1 signal in a %s sector' % r.get('color', ''),
        'trace': '%d %s life trace%s' % (n, r.get('kind', ''), 's' if n > 1 else ''),
    }[t]


def line(rs): return ', '.join(txt(r) for r in rs)


def main():
    os.makedirs(os.path.join(ROOT, 'docs', 'spec', 'data'), exist_ok=True)
    json.dump({'boards': BOARDS, 'star_common': STAR_COMMON}, open(os.path.join(ROOT, 'docs', 'spec', 'data', 'stars.json'), 'w', encoding='utf-8'), indent=1)
    json.dump({'planets': PLANETS, 'discovery_spaces': DISCOVERY}, open(os.path.join(ROOT, 'docs', 'spec', 'data', 'planets.json'), 'w', encoding='utf-8'), indent=1)
    L = ['# Nearby stars and planetary board (draft, owner check in progress)\n',
         'Read from the art and cross-checked against the repo (`constant/sectorSetup.ts`, `constant/boardLayout.ts`). Data in `data/stars.json` and `data/planets.json`; generated by `tools/board/stars_planets.py`.\n',
         '## Nearby stars (sector boards)\n',
         '- **BOARD-20** The four sector boards each carry two stars and cover two neighbouring sectors. Together they give the 8 sectors of the board. The four boards are placed in a random order around the board at setup (from the seeded generator, A-004); each board keeps its own two stars in the order printed. The drawing convention for the table: "low" is the star nearer the 3 o\'clock side when the board is shown as a quarter ring in the top-right quadrant.',
         '- **BOARD-21** Data slot sizes (tokens per slot) are 4 to 6 per star; measured from the slot cutout (44 px per token) and equal to the repo.',
         '- **BOARD-22** Printed on every sector board: each player who contributed at least 1 marker gains 1 publicity (SECTOR-12); a marker in the second position of the data slot scores 2 points (SECTOR-03).',
         '- **BOARD-23** Winner rewards. Where a board prints a circle next to the star it is the reward for the first win of that sector; the capsule next to it is the reward for later wins. Where the board prints one capsule only, the same reward applies to every win. The table gives both.\n',
         '| Board | Star | Color | Slot | First win | Later wins |', '|---|---|---|---|---|---|']
    for b in BOARDS:
        for s in b['stars']:
            L.append('| %d | %s | %s | %d | %s | %s |' % (b['id'], s['name'], s['color'], s['capacity'], line(s['first_win']), line(s['later_win'])))
    L += ['', '## Planetary board\n',
          '- **BOARD-30** Orbiting a planet (ORBIT-03): the first orbiter at a planet scores 3 VP (covers the space, ORBIT-04); every orbit gives the orbit rewards listed below.',
          '- **BOARD-31** Landing on a planet (LAND-03): every lander gains the lander rewards; the first lander(s) also gain the first-lander data. Mars has two first-lander spaces (2 data and 1 data). There is no limit to the number of landers (LAND-04).',
          '- **BOARD-32** Moons (LAND-05): each moon has a single space for one lander and gives its own reward. Mars\'s Phobos and Deimos share one space (to be confirmed by the owner).\n',
          '| Planet | Orbit rewards | First orbiter | Lander rewards | First lander data | Moons |', '|---|---|---|---|---|---|']
    for name, p in sorted(PLANETS.items(), key=lambda kv: kv[1]['order']):
        moons = '; '.join('%s: %s' % (m, line(r)) for m, r in p['moons'].items()) or 'none'
        L.append('| %s | %s | %s | %s | %s | %s |' % (name.title(), line(p['orbit']), line(p['first_orbit']), line(p['land']), ', '.join(str(x) for x in p['first_land_data']), moons))
    L += ['', '## Species discovery spaces on the planetary board\n',
          '- **BOARD-40** The planetary board has two alien species slots, each with discovery spaces for the three trace kinds (pink, yellow, blue) and three overflow spaces below (SETUP-11, LIFE-01). The left slot in the art gives 5 VP and 1 publicity per discovery space; the right slot gives 3 VP and 1 publicity per discovery space. Every overflow space gives 3 VP. Which slot holds the "1st" and which the "2nd" species (rival cards S.3 and S.4) is not shown in the art.',
          '', '## Not covered here', '', "- 'Oumuamua's own orbit and lander spaces (on its tile, not on the planetary board): to be transcribed with the alien boards.", '']
    open(os.path.join(ROOT, 'docs', 'spec', 'board-stars-and-planets.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('ok', len(BOARDS) * 2, 'stars', len(PLANETS), 'planets')


if __name__ == '__main__':
    main()
