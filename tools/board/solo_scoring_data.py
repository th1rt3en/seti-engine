"""Rival boards (solo), objective tiles and gold scoring tiles.

Sources: assets/rival-board-*.png, assets/solo-objective-*.png, assets/gold-scoring-tile-*.png, rulebook pp. 5, 21, 22, 23, 26, 27.

Icon vocabulary used for objective tasks (read from the tiles; the owner confirms the meanings in the check page):
- hexagon icons are ACTIONS: launch (orange hex, shuttle), scan (pink hex, dish), analyze (blue hex, server), land (brown hex, rover), orbit (green hex, satellite);
- chip icons are TECHS: probe tech (orange), telescope tech (pink), computer tech (blue), any tech (rainbow);
- a triangle is a life trace (blue = analyzing kind);
- a grey signal strip with a check = win a sector of any color; a colored strip with a check = win a sector of that color (owner correction, 2026-10-13);
- a white card with a green check = complete a mission.

Run: python tools/board/solo_scoring_data.py  (writes docs/spec/data/solo-boards.json, objectives.json, gold-tiles.json and docs/spec/board-solo-and-scoring.md)
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

# Rival boards ---------------------------------------------------------------------------------------------------------
# The progress track is a ring of 12 spaces that also names the rival's preferred tech (color = tech type, glyph = stack).
# Clockwise from the top (the growth icon sits between the orange cross and the blue dot): blue dot, blue link, blue branch,
# blue cross, pink dot, pink link, pink branch, pink cross, orange dot, orange link, orange branch, orange cross.
PROGRESS_TRACK_CLOCKWISE = ['blue-dot', 'blue-link', 'blue-branch', 'blue-cross', 'pink-dot', 'pink-link', 'pink-branch', 'pink-cross',
                            'orange-dot', 'orange-link', 'orange-branch', 'orange-cross']
RIVAL_BOARDS = [
    {'image': 'rival-board-1-2-star', 'stars': [1, 2], 'basic_cards': 4, 'advanced_cards': 0, 'start_space': 'blue-dot',
     'objectives': {1: None, 2: {'I': 2, 'II': 3, 'III': 5}}, 'note': 'Shared by 1-star (no objectives) and 2-star difficulty.'},
    {'image': 'rival-board-3-star', 'stars': [3], 'basic_cards': 4, 'advanced_cards': 1, 'start_space': 'pink-dot', 'objectives': {3: {'I': 2, 'II': 4, 'III': 6}}},
    {'image': 'rival-board-4-star', 'stars': [4], 'basic_cards': 4, 'advanced_cards': 1, 'start_space': 'blue-cross', 'objectives': {4: {'I': 2, 'II': 6, 'III': 7}}},
    {'image': 'rival-board-5-star', 'stars': [5], 'basic_cards': 4, 'advanced_cards': 1, 'start_space': 'pink-dot', 'objectives': {5: {'I': 2, 'II': 7, 'III': 8}}},
]
RIVAL_COMMON = {
    'computer': {'spaces': 6, 'effects': {'2': 'gains 1 publicity', '4': 'advances 4 on the progress track (the income-tuck space)'},
                 'analyze_slot': 'at the right end: the computer icon with 1 energy, then a blue life trace (the benefit the rival gains when it analyzes, after clearing its computer)'},
    'progress_rewards': {'credit': 1, 'energy': 1, 'card': 1, 'tuck_income': 4, 'note': '1 progress for each credit, energy and card gained; 4 for a tuck-for-income effect'},
    'objective_table': {'rounds_1_to_4': 'spend 1, 2, 3, 4 completed objectives at the end of round 1, 2, 3, 4; each one the player cannot spend makes the rival advance 3', 'round_5': 'each uncompleted objective: 5 VP for the rival'},
    'growth_icon': 'between the orange cross and the blue dot of the progress track: each time the marker crosses it one random advanced card is added to the top of the rival deck',
}

# Objectives -----------------------------------------------------------------------------------------------------------
def t(_k, **kw): d = {'kind': _k}; d.update(kw); return d
SIGNAL = lambda *colors: t('win_sector', sectors=list(colors) or ['any'])   # owner correction 2026-10-13: the strip with a check means WIN a sector, not mark a signal
OBJECTIVES = [
    {'id': 'L1-16-vp', 'level': 'I', 'image': 'solo-objective-L1-16-vp', 'tasks': [[t('reach_vp', n=16)]]},
    {'id': 'L1-5-data', 'level': 'I', 'image': 'solo-objective-L1-5-data', 'tasks': [[t('data_in_pool', n=5)]]},
    {'id': 'L1-8-publicity', 'level': 'I', 'image': 'solo-objective-L1-8-publicity', 'tasks': [[t('reach_publicity', n=8)]]},
    {'id': 'L1-land-or-win-sector', 'level': 'I', 'image': 'solo-objective-L1-probe-or-signal-check', 'tasks': [[t('action', action='land'), SIGNAL()]], 'note': 'one task, either part marks it'},
    {'id': 'L2-asteroid-trace', 'level': 'II', 'image': 'solo-objective-L2-asteroid-satellite-trace', 'tasks': [[t('visit', what='asteroids')], [t('life_trace', color='blue')]]},
    {'id': 'L2-blue-or-red-signal', 'level': 'II', 'image': 'solo-objective-L2-blue-red-signal-checks', 'tasks': [[SIGNAL('blue'), SIGNAL('red')]]},
    {'id': 'L2-computer-tech-trace', 'level': 'II', 'image': 'solo-objective-L2-computer-tech-trace', 'tasks': [[t('tech', type='computer')], [t('life_trace', color='blue')]]},
    {'id': 'L2-jupiter-saturn', 'level': 'II', 'image': 'solo-objective-L2-jupiter-saturn', 'tasks': [[t('orbit_or_land', planet='jupiter'), t('orbit_or_land', planet='saturn')]]},
    {'id': 'L2-mars-uranus-neptune', 'level': 'II', 'image': 'solo-objective-L2-mars-uranus-neptune', 'tasks': [[t('orbit_or_land', planet='mars'), t('orbit_or_land', planet='uranus'), t('orbit_or_land', planet='neptune')]]},
    {'id': 'L2-probe-tech-mission', 'level': 'II', 'image': 'solo-objective-L2-probe-tech-card', 'tasks': [[t('tech', type='probe')], [t('complete_mission')]]},
    {'id': 'L2-red-or-yellow-signal', 'level': 'II', 'image': 'solo-objective-L2-red-yellow-signal-checks', 'tasks': [[SIGNAL('red'), SIGNAL('yellow')]]},
    {'id': 'L2-comet-3-credit-card', 'level': 'II', 'image': 'solo-objective-L2-satellite-3-credit-tech', 'tasks': [[t('visit', what='comet')], [t('play_card_costing', credits=3)]]},
    {'id': 'L2-telescope-tech-mission', 'level': 'II', 'image': 'solo-objective-L2-telescope-tech-card', 'tasks': [[t('tech', type='telescope')], [t('complete_mission')]]},
    {'id': 'L2-venus-mercury', 'level': 'II', 'image': 'solo-objective-L2-venus-mercury', 'tasks': [[t('orbit_or_land', planet='venus'), t('orbit_or_land', planet='mercury')]]},
    {'id': 'L2-yellow-or-blue-signal', 'level': 'II', 'image': 'solo-objective-L2-yellow-blue-signal-checks', 'tasks': [[SIGNAL('yellow'), SIGNAL('blue')]]},
    {'id': 'L3-black-signal', 'level': 'III', 'image': 'solo-objective-L3-black-signal-check', 'tasks': [[SIGNAL('black')]]},
    {'id': 'L3-computer-and-any-tech', 'level': 'III', 'image': 'solo-objective-L3-computer-mixed-tech', 'tasks': [[t('tech', type='computer')], [t('tech', type='any')]]},
    {'id': 'L3-probe-tech-land', 'level': 'III', 'image': 'solo-objective-L3-probe-tech-rover', 'tasks': [[t('tech', type='probe')], [t('action', action='land')]]},
    {'id': 'L3-orbit', 'level': 'III', 'image': 'solo-objective-L3-satellite', 'tasks': [[t('action', action='orbit')]]},
    {'id': 'L3-launch-9-publicity', 'level': 'III', 'image': 'solo-objective-L3-shuttle-9-publicity', 'tasks': [[t('action', action='launch')], [t('reach_publicity', n=9)]]},
    {'id': 'L3-telescope-tech-win-sector', 'level': 'III', 'image': 'solo-objective-L3-telescope-tech-signal', 'tasks': [[t('tech', type='telescope')], [SIGNAL()]]},
    {'id': 'L3-trace-launch-scan', 'level': 'III', 'image': 'solo-objective-L3-trace-probe-telescope', 'tasks': [[t('life_trace', color='blue')], [t('action', action='launch')], [t('action', action='scan')]]},
    {'id': 'L3-two-scans', 'level': 'III', 'image': 'solo-objective-L3-two-telescope-hex', 'tasks': [[t('action', action='scan')], [t('action', action='scan')]]},
    {'id': 'L3-two-blue-traces', 'level': 'III', 'image': 'solo-objective-L3-two-traces', 'tasks': [[t('life_trace', color='blue')], [t('life_trace', color='blue')]]},
]

# Gold scoring tiles ---------------------------------------------------------------------------------------------------
# values: first chooser, second chooser, third and later choosers (the wide slot).
GOLD_TILES = [
    {'tile': 'Tech', 'side': 'A', 'image': 'gold-scoring-tile-three-techs-11-8-5', 'values': [11, 8, 5], 'per': 'each set of three techs, one of each type'},
    {'tile': 'Tech', 'side': 'B', 'image': 'gold-scoring-tile-two-wild-techs-7-5-3', 'values': [7, 5, 3], 'per': 'each pair of techs (any two)'},
    {'tile': 'Mission', 'side': 'A', 'image': 'gold-scoring-tile-card-4-3-2', 'values': [4, 3, 2], 'per': 'each completed mission'},
    {'tile': 'Mission', 'side': 'B', 'image': 'gold-scoring-tile-two-cards-8-6-4', 'values': [8, 6, 4], 'per': 'each pair of completed missions or end-of-game scoring cards'},
    {'tile': 'Income', 'side': 'A', 'image': 'gold-scoring-tile-credit-energy-question-11-8-5', 'values': [11, 8, 5], 'per': 'each set of three tucked income cards, one of each type (credit, energy, card)'},
    {'tile': 'Income', 'side': 'B', 'image': 'gold-scoring-tile-credit-or-energy-5-4-3', 'values': [5, 4, 3], 'per': 'each tucked income card of the type you have most (credit or energy)'},
    {'tile': 'Other', 'side': 'A', 'image': 'gold-scoring-tile-three-traces-8-6-4', 'values': [8, 6, 4], 'per': 'each set of three life traces, one of each color (overflow markers count)'},
    {'tile': 'Other', 'side': 'B', 'image': 'gold-scoring-tile-signal-and-planet-8-6-4', 'values': [8, 6, 4], 'per': 'each sector win paired with an orbiter or lander'},
]


def tt(x):
    k = x['kind']
    return {'reach_vp': lambda: 'reach %d VP (mark at once if already there)' % x['n'], 'data_in_pool': lambda: 'have %d data in the data pool (computer data does not count)' % x['n'],
            'reach_publicity': lambda: 'reach %d publicity' % x['n'], 'action': lambda: 'take a %s action' % x['action'], 'win_sector': lambda: 'win %s' % ('a sector of any color' if x['sectors'] == ['any'] else 'a ' + ' or '.join(x['sectors']) + ' sector'),
            'visit': lambda: 'a probe visits %s' % x['what'], 'life_trace': lambda: 'mark a %s life trace' % x['color'], 'tech': lambda: 'research a %s tech' % x['type'],
            'orbit_or_land': lambda: 'orbit or land at %s' % x['planet'], 'complete_mission': lambda: 'complete a mission', 'play_card_costing': lambda: 'play a card costing exactly %d credits' % x['credits']}[k]()


def main():
    d = os.path.join(ROOT, 'docs', 'spec', 'data'); os.makedirs(d, exist_ok=True)
    json.dump({'progress_track_clockwise': PROGRESS_TRACK_CLOCKWISE, 'boards': RIVAL_BOARDS, 'common': RIVAL_COMMON}, open(os.path.join(d, 'solo-boards.json'), 'w', encoding='utf-8'), indent=1)
    json.dump({'icon_vocabulary': 'see tools/board/solo_scoring_data.py', 'objectives': OBJECTIVES}, open(os.path.join(d, 'objectives.json'), 'w', encoding='utf-8'), indent=1)
    json.dump({'tiles': GOLD_TILES, 'values_order': 'first chooser, second chooser, third and later choosers (wide slot)'}, open(os.path.join(d, 'gold-tiles.json'), 'w', encoding='utf-8'), indent=1)
    L = ['# Solo boards, objectives and gold scoring tiles (draft, owner check in progress)\n',
         'Read from `assets/rival-board-*.png`, `assets/solo-objective-*.png`, `assets/gold-scoring-tile-*.png` and rulebook pp. 21 to 23, 26, 27. Data in `data/solo-boards.json`, `data/objectives.json`, `data/gold-tiles.json`; generated by `tools/board/solo_scoring_data.py`.\n',
         '## Rival boards\n',
         '- **SOLO-DATA-10** There are four rival boards: 1-star and 2-star share one. Per difficulty: the objective stack (level I / II / III counts), the number of cards in the starting action deck (4 basic, plus 1 advanced from 3 stars up) and the starting space of the progress marker.',
         '- **SOLO-DATA-11** The progress track is a ring of 12 spaces that also names the rival\'s preferred tech. Clockwise from the top: ' + ', '.join(PROGRESS_TRACK_CLOCKWISE) + '. Color is the tech type (orange probe, pink telescope, blue computer) and the glyph is the stack on the tech board (dot, link, branch, cross). The growth icon sits between orange-cross and blue-dot.',
         '- **SOLO-DATA-12** Rival computer: 6 spaces; the 2nd gives 1 publicity and the 4th gives 4 progress (the picture shows 1 publicity and an orange progress arrow marked 4). The analyze slot at the right end gives the rival a blue life trace and 1 energy (which is 1 progress, SOLO-10).',
         '- **SOLO-DATA-13** The objective table printed on the left of every board: after round 1, 2, 3, 4 spend 1, 2, 3, 4 completed objectives (each missing one gives the rival 3 progress); after round 5 each uncompleted objective gives the rival 5 VP.\n',
         '| Difficulty | Board | Starting deck | Objective stack (I / II / III) | Progress start |', '|---|---|---|---|---|']
    for b in RIVAL_BOARDS:
        for s in b['stars']:
            ob = b['objectives'].get(s)
            L.append('| %d star | %s | %d basic%s | %s | %s |' % (s, b['image'], b['basic_cards'], ' + 1 advanced' if b['advanced_cards'] else '', 'none' if not ob else '%d / %d / %d' % (ob['I'], ob['II'], ob['III']), b['start_space']))
    L += ['', '## Objective tiles (24)\n',
          '- **SOLO-DATA-20** 4 level I, 11 level II and 9 level III tiles. Each tile has 1 to 3 tasks; a task with "/" is done by either part. Meanings of the icons are in the script header; the owner confirms them in the check page.\n',
          '| Tile | Level | Tasks |', '|---|---|---|']
    for o in OBJECTIVES:
        L.append('| %s | %s | %s |' % (o['id'], o['level'], '; '.join(' / '.join(tt(x) for x in task) for task in o['tasks'])))
    L += ['', '## Gold scoring tiles (8 faces)\n',
          '- **SOLO-DATA-30** Four double-sided tiles. Each has three score slots: the first player to choose it takes the highest, the second the middle, and the third and fourth share the lowest (wide slot). Players score the value under their marker for each set they have (see END-10 to END-17).\n',
          '| Tile | Side | Values (1st, 2nd, 3rd+) | Scores for |', '|---|---|---|---|']
    for g in GOLD_TILES:
        L.append('| %s | %s | %s | %s |' % (g['tile'], g['side'], ' / '.join(map(str, g['values'])), g['per']))
    L.append('')
    open(os.path.join(ROOT, 'docs', 'spec', 'board-solo-and-scoring.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('ok', len(OBJECTIVES), 'objectives')


if __name__ == '__main__':
    main()
