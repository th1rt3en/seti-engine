"""What an agent sees: a fixed-length vector for a view, and a bag of tokens plus a few numbers for each legal move.

The view is the one the engine hands to the seat that is to act (`project(state, seat)`): the agent never sees what its seat may not see (hidden hands,
the deck order, face-down tiles). The legal moves come from the engine; this module only turns them into numbers. It contains no rule logic: every number
is read from the view, and the same view always gives the same numbers (tests/test_features.py).
"""

from __future__ import annotations

import zlib
from typing import Any

import numpy as np
from numpy.typing import NDArray
from seti_engine import tables
from seti_engine.projection import View

TOKEN_BUCKETS = 4096  # the move tokens are hashed into this many buckets (0 is the padding)
MAX_TOKENS = 14  # tokens kept for a move
MOVE_NUM = 16  # numbers for a move (costs, the card's numbers)
INCOME = ("credit", "energy", "card", "data", "publicity")
SECTOR_COLORS = ("red", "yellow", "blue", "black")
PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune")
TECHS = tuple(f"{c}-{g}" for c in ("probe", "telescope", "computer") for g in ("dot", "link", "branch", "cross"))
CARD_IDS = sorted(tables.cards(), key=lambda c: (len(c), c))
CARD_INDEX = {c: i for i, c in enumerate(CARD_IDS)}
PENDING_BUCKETS = 48
MAX_PROBES = 3


def _bucket(token: str) -> int:
    return zlib.crc32(token.encode()) % (TOKEN_BUCKETS - 1) + 1


def _scalar(v: Any) -> str:
    return ",".join(map(str, v)) if isinstance(v, (list, tuple)) else str(v)


def _card_numbers(card: str | None) -> list[float]:
    """cost, the kind of income (5 values), the sector color (4 values), a free-action corner flag: 11 numbers."""
    out = [0.0] * 11
    info = tables.cards().get(card) if card else None
    if info is None:
        return out
    out[0] = float(info["cost"]) / 4
    if info["income"] in INCOME:
        out[1 + INCOME.index(info["income"])] = 1.0
    if info["sector"] in SECTOR_COLORS:
        out[6 + SECTOR_COLORS.index(info["sector"])] = 1.0
    out[10] = 1.0 if info["free"] else 0.0
    return out


def encode_move(move: dict[str, Any], note: dict[str, Any] | None) -> tuple[list[int], list[float]]:
    """The tokens (hashed `type`, `key=value`, `type:key=value`) and the numbers of one legal move."""
    t = str(move["type"])
    tokens = [_bucket(f"type={t}")]
    for k, v in move.items():
        if k == "type":
            continue
        tokens.append(_bucket(f"{k}={_scalar(v)}"))
        tokens.append(_bucket(f"{t}:{k}={_scalar(v)}"))
        tokens.append(_bucket(f"{t}:{k}"))
    nums = [0.0] * MOVE_NUM
    cost = (note or {}).get("cost") or {}
    for i, k in enumerate(("credit", "energy", "publicity", "data")):
        nums[i] = float(cost.get(k, 0)) / 4
    nums[4] = 1.0 if (note or {}).get("irreversible") else 0.0
    nums[5] = 1.0 if note and note.get("rewards") else 0.0
    card = move.get("card")
    if isinstance(card, str):
        nums[MOVE_NUM - 11 :] = _card_numbers(card)
    return tokens[:MAX_TOKENS], nums


def encode_moves(view: View) -> tuple[NDArray[np.int32], NDArray[np.float32]]:
    n = len(view.legal)
    toks = np.zeros((n, MAX_TOKENS), dtype=np.int32)
    nums = np.zeros((n, MOVE_NUM), dtype=np.float32)
    for i, m in enumerate(view.legal):
        t, x = encode_move(m, view.notes[i] if i < len(view.notes) else None)
        toks[i, : len(t)] = t
        nums[i] = x
    return toks, nums


def _player(view: View, p: Any, tracker: Any) -> list[float]:
    s = view.state
    f = [
        p.score / 100,
        p.credits / 8,
        p.energy / 8,
        p.publicity / 10,
        p.data_pool / 6,
        p.movement / 6,
        len(p.hand) / 8,
        sum(p.computer) / 6,
        float(p.passed),
        len([pr for pr in s.probes if pr.player == p.index and not pr.capsule]) / MAX_PROBES,
        sum(p.orbiters.values()) / 4,
        sum(p.landers.values()) / 4,
        len(p.missions) / 3,
        len(p.completed_missions) / 4,
        len(p.end_cards) / 2,
        len(p.gold_markers) / 4,
        p.sector_wins / 4,
        len(p.trace_log) / 6,
    ]
    f += [tracker.income.get(k, 0) / 6 for k in ("credit", "energy", "card")]
    f += [tracker.tucked.get(k, 0) / 4 for k in INCOME]
    f += [1.0 if t in p.techs else 0.0 for t in TECHS]
    return f


