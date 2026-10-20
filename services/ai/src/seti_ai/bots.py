"""Bots for training and testing only: they play offline, against each other and against the learning agent, to give it opponents and yardsticks.

They are not part of the website. A bot chooses one of the legal moves that the engine lists (it never invents a move), and the lookahead bots try a move
on a copy of the state with `engine.apply`. To keep them honest they value only what a player can see of the result: the score, the resources, the
computer and the board, never the identity of cards that were drawn (the hidden part of the state is not read).
"""

from __future__ import annotations

import random
from typing import Any, Protocol

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


def _sectors_led(state: GameState, me: int) -> int:
    """The number of sectors in which the seat has more markers than any other player."""
    n = 0
    for sec in state.sectors:
        mine = sec.markers.count(me)
        if mine and all(mine > sec.markers.count(o) for o in range(len(state.players)) if o != me):
            n += 1
    return n


def _board_value(state: GameState, p: PlayerState, w: dict[str, float], rm: float = 1.0, sm: float = 1.0, tech_values: dict[str, float] | None = None) -> float:
    """The value of a position for a seat: its score plus weights for what turns into score later. `rm` scales the resources and `sm` the structures
    (probes, techs, orbiters ...): at the end of a game a resource that is not spent is worth nothing."""
    markers = sum(sec.markers.count(p.index) for sec in state.sectors)
    in_play = len([pr for pr in state.probes if pr.player == p.index and not pr.capsule])
    techs = sum((tech_values or {}).get(t, w["tech"]) for t in p.techs)
    resources = (
        w["credit"] * p.credits
        + w["energy"] * p.energy
        + w["data"] * p.data_pool
        + w["publicity"] * p.publicity
        + w["move"] * p.movement
        + w["card"] * len(p.hand)
        + w["tuck"] * len(p.tucked)
    )
    structures = (
        w["computer"] * sum(p.computer)
        + w["probe"] * in_play
        + techs
        + w["orbit"] * sum(p.orbiters.values())
        + w["land"] * sum(p.landers.values())
        + w["mission"] * (len(p.completed_missions) + 0.5 * len(p.missions) + len(p.end_cards))
        + w["trace"] * len(p.trace_log)
        + w["win"] * p.sector_wins
        + w["marker"] * markers
        + w.get("lead", 0.0) * _sectors_led(state, p.index)
        + w.get("token", 0.0) * p.signal_tokens
    )
    total: float = p.score + rm * resources + sm * structures
    return total


GREEDY = {
    "credit": 0.5, "energy": 0.5, "data": 0.5, "publicity": 0.4, "move": 0.15, "card": 0.5, "computer": 1.0, "tuck": 1.0, "probe": 2.0,
    "tech": 2.0, "orbit": 2.0, "land": 3.0, "mission": 1.0, "trace": 1.0, "win": 0.0, "marker": 1.0,
}  # fmt: skip
HEURISTIC_V1 = {
    "credit": 0.7, "energy": 0.7, "data": 0.8, "publicity": 0.6, "move": 0.2, "card": 0.8, "computer": 1.3, "tuck": 1.6, "probe": 2.5,
    "tech": 3.5, "orbit": 3.0, "land": 4.0, "mission": 2.0, "trace": 2.0, "win": 1.5, "marker": 1.4,
}  # fmt: skip
# The quantified model of SETI at https://seti.ender-wiggin.com/posts/model (the author's estimates, in credits; 1 credit is about 5 victory points there;
# the weights below are in victory points): 1 energy = 1 credit (0.5 when it only pays for moves), a card drawn 0.75, a move 0.5, a signal 1, a tech 3, a
# launch 2, a trace 2 credits; publicity, data and moves are worth about the same through the free-action corner.
# Its advice for play: cards are the core (a card played costs 0.5 credit and a mission completed is worth 0.5 above its cost), so prefer playing cards
# and completing missions to the standard actions; a scan at the start of round 1 loses about 1 credit, so do not open with it.
# `model` takes the model's values as they are. Measured (16 games): about 9 points against 40 for the first heuristic, because a one-step lookahead that
# counts every resource at its full value does not spend them. So `heuristic` keeps the first heuristic's weights and takes the model's advice for play.
MODEL = {
    "credit": 5.0, "energy": 4.5, "data": 3.0, "publicity": 2.5, "move": 2.5, "card": 3.75, "computer": 2.0, "tuck": 3.0, "probe": 10.0,
    "tech": 18.0, "orbit": 8.0, "land": 10.0, "mission": 6.0, "trace": 5.0, "win": 5.0, "marker": 5.0,
}  # fmt: skip
MODEL_BIAS = {"play_card": 5.0, "complete_mission": 5.0}
USE_THE_TURN = 25.0  # passing before the main action of the turn is taken costs this much (model bot only)
HEURISTIC_V2 = HEURISTIC_V1  # version 2: the weights of the first heuristic
HEURISTIC = {**HEURISTIC_V1, "energy": 0.9}  # version 3: energy is worth more than credits (the guides: movement and landing use it up)
HEURISTIC_BIAS = {"play_card": 1.0, "complete_mission": 1.0}  # the model's advice: cards are the core, and missions the best use of them
TURN_ENDERS = ("pass", "end_turn")


