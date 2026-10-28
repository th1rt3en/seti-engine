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


def test_the_win_head_learns_the_result_of_the_game() -> None:
    torch.manual_seed(0)
    data = Examples()
    for k in range(2):
        ex, _ = bundle_train.bot_game_examples({"kind": k % 2, "bot_a": "heuristic", "bot_b": "greedy", "seed": 700 + k})
        data.extend(ex)
    won = [v for v in data.value if v.win == 1.0][:6]
    lost = [v for v in data.value if v.win == 0.0][:6]
    assert won and lost, "a game of two bots has a winner and a loser"
    data.policy = data.policy[:64]
    data.value = won + lost  # a dozen positions: the head has to be able to fit them (a head that learns nothing stays at the 0.69 of a coin)
    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    rng = np.random.default_rng(0)
    device = torch.device("cpu")
    first = bundle_train.train_epoch(net, opt, data, device, rng, 64)
    for _ in range(70):  # the policy loss is large at first and the gradient is clipped: the head starts to move after a few dozen steps
        last = bundle_train.train_epoch(net, opt, data, device, rng, 64)
    assert first["win_loss"] > 0.5, "an untrained head is near the 0.69 of a coin"
    assert last["win_loss"] < first["win_loss"] - 0.1, (first, last)
    assert last["win_accuracy"] > 0.75


def test_positions_without_a_label_are_left_out_of_the_win_loss() -> None:
    data = small_data()
    for v in data.value:
        v.win = -1.0  # made before the win target (the buffer of an older run)
    data.policy = data.policy[:100]
    net = new_net("small")
    st = bundle_train.train_epoch(net, torch.optim.AdamW(net.parameters(), lr=3e-4), data, torch.device("cpu"), np.random.default_rng(0), 64)
    assert st["win_loss"] == 0.0 and st["value_rmse_points"] > 0
