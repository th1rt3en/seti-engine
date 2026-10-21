"""A bot that searches with the network: the policy proposes, a short look into the future disposes (inference only, no training).

At each decision the network scores the legal moves. For the best `k` of them the bot plays on, on copies of the game: the rest of its own turn, then the opponent's
turn, with the network choosing the best move for both seats, until it is the bot's move again. The hidden things of the copy are drawn again (the order of the
deck and the random state, so that the cards that come are not the ones that really come: chance events are sampled, as in ZeusAI). The value of a move is the
mean over `samples` such futures of (the points gained on the way + the network's value of the position that is reached). The move with the best value is played.

The copies are made from the real game state, so the opponent's hand in them is the real one. That is fine for games between bots; before the bot plays humans
the hand has to be replaced by a draw from the cards that the bot has not seen (docs/AI-DECISIONS.md).
"""

from __future__ import annotations

import copy
import random
from typing import Any

import numpy as np
from seti_engine import engine
from seti_engine.models import GameState
from seti_engine.projection import View, project, to_act

from . import features
from .agent import VALUE_SCALE, NNAgent
from .knowledge import Knowledge

NEVER = ("undo",)
MAX_ROLLOUT = 400  # decisions of one look-ahead


class NetSearchBot:
    name = "netsearch"

    def __init__(self, net: Any, k: int = 4, samples: int = 2) -> None:
        self.net, self.k, self.samples = net, k, samples
        self.history: list[tuple[int, dict[str, Any]]] | None = None
        self.knowledge: Knowledge | None = None
        self.searched = 0

    def _scores(self, view: View, hist: Any, know: Any) -> tuple[list[int], np.ndarray, float]:
        keep = [i for i, m in enumerate(view.legal) if m["type"] not in NEVER] or list(range(len(view.legal)))
        tokens = features.encode_view(view, hist, know)
        toks, nums = features.encode_moves(view, keep)
        logits, value = self.net.evaluate(tokens, toks, nums)
        return keep, np.asarray(logits, dtype=np.float32), float(value)

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        keep, logits, _ = self._scores(view, self.history, self.knowledge)
        if len(keep) == 1:
            return keep[0]
        order = np.argsort(-logits)[: self.k]
        self.searched += 1
        best, best_value = int(order[0]), -1e18
        for a in order:
            total = 0.0
            for _ in range(self.samples):
                total += self._future(state, view.legal[keep[int(a)]], seat, rng)
            total /= self.samples
            total += 0.01 * float(logits[int(a)])  # the network's own preference breaks ties
            if total > best_value:
                best, best_value = int(a), total
        return keep[best]

    def _future(self, state: GameState, move: dict[str, Any], seat: int, rng: random.Random) -> float:
        """Points gained by `seat` until it is its move again after the other seat has played: on a copy with the chance events drawn again."""
        s = state.model_copy(deep=True)
        s.rng_state = rng.getrandbits(62)
        rng.shuffle(s.deck)
        hist = list(self.history or [])
        know = copy.deepcopy(self.knowledge) if self.knowledge is not None else Knowledge()
        base = state.players[seat].score
        r = engine.apply(s, move)
        know.update(seat, move, r.events)
        hist.append((seat, dict(move)))
        other_moved = False
        steps = 0
        while r.legal and steps < MAX_ROLLOUT:
            cur = to_act(r.state)
            if cur is None:
                break
            if cur == seat and other_moved:
                break
            v = project(r.state, cur, previews=False)
            keep, logits, _ = self._scores(v, hist, know)
            m = dict(v.legal[keep[int(np.argmax(logits))]])
            r = engine.apply(r.state, m)
            know.update(cur, m, r.events)
            hist.append((cur, m))
            other_moved = other_moved or cur != seat
            steps += 1
        end = r.state
        if end.phase == "finished":
            rows = {x["player"]: x["total"] for x in end.final_scores}
            return float(rows.get(seat, end.players[seat].score)) - base
        v = project(end, seat, previews=False)
        if not v.legal:
            return float(end.players[seat].score - base)
        _, _, value = self._scores(v, hist, know)
        return float(end.players[seat].score - base) + VALUE_SCALE * value


def play_agent(net: Any) -> NNAgent:
    return NNAgent(net, explore=False, record=False)
