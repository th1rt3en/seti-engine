"""What an agent sees: everything that the seat to act sees of the game, and nothing else.

The view is the one the engine hands to the seat that is to act (`project(state, seat)`): the board, both players' tracks, resources, techs, missions and
cards in play, the card row, the discard pile, the sectors and signals, the planets, the species (discovered or not, their discovery spaces, boards,
decks sizes, per-species state such as anomaly tokens, exofossils or samples), the pending decision, the trackers of both players. What the seat may not
see is already hidden by the projection (the deck order, the opponent's hand, the face-down tiles, an undiscovered species): it arrives as "?" and only
its count can be seen.

Instead of picking fields by hand, the whole view is walked: every number, flag, name and list in it becomes a feature (feature hashing into
`OBS_DIM` slots), so that nothing that a player sees is left out and a new field of the engine is seen at once. The seat is made relative: the seat
to act is player 0 and the others follow in turn order, so that both seats of a game look the same to the network. `EXCLUDED` lists what is not
turned into features and why (bookkeeping that is not information about the game). tests/test_features.py checks the walk.

The legal moves are encoded one by one: a bag of hashed tokens (the type, every field and value, the note of the engine: cost and rewards) and a few
numbers.
"""

from __future__ import annotations

import math
import zlib
from typing import Any

import numpy as np
from numpy.typing import NDArray
from seti_engine import tables
from seti_engine.projection import View

OBS_DIM = 32768  # the slots of the hashed features of a view
TOKEN_BUCKETS = 4096  # the move tokens are hashed into this many buckets (0 is the padding)
MAX_TOKENS = 28  # tokens kept for a move
MOVE_NUM = 17  # numbers for a move: costs, flags, the numbers of the card it names
INCOME = ("credit", "energy", "card", "data", "publicity")
SECTOR_COLORS = ("red", "yellow", "blue", "black")
POSITIONAL = 24  # a list is also seen position by position up to this many entries
MAX_LIST = 40  # a list of structures is seen up to this many entries

# What is left out of the view, and why. Everything else in the view is a feature.
EXCLUDED = {
    "state.options.seed": "the seed of the game: not information about the position",
    "state.rng_state": "the state of the random generator: hidden by the projection (0)",
    "state.undo": "the saved state for taking a move back: never shown to a player",
    "state.undo_log": "the same",
    "state.trail": "bookkeeping of the gains of the step being played, empty between steps",
    "state.log": "text lines, not used by the engine",
    "state.final_scores": "only exists when the game is over",
    "state.winners": "only exists when the game is over",
    "planet_cells": "the same as the discs and the planets, worked out",
    "rotation_previews": "a preview for the page: the engine's copy of the next rotations, not the position",
    "legal": "the moves are encoded one by one (encode_moves)",
    "notes": "the notes of the moves are part of each move",
    "reach": "where the probes can go: derived from the position and the moves",
    "viewer": "the seat is made relative: the seat to act is player 0",
}


def _bucket(token: str) -> int:
    return zlib.crc32(token.encode()) % (TOKEN_BUCKETS - 1) + 1


_PATH: dict[str, int] = {}


def _slot(path: str) -> int:
    i = _PATH.get(path)
    if i is None:
        i = zlib.crc32(path.encode()) % OBS_DIM
        _PATH[path] = i
    return i


def _signed_log(x: float) -> float:
    return math.copysign(math.log1p(abs(x)), x) / 3.0


# ---------------------------------------------------------------------------------------------------------------------------------
# the seat is made relative
# ---------------------------------------------------------------------------------------------------------------------------------

PLAYER_LISTS = {"markers", "winners", "orbiters", "landers", "low_markers", "overflow", "done", "owners", "players"}
PLAYER_SCALARS = {"player", "marker", "owner", "first_orbiter", "current_player", "start_player", "pluto_owner", "index"}


def _rel(v: Any, me: int, n: int) -> Any:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0 or v >= n:
        return v  # not a seat (a neutral marker, a number)
    return (v - me) % n


def _rel_discovery(v: Any, me: int, n: int) -> Any:
    if isinstance(v, str) and len(v) >= 2 and v[0] == "p" and v[1:].isdigit():
        return f"p{(int(v[1:]) - me) % n}"
    return v


