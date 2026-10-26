"""The brains that the bundle search can use (bundle_search.Brain): a hand-made one (the heuristic bot's own evaluator, for tests and as a baseline) and
the network."""

from __future__ import annotations

from typing import Any

import numpy as np
from seti_engine.models import GameState
from seti_engine.projection import View

from . import bots, features
from .agent import VALUE_SCALE
from .bundle_search import History
from .knowledge import Knowledge
from .views import project


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
        # the mark of the irreversible moves is in the views of the network that was made with it (views.py)
        self.irreversible: bool = getattr(getattr(getattr(net, "net", None), "cfg", None), "irreversible", True)

    def logits(self, view: View, history: History, knowledge: Knowledge | None) -> np.ndarray:
        keep = [i for i, c in enumerate(view.classes) if c != "control"] or list(range(len(view.legal)))
        tokens = features.encode_view(view, history if self.memory else None, knowledge if self.memory else None)
        toks, nums = features.encode_moves(view, keep)
        scores, _ = self.net.evaluate(tokens, toks, nums)
        out = np.full(len(view.legal), -1e9)
        out[keep] = np.asarray(scores, dtype=np.float64)
        return out

    def answer_many(self, requests: list[tuple[Any, ...]]) -> list[Any]:
        """The answers to many requests of the search at once (`bundle_search.drive`): one call of the network for the whole batch."""
        items: list[tuple[features.Tokens, np.ndarray, np.ndarray]] = []
        metas: list[tuple[list[int], int] | None] = []
        for r in requests:
            if r[0] == "logits":
                view, hist, know = r[1], r[2], r[3]
                keep = [i for i, c in enumerate(view.classes) if c != "control"] or list(range(len(view.legal)))
                tokens = features.encode_view(view, hist if self.memory else None, know if self.memory else None)
                toks, nums = features.encode_moves(view, keep)
                items.append((tokens, toks, nums))
                metas.append((keep, len(view.legal)))
            else:
                state, seat, hist, know = r[1], r[2], r[3], r[4]
                view = project(state, seat, previews=False, irreversible=self.irreversible)
                tokens = features.encode_view(view, hist if self.memory else None, know if self.memory else None)
                items.append((tokens, np.zeros((1, features.MAX_TOKENS), dtype=np.int32), np.zeros((1, features.MOVE_NUM), dtype=np.float32)))
                metas.append(None)
        many = getattr(self.net, "evaluate_many", None)
        results = many(items) if many is not None else [self.net.evaluate(*it) for it in items]
        out: list[Any] = []
        for (scores, v), meta in zip(results, metas, strict=True):
            if meta is None:
                out.append(float(v) * VALUE_SCALE)
            else:
                keep, n = meta
                full = np.full(n, -1e9)
                full[keep] = np.asarray(scores, dtype=np.float64)
                out.append(full)
        return out

    def value(self, state: GameState, seat: int, history: History, knowledge: Knowledge | None) -> float:
        view = project(state, seat, previews=False, irreversible=self.irreversible)
        tokens = features.encode_view(view, history if self.memory else None, knowledge if self.memory else None)
        toks = np.zeros((1, features.MAX_TOKENS), dtype=np.int32)
        nums = np.zeros((1, features.MOVE_NUM), dtype=np.float32)
        _, v = self.net.evaluate(tokens, toks, nums)
        return float(v) * VALUE_SCALE
