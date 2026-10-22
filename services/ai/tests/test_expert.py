"""Learning from games of people with the bundle search (expert.py, selfplay.py, docs/AI-TURN-BUNDLES.md section 13). Inference only; the "people" are
games of bots, which is the same thing to the code: a log of turns."""

import json
import random
from pathlib import Path
from typing import Any

import pytest
from seti_engine import engine
from seti_engine.models import GameState, Options
from seti_engine.projection import project, to_act
from test_bundle_search import turn_starts

from seti_ai import arena, bots, dataset, expert, selfplay
from seti_ai.brains import HeuristicBrain
from seti_ai.bundle_search import BundleSearch, SearchConfig
from seti_ai.bundles import bundles_of_game

FAST = SearchConfig(samples=3, keep=1, neighbours=4, finalists=2, copies=2)


@pytest.fixture(scope="module")
def game() -> tuple[Options, list[dict[str, Any]]]:
    """A finished game of two heuristic bots: its log plays the part of the log of a game of people."""
    res = arena.play_game([bots.heuristic(), bots.heuristic()], 21, random.Random(21))
    assert res.finished
    return Options(players=2, seed=21), res.actions


@pytest.fixture(scope="module")
def states() -> list[GameState]:
    out = turn_starts(Options(players=2, seed=11), 5)
    assert len(out) >= 6
    return out


def test_the_turn_of_a_person_is_offered_as_a_candidate_and_scored_like_any_other(states: list[GameState]) -> None:
    state = states[2]
    me = state.current_player
    rich = BundleSearch(HeuristicBrain(), SearchConfig(samples=8, keep=2, neighbours=12, finalists=3, copies=1)).search(state, me, [], None, random.Random(3))
    offered = rich.best.moves
    search = BundleSearch(HeuristicBrain(), SearchConfig(samples=0, keep=0, neighbours=0, finalists=2, copies=1))
    got = search.search(state, me, [], None, random.Random(4), offered=[offered])
    mine = next(c for c in got.candidates if c.key == json.dumps(offered, sort_keys=True))
    assert mine.origin in ("offered", "greedy")  # the greedy rollout may have found the same bundle first
    assert abs(mine.score - rich.best.score) < 1e-6 or mine.score <= rich.best.score + 1e-6
    assert got.best.moves  # and the search returns a whole bundle as before


def test_an_offered_bundle_that_cannot_be_played_here_is_dropped(states: list[GameState]) -> None:
    state = states[1]
    me = state.current_player
    nonsense: list[dict[str, Any]] = [{"type": "place_data"}, {"type": "scan_earth", "sector": 99}]
    search = BundleSearch(HeuristicBrain(), FAST)
    got = search.search(state, me, [], None, random.Random(1), offered=[nonsense, []])
    assert json.dumps(nonsense, sort_keys=True) not in {c.key for c in got.candidates}
    assert got.best.moves


def test_offering_bundles_cannot_lower_the_best_score_of_the_same_samples(states: list[GameState]) -> None:
    """Without neighbours the candidates of the same samples are all there, so one more candidate can only raise the best score."""
    cfg = SearchConfig(samples=4, keep=0, neighbours=0, finalists=1, copies=1)
    for i, state in enumerate(states[:4]):
        me = state.current_player
        extra = BundleSearch(HeuristicBrain(), SearchConfig(samples=6, keep=1, neighbours=8, finalists=1, copies=1)).search(
            state, me, [], None, random.Random(90 + i)
        )
        a = BundleSearch(HeuristicBrain(), cfg).search(state, me, [], None, random.Random(30 + i))
        b = BundleSearch(HeuristicBrain(), cfg).search(state, me, [], None, random.Random(30 + i), offered=[extra.best.moves])
        assert max(c.score for c in b.candidates) >= max(c.score for c in a.candidates) - 1e-9


def test_the_played_bundle_is_the_best_one_unless_the_search_explores(states: list[GameState]) -> None:
    state = states[3]
    me = state.current_player
    cold = BundleSearch(HeuristicBrain(), SearchConfig(samples=6, keep=2, neighbours=8, finalists=4, copies=1)).search(state, me, [], None, random.Random(5))
    assert cold.played is not None and cold.played.key == cold.best.key
    hot_cfg = SearchConfig(samples=6, keep=2, neighbours=8, finalists=4, copies=1, pick_temperature=1e6)  # all finalists as likely as each other
    played = {
        BundleSearch(HeuristicBrain(), hot_cfg).search(state, me, [], None, random.Random(100 + k)).played.key  # type: ignore[union-attr]
        for k in range(12)
    }
    assert len(played) > 1, "a high temperature never played anything but the best bundle"