def relative(x: Any, me: int, n: int, key: str = "") -> Any:
    """The same data with the players renumbered from the seat to act (0, then the others in turn order)."""
    if isinstance(x, dict):
        return {k: relative(v, me, n, k) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        if key in PLAYER_LISTS:
            return [_rel(v, me, n) if not isinstance(v, (list, dict)) else relative(v, me, n, key) for v in x]
        if key == "discovery_spaces":
            return [_rel_discovery(v, me, n) for v in x]
        return [relative(v, me, n, key if key == "board" else "") for v in x]
    if key in PLAYER_SCALARS:
        return _rel(x, me, n)
    return x


def _reorder(seq: list[Any], me: int) -> list[Any]:
    n = len(seq)
    return [seq[(me + k) % n] for k in range(n)]


def relative_view(view: View) -> dict[str, Any]:
    """The view as plain data, seen from the seat to act."""
    d = view.model_dump(
        mode="json",
        exclude={
            "legal": True,
            "notes": True,
            "reach": True,
            "rotation_previews": True,
            "planet_cells": True,
            "state": {
                "undo": True,
                "undo_log": True,
                "trail": True,
                "log": True,
                "rng_state": True,
                "final_scores": True,
                "winners": True,
                "options": {"seed": True},
            },
        },
    )
    n = len(d["state"]["players"])
    me = view.viewer if view.viewer is not None else 0
    st = d["state"]
    for key in ("players",):
        st[key] = _reorder(st[key], me)
    d["trackers"] = _reorder(d["trackers"], me) if d.get("trackers") else []
    counts = d["counts"]
    for key in ("hands", "exertian_hands", "exertian_played"):
        if counts.get(key):
            counts[key] = _reorder(counts[key], me)
    # the board markers of the species are lists of lists of players: renumber them with the rest
    rel: dict[str, Any] = relative({"state": st, "counts": counts, "trackers": d["trackers"], "to_act": d.get("to_act")}, me, n)
    rel["state"]["players"] = [dict(p, index=(i)) for i, p in enumerate(rel["state"]["players"])]
    return rel


# ---------------------------------------------------------------------------------------------------------------------------------
# the walk: every leaf becomes a feature of an entity (a token of the transformer)
# ---------------------------------------------------------------------------------------------------------------------------------

import re  # noqa: E402

MAX_CARD_TOKENS = 16  # a list of cards with up to this many cards is one token for each card; a longer one (the discard pile) is a bag
ENTITY_TYPES = 256  # kinds of entities (a player, a sector, a planet, a card in a zone ...), hashed
_CARD_LIKE = set(tables.cards()) | set(tables.organizations()) | set(tables.quick_start_cards())
_ENTITY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^state\.players\[(\d+)\]"), "player"),
    (re.compile(r"^state\.sectors\[(\d+)\]"), "sector"),
    (re.compile(r"^state\.planets\.(\w+)"), "planet"),
    (re.compile(r"^state\.probes\[(\d+)\]"), "probe"),
    (re.compile(r"^state\.tech_stacks\[(\d+)\]"), "stack"),
    (re.compile(r"^state\.gold_tiles\[(\d+)\]"), "gold"),
    (re.compile(r"^state\.species\[(\d+)\]\.extra\.(\w+)"), "species.extra"),
    (re.compile(r"^state\.species\[(\d+)\]"), "species"),
    (re.compile(r"^state\.pending\[(\d+)\]"), "pending"),
    (re.compile(r"^state\.stashed\[(\d+)\]"), "stashed"),
    (re.compile(r"^trackers\[(\d+)\]"), "tracker"),
    (re.compile(r"^state\.(rival|objectives)"), "solo"),
    (re.compile(r"^counts"), "counts"),
]


_ENTITY: dict[str, tuple[str, str]] = {}


def _entity(path: str) -> tuple[str, str]:
    """(the kind, the key) of the entity that a feature belongs to: one player, one sector, one planet ... or the rest of the game."""
    e = _ENTITY.get(path)
    if e is None:
        e = ("global", "global")
        for pat, kind in _ENTITY_RULES:
            m = pat.match(path)
            if m:
                e = (kind, f"{kind}:{'.'.join(m.groups())}")
                break
        _ENTITY[path] = e
    return e


