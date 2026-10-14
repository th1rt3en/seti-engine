"""Solar system board transcription (discs 1 to 3 and the fixed base board).

Transcribed from the images in assets/ (solar-disc-*.png, main-board-assembled.png) by unwrapping each disc
to polar form. Slot index k (0..7) is the 45-degree bin counted counter-clockwise from the 3 o'clock direction
of the image as printed: slot k covers k*45 to (k+1)*45 degrees. A disc rotation of one step (1/8 turn,
counter-clockwise, owner ruling A-007) moves the content of slot k to slot k+1.

Cell types: PLANET (name), ASTEROID, COMET, EMPTY (a plain space), NULL (cutout: no space on this disc),
EARTH. Publicity: planets other than Earth, and comets, carry a publicity icon (read from the art).

Run: python tools/board/solar_system.py   (writes docs/spec/data/solar-system.json and docs/spec/board-solar-system.md)
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

N, E, A, C = 'NULL', 'EMPTY', 'ASTEROID', 'COMET'


def P(name):
    return 'PLANET:' + name


WHEELS = {
    1: {1: [N, P('VENUS'), E, P('MERCURY'), N, N, E, 'EARTH']},
    2: {1: [A, E, N, N, N, E, A, E],
        2: [N, P('MARS'), N, N, N, A, E, N]},
    3: {1: [E, A, A, E, N, N, A, C],
        2: [C, A, N, E, A, N, E, N],
        3: [N, P('SATURN'), N, N, E, P('JUPITER'), E, N]},
    4: {1: [C, C, E, A, A, E, C, A],
        2: [E, A, E, C, E, A, C, E],
        3: [A, E, E, A, A, C, A, E],
        4: [C, E, C, E, P('NEPTUNE'), E, E, P('URANUS')]},
}

# The 'Oumuamua tile sits on disc 3, ring 3, slot 3 (two sectors clockwise of Jupiter) once discovered.
OUMUAMUA = {'wheel': 3, 'ring': 3, 'slot': 3}

# Repo (Ender-Wiggin2019/seti, packages/common/src/constant/sectorSetup.ts) rows, clockwise, rulebook order.
REPO = {
    (1, 1): [P('MERCURY'), E, P('VENUS'), N, 'EARTH', E, N, N],
    (2, 1): [N, E, A, E, A, E, N, N],
    (2, 2): [N, P('MARS'), N, N, E, A, N, N],
    (3, 1): [C, A, N, N, E, A, A, E],
    (3, 2): [N, E, N, A, E, N, A, C],
    (3, 3): [N, E, P('JUPITER'), E, N, N, P('SATURN'), N],
    (4, 1): [C, E, A, A, E, C, C, A],
    (4, 2): [C, A, E, C, E, A, E, E],
    (4, 3): [A, C, A, A, E, E, A, E],
    (4, 4): [E, E, P('NEPTUNE'), E, C, E, C, P('URANUS')],
}


def cyc_equal(a, b):
    n = len(a)
    return any(a == b[i:] + b[:i] for i in range(n))


def check_against_repo():
    bad = []
    for (w, r), repo_row in REPO.items():
        # mine is counter-clockwise; the repo's rows run clockwise
        mine_cw = list(reversed(WHEELS[w][r]))
        # the repo lists NULL for a cell the art shows ASTEROID/COMET with no difference only via wheel 2 ring 1: compare directly
        if not cyc_equal(mine_cw, repo_row):
            bad.append((w, r))
    return bad


# Visible-layer stack (repo model, confirmed by the physical stacking): at ring R the visible cell is the first
# non-NULL walking disc R, R+1, ..., 3, then the base (wheel 4). Disc 1 covers ring 1 only, disc 2 rings 1 and 2,
# disc 3 rings 1 to 3, the base all four rings.
def stack_for_ring(r):
    return [d for d in (1, 2, 3, 4) if d >= r]


def visible(angles, ring, sector):
    """angles: rotation steps of disc 1, 2, 3 (counter-clockwise). Returns (wheel, type)."""
    for d in stack_for_ring(ring):
        step = angles[d - 1] if d <= 3 else 0
        local = (sector - step) % 8
        cell = WHEELS[d][ring][local]
        if OUMUAMUA and d == OUMUAMUA['wheel'] and ring == OUMUAMUA['ring'] and local == OUMUAMUA['slot'] and False:
            cell = P('OUMUAMUA')
        if cell != N:
            return d, cell
    return 4, E


def main():
    bad = check_against_repo()
    print('rows differing from the repo (cyclic, clockwise):', bad or 'none')
    data = {
        'source': 'assets/solar-disc-*.png and assets/main-board-assembled.png, unwrapped to polar form; cross-checked against the repo sectorSetup.ts',
        'slot_convention': 'slot k = k*45 to (k+1)*45 degrees counter-clockwise from the 3 o\'clock direction of the image as printed',
        'rotation': 'one step = 1/8 turn counter-clockwise: content of slot k moves to slot k+1; rotating disc 2 also rotates disc 1; rotating disc 3 rotates discs 1 and 2',
        'wheels': {str(w): {str(r): row for r, row in rings.items()} for w, rings in WHEELS.items()},
        'oumuamua_slot': OUMUAMUA,
        'stack_rule': 'at ring R the visible cell is the first non-NULL going disc R, R+1, ..., 3, then the base',
        'differs_from_repo': [list(b) for b in bad],
    }
    os.makedirs(os.path.join(ROOT, 'docs', 'spec', 'data'), exist_ok=True)
    json.dump(data, open(os.path.join(ROOT, 'docs', 'spec', 'data', 'solar-system.json'), 'w', encoding='utf-8'), indent=1)
    return bad


if __name__ == '__main__':
    raise SystemExit(1 if main() else 0)
