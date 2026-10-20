"""How fast each size of the network is on this machine: a forward and backward pass on a batch of random positions, and the answer to a batch of requests.
It does not train anything: the weights are new and thrown away. It is only a measurement, to choose a size from what this GPU can do.

    .venv/Scripts/python.exe -m seti_ai.benchmark [--presets small base large xlarge]
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import torch

from . import features
from .agent import PRESETS, PolicyNet, collate


def fake(rng: np.random.Generator, tokens: int = 65, per_token: int = 14, moves: int = 40) -> tuple[features.Tokens, np.ndarray, np.ndarray]:
    kinds = rng.integers(0, features.ENTITY_TYPES, tokens).astype(np.int32)
    offsets = (np.arange(tokens + 1) * per_token).astype(np.int32)
    idx = rng.integers(0, features.OBS_DIM, tokens * per_token).astype(np.int32)
    val = rng.random(tokens * per_token).astype(np.float32)
    toks = rng.integers(1, features.TOKEN_BUCKETS, (moves, features.MAX_TOKENS)).astype(np.int32)
    nums = rng.random((moves, features.MOVE_NUM)).astype(np.float32)
    return features.Tokens(kinds, offsets, idx, val), toks, nums


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presets", nargs="*", default=list(PRESETS))
    ap.add_argument("--batch", type=int, default=64)
    a = ap.parse_args()
    dev = torch.device("cuda")
    rng = np.random.default_rng(0)
    for name in a.presets:
        net = PolicyNet(PRESETS[name]).to(dev)
        n = sum(p.numel() for p in net.parameters())
        opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
        batch = collate([fake(rng) for _ in range(a.batch)], dev)
        torch.cuda.reset_peak_memory_stats()
        for mode in ("train", "infer"):
            for k in range(8):
                if k == 3:
                    torch.cuda.synchronize()
                    t = time.time()
                if mode == "train":
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        logits, value = net(batch)
                    loss = logits.float().logsumexp(dim=1).mean() + value.float().mean()
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
                else:
                    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                        net(batch)
            torch.cuda.synchronize()
            per = (time.time() - t) / 5
            if mode == "train":
                train_ms = per * 1000
            else:
                infer_ms = per * 1000
        peak = torch.cuda.max_memory_allocated() / 1e9
        print(
            f"{name}: {n / 1e6:.0f}M parameters; a batch of {a.batch}: update {train_ms:.0f} ms, answer {infer_ms:.0f} ms; peak GPU memory {peak:.1f} GB",
            flush=True,
        )
        del net, opt, batch
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
