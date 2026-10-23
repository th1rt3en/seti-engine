"""The training examples of the network at the level of bundles (docs/AI-TURN-BUNDLES.md), made from the log of a game (a game of bots, of the model, or
of people).

Two kinds of example, both from the view of the seat as it saw the game (its own hand, the other hands hidden):
- **policy**: the state before a micro move of a bundle, and the move that was chosen among the legal ones (undo and the control moves are not
  offered);
- **value**: the position right after the last move of a bundle (the seat is not the one to act there: the network is given a blank move and ignores
  it), and the points that the seat gained from there to the end of the game, end-of-game scoring included (divided by `VALUE_SCALE`, like the value
  of the network).

Moves that were taken back by `undo` make no example. A game that was not played to its end gives policy examples only (there is no final score to
learn the value from). `game_weights` is the rule for games of people against the model: a game that the model lost counts, with more weight; a game
that the model won, or tied, is skipped.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from seti_engine import engine, orgs
from seti_engine.models import GameState, Options
from seti_engine.projection import actor_of, project
from seti_engine.replay import js_number

from . import features
from .agent import VALUE_SCALE
from .bundles import cut, micros_from_log
from .knowledge import Knowledge

Weight = float | Callable[[int], float]


@dataclass
class PolicyExample:
    tokens: features.Tokens
    toks: NDArray[np.int32]
    nums: NDArray[np.float32]
    action: int  # the index of the chosen move among the moves that were offered to the network
    weight: float


@dataclass
class ValueExample:
    tokens: features.Tokens
    target: float  # points from here to the end of the game, divided by VALUE_SCALE
    weight: float


@dataclass
class Examples:
    policy: list[PolicyExample] = field(default_factory=list)
    value: list[ValueExample] = field(default_factory=list)
    bundles: int = 0
    finished: bool = False

    def extend(self, other: Examples) -> None:
        self.policy += other.policy
        self.value += other.value
        self.bundles += other.bundles


def _w(weight: Weight, seat: int) -> float:
    return float(weight(seat)) if callable(weight) else float(weight)


def _final_total(state: GameState, seat: int) -> float:
    for row in state.final_scores:
        if row.get("player") == seat:
            return float(row.get("total", state.players[seat].score))
    return float(state.players[seat].score)


def public_move(move: dict[str, Any], events: list[dict[str, Any]], seat: int) -> dict[str, Any]:
    """The move as the memory of the network gets it: with the card that was taken from the display named (the arena and the AI service do the same)."""
    out = dict(move)
    for e in events:
        if e.get("type") == "take_display_card" and e.get("player") == seat:
            out["display_card"] = e["card"]
    return out


def examples_from_log(
    options: Options,
    actions: list[dict[str, Any]],
    rng_encoding: str = "exact",
    policy_weight: Weight = 1.0,
    value_weight: Weight = 1.0,
    memory: bool = True,
) -> Examples:
    """The examples of one game. The weights are per seat (a number, or a function of the seat); an example of weight 0 is not made."""
    micros, final = micros_from_log(options, actions, rng_encoding)
    bundles = cut(micros)
    kept = {m.index for m in micros}
    last_of_bundle = {b.steps[-1].index for b in bundles}
    finished = final.phase == "finished"
    out = Examples(bundles=len(bundles), finished=finished)

    state = engine.start(options).state
    history: list[tuple[int, dict[str, Any]]] = []
    know = Knowledge()
    for index, move in enumerate(actions):
        if rng_encoding == "double":
            state = state.model_copy()
            state.rng_state = js_number(state.rng_state)
        seat = actor_of(state, move)
        assert seat is not None
        if move["type"] == "undo":
            taken = state.undo_log[-1] if state.undo_log else None
            for k in range(len(history) - 1, -1, -1):
                h = {key: v for key, v in history[k][1].items() if key != "display_card"}
                if history[k][0] == seat and h == taken:
                    del history[k]
                    break
            state = engine.apply(state, move).state
            continue
        if index in kept and _w(policy_weight, seat) > 0:
            view = project(state, seat, previews=False)
            if move in view.legal:  # a move of an old log that the engine does not offer any more (the legacy scan skip) makes no example
                keep = [i for i, c in enumerate(view.classes) if c != "control"]
                toks, nums = features.encode_moves(view, keep)
                chosen = keep.index(view.legal.index(move))
                tokens = features.encode_view(view, history if memory else None, know if memory else None)
                out.policy.append(PolicyExample(tokens, toks, nums, chosen, _w(policy_weight, seat)))
        res = engine.apply(state, move)
        if move["type"] not in orgs.SETUP_TYPES:  # the choices of the simultaneous setup are secret until all are locked in (EXP-ORG-14)
            know.update(seat, move, res.events)
            history.append((seat, public_move(move, res.events, seat)))
        state = res.state
        if finished and index in last_of_bundle and index in kept and _w(value_weight, seat) > 0:
            after = project(state, seat, previews=False)
            tokens = features.encode_view(after, history if memory else None, know if memory else None)
            target = (_final_total(final, seat) - state.players[seat].score) / VALUE_SCALE
            out.value.append(ValueExample(tokens, target, _w(value_weight, seat)))
    return out


def game_weights(
    scores: list[int], model_seats: set[int], lost_weight: float = 3.0, value_lost_weight: float = 1.0
) -> tuple[dict[int, float], dict[int, float]]:
    """The weights of the examples of a game, per seat: (policy weights, value weights).

    - no seat is the model's (a game of bots, or of people against each other): every example counts once;
    - the model lost (a seat that is not the model's scored more): the moves of the others (the people) are examples with `lost_weight`, the moves of
      the model are not imitated (weight 0), and the positions of both seats give value labels (`value_lost_weight`);
    - the model won or tied: the game is skipped (all weights 0)."""
    seats = range(len(scores))
    if not model_seats:
        return {s: 1.0 for s in seats}, {s: 1.0 for s in seats}
    best_model = max(scores[s] for s in model_seats)
    best_other = max((scores[s] for s in seats if s not in model_seats), default=-1)
    if best_model >= best_other:
        return {s: 0.0 for s in seats}, {s: 0.0 for s in seats}
    return {s: (0.0 if s in model_seats else lost_weight) for s in seats}, {s: value_lost_weight for s in seats}
