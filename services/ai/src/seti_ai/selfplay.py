"""Self-play with the bundle search (docs/AI-TURN-BUNDLES.md section 13): the model plays whole turns found by its own search, and the game is cut into
examples.

A game is played by `BundleBot`s that share one network (or by one of them against a bot that keeps the model grounded: the heuristic bot). What the model
learns from the log of the game (`bundle_data.examples_from_log`):
- the policy: every move of every bundle that the model played is an example, so the policy is pulled toward what the search chose (the search is the
  teacher, as in AlphaZero); the moves of a bot are not imitated;
- the value: the position after every bundle of both seats, with the points that the seat really gained to the end of the game.

To keep the games from being all the same the bundle that is played in the first rounds is drawn among the best ones (`explore`: the temperature, in
points, and the number of rounds it is used for; the search of the lobby plays the best one). Nothing here knows a rule.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from seti_engine.models import GameState, Options
from seti_engine.projection import View

from . import arena, bots
from .brains import NetBrain
from .bundle_data import Examples, examples_from_log
from .bundle_search import Brain, BundleBot, SearchConfig

OPTIONS = [{}, {"expansion": True, "organizations": True}]  # the base game and the expansion, half of the games each (as bundle_train)


@dataclass
class SelfPlayConfig:
    search: SearchConfig = field(default_factory=SearchConfig)
    explore_temperature: float = 3.0  # points; 0: always the best bundle
    explore_rounds: int = 2  # the temperature is used until the end of this round of the game
    bot: str = ""  # a bot of bots.BOTS for the second seat ("" : the model plays both seats)


class ExploringBot(BundleBot):
    """The bundle bot of the lobby that draws its bundle among the best ones in the first rounds of a game."""

    def __init__(self, brain: Brain, config: SearchConfig, temperature: float, rounds: int) -> None:
        super().__init__(brain, config)
        self.temperature, self.rounds = temperature, rounds

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        self.search.cfg.pick_temperature = self.temperature if state.round <= self.rounds else 0.0
        return super().act(state, view, rng)


@dataclass
class SelfPlayGame:
    examples: Examples
    scores: list[int]
    model_seats: list[int]
    steps: int
    searches: int


def play(brain: Brain, seed: int, cfg: SelfPlayConfig, kind: int = 0) -> SelfPlayGame:
    """One game: the model (a search with `brain`) against itself, or against `cfg.bot`; `kind` 0 is the base game, 1 the expansion. The seat of the model
    is drawn by the seed when a bot plays the other seat."""
    opts = dict(OPTIONS[kind])
    rng = random.Random(seed)
    model_seat = rng.randrange(2) if cfg.bot else -1
    players: list[Any] = []
    for seat in range(2):
        if cfg.bot and seat != model_seat:
            players.append(bots.BOTS[cfg.bot]())
        else:
            players.append(ExploringBot(brain, SearchConfig(**vars(cfg.search)), cfg.explore_temperature, cfg.explore_rounds))
    res = arena.play_game(players, seed, rng, opts)
    seats = [s for s in range(2) if not cfg.bot or s == model_seat]
    ex = examples_from_log(
        Options(players=2, seed=seed, **opts),
        res.actions,
        policy_weight=lambda s: 1.0 if s in seats else 0.0,
        value_weight=1.0,
    )
    return SelfPlayGame(ex, res.scores, seats, res.steps, sum(p.searches for p in players if isinstance(p, BundleBot)))


def make_brain(net: Any, memory: bool = True) -> NetBrain:
    """The network as the brain of the search (`net` is a `LocalNet`, or anything with `evaluate`)."""
    return NetBrain(net, memory)
