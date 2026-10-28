"""Pause and resume of a training run (checkpoint.py): what is saved is what is restored, and a pause is heard."""

import random
from pathlib import Path

import numpy as np
import pytest
import torch

from seti_ai import checkpoint
from seti_ai.agent import new_net


def test_a_checkpoint_gives_back_the_network_the_optimizer_and_the_random_generators(tmp_path: Path) -> None:
    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
    loss = sum(p.sum() for p in net.parameters()) * 1e-3
    loss.backward()  # type: ignore[no-untyped-call]
    opt.step()  # the optimizer has moments now
    random.seed(5)
    np.random.seed(5)
    torch.manual_seed(5)
    checkpoint.save(tmp_path, net, opt, {"iteration": 7, "best": 61.5, "parent": "bc-base"})
    after = (random.random(), float(np.random.rand()), float(torch.rand(1)))
    net2, opt_state, meta, rng = checkpoint.load(tmp_path, torch.device("cpu"))
    assert meta == {"iteration": 7, "best": 61.5, "parent": "bc-base"}
    assert all(torch.equal(a, b) for a, b in zip(net.state_dict().values(), net2.state_dict().values(), strict=True))
    opt2 = torch.optim.AdamW(net2.parameters(), lr=1e-4)
    opt2.load_state_dict(opt_state)
    assert len(opt2.state_dict()["state"]) == len(opt.state_dict()["state"]) > 0
    checkpoint.restore_rng(rng)
    assert (random.random(), float(np.random.rand()), float(torch.rand(1))) == after  # the games that follow are the same as if there had been no pause
    assert "round 7" in checkpoint.status(tmp_path) and not list(tmp_path.glob("checkpoint/*.tmp"))


def test_a_pause_is_asked_for_with_a_file_and_cleared(tmp_path: Path) -> None:
    assert not checkpoint.pause_requested(tmp_path)
    checkpoint.request_pause(tmp_path)
    assert checkpoint.pause_requested(tmp_path) and (tmp_path / "PAUSE").exists()
    checkpoint.clear_pause(tmp_path)
    assert not checkpoint.pause_requested(tmp_path)
    assert checkpoint.status(tmp_path) == "no checkpoint"


def test_weights_from_before_the_win_head_still_load_and_other_gaps_do_not(tmp_path: Path) -> None:
    from seti_ai.agent import load_weights

    net = new_net("small")
    old = {k: v.clone() for k, v in net.state_dict().items() if not k.startswith("win.")}
    other = new_net("small")
    before = {k: v.clone() for k, v in other.state_dict().items() if k.startswith("win.")}
    load_weights(other, old)
    assert all(torch.equal(v, other.state_dict()[k]) for k, v in before.items()), "the head that the file does not have keeps its values"
    assert torch.equal(other.state_dict()["feat.weight"], net.state_dict()["feat.weight"])
    broken = {k: v for k, v in old.items() if k != "feat.weight"}
    with pytest.raises(RuntimeError):
        load_weights(new_net("small"), broken)


def test_the_state_of_an_optimizer_without_the_new_head_is_dropped_not_fatal() -> None:
    from seti_ai.checkpoint import restore_optimizer

    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    ok = torch.optim.AdamW(net.parameters(), lr=1e-3)
    assert restore_optimizer(ok, opt.state_dict())
    short = torch.optim.AdamW([p for k, p in net.named_parameters() if not k.startswith("win.")], lr=1e-3)
    assert not restore_optimizer(torch.optim.AdamW(net.parameters(), lr=1e-3), short.state_dict())
