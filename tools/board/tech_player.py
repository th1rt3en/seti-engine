"""Tech board, publicity and score tracks, and player board transcription.

Sources: assets/main-board-assembled.png (tech board, publicity track), the 48 tech tile images in assets/, rulebook p.6, p.14, p.16, p.17.
The human player board is NOT among the supplied assets (the files once called player-board-* are the solo rival boards), so its layout
comes from the rulebook pictures and from the tech board, whose stacks mirror the printed slots of the player board.

Run: python tools/board/tech_player.py  (writes docs/spec/data/tech-board.json, player-board.json and docs/spec/board-tech-and-player.md)
Reward item types as in stars_planets.py plus launch (free probe launch) and data.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def vp(n): return {'t': 'vp', 'n': n}
def data(n): return {'t': 'data', 'n': n}
def pub(n): return {'t': 'publicity', 'n': n}
def energy(n): return {'t': 'energy', 'n': n}
def credit(n): return {'t': 'credit', 'n': n}
def card(n=1): return {'t': 'card_any', 'n': n}
def launch(): return {'t': 'launch', 'n': 1}


# Tile bonus (the side placed on the player board). Each stack holds four tiles, one of each bonus below.
FOUR_BONUSES = [[vp(3)], [card(1)], [energy(1)], [pub(1)]]

# Stack glyph, as printed in the corner of every tile of the stack and on the tech board: dot, link (infinity), branch, cross.
STACKS = {
    'probe': [
        {'glyph': 'dot', 'tech': 'PT#01', 'effect': 'You can have up to 2 probes in space at the same time.', 'extra_bonus': [launch()], 'front': 'front-probe-2-satellites'},
        {'glyph': 'link', 'tech': 'PT#03', 'effect': 'Moving onto asteroids gives 1 publicity; leaving asteroids no longer costs 1 extra movement.', 'extra_bonus': [], 'front': 'front-probe-asteroid-trade'},
        {'glyph': 'branch', 'tech': 'PT#02', 'effect': 'Landing costs 1 less energy.', 'extra_bonus': [], 'front': 'front-probe-rover-2-energy'},
        {'glyph': 'cross', 'tech': 'PT#04', 'effect': "You can land on a planet's moon instead of the planet; same cost.", 'extra_bonus': [], 'front': 'front-probe-moon-rover'},
    ],
    'telescope': [
        {'glyph': 'dot', 'tech': 'TT#01', 'effect': 'During a Scan, you can mark a signal in a sector adjacent to Earth instead of marking Earth\'s sector.', 'extra_bonus': [data(2)], 'front': 'front-telescope-earth-signal'},
        {'glyph': 'link', 'tech': 'TT#03', 'effect': 'During a Scan, pay 1 publicity to mark an extra signal in a sector with Mercury.', 'extra_bonus': [], 'front': 'front-telescope-mercury-signal'},
        {'glyph': 'branch', 'tech': 'TT#02', 'effect': 'During a Scan, discard one card from hand to mark an extra signal in a matching sector.', 'extra_bonus': [], 'front': 'front-telescope-discard-signal'},
        {'glyph': 'cross', 'tech': 'TT#04', 'effect': 'During a Scan, pay 1 energy to launch a probe, or gain 1 movement.', 'extra_bonus': [], 'front': 'front-telescope-energy-to-probe'},
    ],
    'computer': [
        {'glyph': 'dot', 'tech': 'CT#01', 'effect': 'A new computer space: 2 VP on the upper space when data is placed there; the lower space gives 1 credit.', 'extra_bonus': [], 'front': 'front-computer-1-credit', 'lower': [credit(1)]},
        {'glyph': 'link', 'tech': 'CT#02', 'effect': 'A new computer space: 2 VP upper; the lower space gives 1 energy.', 'extra_bonus': [], 'front': 'front-computer-1-energy', 'lower': [energy(1)]},
        {'glyph': 'branch', 'tech': 'CT#03', 'effect': 'A new computer space: 2 VP upper; the lower space gives 1 card.', 'extra_bonus': [], 'front': 'front-computer-1-card', 'lower': [card(1)]},
        {'glyph': 'cross', 'tech': 'CT#04', 'effect': 'A new computer space: 2 VP upper; the lower space gives 2 publicity.', 'extra_bonus': [], 'front': 'front-computer-2-publicity', 'lower': [pub(2)]},
    ],
}

TECH_BOARD = {
    'stacks_per_category': 4, 'tiles_per_stack': 4,
    'first_taker_bonus': [vp(2)], 'first_taker_note': 'A 2-point tile sits on top of each stack; the first player to take from a stack discards it and scores 2 points.',
    'rotation_counter': {'positions': ['ring 1', 'rings 1+2', 'rings 1+2+3'], 'start': 'ring 1',
                         'note': 'Three labelled spaces: yellow ring 1, orange rings 1+2, teal rings 1+2+3. The counter advances one position each time the solar system rotates and then cycles. The starting space is the one the rulebook calls "the marked space" (read as ring 1).'},
    'neutral_milestone_box': {'players_4': 0, 'players_3': 1, 'players_1_2': 2, 'note': 'Printed next to the 20-point milestone: number of nonplayer markers by player count (4: none, 3: one, 1-2: two per milestone).'},
}

PUBLICITY_TRACK = {
    'range': [0, 10], 'start': 4,
    'zones': [{'from': 3, 'to': 5, 'printed': 'Buy a card: pay 3 publicity, take 1 card (free action). The box is drawn beside spaces 3 to 5 but the action is available at any publicity of 3 or more (owner note).'},
              {'from': 6, 'to': 10, 'printed': 'Research a tech: pay 6 publicity, rotate the solar system, take a tech (main action).'}],
    'cap': 10,
}

SCORE_TRACK = {
    'spaces': '1 to 100, then around again (100/200 token)',
    'milestones': [{'at': 20, 'kind': 'neutral', 'icon': 'alien'}, {'at': 25, 'kind': 'gold'}, {'at': 30, 'kind': 'neutral', 'icon': 'alien'}, {'at': 50, 'kind': 'gold'}, {'at': 70, 'kind': 'gold'}],
}

PLAYER_BOARD = {
    'data_pool_capacity': 6,
    'computer': {
        'top_row_spaces': 6, 'fill_order': 'left to right',
        'space_effects': {'2': [pub(1)], '4': 'tuck a card for income (income icon)'},
        'tech_slots_under_spaces': [1, 3, 5, 6],
        'tech_slot_note': 'Four computer tech slots sit behind spaces 1, 3, 5 and 6 (read from the picture on rulebook p.14). A tech slot adds a lower space under its top space.',
    },
    'analyze_slot': {'cost': [energy(1)], 'requires': 'top row full', 'gives': 'blue life trace'},
    'probe_tech_slots': 4, 'telescope_tech_slots': 4,
    'slot_note': 'Probe and telescope techs go on their own slot, one per technology. The slot positions print the same four pictures as the stacks on the tech board.',
}


def txt(r):
    t, n = r['t'], r.get('n', 1)
    return {'vp': '%d VP' % n, 'data': '%d data' % n, 'publicity': '%d publicity' % n, 'energy': '%d energy' % n, 'credit': '%d credit' % n,
            'card_any': '%d card%s from the row or the deck' % (n, 's' if n > 1 else ''), 'launch': 'launch a probe (no cost)'}[t]


def line(rs): return ', '.join(txt(r) for r in rs) or 'none'


def main():
    os.makedirs(os.path.join(ROOT, 'docs', 'spec', 'data'), exist_ok=True)
    json.dump({'stacks': STACKS, 'bonuses_per_stack': FOUR_BONUSES, 'tech_board': TECH_BOARD, 'publicity_track': PUBLICITY_TRACK, 'score_track': SCORE_TRACK},
              open(os.path.join(ROOT, 'docs', 'spec', 'data', 'tech-board.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(PLAYER_BOARD, open(os.path.join(ROOT, 'docs', 'spec', 'data', 'player-board.json'), 'w', encoding='utf-8'), indent=1)
    L = ['# Tech board, tracks and player board (confirmed by the owner, 2026-10-13, with two notes)\n',
         'Transcribed from the tech board in `assets/main-board-assembled.png`, the 48 tech tile images and rulebook pp. 6, 14, 16, 17. Data in `data/tech-board.json` and `data/player-board.json`; generated by `tools/board/tech_player.py`. The owner confirmed all 23 items in the check page (marks in `data/board-check-tech-player.json`). The human player board is not among the supplied assets (gap noted in `docs/asset-gaps.md`).\n',
         '## Tech board\n',
         '- **BOARD-50** The tech board has 12 stacks in 3 rows of 4: probe (orange), telescope (pink) and computer (blue). Each stack has a corner glyph (dot, link, branch, cross) that is printed on every tile of that stack. A stack holds 4 tiles of the same technology (TECH-01) with a 2-point tile on top (SETUP-16).',
         '- **BOARD-51** The four tiles of a stack differ only in the bonus on the placed side: 3 VP, 1 card (from the row or the deck), 1 energy, 1 publicity (BOARD-52 lists the extras). Stack order in the picture, left to right: probe row (two satellites, asteroids, landing, moon); telescope row (Earth signal, Mercury signal, discard-card signal, energy to launch); computer row (1 credit, 1 energy, 1 card, 2 publicity).',
         '- **BOARD-52** Two stacks add an extra immediate bonus on every tile: the probe "two satellites" stack launches a probe for free (TECH-PT01), and the telescope "Earth signal" stack gives 2 data (TECH-TT01).',
         '- **BOARD-53** The rotation counter has three positions labelled ring 1, rings 1+2 and rings 1+2+3, advanced on every rotation of the solar system (ROTATE-02, BOARD-11); it starts on ring 1.',
         '- **BOARD-54** Next to the 20-point milestone the board prints the nonplayer marker counts: 4 players none, 3 players one, 1 to 2 players two (SETUP-20).\n',
         '| Row | Stack glyph | Tech | Effect | Extra bonus on every tile |', '|---|---|---|---|---|']
    for cat, lst in STACKS.items():
        for s in lst:
            L.append('| %s | %s | %s | %s | %s |' % (cat, s['glyph'], s['tech'], s['effect'], line(s['extra_bonus'])))
    L += ['', 'Tile bonuses per stack (every stack): ' + '; '.join(line(b) for b in FOUR_BONUSES) + '.', '',
          '## Tracks\n',
          '- **BOARD-60** Publicity track: spaces 0 to 10, markers start on 4 (SETUP-34). The track prints the research-tech box (6 publicity) beside spaces 6 to 10 and the buy-a-card box (3 publicity) beside spaces 3 to 5, but both actions are available at any publicity of at least their cost (owner note: buying a card at 3 publicity works at any publicity of 3 or more, not only at 3 to 5). The cap is 10 (SETUP-37).',
          '- **BOARD-61** Score track: 1 to 100 and around again with the 100/200 token. Milestone spaces: 20 and 30 (neutral, alien head), 25, 50 and 70 (gold) (MILE-02, MILE-05).\n',
          '## Player board (read from the rulebook pictures)\n',
          '- **BOARD-70** Data pool: holds up to 6 data (RES-01). Owner note: when a gain of data would take the pool over 6, the player may first place data from the pool into the computer (free action, FREE-03) to make room, then take the new data. This follows from FREE-03 being allowed at any time during the player\'s own turn, before or during the main action.',
          '- **BOARD-71** Computer: a top row of 6 spaces filled left to right (FREE-03). Space 2 gives 1 publicity when covered; space 4 lets the player tuck a card for income (INCOME-02). The other spaces have no effect.',
          '- **BOARD-72** Four computer tech slots sit behind spaces 1, 3, 5 and 6; a computer tech there adds a lower space under it (TECH-20, TECH-21). Spaces 2 and 4 have no tech slot.',
          '- **BOARD-73** Analyze data: pay 1 energy, requires the whole top row filled, clears the computer, then mark a blue life trace (ANALYZE-01 to 03).',
          '- **BOARD-74** Four probe tech slots and four telescope tech slots, one per technology; the printed slot pictures match the stacks on the tech board.',
          '- **BOARD-75** The printed left edge of the board also lists action costs and a "launch" hex; these repeat costs already in the spec (LAUNCH-01, SCAN-01, TECHACT-01).', '']
    open(os.path.join(ROOT, 'docs', 'spec', 'board-tech-and-player.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('ok')


if __name__ == '__main__':
    main()
