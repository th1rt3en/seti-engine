"""How close is the small copy of a network (slim.py) to the original? Measured on turn starts of games of people, with the real views of the engine."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
from seti_engine.projection import project

from . import expert, features
from .agent import LocalNet, PolicyNet
from .slim import SlimNet


def agreement(big: PolicyNet, small: SlimNet, people: Path, positions: int) -> str:
    found, _ = expert.sample_positions(people, positions, 1)
    a, b = LocalNet(big), LocalNet(small)
    same_best = 0
    n = 0
    logit_err: list[float] = []
    value_err: list[float] = []
    rank_corr: list[float] = []
    t_big = t_small = 0.0
    for pos in found:
        view = project(pos.state, pos.seat, previews=False)
        if not view.legal:
            continue
        keep = [i for i, c in enumerate(view.classes) if c != "control"] or list(range(len(view.legal)))
        tokens = features.encode_view(view, pos.history, pos.knowledge)
        toks, nums = features.encode_moves(view, keep)
        t = time.time()
        la, va = a.evaluate(tokens, toks, nums)
        t_big += time.time() - t
        t = time.time()
        lb, vb = b.evaluate(tokens, toks, nums)
        t_small += time.time() - t
        n += 1
        same_best += int(np.argmax(la) == np.argmax(lb))
        logit_err.append(float(np.abs(la - lb).max()))
        value_err.append(abs(va - vb))
        if len(la) > 2:
            rank_corr.append(float(np.corrcoef(la, lb)[0, 1]))
    return (
        f"{n} positions: the best move is the same in {same_best} ({same_best / max(n, 1):.0%}); the logits differ by {np.mean(logit_err):.3f} on average "
        f"(at most {np.max(logit_err):.3f}), their correlation is {np.mean(rank_corr):.4f}; the value differs by {np.mean(value_err):.4f} on average "
        f"(at most {np.max(value_err):.4f}); time of the original {t_big:.1f}s, of the small copy {t_small:.1f}s"
    )


__all__ = ["agreement"]
_ = torch
