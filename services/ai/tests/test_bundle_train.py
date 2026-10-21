"""The training of the network at the level of bundles (bundle_train.py): a tiny run on the processor, to see that the pieces fit and that the network
learns."""

import numpy as np
import torch

from seti_ai import bundle_train
from seti_ai.agent import new_net
from seti_ai.bundle_data import Examples


def small_data() -> Examples:
    out = Examples()
    for k in range(4):
        ex, scores = bundle_train.bot_game_examples({"kind": k % 2, "bot_a": "heuristic", "bot_b": "greedy", "seed": 700 + k})
        assert len(scores) == 2
        out.extend(ex)
    return out


def test_a_game_of_bots_gives_examples() -> None:
    ex, scores = bundle_train.bot_game_examples({"kind": 0, "bot_a": "heuristic", "bot_b": "heuristic", "seed": 9})
    assert ex.finished and len(ex.policy) > 100 and len(ex.value) > 10 and ex.bundles > 10
    assert all(p.action < p.toks.shape[0] for p in ex.policy)


def test_a_few_epochs_on_a_few_games_lower_the_losses() -> None:
    torch.manual_seed(0)
    data = small_data()
    data.policy = data.policy[:600]  # a few hundred choices are enough to see the loss go down
    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4)
    rng = np.random.default_rng(0)
    device = torch.device("cpu")
    first = bundle_train.train_epoch(net, opt, data, device, rng, 64)
    for _ in range(4):
        last = bundle_train.train_epoch(net, opt, data, device, rng, 64)
    assert np.isfinite(list(first.values())).all() and np.isfinite(list(last.values())).all()
    assert last["policy_loss"] < first["policy_loss"] - 0.05, (first, last)
    assert last["accuracy"] > first["accuracy"]
    assert last["value_rmse_points"] < first["value_rmse_points"], (first, last)


def test_the_network_plays_against_a_bot_after_training_on_the_processor() -> None:
    net = new_net("small")
    out = bundle_train.evaluate_vs_bots(net, 2, torch.device("cpu"), opponents=("random",))
    assert out["random"]["games"] == 2 and out["random"]["agent_score"] >= 0