class LookaheadBot:
    """Tries every legal move on a copy of the state and takes the one that gives the seat the best value (one step ahead).
    The value is the score plus a weight for each thing that will turn into score later (resources, computer, tech, orbiters, missions ...)."""

    def __init__(
        self,
        name: str,
        weights: dict[str, float],
        noise: float = 0.05,
        scale: float = 1.0,
        bias: dict[str, float] | None = None,
        no_scan_in_round_1: bool = False,
        use_the_turn: float = 0.0,
        res_by_round: list[float] | None = None,
        struct_by_round: list[float] | None = None,
        tech_values: dict[str, float] | None = None,
        org_bias: dict[str, float] | None = None,
        quick_bias: dict[str, float] | None = None,
    ) -> None:
        self.name = name
        self.weights = weights
        self.noise = noise
        self.scale = scale  # the penalties for ending the turn are in units of the weights
        self.bias = bias or {}
        self.no_scan_in_round_1 = no_scan_in_round_1
        self.use_the_turn = use_the_turn  # passing before the main action of the turn is taken costs this much
        self.res_by_round = res_by_round or [1.0] * 5  # how much the resources count in each round (they are worth less as the game ends)
        self.struct_by_round = struct_by_round or [1.0] * 5
        self.tech_values = tech_values
        self.org_bias = org_bias or {}  # the expansion: how much each organization is liked when it is chosen
        self.quick_bias = quick_bias or {}  # and each quick start card

    def _value(self, state: GameState, p: PlayerState) -> float:
        r = max(1, min(state.round, 5)) - 1
        return _board_value(state, p, self.weights, self.res_by_round[r], self.struct_by_round[r], self.tech_values)

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        base = self._value(state, state.players[seat])
        best, best_value = 0, -1e9
        for i in _options(view):
            m = view.legal[i]
            try:
                nxt = engine.apply(state, m).state
            except Exception:  # a move that cannot be tried is not chosen
                continue
            gain = self._value(nxt, nxt.players[seat]) - base
            # ending the turn or passing is the last choice while something else gives value, so that a turn is used before it is given up
            if m["type"] in TURN_ENDERS:
                gain -= (0.5 if m["type"] == "end_turn" else 1.0) * self.scale  # something that gives value is done first
            elif gain <= 0:
                gain -= 0.001 * (1 + rng.random())  # a move that does nothing is worse than ending the turn only when nothing else gives value
            gain += self.bias.get(m["type"], 0.0)
            if m["type"] == "choose_org":
                gain += self.org_bias.get(str(m.get("org")), 0.0)
            elif m["type"] == "choose_quick":
                gain += sum(self.quick_bias.get(c, 0.0) for c in m.get("cards", []))
            if m["type"] == "pass" and not state.main_done:
                gain -= self.use_the_turn
            if self.no_scan_in_round_1 and m["type"] == "scan" and state.round == 1:
                gain -= 5.0  # the model: starting round 1 with a scan loses about a credit
            value = gain + self.noise * self.scale * rng.random()
            if value > best_value:
                best, best_value = i, value
        return best


def greedy() -> LookaheadBot:
    return LookaheadBot("greedy", GREEDY)


def heuristic_v1() -> LookaheadBot:
    """The first heuristic bot (hand-chosen weights); kept as a yardstick for the versions that were measured against it."""
    return LookaheadBot("heuristic_v1", HEURISTIC_V1)


def heuristic_v2() -> LookaheadBot:
    """The heuristic bot, version 2: the first heuristic's weights plus the model's advice for play (cards and missions first, no scan in round 1)."""
    return LookaheadBot("heuristic_v2", HEURISTIC_V2, bias=HEURISTIC_BIAS, no_scan_in_round_1=True)


def heuristic() -> LookaheadBot:
    """The heuristic bot, version 3: version 2 with energy worth 0.9 and credits 0.7 (found by trying variants; 85% against the greedy bot over 200 games)."""
    return LookaheadBot("heuristic", HEURISTIC, bias=HEURISTIC_BIAS, no_scan_in_round_1=True)


def model() -> LookaheadBot:
    """The values of the quantified model taken as they are (see MODEL); weaker than the heuristic bot."""
    return LookaheadBot("model", MODEL, scale=5.0, bias=MODEL_BIAS, no_scan_in_round_1=True, use_the_turn=USE_THE_TURN)


def from_spec(spec: dict[str, Any]) -> LookaheadBot:
    """A lookahead bot from a description: {"name", "base": "heuristic_v1" | "greedy" | "model", "weights": {overrides}, "bias": {...}, "res": [5 numbers],
    "struct": [5 numbers], "tech": {tech id: value}, "no_scan_r1": bool, "noise": number}. Used to try variants of the heuristic bot."""
    weights = dict({"greedy": GREEDY, "model": MODEL}.get(spec.get("base", "heuristic_v1"), HEURISTIC_V1))
    weights.update(spec.get("weights", {}))
    return LookaheadBot(
        spec.get("name", "variant"),
        weights,
        noise=spec.get("noise", 0.05),
        bias=spec.get("bias"),
        no_scan_in_round_1=spec.get("no_scan_r1", False),
        use_the_turn=spec.get("use_the_turn", 0.0),
        res_by_round=spec.get("res"),
        struct_by_round=spec.get("struct"),
        tech_values=spec.get("tech"),
        org_bias=spec.get("org_bias"),
        quick_bias=spec.get("quick_bias"),
    )


BOTS = {"random": RandomBot, "greedy": greedy, "heuristic_v1": heuristic_v1, "heuristic_v2": heuristic_v2, "heuristic": heuristic, "model": model}
BOT_VERSIONS = {"random": 1, "greedy": 1, "heuristic": 3}  # recorded in the manifest of a model version: its numbers are against these bots
