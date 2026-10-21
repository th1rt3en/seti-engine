"""The bundle search (docs/AI-TURN-BUNDLES.md, stage B): complete legal turns, better than plain sampling, never reading the opponent's real hand.
Inference only."""

import random
from typing import Any

import numpy as np
import pytest
from seti_engine import engine
from seti_engine.models import GameState, Options
from seti_engine.projection import project, to_act

from seti_ai import arena, bots
from seti_ai.brains import HeuristicBrain, NetBrain
from seti_ai.bundle_search import BundleBot, BundleSearch, SearchConfig, determinize
from seti_ai.bundles import bundle_key
from seti_ai.knowledge import Knowledge


def turn_starts(options: Options, seed: int, want: int = 8, limit: int = 600) -> list[GameState]:
    """States at the start of a turn (nothing pending, the main action not taken yet), from a game played with random moves."""
    rng = random.Random(seed)
    state = engine.start(options).state
    out: list[GameState] = []
    last_key = None
    for _ in range(limit):
        moves = [m for m in engine.legal_moves(state) if m["type"] != "undo"]
        if not moves:
            break
        if state.phase == "play" and not state.pending and not state.main_done:
            key = (state.round, state.turn, state.current_player)
            if key != last_key and len(out) < want and state.players[state.current_player].energy + state.players[state.current_player].credits > 0:
                out.append(state.model_copy(deep=True))
                last_key = key
        state = engine.apply(state, rng.choice(moves)).state
    return out


def starts() -> list[GameState]:
    return turn_starts(Options(players=2, seed=11), 5) + turn_starts(Options(players=2, seed=12, expansion=True, organizations=True), 6, want=4)


@pytest.fixture(scope="module")
def states() -> list[GameState]:
    s = starts()
    assert len(s) >= 8
    return s


def replay(state: GameState, moves: list[dict[str, Any]]) -> GameState:
    for m in moves:
        assert m in engine.legal_moves(state), f"{m} is not legal"
        state = engine.apply(state, m).state
    return state


def test_determinize_draws_the_unseen_cards_again_and_keeps_the_seen_ones(states) -> None:  # type: ignore[no-untyped-def]
    state = states[3]
    me = state.current_player
    other = 1 - me
    opp = state.players[other]
    assert len(opp.hand) >= 2
    know = Knowledge()
    know.known[other] = [opp.hand[0]]  # one card of the opponent is known (it was taken from the display)
    seen: set[tuple[str, ...]] = set()
    for seed in range(8):
        d = determinize(state, me, know, random.Random(seed))
        assert len(d.players[other].hand) == len(opp.hand), "the opponent keeps as many cards"
        assert opp.hand[0] in d.players[other].hand, "a card that is known stays in the hand"
        assert d.players[me].hand == state.players[me].hand, "the seat's own hand is not changed"
        assert sorted(d.deck + d.players[other].hand) == sorted(state.deck + opp.hand), "no card is lost or made up"
        seen.add(tuple(d.players[other].hand))
    assert len(seen) > 1, "the hidden cards are not drawn again"


def test_the_search_never_reads_the_real_hand_of_the_opponent(states) -> None:  # type: ignore[no-untyped-def]
    """Two states that are the same to the seat (the unseen cards of the opponent and the deck are the same cards, in different places) give the same
    result."""
    state = states[4]
    me = state.current_player
    other = 1 - me
    swapped = state.model_copy(deep=True)
    n = min(2, len(swapped.players[other].hand), len(swapped.deck))
    assert n >= 1
    hand, deck = swapped.players[other].hand, swapped.deck
    hand[:n], deck[:n] = deck[:n], hand[:n]  # the opponent holds other cards of the unseen ones
    assert swapped.players[other].hand != state.players[other].hand
    search = BundleSearch(HeuristicBrain(), SearchConfig(samples=3, keep=1, neighbours=4, finalists=2, copies=2))
    a = search.search(state, me, [], None, random.Random(7))
    b = search.search(swapped, me, [], None, random.Random(7))
    assert a.best.moves == b.best.moves
    assert [c.score for c in a.candidates] == [c.score for c in b.candidates]


