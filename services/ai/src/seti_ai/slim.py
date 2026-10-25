"""A small copy of the network for serving (owner, 2026-10-25): the same network with its weights in 8 bits, so that a large version fits in a small service.

The large network has 144M parameters: 575 MB as it is trained (32 bits each). The service has 1 GiB. Here every matrix of the transformer is kept as 8 bits
with a scale for each output (about a quarter of the size) and the matrix products run on the 8 bit weights (`torch.ao.nn.quantized.dynamic.Linear`), which on a
processor is as fast as the 32 bit ones; the table of the features (25M parameters, a few rows of which are read for a position) is kept as 16 bits; the norms
and the biases stay as they are. `SlimNet.forward` takes the same `Batch` as `PolicyNet` and gives the same answer (to a small error: `agreement` measures it).

    python -m seti_ai.slim models_v3/v003/model.pt models_v3/v003/model.int8.pt          # make the small file
    python -m seti_ai.slim models_v3/v003/model.pt --check archive_new                     # how close is it to the original?

Nothing here is rules or training: it only reads a trained network.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import torch
import torch.nn.functional as F
from torch import nn
from torch.ao.nn.quantized.dynamic import Linear as QLinear

from .agent import Batch, NetConfig, PolicyNet

# The kinds of linear layers that stay in 32 bits: the small ones, which the 8 bit copy gets wrong the most (measured with `--check` on the large network of the
# run v003: the best move is the same in 100% of 39 positions with these two kept, 95% without; they weigh 1.5M parameters of 144M).
# Set by `slim_from` and `load_slim`.
DEFAULT_KEEP32 = frozenset({"head", "move_in"})
KEEP32: set[str] = set()


def _quantized(linear: nn.Linear, kind: str = "") -> nn.Module:
    """A linear layer with 8 bit weights (a scale for each output) and 8 bit activations measured at each call; a kind that is in KEEP32 stays as it is."""
    if kind in KEEP32:
        return linear
    linear.qconfig = torch.ao.quantization.per_channel_dynamic_qconfig  # type: ignore[assignment]
    return cast(nn.Module, QLinear.from_float(linear))  # type: ignore[no-untyped-call]


def _linear(weight: torch.Tensor, bias: torch.Tensor | None) -> nn.Linear:
    out, inn = weight.shape
    lin = nn.Linear(inn, out, bias=bias is not None)
    with torch.no_grad():
        lin.weight.copy_(weight)
        if bias is not None:
            lin.bias.copy_(bias)
    return lin


def _skeleton(inn: int, out: int, kind: str = "") -> nn.Module:
    """A quantized linear layer with nothing in it yet (to be filled by `load_state_dict`)."""
    if kind in KEEP32:
        return nn.Linear(inn, out)
    return cast(nn.Module, QLinear(inn, out))  # zeros of the right size, with no 32 bit copy of the matrix on the way


class SlimAttention(nn.Module):
    def __init__(self, d: int, heads: int) -> None:
        super().__init__()
        self.heads, self.d = heads, d
        self.q, self.k, self.v, self.out = (_skeleton(d, d, kind) for kind in ('q', 'k', 'v', 'out'))

    def forward(self, x: torch.Tensor, memory: torch.Tensor, allow: torch.Tensor) -> torch.Tensor:
        """`allow` [B, 1, 1, S] is True where a key may be looked at."""
        b, t, d = x.shape
        s = memory.shape[1]
        h = self.heads

        def split(y: torch.Tensor, n: int) -> torch.Tensor:
            return y.view(b, n, h, d // h).transpose(1, 2)

        a = F.scaled_dot_product_attention(split(self.q(x), t), split(self.k(memory), s), split(self.v(memory), s), attn_mask=allow)
        return cast(torch.Tensor, self.out(a.transpose(1, 2).reshape(b, t, d)))


class SlimFeed(nn.Module):
    def __init__(self, d: int, ffn: int) -> None:
        super().__init__()
        self.up, self.down = _skeleton(d, ffn, 'up'), _skeleton(ffn, d, 'down')

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.down(F.gelu(self.up(x))))


class SlimEncoderLayer(nn.Module):
    def __init__(self, c: NetConfig) -> None:
        super().__init__()
        self.norm1, self.norm2 = nn.LayerNorm(c.d_model), nn.LayerNorm(c.d_model)
        self.attn, self.feed = SlimAttention(c.d_model, c.heads), SlimFeed(c.d_model, c.ffn)

    def forward(self, x: torch.Tensor, allow: torch.Tensor) -> torch.Tensor:
        y = self.norm1(x)
        x = x + self.attn(y, y, allow)
        return cast(torch.Tensor, x + self.feed(self.norm2(x)))


class SlimDecoderLayer(nn.Module):
    def __init__(self, c: NetConfig) -> None:
        super().__init__()
        self.norm1, self.norm2, self.norm3 = (nn.LayerNorm(c.d_model) for _ in range(3))
        self.self_attn, self.cross = SlimAttention(c.d_model, c.heads), SlimAttention(c.d_model, c.heads)
        self.feed = SlimFeed(c.d_model, c.ffn)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, self_allow: torch.Tensor, memory_allow: torch.Tensor) -> torch.Tensor:
        y = self.norm1(x)
        x = x + self.self_attn(y, y, self_allow)
        x = x + self.cross(self.norm2(x), memory, memory_allow)
        return cast(torch.Tensor, x + self.feed(self.norm3(x)))


class SlimNet(nn.Module):
    """`PolicyNet` with 8 bit matrices: the same `forward(batch) -> (logits, values)`."""

    def __init__(self, cfg: NetConfig) -> None:
        super().__init__()
        self.cfg = cfg
        d = cfg.d_model
        self.feat = nn.Parameter(torch.zeros(cfg.obs_dim, d, dtype=torch.float16), requires_grad=False)
        self.kind = nn.Embedding(cfg.entity_types, d)
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.norm_in = nn.LayerNorm(d)
        self.encoder = nn.ModuleList(SlimEncoderLayer(cfg) for _ in range(cfg.layers))
        self.norm_out = nn.LayerNorm(d)
        self.tok = nn.Embedding(cfg.token_buckets, d, padding_idx=0)
        self.num = nn.Linear(cfg.move_num, d)
        self.move_in1, self.move_in2 = _skeleton(d, d, 'move_in'), _skeleton(d, d, 'move_in')
        self.decoder = nn.ModuleList(SlimDecoderLayer(cfg) for _ in range(cfg.move_layers))
        self.score_norm, self.value_norm = nn.LayerNorm(d), nn.LayerNorm(d)
        self.score1, self.score2 = _skeleton(d, d // 2, 'head'), nn.Linear(d // 2, 1)
        self.value1, self.value2 = _skeleton(d, d // 2, 'head'), nn.Linear(d // 2, 1)
        self.eval()

    def bag(self, batch: Batch) -> torch.Tensor:
        """The sum of the (weighted) rows of the feature table of each entity: only the rows that the position uses are read."""
        rows = self.feat[batch.idx].float() * batch.val.float().unsqueeze(1)
        n = batch.offsets.shape[0]
        ends = torch.cat([batch.offsets[1:], batch.offsets.new_tensor([batch.idx.shape[0]])])
        owner = torch.repeat_interleave(torch.arange(n, device=rows.device), ends - batch.offsets)
        return torch.zeros(n, rows.shape[1], device=rows.device).index_add_(0, owner, rows)

    @torch.no_grad()
    def forward(self, batch: Batch) -> tuple[torch.Tensor, torch.Tensor]:
        tok = self.norm_in(self.bag(batch) + self.kind(batch.kinds))
        b, t = batch.mask.shape
        x = tok.new_zeros(b, t, tok.shape[-1])
        x[batch.sample, batch.pos] = tok
        x = torch.cat([self.cls.expand(b, -1, -1), x], dim=1)
        pad = torch.cat([torch.zeros(b, 1, dtype=torch.bool, device=x.device), ~batch.mask], dim=1)
        allow = (~pad)[:, None, None, :]
        for layer in self.encoder:
            x = layer(x, allow)
        memory = self.norm_out(x)
        e = self.tok(batch.toks).sum(dim=2)
        q = self.move_in2(F.gelu(self.move_in1(e + self.num(batch.nums))))
        move_allow = batch.move_mask[:, None, None, :]
        for dec in self.decoder:
            q = dec(q, memory, move_allow, allow)
        logits = self.score2(F.gelu(self.score1(self.score_norm(q)))).squeeze(-1).float().masked_fill(~batch.move_mask, -1e9)
        value = self.value2(F.gelu(self.value1(self.value_norm(memory[:, 0])))).squeeze(-1).float()
        return logits, value


def slim_from(net: PolicyNet, keep32: set[str] | None = None) -> SlimNet:
    """The small copy of a trained network (the quantization is done here, a layer at a time). `keep32` names the kinds of layers that stay in 32 bits."""
    KEEP32.clear()
    KEEP32.update(DEFAULT_KEEP32 if keep32 is None else keep32)
    cfg = net.cfg
    d = cfg.d_model
    s = SlimNet(cfg)
    sd = {k: v.detach() for k, v in net.state_dict().items()}
    with torch.no_grad():
        s.feat.copy_(sd["feat.weight"].half())
        s.kind.weight.copy_(sd["kind.weight"])
        s.cls.copy_(sd["cls"])
        s.norm_in.load_state_dict({"weight": sd["norm_in.weight"], "bias": sd["norm_in.bias"]})
        s.norm_out.load_state_dict({"weight": sd["norm_out.weight"], "bias": sd["norm_out.bias"]})
        s.tok.weight.copy_(sd["tok.weight"])
        s.num.load_state_dict({"weight": sd["num.weight"], "bias": sd["num.bias"]})

    def attn(dst: SlimAttention, prefix: str) -> None:
        w, bias = sd[f"{prefix}.in_proj_weight"], sd[f"{prefix}.in_proj_bias"]
        for k, name in enumerate(("q", "k", "v")):
            setattr(dst, name, _quantized(_linear(w[k * d : (k + 1) * d], bias[k * d : (k + 1) * d]), name))
        dst.out = _quantized(_linear(sd[f"{prefix}.out_proj.weight"], sd[f"{prefix}.out_proj.bias"]), "out")

    def norm(dst: nn.LayerNorm, prefix: str) -> None:
        dst.load_state_dict({"weight": sd[f"{prefix}.weight"], "bias": sd[f"{prefix}.bias"]})

    def feed(dst: SlimFeed, prefix: str) -> None:
        dst.up = _quantized(_linear(sd[f"{prefix}.linear1.weight"], sd[f"{prefix}.linear1.bias"]), "up")
        dst.down = _quantized(_linear(sd[f"{prefix}.linear2.weight"], sd[f"{prefix}.linear2.bias"]), "down")

    for i, layer_ in enumerate(s.encoder):
        layer = cast(SlimEncoderLayer, layer_)
        p = f"encoder.layers.{i}"
        attn(layer.attn, f"{p}.self_attn")
        feed(layer.feed, p)
        norm(layer.norm1, f"{p}.norm1")
        norm(layer.norm2, f"{p}.norm2")
    for i, dec_ in enumerate(s.decoder):
        dec = cast(SlimDecoderLayer, dec_)
        p = f"decoder.layers.{i}"
        attn(dec.self_attn, f"{p}.self_attn")
        attn(dec.cross, f"{p}.multihead_attn")
        feed(dec.feed, p)
        for k in (1, 2, 3):
            norm(getattr(dec, f"norm{k}"), f"{p}.norm{k}")
    s.move_in1 = _quantized(_linear(sd["move_in.0.weight"], sd["move_in.0.bias"]), "move_in")
    s.move_in2 = _quantized(_linear(sd["move_in.2.weight"], sd["move_in.2.bias"]), "move_in")
    for name, head in (("score", s.score_norm), ("value", s.value_norm)):
        norm(head, f"{name}.0")
        setattr(s, f"{name}1", _quantized(_linear(sd[f"{name}.1.weight"], sd[f"{name}.1.bias"]), "head"))
        getattr(s, f"{name}2").load_state_dict({"weight": sd[f"{name}.3.weight"], "bias": sd[f"{name}.3.bias"]})
    return s.eval()


def save_slim(net: SlimNet, path: str) -> None:
    from dataclasses import asdict

    torch.save({"slim": 1, "config": asdict(net.cfg), "keep32": sorted(KEEP32), "weights": net.state_dict()}, path)


def load_slim(path: str) -> SlimNet:
    """Read the small file: the quantized layers are rebuilt with the right sizes and filled from the file (which is read in place, not copied twice)."""
    saved: dict[str, Any] = torch.load(path, map_location="cpu", weights_only=False, mmap=True)
    KEEP32.clear()
    KEEP32.update(saved.get("keep32", []))
    net = SlimNet(NetConfig(**saved["config"]))
    net.load_state_dict(saved["weights"])
    return net.eval()


def is_slim(path: str) -> bool:
    return Path(path).name.endswith(".int8.pt")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("out", nargs="?", default="")
    ap.add_argument("--check", default="", help="a folder of games of people: compare the small copy with the original on positions of them")
    ap.add_argument("--positions", type=int, default=40)
    ap.add_argument(
        "--keep32",
        default=",".join(sorted(DEFAULT_KEEP32)),
        help="kinds of layers that stay in 32 bits, comma separated: q,k,v,out,up,down,move_in,head",
    )
    a = ap.parse_args()
    from .agent import net_from

    big = net_from(a.model, "cpu").eval()
    small = slim_from(big, {k for k in a.keep32.split(',') if k})
    if a.out:
        save_slim(small, a.out)
        print(f"wrote {a.out}: {Path(a.out).stat().st_size / 1e6:.0f} MB (the original is {Path(a.model).stat().st_size / 1e6:.0f} MB)")
    if a.check:
        from .slim_check import agreement

        print(agreement(big, small, Path(a.check), a.positions))


if __name__ == "__main__":
    main()