def encode_view(view: View) -> NDArray[np.float32]:
    """The fixed-length vector of a view (the seat that is to act is `view.viewer`)."""
    s = view.state
    me = view.viewer if view.viewer is not None else 0
    opp = 1 - me if len(s.players) == 2 else (me + 1) % len(s.players)
    f: list[float] = [
        s.round / 5,
        s.turn / 40,
        1.0 if s.phase == "setup" else 0.0,
        float(s.main_done),
        float(s.first_pass_done),
        len(s.deck) / 140,
        view.counts.hands[opp] / 8 if view.counts.hands else 0.0,
        float(s.rotations % 3 == 0),
        float(s.rotations % 3 == 1),
        float(s.rotations % 3 == 2),
        len(s.pending) / 3,
    ]
    f += [a / 8 for a in s.disc_angles]
    kind = [0.0] * PENDING_BUCKETS
    if s.pending:
        kind[zlib.crc32(s.pending[0].kind.encode()) % PENDING_BUCKETS] = 1.0
    f += kind
    f += _player(view, s.players[me], view.trackers[me])
    f += _player(view, s.players[opp], view.trackers[opp])
    # the card row: three cards, each with its numbers
    for i in range(3):
        f += _card_numbers(s.card_row[i] if i < len(s.card_row) else None)
    # the hand, the open missions and the end-of-game cards of the seat: which cards (multi-hot over the card ids)
    hand = np.zeros(len(CARD_IDS), dtype=np.float32)
    for c in s.players[me].hand:
        if c in CARD_INDEX:
            hand[CARD_INDEX[c]] = 1.0
    mission = np.zeros(len(CARD_IDS), dtype=np.float32)
    for m in s.players[me].missions:
        if m.card in CARD_INDEX:
            mission[CARD_INDEX[m.card]] = 1.0
    ends = np.zeros(len(CARD_IDS), dtype=np.float32)
    for c in s.players[me].end_cards + s.players[opp].end_cards:
        if c in CARD_INDEX:
            ends[CARD_INDEX[c]] = 1.0
    # the sectors: color, data left, the markers of both seats, wins
    for sec in s.sectors:
        color = [1.0 if sec.color == c else 0.0 for c in SECTOR_COLORS]
        f += color + [
            sec.data_remaining / 6,
            sec.markers.count(me) / 4,
            sec.markers.count(opp) / 4,
            len(sec.markers) / max(sec.capacity, 1),
            sec.winners.count(me) / 2,
            sec.winners.count(opp) / 2,
        ]
    # the planets: orbiters and landers of both seats
    for name in PLANETS:
        st = s.planets.get(name)
        if st is None:
            f += [0.0] * 4
            continue
        f += [st.orbiters.count(me) / 2, st.orbiters.count(opp) / 2, st.landers.count(me) / 2, st.landers.count(opp) / 2]
    # the probes of both seats: where they are (ring, the position in the circle) as a few numbers
    for who in (me, opp):
        mine = [pr for pr in s.probes if pr.player == who and not pr.capsule][:MAX_PROBES]
        for i in range(MAX_PROBES):
            if i < len(mine):
                pr = mine[i]
                ang = 2 * np.pi * pr.sector / 8
                f += [1.0, pr.ring / 4, float(np.sin(ang)), float(np.cos(ang))]
            else:
                f += [0.0] * 4
    # the tech stacks and the gold tiles
    for st in s.tech_stacks:
        f += [len(st.tiles) / 4, float(st.two_point_tile)]
    for g in s.gold_tiles:
        f += [
            g.markers.index(me) / 2 + 0.2 if me in g.markers else 0.0,
            g.markers.index(opp) / 2 + 0.2 if opp in g.markers else 0.0,
            len(g.markers) / 3,
        ]
    return np.concatenate([np.asarray(f, dtype=np.float32), hand, mission, ends])


_PROBE = None


def obs_size() -> int:
    """The length of `encode_view` (found once, from a new game)."""
    global _PROBE
    if _PROBE is None:
        from seti_engine.engine import start
        from seti_engine.models import Options
        from seti_engine.projection import project, to_act

        r = start(Options(players=2, seed=1))
        a = to_act(r.state)
        _PROBE = int(encode_view(project(r.state, a)).shape[0])
    return _PROBE
