"""Bots for training and testing only: they play offline, against each other and against the learning agent, to give it opponents and yardsticks.

They are not part of the website. A bot chooses one of the legal moves that the engine lists (it never invents a move), and the lookahead bots try a move
on a copy of the state with `engine.apply`. To keep them honest they value only what a player can see of the result: the score, the resources, the
computer and the board, never the identity of cards that were drawn (the hidden part of the state is not read).
"""

from __future__ import annotations

import random
from typing import Protocol

from seti_engine import engine
from seti_engine.models import GameState, PlayerState
from seti_engine.projection import View

NEVER = ("undo",)  # a move that only takes back: a bot does not use it


class Bot(Protocol):
    name: str

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        """The index of the chosen move in `view.legal`."""
        ...


def _options(view: View) -> list[int]:
    ok = [i for i, m in enumerate(view.legal) if m["type"] not in NEVER]
    return ok or list(range(len(view.legal)))


class RandomBot:
    """Chooses any legal move with equal chance, except that it does not undo."""

    name = "random"

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        return rng.choice(_options(view))


def _board_value(state: GameState, p: PlayerState, w: dict[str, float]) -> float:
    markers = sum(sec.markers.count(p.index) for sec in state.sectors)
    in_play = len([pr for pr in state.probes if pr.player == p.index and not pr.capsule])
    total: float = (
        p.score
        + w["credit"] * p.credits
        + w["energy"] * p.energy
        + w["data"] * p.data_pool
        + w["publicity"] * p.publicity
        + w["move"] * p.movement
        + w["card"] * len(p.hand)
        + w["computer"] * sum(p.computer)
        + w["tuck"] * len(p.tucked)
        + w["probe"] * in_play
        + w["tech"] * len(p.techs)
        + w["orbit"] * sum(p.orbiters.values())
        + w["land"] * sum(p.landers.values())
        + w["mission"] * (len(p.completed_missions) + 0.5 * len(p.missions) + len(p.end_cards))
        + w["trace"] * len(p.trace_log)
        + w["win"] * p.sector_wins
        + w["marker"] * markers
    )
    return total


GREEDY = {
    "credit": 0.5, "energy": 0.5, "data": 0.5, "publicity": 0.4, "move": 0.15, "card": 0.5, "computer": 1.0, "tuck": 1.0, "probe": 2.0,
    "tech": 2.0, "orbit": 2.0, "land": 3.0, "mission": 1.0, "trace": 1.0, "win": 0.0, "marker": 1.0,
}  # fmt: skip
HEURISTIC = {
    "credit": 0.7, "energy": 0.7, "data": 0.8, "publicity": 0.6, "move": 0.2, "card": 0.8, "computer": 1.3, "tuck": 1.6, "probe": 2.5,
    "tech": 3.5, "orbit": 3.0, "land": 4.0, "mission": 2.0, "trace": 2.0, "win": 1.5, "marker": 1.4,
}  # fmt: skip
TURN_ENDERS = ("pass", "end_turn")


class LookaheadBot:
    """Tries every legal move on a copy of the state and takes the one that gives the seat the best value (one step ahead).
    The value is the score plus a weight for each thing that will turn into score later (resources, computer, tech, orbiters, missions ...)."""

    def __init__(self, name: str, weights: dict[str, float], noise: float = 0.05) -> None:
        self.name = name
        self.weights = weights
        self.noise = noise

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        base = _board_value(state, state.players[seat], self.weights)
        best, best_value = 0, -1e9
        for i in _options(view):
            m = view.legal[i]
            try:
                nxt = engine.apply(state, m).state
            except Exception:  # a move that cannot be tried is not chosen
                continue
            gain = _board_value(nxt, nxt.players[seat], self.weights) - base
            # ending the turn or passing is the last choice while something else gives value, so that a turn is used before it is given up
            if m["type"] in TURN_ENDERS:
                gain -= 0.5 if m["type"] == "end_turn" else 1.0  # something that gives value is done first
            elif gain <= 0:
                gain -= 0.001 * (1 + rng.random())  # a move that does nothing is worse than ending the turn only when nothing else gives value
            value = gain + self.noise * rng.random()
            if value > best_value:
                best, best_value = i, value
        return best


def greedy() -> LookaheadBot:
    return LookaheadBot("greedy", GREEDY)


def heuristic() -> LookaheadBot:
    return LookaheadBot("heuristic", HEURISTIC)


BOTS = {"random": RandomBot, "greedy": greedy, "heuristic": heuristic}
