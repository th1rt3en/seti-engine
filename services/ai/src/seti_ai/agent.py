"""The learning agent: a network that scores each legal move, and a player that uses it.

The network reads the vector of the view (features.encode_view) and, for every legal move, a bag of hashed tokens and a few numbers
(features.encode_move). It gives one score for each legal move (the policy is a softmax over the legal moves, so an illegal move can never be chosen)
and one value for the position (the points it expects to still score). The weights are learned by train.py; the agent never sees more than its own view.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from seti_engine.models import GameState
from seti_engine.projection import View
from torch import nn

from . import features

VALUE_SCALE = 20.0  # rewards and values are in units of 20 points


class PolicyNet(nn.Module):
    def __init__(self, obs_dim: int, hidden: int = 384, move_dim: int = 128, emb: int = 64) -> None:
        super().__init__()
        self.obs_dim = obs_dim
        self.obs = nn.Sequential(nn.Linear(obs_dim, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.tok = nn.Embedding(features.TOKEN_BUCKETS, emb, padding_idx=0)
        self.num = nn.Linear(features.MOVE_NUM, emb)
        self.move = nn.Sequential(nn.Linear(2 * emb, move_dim), nn.ReLU(), nn.Linear(move_dim, move_dim), nn.ReLU())
        self.gate = nn.Linear(hidden, move_dim)
        self.score = nn.Sequential(nn.Linear(hidden + 2 * move_dim, 192), nn.ReLU(), nn.Linear(192, 1))
        self.value = nn.Sequential(nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, 1))

    def forward(self, obs: torch.Tensor, toks: torch.Tensor, nums: torch.Tensor, mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """obs [B, D], toks [B, M, T], nums [B, M, N], mask [B, M] (True where a move exists): the logits [B, M] and the values [B]."""
        h = self.obs(obs)
        e = self.tok(toks).sum(dim=2)  # the bag of tokens of each move
        m = self.move(torch.cat([e, torch.relu(self.num(nums))], dim=-1))
        g = self.gate(h).unsqueeze(1) * m
        z = torch.cat([h.unsqueeze(1).expand(-1, m.shape[1], -1), m, g], dim=-1)
        logits = self.score(z).squeeze(-1).masked_fill(~mask, -1e9)
        return logits, self.value(h).squeeze(-1)


@dataclass
class Step:
    """One decision of one seat, as the learner needs it."""

    obs: NDArray[np.float32]
    toks: NDArray[np.int32]
    nums: NDArray[np.float32]
    action: int
    logp: float
    value: float
    board_score: int
    seat: int


class NNAgent:
    """Plays with a network. With `record` the decisions are kept (for training); `explore` samples from the policy, else it takes the best move."""

    name = "agent"

    def __init__(self, net: PolicyNet, explore: bool = True, record: bool = False, temperature: float = 1.0) -> None:
        self.net = net
        self.explore = explore
        self.record = record
        self.temperature = temperature
        self.steps: list[Step] = []

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        obs = features.encode_view(view)
        toks, nums = features.encode_moves(view)
        with torch.no_grad():
            logits, value = self.net(
                torch.from_numpy(obs).unsqueeze(0),
                torch.from_numpy(toks).long().unsqueeze(0),
                torch.from_numpy(nums).unsqueeze(0),
                torch.ones(1, len(view.legal), dtype=torch.bool),
            )
        lg = logits[0] / self.temperature
        if self.explore:
            probs = torch.softmax(lg, dim=0)
            a = int(torch.multinomial(probs, 1).item())
        else:
            a = int(torch.argmax(lg).item())
        if self.record:
            logp = float(torch.log_softmax(logits[0], dim=0)[a].item())
            self.steps.append(Step(obs, toks, nums, a, logp, float(value.item()), state.players[seat].score, seat))
        return a


def new_net() -> PolicyNet:
    return PolicyNet(features.obs_size())


def to_cpu_state(net: PolicyNet) -> dict[str, Any]:
    return {k: v.detach().cpu() for k, v in net.state_dict().items()}
