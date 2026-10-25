"""The model in the lobby: given a game (its options and the moves played so far) and a seat, the move that the model plays there.

The service is stateless (the Worker keeps the game): every request carries the whole log, so the game is replayed here, the seat's own view of it is
built (its hand, the other hands hidden) with what the seat has seen, and the bundle search plays the turn. The search plans a whole bundle, so the
reply carries the rest of the plan too; the Worker gives it back with the next request of the same turn, and it is used as long as the game asks for
the moves that were planned. Only the versions the owner approved are served (`approved` in the index of the models).
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seti_engine import engine, orgs
from seti_engine.models import GameState, Options
from seti_engine.projection import View, acting, actor_of, project
from seti_engine.replay import js_number

from .bundle_data import public_move
from .bundle_search import Brain, BundleBot, SearchConfig
from .bundles import bundle_key
from .knowledge import Knowledge

History = list[tuple[int, dict[str, Any]]]


class NoSuchModel(Exception):
    pass


class NotYourTurn(Exception):
    pass


@dataclass
class Reply:
    action: dict[str, Any]
    plan: list[dict[str, Any]]
    searched: bool  # False when the move came from the plan of an earlier request
    candidates: int = 0


def replay(options: Options, actions: list[dict[str, Any]], rng_encoding: str = "exact") -> tuple[GameState, History, Knowledge]:
    """The game after the moves, with what the seats have seen (the memory of the network), as the arena and the training data build it."""
    state = engine.start(options).state
    history: History = []
    know = Knowledge()
    for move in actions:
        if rng_encoding == "double":
            state = state.model_copy()
            state.rng_state = js_number(state.rng_state)
        seat = actor_of(state, move)
        if seat is None:
            raise ValueError("the log has moves after the end of the game")
        if move["type"] == "undo":
            taken = state.undo_log[-1] if state.undo_log else None
            for k in range(len(history) - 1, -1, -1):
                h = {key: v for key, v in history[k][1].items() if key != "display_card"}
                if history[k][0] == seat and h == taken:
                    del history[k]
                    break
            state = engine.apply(state, move).state
            continue
        res = engine.apply(state, move)
        if not orgs.is_secret_setup(move):  # the others' choices of the simultaneous setup are secret (EXP-ORG-14)
            know.update(seat, move, res.events)
            history.append((seat, public_move(move, res.events, seat)))
        state = res.state
    return state, history, know


class LazyBrains(Mapping[str, Brain]):
    """The brains of the approved versions, each loaded when it is first asked for: a version that nobody plays (a large one that does not fit in the
    memory of the service) cannot take down the others."""

    def __init__(self, names: list[str], load: Callable[[str], Brain]) -> None:
        self._names = list(names)
        self._load = load
        self._loaded: dict[str, Brain] = {}

    def __getitem__(self, name: str) -> Brain:
        if name not in self._names:
            raise KeyError(name)
        if name not in self._loaded:
            self._loaded[name] = self._load(name)
        return self._loaded[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._names)

    def __len__(self) -> int:
        return len(self._names)


class Lobby:
    """The approved models, loaded when first asked for."""

    def __init__(self, brains: Mapping[str, Brain], config: SearchConfig | None = None) -> None:
        self.brains = brains
        self.config = config or SearchConfig()

    def models(self) -> list[str]:
        return sorted(self.brains)

    def _setup_move(self, brain: Brain, view: View, history: History, know: Knowledge) -> dict[str, Any]:
        """EXP-ORG-14: the organization, the quick start cards and the lock, one move at a time, on the seat's own view (the choices of the others
        are hidden): the best of what is still open, and the lock as soon as both are chosen."""
        seat = view.viewer
        assert seat is not None
        me = view.state.players[seat]
        lock = next((m for m in view.legal if m["type"] == "setup_lock"), None)
        if lock is not None:
            return dict(lock)
        tucks = [m for m in view.legal if m["type"] == "setup_tuck"]
        if tucks:  # EXP-ORG-07: the cards to tuck for income, one at a time (the model has no score for this move yet: the first card is kept)
            return dict(tucks[0])
        scores = brain.logits(view, history, know)
        open_moves = [
            i
            for i, m in enumerate(view.legal)
            if not (m["type"] == "choose_org" and me.setup_org is not None) and not (m["type"] == "choose_quick" and me.setup_quick)
        ]
        return dict(view.legal[max(open_moves, key=lambda i: scores[i])])

    def move(self, model: str, options: Options, actions: list[dict[str, Any]], seat: int, plan: list[dict[str, Any]], rng_encoding: str = "exact") -> Reply:
        brain = self.brains.get(model)
        if brain is None:
            raise NoSuchModel(model)
        state, history, know = replay(options, actions, rng_encoding)
        if seat is None or seat not in acting(state):
            raise NotYourTurn(f"seat {seat} is not the one to act")
        view = project(state, seat, previews=False)
        if state.pending and state.pending[0].kind == "setup_choice":
            return Reply(self._setup_move(brain, view, history, know), [], False)  # EXP-ORG-14: chosen on the seat's own view, no search
        bot = BundleBot(brain, self.config)
        bot.history, bot.knowledge = history, know
        bot.plan, bot.pos, bot.key = list(plan), 0, bundle_key(state, seat)
        # the same seed gives the same search for the same position (a retry after a failure plays the same move)
        rng = random.Random(hash((options.seed, len(actions))) & 0xFFFFFFFF)
        index = bot.act(state, view, rng)
        action = view.legal[index]
        return Reply(action, bot.plan[bot.pos :], bot.searches > 0, len(bot.last.candidates) if bot.last is not None else 0)


def approved_versions(root: Path, allow_unapproved: bool = False) -> list[str]:
    index = root / "index.json"
    if not index.exists():
        return []
    return [v["version"] for v in json.loads(index.read_text(encoding="utf-8")) if v.get("approved") or allow_unapproved]


def load_lobby(root: Path, config: SearchConfig | None = None, allow_unapproved: bool = False) -> Lobby:
    """The approved versions in `root` (the models folder), each as a brain on the processor."""
    import torch

    from .agent import LocalNet, net_from
    from .brains import NetBrain

    torch.set_num_threads(2)

    def load(version: str) -> Brain:
        net = net_from(str(root / version / "model.pt"), "cpu").eval()
        return NetBrain(LocalNet(net))

    return Lobby(LazyBrains(approved_versions(root, allow_unapproved), load), config)
