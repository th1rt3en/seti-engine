"""The brains that the bundle search can use (bundle_search.Brain): a hand-made one (the heuristic bot's own evaluator, for tests and as a baseline) and
the network."""

from __future__ import annotations

from typing import Any

import numpy as np
from seti_engine.models import GameState
from seti_engine.projection import View, project

from . import bots, features
from .agent import VALUE_SCALE
from .bundle_search import History
from .knowledge import Knowledge


class HeuristicBrain:
    """No policy (all moves look the same: the search samples and builds bundles at random) and the value that the heuristic bot gives a position: what
    its resources and structures are worth, on top of the score. With it the search is a bot that plays whole turns without any network."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or bots.HEURISTIC

    def logits(self, view: View, history: History, knowledge: Knowledge | None) -> np.ndarray:
        return np.zeros(len(view.legal))

    def value(self, state: GameState, seat: int, history: History, knowledge: Knowledge | None) -> float:
        p = state.players[seat]
        return float(bots._board_value(state, p, self.weights) - p.score)


class NetBrain:
    """The network as a brain: the policy scores the legal moves of a decision, the value head reads the position after a bundle (from the seat's own
    side: the seat is not the one to act there, so the network is given no move to choose among, only a blank one that it ignores)."""

    def __init__(self, net: Any, memory: bool = True) -> None:
        self.net = net  # anything with evaluate(tokens, toks, nums) -> (logits, value): a LocalNet, or the client of the inference server
        self.memory = memory

    def logits(self, view: View, history: History, knowledge: Knowledge | None) -> np.ndarray:
        keep = [i for i, c in enumerate(view.classes) if c != "control"] or list(range(len(view.legal)))
        tokens = features.encode_view(view, history if self.memory else None, knowledge if self.memory else None)
        toks, nums = features.encode_moves(view, keep)
        scores, _ = self.net.evaluate(tokens, toks, nums)
        out = np.full(len(view.legal), -1e9)
        out[keep] = np.asarray(scores, dtype=np.float64)
        return out

    def value(self, state: GameState, seat: int, history: History, knowledge: Knowledge | None) -> float:
        view = project(state, seat, previews=False)
        tokens = features.encode_view(view, history if self.memory else None, knowledge if self.memory else None)
        toks = np.zeros((1, features.MAX_TOKENS), dtype=np.int32)
        nums = np.zeros((1, features.MOVE_NUM), dtype=np.float32)
        _, v = self.net.evaluate(tokens, toks, nums)
        return float(v) * VALUE_SCALE
