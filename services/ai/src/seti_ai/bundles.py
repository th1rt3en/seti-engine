"""Bundles: a game cut into the turns of the seats (docs/AI-TURN-BUNDLES.md, decisions of the owner of 2026-10-21).

A bundle is everything that one seat does from the moment it is to act until the turn passes on: free actions (with the answers that they ask for), the main
action with the answers that it asks for, free actions, and the end of the turn (a `pass` ends it by itself, and the discard, the rotation and the choice of the
end-of-round card are part of it; so are the sectors and milestones that the end of a turn resolves).
This module knows no rule: the engine says what a move is (`legal_classified`: free, main, answer, end, control) and in which turn it is played (round, turn
number, the seat whose turn it is).

- The decisions of the setup (the organization, the quick start cards, the cards tucked at the start) of a seat are one bundle ("setup").
- A decision that another seat has to answer during a turn (a trace placed by the seat that won a sector, say) is a bundle of its own for that seat ("answer").
- `undo` is no part of the game: it takes back the last move that can be taken back, and that move is removed from its bundle.
- A bundle's points are the points the seat gained from the state before its first move to the state after its last one; what a seat gains outside its bundles
  (an opponent's turn gives points, the end of the game scores) is kept apart, so that the points of all the bundles and these gains add up to the final score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from seti_engine import engine
from seti_engine.models import GameState, Options
from seti_engine.projection import actor_of
from seti_engine.replay import js_number

SETUP = "setup"
TURN = "turn"
ANSWER = "answer"


@dataclass(frozen=True)
class Micro:
    """One decision of a seat: the move, its class, the turn it was made in, and the score of the seat around it."""

    index: int  # the position of the move in the log (the action number)
    seat: int
    move: dict[str, Any]
    cls: str
    kind: str  # SETUP, TURN or ANSWER
    key: tuple[int, int, int]  # (round, turn number, seat whose turn it is); (0, 0, seat) in the setup
    score_before: int
    score_after: int


@dataclass
class Bundle:
    seat: int
    kind: str
    key: tuple[int, int, int]
    steps: list[Micro] = field(default_factory=list)

    @property
    def points(self) -> int:
        """The points the seat gained from before its first move to after its last one."""
        return self.steps[-1].score_after - self.steps[0].score_before if self.steps else 0

    @property
    def main(self) -> str | None:
        """The type of the main action, if the bundle has one."""
        for m in self.steps:
            if m.cls == "main":
                return str(m.move["type"])
        return None

    @property
    def shape(self) -> str:
        """The bundle in a few words, for a log: `free free main:analyze answer free end`."""
        return " ".join(f"main:{m.move['type']}" if m.cls == "main" else m.cls for m in self.steps)

    @property
    def complete(self) -> bool:
        """A turn that ended: with `end_turn`, or with the `pass` (and the decisions that a pass asks for)."""
        return self.kind == TURN and self.main is not None and (self.main == "pass" or any(m.cls == "end" for m in self.steps))


def bundle_key(state: GameState, seat: int) -> tuple[str, tuple[int, int, int]]:
    """The kind and the key of the bundle that a decision of `seat` in this state belongs to (the bundle search stops when it changes)."""
    if state.phase != "play":
        return SETUP, (0, 0, seat)
    key = (state.round, state.turn, state.current_player)
    if seat != state.current_player:
        return ANSWER, (state.round, state.turn, seat)
    return TURN, key


def micros_from_log(options: Options, actions: list[dict[str, Any]], rng_encoding: str = "exact") -> tuple[list[Micro], GameState]:
    """Replay a game and give its decisions with their classes (without the moves that an `undo` took back), and the last state.

    `actions` are the moves of the log in order (`{"type": ...}`); `rng_encoding` is "double" for a game that was played through the Worker before the random
    state became a string (seti_engine.replay)."""
    state = engine.start(options).state
    kept: list[Micro] = []
    for index, move in enumerate(actions):
        if rng_encoding == "double":
            state = state.model_copy()
            state.rng_state = js_number(state.rng_state)
        classified = engine.legal_classified(state)
        cls = next((c for m, c in classified if m == move), None)
        if cls is None:
            # a move that the engine does not offer is refused by `apply` with the list of what is legal; one that it still accepts is a move of an old
            # log (the `scan_skip` of the games played before the scan could be done in any order, 2026-10-22): an answer of its seat
            engine.apply(state, move)
            cls = "answer"
        seat = actor_of(state, move)  # the simultaneous setup names the seat in the move (EXP-ORG-14)
        assert seat is not None
        if move["type"] == "undo":
            taken_back = state.undo_log[-1] if state.undo_log else None
            for k in range(len(kept) - 1, -1, -1):
                if kept[k].move == taken_back:
                    del kept[k]
                    break
            else:
                raise AssertionError(f"the undo at {index} takes back {taken_back}, which is not in the bundles")
            state = engine.apply(state, move).state
            continue
        before = state.players[seat].score
        kind, key = bundle_key(state, seat)
        nxt = engine.apply(state, move).state
        kept.append(Micro(index, seat, move, cls, kind, key, before, nxt.players[seat].score))
        state = nxt
    return kept, state


def cut(micros: list[Micro]) -> list[Bundle]:
    """Cut the decisions into bundles: the decisions of one seat that are in the same turn (or in the setup), in the order of their first move.

    A seat that answers a decision of someone else's turn in the middle of a turn of its own keeps its own bundle open: the bundles are kept for each seat.
    """
    open_by_seat: dict[int, Bundle] = {}
    out: list[Bundle] = []
    for m in micros:
        b = open_by_seat.get(m.seat)
        if b is None or (b.kind, b.key) != (m.kind, m.key):
            b = Bundle(m.seat, m.kind, m.key)
            open_by_seat[m.seat] = b
            out.append(b)
        b.steps.append(m)
    return out


def outside_gains(bundles: list[Bundle], seat: int) -> list[int]:
    """What the seat gained between its bundles (the turns of the others give points to a seat, for example): the score before each bundle minus the score
    after the one before; the first is the gain before its first bundle."""
    mine = [b for b in bundles if b.seat == seat]
    gains: list[int] = []
    last = None
    for b in mine:
        first = b.steps[0].score_before
        gains.append(first - last if last is not None else first)
        last = b.steps[-1].score_after
    return gains


def bundles_of_game(options: Options, actions: list[dict[str, Any]], rng_encoding: str = "exact") -> tuple[list[Bundle], GameState]:
    micros, state = micros_from_log(options, actions, rng_encoding)
    return cut(micros), state
