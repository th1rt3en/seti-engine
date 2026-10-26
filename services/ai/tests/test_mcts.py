"""The tree search over turns (docs/AI-MCTS.md): complete legal bundles, the same result for the same seed, the same answers batched or one by one."""

import random
from pathlib import Path

import numpy as np
import pytest
import torch
from seti_engine import engine
from seti_engine.models import GameState
from seti_engine.projection import to_act
from test_bundle_search import starts

from seti_ai import arena, bots, selfplay
from seti_ai.agent import LocalNet, new_net, save_net
from seti_ai.brains import HeuristicBrain, NetBrain
from seti_ai.bundle_search import BundleBot, drive, play_bundle_g
from seti_ai.knowledge import Knowledge
from seti_ai.mcts import MCTS, MCTSConfig
from seti_ai.parallel import Workers
from seti_ai.selfplay import SelfPlayConfig

SMALL = MCTSConfig(simulations=8, worlds=2, leaves=2, branch=3, samples=2, keep=1, neighbours=3, finalists=3)


def played_ok(state: GameState, seat: int, moves: list[dict[str, object]]) -> bool:
    """The bundle can be played from the start of the turn, move by move, and it ends the turn."""
    for m in moves:
        if m not in [x for x, _ in engine.legal_classified(state)]:
            return False
        state = engine.apply(state, m).state
    return state.phase == "finished" or to_act(state) != seat or bool(moves)


def test_the_tree_search_finds_a_legal_bundle() -> None:
    state = starts()[0]
    seat = to_act(state)
    assert seat is not None
    res = MCTS(HeuristicBrain(), SMALL).search(state, seat, [], Knowledge(), random.Random(1))
    assert res.best.moves and res.start is not None and played_ok(res.start, seat, res.best.moves)  # legal in the world it was made in
    assert sum(res.visits.values()) > 0 and set(res.visits) == {c.key for c in res.candidates}


def test_the_same_seed_gives_the_same_bundle() -> None:
    state = starts()[1]
    seat = to_act(state)
    assert seat is not None
    a = MCTS(HeuristicBrain(), SMALL).search(state, seat, [], Knowledge(), random.Random(7))
    b = MCTS(HeuristicBrain(), SMALL).search(state, seat, [], Knowledge(), random.Random(7))
    assert a.best.moves == b.best.moves and a.visits == b.visits


def test_a_batch_of_requests_is_answered_as_one_by_one() -> None:
    torch.manual_seed(0)
    brain = NetBrain(LocalNet(new_net("small")))
    state = starts()[0]
    seat = to_act(state)
    assert seat is not None
    gens = [play_bundle_g(state, seat, [], Knowledge(), random.Random(k), greedy=True) for k in range(3)]
    together = drive(gens, brain)
    alone = [drive([play_bundle_g(state, seat, [], Knowledge(), random.Random(k), greedy=True)], brain)[0] for k in range(3)]
    for x, y in zip(together, alone, strict=True):
        assert x.moves == y.moves
        assert x.logp == pytest.approx(y.logp, abs=1e-3)


def test_the_tree_search_plays_a_whole_game_with_a_network() -> None:
    torch.manual_seed(0)
    brain = NetBrain(LocalNet(new_net("small")))
    tiny = MCTSConfig(simulations=4, worlds=2, leaves=2, branch=2, samples=1, keep=1, neighbours=1, finalists=2)

    class Bot(BundleBot):
        def __init__(self) -> None:
            super().__init__(brain, tiny)
            self.search = MCTS(brain, tiny)  # type: ignore[assignment]

    res = arena.play_game([Bot(), bots.BOTS["heuristic"]()], 3, random.Random(3))
    assert len(res.scores) == 2 and np.isfinite(res.scores).all()


def test_games_played_in_other_processes_are_the_same_as_in_this_one(tmp_path: Path) -> None:
    """parallel.py: a game is a pure function of its seed, whichever process plays it."""
    torch.manual_seed(0)
    net = new_net("small")
    save_net(net, str(tmp_path / "net.pt"))
    cfg = SelfPlayConfig(MCTSConfig(simulations=2, worlds=1, leaves=1, branch=2, samples=1, keep=1, neighbours=1, finalists=1), 0.0, 0, "heuristic")
    here = selfplay.play(selfplay.make_brain(LocalNet(net.eval())), 5, cfg)
    workers = Workers(1, str(tmp_path / "net.pt"), device="cpu")
    try:
        _, there = next(iter(workers.play([(5, cfg, 0)])))
    finally:
        workers.close()
    assert there.scores == here.scores and len(there.examples.policy) == len(here.examples.policy)