def _walk(path: str, x: Any, add: Any, add_card: Any) -> None:
    if path in EXCLUDED:
        return
    if x is None:
        add(f"{path}=None", 1.0)
    elif isinstance(x, bool):
        add(path, 1.0 if x else 0.0)
    elif isinstance(x, (int, float)):
        add(path, _signed_log(float(x)))
        if isinstance(x, int):
            add(f"{path}#{max(-3, min(int(x), 12))}", 1.0)
    elif isinstance(x, str):
        add(f"{path}={x}", 1.0)
    elif isinstance(x, (list, tuple)):
        add(f"{path}.len", _signed_log(float(len(x))))
        scalars = all(not isinstance(v, (list, tuple, dict)) for v in x)
        cards = scalars and 0 < len(x) <= MAX_CARD_TOKENS and all(isinstance(v, str) and v in _CARD_LIKE for v in x)
        if cards:  # a card is a token of its own: its name and where it lies (the zone)
            for i, v in enumerate(x):
                add_card(path, v, i)
            return
        for i, v in enumerate(x[: MAX_LIST if not scalars else POSITIONAL]):
            _walk(f"{path}[{i}]", v, add, add_card)
        if scalars:  # a list of names or numbers is also a bag (which markers, which cards of a long pile), whatever the order
            for v in x:
                add(f"{path}[]={v}", 1.0)
    elif isinstance(x, dict):
        for k, v in x.items():
            _walk(f"{path}.{k}", v, add, add_card)


class Tokens:
    """The entities of a view as tokens: for each, its kind and the sparse features that describe it."""

    __slots__ = ("kinds", "offsets", "idx", "val")

    def __init__(self, kinds: NDArray[np.int32], offsets: NDArray[np.int32], idx: NDArray[np.int32], val: NDArray[np.float32]) -> None:
        self.kinds, self.offsets, self.idx, self.val = kinds, offsets, idx, val

    @property
    def count(self) -> int:
        return int(self.kinds.shape[0])


HISTORY_LEN = 48  # how many of the last actions of both seats the agent remembers
CARD_PUBLIC = {"play_card", "discard_free", "discard", "cover", "complete_mission", "decline_cover", "discard_corner", "show_card", "choose_org"}


def public_action(action: dict[str, Any]) -> dict[str, Any]:
    """An action as the other seat saw it happen: a card is named when it was played or discarded face up, and not when it went into the hand or under
    the income card (the identity of those is not seen)."""
    t = action.get("type")
    return {k: ("?" if k == "card" and t not in CARD_PUBLIC else v) for k, v in action.items()}


def history_tokens(history: list[tuple[int, dict[str, Any]]], me: int, n: int) -> list[tuple[str, dict[int, float]]]:
    """The memory: one token for each of the last actions of both seats, newest first (who, in turn order from the seat to act; the type; the parameters)."""
    out: list[tuple[str, dict[int, float]]] = []
    for age, (seat, action) in enumerate(reversed(history[-HISTORY_LEN:])):
        a = public_action(action)
        t = str(a.get("type"))
        who = (seat - me) % n
        names = [f"hist|who={who}", f"hist|type={t}", f"hist|who={who}|type={t}", f"hist|age={min(age, 15)}", f"hist|age={min(age, 15)}|who={who}"]
        for k, v in a.items():
            if k == "type":
                continue
            s = ",".join(map(str, v)) if isinstance(v, (list, tuple)) else str(v)
            names += [f"hist|{t}:{k}={s}", f"hist|{k}={s}"]
        out.append((f"hist:{age}", {_slot(f): 1.0 for f in names}))
    return out


