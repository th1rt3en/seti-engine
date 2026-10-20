"""The offline bots, the agent and the network: they only choose among the legal moves, and the same seed gives the same game."""

import random

import numpy as np
import torch
from seti_engine import engine
from seti_engine.models import Options
from seti_engine.projection import project, to_act

from seti_ai import arena, bots, features
from seti_ai.agent import PRESETS, LocalNet, NNAgent, PolicyNet, collate, new_net
from seti_ai.train import gae, rewards_of


def views(seed: int = 3, n: int = 60):
    rnd = random.Random(seed)
    r = engine.start(Options(players=2, seed=seed))
    for _ in range(n):
        if not r.legal:
            break
        seat = to_act(r.state)
        yield r.state, project(r.state, seat, previews=False)
        r = engine.apply(r.state, rnd.choice(r.legal))


def test_the_move_features_have_a_fixed_shape() -> None:
    for _state, view in views():
        toks, nums = features.encode_moves(view)
        assert toks.shape == (len(view.legal), features.MAX_TOKENS) and nums.shape == (len(view.legal), features.MOVE_NUM)
        assert toks.max() < features.TOKEN_BUCKETS and np.isfinite(nums).all()


def test_every_bot_and_the_agent_choose_a_legal_move_and_finish_games() -> None:
    agent = NNAgent(LocalNet(new_net("small")), explore=True)
    for player in (bots.RandomBot(), bots.greedy(), bots.heuristic(), agent):
        res = arena.play_game([player, bots.RandomBot()], 4)
        assert res.finished and len(res.scores) == 2
    for state, view in views(7, 30):
        for bot in (bots.RandomBot(), bots.greedy(), agent):
            i = bot.act(state, view, random.Random(1))
            assert 0 <= i < len(view.legal) and view.legal[i]["type"] != "undo" or len(view.legal) == 1


def test_the_same_seed_gives_the_same_game() -> None:
    a = arena.play_game([bots.RandomBot(), bots.RandomBot()], 9, random.Random(1))
    b = arena.play_game([bots.RandomBot(), bots.RandomBot()], 9, random.Random(1))
    assert a.scores == b.scores and a.steps == b.steps


def test_the_rewards_of_a_seat_add_up_to_the_score_it_gains_and_an_unfinished_game_is_penalised() -> None:
    agent = NNAgent(LocalNet(new_net("small")), explore=True, record=True)
    res = arena.play_game([agent, bots.RandomBot()], 2, random.Random(2))
    steps = [s for s in agent.steps if s.seat == 0]
    r = rewards_of(steps, res.scores[0])
    assert abs(float(r.sum()) * 20 + steps[0].board_score - res.scores[0]) < 1e-3  # what the seat gains from its first decision to the end
    assert abs(float(rewards_of(steps, res.scores[0], finished=False).sum()) - float(r.sum()) + 1.0) < 1e-6
    adv, ret = gae(np.array([s.value for s in steps], dtype=np.float32), r)
    assert adv.shape == r.shape and np.isfinite(ret).all()


def test_the_network_gives_an_absent_move_no_chance_and_a_batch_of_different_sizes_works() -> None:
    net = new_net("small").eval()
    items = []
    for _state, view in views(5, 8):
        items.append((features.encode_view(view), *features.encode_moves(view)))
    batch = collate(items, torch.device("cpu"))
    with torch.no_grad():
        logits, values = net(batch)
    assert logits.shape[0] == len(items) and values.shape == (len(items),)
    for i, it in enumerate(items):
        n = it[1].shape[0]
        assert torch.softmax(logits[i], dim=0)[n:].sum() == 0
        one, _ = net(collate([it], torch.device("cpu")))
        assert torch.allclose(one[0, :n], logits[i, :n], atol=1e-4)  # the padding of the batch changes nothing


def test_the_presets_have_the_sizes_that_the_plan_says() -> None:
    sizes = {name: sum(p.numel() for p in PolicyNet(cfg).parameters()) / 1e6 for name, cfg in PRESETS.items()}
    assert 5 < sizes["small"] < 30 and 30 < sizes["base"] < 80 and 80 < sizes["large"] < 160
