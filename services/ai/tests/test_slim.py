"""The 8 bit copy of a network (slim.py) plays like the original."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from seti_engine import engine
from seti_engine.models import Options
from seti_engine.projection import project

from seti_ai import features
from seti_ai.agent import LocalNet, new_net
from seti_ai.slim import is_slim, load_slim, save_slim, slim_from


def evaluation(net, seed: int) -> tuple[np.ndarray, float]:  # type: ignore[no-untyped-def]
    state = engine.start(Options(players=2, seed=seed)).state
    view = project(state, state.current_player, previews=False)
    tokens = features.encode_view(view, [], None)
    toks, nums = features.encode_moves(view)
    return LocalNet(net).evaluate(tokens, toks, nums)


def test_the_small_copy_gives_the_answers_of_the_original() -> None:
    torch.manual_seed(0)
    net = new_net("small").eval()
    small = slim_from(net)
    for seed in (1, 2, 3):
        la, va = evaluation(net, seed)
        lb, vb = evaluation(small, seed)
        assert la.shape == lb.shape
        assert float(np.abs(la - lb).max()) < 0.15 * max(float(np.abs(la).max()), 1.0)  # the 8 bit weights change a logit by a few percent at most
        assert abs(va - vb) < 0.1
        assert np.corrcoef(la, lb)[0, 1] > 0.98


def test_the_small_copy_is_saved_and_read_back_the_same(tmp_path: Path) -> None:
    torch.manual_seed(1)
    net = new_net("small").eval()
    small = slim_from(net)
    path = tmp_path / "model.int8.pt"
    save_slim(small, str(path))
    assert is_slim(str(path)) and path.stat().st_size < 0.5 * sum(p.numel() * 4 for p in net.parameters())  # well under half of the original
    back = load_slim(str(path))
    la, va = evaluation(small, 5)
    lb, vb = evaluation(back, 5)
    assert np.allclose(la, lb, atol=1e-5) and abs(va - vb) < 1e-5