def test_the_best_bundle_is_a_whole_legal_turn_with_one_main_action(states) -> None:  # type: ignore[no-untyped-def]
    search = BundleSearch(HeuristicBrain(), SearchConfig(samples=4, keep=2, neighbours=6, finalists=3, copies=2))
    for i, state in enumerate(states):
        me = state.current_player
        result = search.search(state, me, [], None, random.Random(100 + i))
        best = result.best
        assert best.moves, "an empty bundle"
        assert result.start is not None
        end = replay(result.start, best.moves)  # every move legal, in order, on the copy that it was made on (on the real game a chance event can differ)
        classes = []
        s = result.start
        for m in best.moves:
            classes.append(next(c for mm, c in engine.legal_classified(s) if mm == m))
            s = engine.apply(s, m).state
        assert classes.count("main") == 1, classes
        assert "control" not in classes
        assert end.phase == "finished" or to_act(end) != me or bundle_key(end, me) != bundle_key(result.start, me), "the bundle did not end the turn"
        assert best.key in {c.key for c in result.candidates}


def test_the_neighbours_find_bundles_that_the_samples_did_not(states) -> None:  # type: ignore[no-untyped-def]
    """With the same samples, adding the neighbours can only add candidates, so the best score cannot be lower; over several turns it is higher in some."""
    base = SearchConfig(samples=4, keep=0, neighbours=0, finalists=1, copies=1)
    more = SearchConfig(samples=4, keep=2, neighbours=12, finalists=1, copies=1)
    better = 0
    for i, state in enumerate(states):
        me = state.current_player
        a = BundleSearch(HeuristicBrain(), base).search(state, me, [], None, random.Random(30 + i))
        b = BundleSearch(HeuristicBrain(), more).search(state, me, [], None, random.Random(30 + i))
        top_a, top_b = max(c.score for c in a.candidates), max(c.score for c in b.candidates)
        assert top_b >= top_a - 1e-9, (i, top_a, top_b)
        better += top_b > top_a + 1e-9
        origins = {c.origin for c in b.candidates}
        assert origins <= {"greedy", "sample", "add", "remove", "move"}
    assert better >= 1, "the neighbours never found a better bundle in these turns"


def test_the_bot_plays_whole_turns_in_a_game() -> None:
    bot = BundleBot(HeuristicBrain(), SearchConfig(samples=3, keep=1, neighbours=4, finalists=2, copies=2))
    other = bots.greedy()
    arena.MAX_STEPS, saved = 120, arena.MAX_STEPS
    try:
        res = arena.play_game([bot, other], 3, random.Random(3))
    finally:
        arena.MAX_STEPS = saved
    assert res.steps > 60
    assert bot.searches >= 3
    assert bot.last is not None and bot.last.best.moves
    # it asked for a search about once per turn, so a search planned several moves
    assert res.steps / 2 / bot.searches > 1.2


def test_the_net_brain_scores_moves_and_reads_a_position_with_nobody_to_act(states) -> None:  # type: ignore[no-untyped-def]
    from seti_ai.agent import LocalNet, new_net

    brain = NetBrain(LocalNet(new_net("small")))
    state = states[0]
    me = state.current_player
    view = project(state, me, previews=False)
    lg = brain.logits(view, [], None)
    assert lg.shape == (len(view.legal),) and np.isfinite(lg).any()
    assert all(lg[i] <= -1e8 for i, c in enumerate(view.classes) if c == "control")
    after = replay(state, [next(m for m, c in engine.legal_classified(state) if c == "main" and m["type"] == "pass")])
    while to_act(after) == me and engine.legal_moves(after):
        usable = [m for m in engine.legal_moves(after) if m["type"] != "undo"]
        after = engine.apply(after, usable[0]).state
    assert isinstance(brain.value(after, me, [], None), float)
    result = BundleSearch(brain, SearchConfig(samples=2, keep=1, neighbours=3, finalists=2, copies=2)).search(state, me, [], None, random.Random(1))
    assert result.best.moves
