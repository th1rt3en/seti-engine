"""The offline bots, the features and the agent: they only choose among the legal moves, and the same view gives the same numbers."""

import random

import numpy as np
import torch
from seti_engine import engine
from seti_engine.models import Options
from seti_engine.projection import project, to_act

from seti_ai import arena, bots, features
from seti_ai.agent import NNAgent, new_net
from seti_ai.train import gae, rewards_of


def views(seed: int = 3, n: int = 60):
    rnd = random.Random(seed)
    r = engine.start(Options(players=2, seed=seed))
    for _ in range(n):
        if not r.legal:
            break
        seat = to_act(r.state)
        yield r.state, project(r.state, seat)
        r = engine.apply(r.state, rnd.choice(r.legal))


def test_the_features_have_a_fixed_size_and_do_not_change() -> None:
    sizes = set()
    for _state, view in views():
        a, b = features.encode_view(view), features.encode_view(view)
        assert np.array_equal(a, b) and np.isfinite(a).all()
        sizes.add(a.shape[0])
        toks, nums = features.encode_moves(view)
        assert toks.shape == (len(view.legal), features.MAX_TOKENS) and nums.shape == (len(view.legal), features.MOVE_NUM)
        assert toks.max() < features.TOKEN_BUCKETS
    assert sizes == {features.obs_size()}


def test_the_features_do_not_depend_on_what_the_seat_cannot_see() -> None:
    """Two games that differ only in the deck order give the same view numbers (the hidden part is hidden before the agent sees it)."""
    r = engine.start(Options(players=2, seed=5))
    s2 = r.state.model_copy(deep=True)
    s2.deck = list(reversed(s2.deck))
    seat = to_act(r.state)
    assert np.array_equal(features.encode_view(project(r.state, seat)), features.encode_view(project(s2, seat)))


def test_every_bot_and_the_agent_choose_a_legal_move_and_finish_games() -> None:
    agent = NNAgent(new_net(), explore=True)
    for player in (bots.RandomBot(), bots.greedy(), agent):
        res = arena.play_game([player, bots.RandomBot()], 4)
        assert res.finished and len(res.scores) == 2
    for state, view in views(7, 30):
        for bot in (bots.RandomBot(), bots.greedy(), agent):
            i = bot.act(state, view, random.Random(1))
            assert 0 <= i < len(view.legal)


def test_the_same_seed_gives_the_same_game() -> None:
    a = arena.play_game([bots.RandomBot(), bots.RandomBot()], 9, random.Random(1))
    b = arena.play_game([bots.RandomBot(), bots.RandomBot()], 9, random.Random(1))
    assert a.scores == b.scores and a.steps == b.steps


def test_the_rewards_of_a_seat_add_up_to_the_score_it_gains() -> None:
    agent = NNAgent(new_net(), explore=True, record=True)
    res = arena.play_game([agent, bots.RandomBot()], 2, random.Random(2))
    steps = [s for s in agent.steps if s.seat == 0]
    r = rewards_of(steps, res.scores[0])
    assert abs(float(r.sum()) * 20 + steps[0].board_score - res.scores[0]) < 1e-3  # what the seat gains from its first decision to the end
    adv, ret = gae(np.array([s.value for s in steps], dtype=np.float32), r)
    assert adv.shape == r.shape and np.isfinite(ret).all()


def test_the_network_never_gives_an_absent_move_any_chance() -> None:
    net = new_net()
    state, view = next(iter(views()))
    toks, nums = features.encode_moves(view)
    n = len(view.legal)
    pad = 5
    mask = torch.tensor([[True] * n + [False] * pad])
    logits, _ = net(
        torch.from_numpy(features.encode_view(view)).unsqueeze(0),
        torch.from_numpy(np.pad(toks, ((0, pad), (0, 0)))).long().unsqueeze(0),
        torch.from_numpy(np.pad(nums, ((0, pad), (0, 0)))).unsqueeze(0),
        mask,
    )
    assert torch.softmax(logits, dim=1)[0, n:].sum() == 0