def test_the_turns_of_a_game_are_the_positions_with_the_turn_that_was_played(game: tuple[Options, list[dict[str, Any]]]) -> None:
    options, actions = game
    bundles, _ = bundles_of_game(options, actions)
    complete = [b for b in bundles if b.kind == "turn" and b.complete]
    found = list(expert.positions(options, actions))
    assert len(found) == len(complete) > 20
    for pos, b in zip(found[:6], complete[:6], strict=False):
        assert pos.seat == b.seat and pos.human == [m.move for m in b.steps]
        state = pos.state
        assert to_act(state) == pos.seat
        for m in pos.human:  # the turn can be played from the state of the position, move after move
            assert m in engine.legal_moves(state)
            state = engine.apply(state, m).state
    few = list(expert.positions(options, actions, limit=5, rng=random.Random(2)))
    assert len(few) == 5 and {p.index for p in few} <= {p.index for p in found}
    assert not list(expert.positions(options, actions, skip_seats=frozenset({0, 1})))  # a seat of the model gives no human turn
    only_one = list(expert.positions(options, actions, skip_seats=frozenset({0})))
    assert only_one and all(p.seat == 1 for p in only_one)


def test_the_examples_of_a_bundle_are_one_per_move_and_name_the_move_that_was_played(game: tuple[Options, list[dict[str, Any]]]) -> None:
    options, actions = game
    pos = next(expert.positions(options, actions, limit=1, rng=random.Random(4)))
    ex = expert.bundle_examples(pos.state, pos.seat, pos.history, pos.knowledge, pos.human, weight=2.0)
    assert len(ex) == len(pos.human) and all(e.weight == 2.0 for e in ex)
    state = pos.state
    for e, m in zip(ex, pos.human, strict=True):
        view = project(state, pos.seat, previews=False)
        keep = [i for i, c in enumerate(view.classes) if c != "control"]
        assert view.legal[keep[e.action]] == m
        state = engine.apply(state, m).state
    # a bundle that stops being legal gives the examples up to there
    cut = expert.bundle_examples(pos.state, pos.seat, pos.history, pos.knowledge, [pos.human[0], {"type": "scan_earth", "sector": 99}])
    assert len(cut) == 1


def test_the_search_from_the_positions_makes_examples_from_the_best_bundle(game: tuple[Options, list[dict[str, Any]]]) -> None:
    options, actions = game
    found = list(expert.positions(options, actions, limit=4, rng=random.Random(6)))
    search = BundleSearch(HeuristicBrain(), FAST)
    ex, st = expert.search_positions(found, search, random.Random(1))
    assert st.positions == 4 and ex.bundles == 4 and ex.policy and not ex.value
    assert 0 <= st.human_best <= st.human_scored <= 4
    assert sum(st.origins.values()) == 4
    assert st.margin >= -1e-6 * max(st.human_scored, 1)  # the best bundle never scores less than the one of the person
    assert str(st)
    alone, st2 = expert.search_positions(found, search, random.Random(1), offer=False)
    assert st2.positions == 4 and "offered" not in st2.origins


def test_positions_are_sampled_from_the_usable_games_of_an_archive(tmp_path: Path, game: tuple[Options, list[dict[str, Any]]]) -> None:
    options, actions = game
    header = {"options": options.model_dump(), "seats": [], "rngEncoding": "exact", "id": "g1"}
    result = {"status": "finished", "result": {"reason": "completed", "ranking": [{"seat": 0, "score": 100}, {"seat": 1, "score": 90}]}}
    (tmp_path / "g1").mkdir()
    (tmp_path / "g1" / "replay.json").write_text(
        json.dumps({"header": header, "actions": [{"seq": i, "action": a} for i, a in enumerate(actions)], "result": result}), encoding="utf-8"
    )
    (tmp_path / "g2").mkdir()
    resigned = {"status": "abandoned", "result": {"reason": "resigned", "ranking": []}}
    (tmp_path / "g2" / "replay.json").write_text(json.dumps({"header": {**header, "id": "g2"}, "actions": [], "result": resigned}), encoding="utf-8")
    found, stats = expert.sample_positions(tmp_path, 7, seed=3)
    assert len(found) == 7 and stats.used == 1 and stats.skipped == {"not played to the end": 1}
    assert {p.game for p in found} == {"g1"}
    again, _ = expert.sample_positions(tmp_path, 7, seed=3)
    assert [p.index for p in again] == [p.index for p in found]  # the same seed, the same positions
    assert dataset.skip_reason(dataset.parse(dataset.load_file(tmp_path / "g2" / "replay.json"))) == "not played to the end"


def test_a_game_of_self_play_gives_policy_examples_of_the_model_seats_and_values_of_both() -> None:
    cfg = selfplay.SelfPlayConfig(search=FAST, explore_temperature=3.0, explore_rounds=1, bot="greedy")
    arena.MAX_STEPS, saved = 1500, arena.MAX_STEPS
    try:
        g = selfplay.play(HeuristicBrain(), 5, cfg)
    finally:
        arena.MAX_STEPS = saved
    assert len(g.model_seats) == 1 and g.searches > 10 and len(g.scores) == 2
    assert g.examples.policy and g.examples.value
    assert g.examples.finished