def encode_view(view: View, history: list[tuple[int, dict[str, Any]]] | None = None, knowledge: Any = None) -> Tokens:
    """The tokens of a view: one for each player, sector, planet, probe, tech stack, gold tile, species, pending decision, tracker, one for each card
    in front of a seat or in the row, one for each of the last actions of both seats (the memory) and one for the rest of the game.
    one for each card that the other seats are known to hold. The same view, history and knowledge always give the same tokens."""
    data = relative_view(view)
    ents: dict[str, tuple[str, dict[int, float]]] = {}

    def bucket_of(key: str, kind: str) -> dict[int, float]:
        e = ents.get(key)
        if e is None:
            e = (kind, {})
            ents[key] = e
        return e[1]

    def add(path: str, value: float) -> None:
        kind, key = _entity(path)
        acc = bucket_of(key, kind)
        i = _slot(path)
        acc[i] = acc.get(i, 0.0) + value

    def add_card(path: str, card: str, i: int) -> None:
        zone = re.sub(r"\[\d+\]", "[]", path) if "players" not in path else path
        acc = bucket_of(f"card:{path}:{card}:{i}", f"card:{zone}")
        for f in (f"card={card}", f"{zone}|card={card}", f"{zone}|pos={min(i, 8)}"):
            acc[_slot(f)] = acc.get(_slot(f), 0.0) + 1.0

    for top, sub in data.items():
        if top == "state":
            for k, v in sub.items():
                _walk(f"state.{k}", v, add, add_card)
        else:
            _walk(top, sub, add, add_card)
    if knowledge is not None:  # the cards that the other seats took from the display or showed: known to be in their hands
        me = view.viewer if view.viewer is not None else 0
        n = len(view.state.players)
        for seat in range(n):
            if seat == me:
                continue
            for i, card in enumerate(knowledge.of(seat)):
                rel = (seat - me) % n
                acc = bucket_of(f"known:{rel}:{card}:{i}", "card:known_hand")
                for f in (f"card={card}", f"known_hand:{rel}|card={card}", f"known_hand:{rel}|pos={min(i, 8)}"):
                    acc[_slot(f)] = acc.get(_slot(f), 0.0) + 1.0
    if history:
        me = view.viewer if view.viewer is not None else 0
        for key, acc in history_tokens(history, me, len(view.state.players)):
            ents[key] = ("hist", acc)
    kinds = np.empty(len(ents), dtype=np.int32)
    offsets = np.zeros(len(ents) + 1, dtype=np.int32)
    idx_parts: list[int] = []
    val_parts: list[float] = []
    for n, (kind, acc) in enumerate(ents.values()):
        kinds[n] = zlib.crc32(kind.encode()) % ENTITY_TYPES
        idx_parts += acc.keys()
        val_parts += acc.values()
        offsets[n + 1] = offsets[n] + len(acc)
    return Tokens(kinds, offsets, np.asarray(idx_parts, dtype=np.int32), np.asarray(val_parts, dtype=np.float32))


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


def _note_tokens(prefix: str, note: Any, out: list[int]) -> None:
    if isinstance(note, dict):
        for k, v in note.items():
            _note_tokens(f"{prefix}.{k}", v, out)
    elif isinstance(note, (list, tuple)):
        for v in note:
            _note_tokens(prefix, v, out)
    elif note is not None:
        out.append(_bucket(f"{prefix}={note}"))


def encode_move(move: dict[str, Any], note: dict[str, Any] | None) -> tuple[list[int], list[float]]:
    """The tokens (hashed `type`, `key=value`, `type:key=value`, and the engine's note of the move) and the numbers of one legal move."""
    t = str(move["type"])
    tokens = [_bucket(f"type={t}")]
    for k, v in move.items():
        if k == "type":
            continue
        s = ",".join(map(str, v)) if isinstance(v, (list, tuple)) else str(v)
        tokens += [_bucket(f"{k}={s}"), _bucket(f"{t}:{k}={s}"), _bucket(f"{t}:{k}")]
    if note:
        _note_tokens(f"note:{t}", note, tokens)
    nums = [0.0] * MOVE_NUM
    cost = (note or {}).get("cost") or {}
    for i, k in enumerate(("credit", "energy", "publicity", "data")):
        nums[i] = float(cost.get(k, 0)) / 4
    nums[4] = 1.0 if (note or {}).get("irreversible") else 0.0
    nums[5] = 1.0 if note and note.get("rewards") else 0.0
    card = move.get("card")
    if isinstance(card, str):
        nums[MOVE_NUM - 11 :] = _card_numbers(card)  # the last 11 numbers
    return tokens[:MAX_TOKENS], nums


def encode_moves(view: View, keep: list[int] | None = None) -> tuple[NDArray[np.int32], NDArray[np.float32]]:
    """The moves of the view (or only those at the positions `keep`), one row for each."""
    ids = list(range(len(view.legal))) if keep is None else keep
    toks = np.zeros((len(ids), MAX_TOKENS), dtype=np.int32)
    nums = np.zeros((len(ids), MOVE_NUM), dtype=np.float32)
    for row, i in enumerate(ids):
        t, x = encode_move(view.legal[i], view.notes[i] if i < len(view.notes) else None)
        toks[row, : len(t)] = t
        nums[row] = x
    return toks, nums


def obs_size() -> int:
    return OBS_DIM
