"""The learning agent: a transformer that reads the entities of the position and scores each legal move.

How it is built (see docs/AI-PLAN.md, section 11). The design follows ZeusAI (Paolini et al., "Learning to Play 7 Wonders Duel Without Human Supervision",
arXiv 2406.00741), which plays a card game with a transformer encoder that has learned embeddings for each component of the game and its place, and no
rule knowledge: costs and effects are learned from play. Here:

- every entity of the position (a player, a sector, a planet, a probe, a tech stack, a gold tile, a species with its state, a card in a zone ...) is one
  token; its vector is the sum of the learned embeddings of the features that describe it (features.py), plus an embedding of its kind;
- a transformer encoder (self-attention between all the entities) builds the picture of the position;
- every legal move is encoded from its own tokens and numbers and, as a query, attends to the position (a small transformer decoder that also lets the
  moves look at each other) and gets one score: the policy is a softmax over the legal moves, so an illegal move can never be chosen;
- the value head reads a summary token of the position and gives the points the seat expects to gain from now on (in units of 20 points).

`PRESETS` are sizes of the same network. The data that this machine can make (games per day) limits what size can be trained, not the shape of the net:
`base` is where training starts and `large` is the size of ZeusAI's network, for when the data allows it.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from seti_engine.models import GameState
from seti_engine.projection import View
from torch import nn

from . import features

VALUE_SCALE = features.VALUE_SCALE  # rewards and values are in units of 20 points (here for the code that imports it from the network)


@dataclass(frozen=True)
class NetConfig:
    d_model: int = 512
    layers: int = 8
    heads: int = 8
    ffn: int = 2048
    move_layers: int = 2
    obs_dim: int = features.OBS_DIM
    entity_types: int = features.ENTITY_TYPES
    token_buckets: int = features.TOKEN_BUCKETS
    max_tokens: int = features.MAX_TOKENS
    move_num: int = features.MOVE_NUM
    irreversible: bool = True  # the views have the mark of the moves that cannot be taken back (views.py); the Beta line is made without it


PRESETS = {
    "small": NetConfig(d_model=256, layers=4, heads=4, ffn=1024, move_layers=1),  # about 12M parameters: tests and quick experiments
    "medium": NetConfig(d_model=384, layers=6, heads=6, ffn=1536, move_layers=2, irreversible=False),  # about 30M: between small and base (the Beta line)
    "base": NetConfig(d_model=512, layers=8, heads=8, ffn=2048, move_layers=2),  # about 45M: where training starts
    "large": NetConfig(d_model=768, layers=12, heads=12, ffn=3072, move_layers=3),  # about 144M: the size of ZeusAI's network and more
    "xlarge": NetConfig(d_model=1024, layers=16, heads=16, ffn=4096, move_layers=4),  # about 300M: larger than ZeusAI's; measured before it is chosen
}


class PolicyNet(nn.Module):
    def __init__(self, cfg: NetConfig | None = None) -> None:
        super().__init__()
        self.cfg = cfg or PRESETS["base"]
        c = self.cfg
        d = c.d_model
        self.feat = nn.EmbeddingBag(c.obs_dim, d, mode="sum")  # a feature has a learned vector; an entity is the sum of its features (weighted)
        self.kind = nn.Embedding(c.entity_types, d)
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.norm_in = nn.LayerNorm(d)
        layer = nn.TransformerEncoderLayer(d, c.heads, c.ffn, dropout=0.0, activation="gelu", batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, c.layers, enable_nested_tensor=False)
        self.norm_out = nn.LayerNorm(d)
        # the moves
        self.tok = nn.Embedding(c.token_buckets, d, padding_idx=0)
        self.num = nn.Linear(c.move_num, d)
        self.move_in = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, d))
        dec = nn.TransformerDecoderLayer(d, c.heads, c.ffn, dropout=0.0, activation="gelu", batch_first=True, norm_first=True)
        self.decoder = nn.TransformerDecoder(dec, c.move_layers)
        self.score = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d // 2), nn.GELU(), nn.Linear(d // 2, 1))
        self.value = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d // 2), nn.GELU(), nn.Linear(d // 2, 1))
        nn.init.normal_(self.cls, std=0.02)
        nn.init.normal_(self.feat.weight, std=0.02)

    def encode(self, batch: Batch) -> tuple[torch.Tensor, torch.Tensor]:
        """The entities of a batch of positions: [B, 1 + T, d] (the first is the summary token)."""
        bag = self.feat(batch.idx, batch.offsets, per_sample_weights=batch.val)  # [N, d]
        tok = self.norm_in(bag + self.kind(batch.kinds))
        b, t = batch.mask.shape
        x = tok.new_zeros(b, t, tok.shape[-1])
        x[batch.sample, batch.pos] = tok
        x = torch.cat([self.cls.expand(b, -1, -1), x], dim=1)
        pad = torch.cat([torch.zeros(b, 1, dtype=torch.bool, device=x.device), ~batch.mask], dim=1)
        return self.norm_out(self.encoder(x, src_key_padding_mask=pad)), pad

    def forward(self, batch: Batch) -> tuple[torch.Tensor, torch.Tensor]:
        """The logits of the moves [B, M] (-1e9 where there is no move) and the values [B]."""
        memory, pad = self.encode(batch)
        e = self.tok(batch.toks).sum(dim=2)
        q = self.move_in(e + self.num(batch.nums))
        out = self.decoder(q, memory, tgt_key_padding_mask=~batch.move_mask, memory_key_padding_mask=pad)
        logits = self.score(out).squeeze(-1).float().masked_fill(~batch.move_mask, -1e9)
        return logits, self.value(memory[:, 0]).squeeze(-1).float()


@dataclass
class Batch:
    """A padded batch of positions: the tokens of the entities (a sparse bag for each), and the legal moves."""

    idx: torch.Tensor  # [F] feature slots of all the entities of the batch
    val: torch.Tensor  # [F]
    offsets: torch.Tensor  # [N] where the bag of each entity starts
    kinds: torch.Tensor  # [N]
    sample: torch.Tensor  # [N] the position of the batch that each entity belongs to
    pos: torch.Tensor  # [N] its place among that position's entities
    mask: torch.Tensor  # [B, T] True where there is an entity
    toks: torch.Tensor  # [B, M, K]
    nums: torch.Tensor  # [B, M, N]
    move_mask: torch.Tensor  # [B, M]


@dataclass
class Step:
    """One decision of one seat, as the learner needs it."""

    tokens: features.Tokens
    toks: NDArray[np.int32]
    nums: NDArray[np.float32]
    action: int
    logp: float
    value: float
    board_score: int
    seat: int


def collate(steps: list[tuple[features.Tokens, NDArray[np.int32], NDArray[np.float32]]], device: torch.device) -> Batch:
    b = len(steps)
    t_max = max(s[0].count for s in steps)
    m_max = max(s[1].shape[0] for s in steps)
    n_tok = sum(s[0].count for s in steps)
    idx = np.concatenate([s[0].idx for s in steps])
    val = np.concatenate([s[0].val for s in steps])
    offsets = np.empty(n_tok, dtype=np.int64)
    kinds = np.empty(n_tok, dtype=np.int64)
    sample = np.empty(n_tok, dtype=np.int64)
    pos = np.empty(n_tok, dtype=np.int64)
    mask = np.zeros((b, t_max), dtype=bool)
    k = 0
    base = 0
    for i, (tk, _, _) in enumerate(steps):
        c = tk.count
        offsets[k : k + c] = tk.offsets[:-1] + base
        kinds[k : k + c] = tk.kinds
        sample[k : k + c] = i
        pos[k : k + c] = np.arange(c)
        mask[i, :c] = True
        k += c
        base += int(tk.offsets[-1])
    toks = np.zeros((b, m_max, steps[0][1].shape[1]), dtype=np.int64)
    nums = np.zeros((b, m_max, steps[0][2].shape[1]), dtype=np.float32)
    move_mask = np.zeros((b, m_max), dtype=bool)
    for i, (_, mt, nm) in enumerate(steps):
        m = mt.shape[0]
        toks[i, :m], nums[i, :m], move_mask[i, :m] = mt, nm, True

    def t(a: NDArray[Any]) -> torch.Tensor:
        return torch.from_numpy(a).to(device)

    return Batch(t(idx.astype(np.int64)), t(val), t(offsets), t(kinds), t(sample), t(pos), t(mask), t(toks), t(nums), t(move_mask))


def net_from(path: str, device: torch.device | str = "cpu") -> PolicyNet:
    saved = torch.load(path, map_location=device)
    cfg = NetConfig(**saved["config"]) if "config" in saved else PRESETS["base"]
    net = PolicyNet(cfg).to(device)
    net.load_state_dict(saved["weights"] if "weights" in saved else saved)
    return net


def save_net(net: PolicyNet, path: str) -> None:
    torch.save({"config": asdict(net.cfg), "weights": {k: v.detach().cpu() for k, v in net.state_dict().items()}}, path)


class NNAgent:
    """Plays with a network (here, or a client of the inference server in a worker: anything with `evaluate`).
    With `record` the decisions are kept (for training); `explore` samples from the policy, else it takes the best move."""

    name = "agent"

    def __init__(self, net: Any, explore: bool = True, record: bool = False, temperature: float = 1.0, memory: bool = True) -> None:
        self.net = net
        self.explore = explore
        self.record = record
        self.temperature = temperature
        self.steps: list[Step] = []
        self.memory = memory  # False: a network from before the memory features; it does not get the history or the known cards
        self.history: list[tuple[int, dict[str, Any]]] | None = None  # set by the arena: the actions of both seats so far
        self.knowledge: Any = None  # set by the arena: the cards that the other seats are known to hold

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        # a move that only takes back (undo) is not offered: the agent would use it to stall
        keep = [i for i, m in enumerate(view.legal) if m["type"] != "undo"] or list(range(len(view.legal)))
        tokens = features.encode_view(view, self.history if self.memory else None, self.knowledge if self.memory else None)
        toks, nums = features.encode_moves(view, keep)
        logits, value = self.net.evaluate(tokens, toks, nums)
        lg = torch.from_numpy(np.asarray(logits, dtype=np.float32)) / self.temperature
        if self.explore:
            a = int(torch.multinomial(torch.softmax(lg, dim=0), 1).item())
        else:
            a = int(torch.argmax(lg).item())
        if self.record:
            logp = float(torch.log_softmax(torch.from_numpy(np.asarray(logits, dtype=np.float32)), dim=0)[a].item())
            self.steps.append(Step(tokens, toks, nums, a, logp, float(value), state.players[seat].score, seat))
        return keep[a]


class LocalNet:
    """A network used in this process (a test, an evaluation by hand): the same `evaluate` as the client of the server."""

    def __init__(self, net: nn.Module) -> None:
        self.net = net.eval()
        self.device = next(net.parameters()).device

    def evaluate(self, tokens: features.Tokens, toks: NDArray[np.int32], nums: NDArray[np.float32]) -> tuple[NDArray[np.float32], float]:
        with torch.no_grad():
            batch = collate([(tokens, toks, nums)], self.device)
            logits, value = self.net(batch)
        return logits[0, : toks.shape[0]].cpu().numpy(), float(value[0].item())

    def evaluate_many(
        self, items: list[tuple[features.Tokens, NDArray[np.int32], NDArray[np.float32]]], chunk: int = 64
    ) -> list[tuple[NDArray[np.float32], float]]:
        """The answers to many positions at once (the network is called once for each `chunk`): what the batched search uses."""
        out: list[tuple[NDArray[np.float32], float]] = []
        for at in range(0, len(items), chunk):
            part = items[at : at + chunk]
            with torch.no_grad():
                batch = collate(part, self.device)
                logits, value = self.net(batch)
            lg = logits.float().cpu().numpy()
            vs = value.float().cpu().numpy()
            out += [(lg[i, : it[1].shape[0]], float(vs[i])) for i, it in enumerate(part)]
        return out


def new_net(preset: str = "base") -> PolicyNet:
    return PolicyNet(PRESETS[preset])
