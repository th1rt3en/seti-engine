"""The examples of bundle training (bundle_data.py): from the real game of a person, from games of bots, and the rule for games of people against the
model."""

import json
import random
from pathlib import Path

from seti_engine.models import Options

from seti_ai import arena, bots
from seti_ai.agent import VALUE_SCALE
from seti_ai.bundle_data import Examples, examples_from_log, game_weights
from seti_ai.bundles import bundles_of_game

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "solo-289.json").read_text(encoding="utf-8"))
OPTIONS = Options(**FIXTURE["options"])


def real() -> Examples:
    return examples_from_log(OPTIONS, FIXTURE["actions"], FIXTURE["rng_encoding"])


def test_the_real_game_gives_a_choice_for_every_move_that_was_not_taken_back() -> None:
    ex = real()
    undos = sum(1 for a in FIXTURE["actions"] if a["type"] == "undo")
    legacy = 1  # one `scan_skip` of the old rule (played before the scan could be done in any order, 2026-10-22): accepted, no longer offered
    assert len(ex.policy) == len(FIXTURE["actions"]) - 2 * undos - legacy
    for p in ex.policy:
        assert 0 <= p.action < p.toks.shape[0], "the chosen move is one of the moves that were offered"
        assert p.toks.shape[0] == p.nums.shape[0]
        assert p.weight == 1.0
    assert ex.finished


def test_there_is_a_value_example_after_each_bundle_with_the_points_that_the_seat_still_gained() -> None:
    ex = real()
    bs, final = bundles_of_game(OPTIONS, FIXTURE["actions"], FIXTURE["rng_encoding"])
    mine = [b for b in bs if b.seat == 0]
    assert len(ex.value) == len(bs) - len([b for b in bs if b.seat != 0]) or len(ex.value) == len(bs)
    # the seat is seat 0 in a solo game: the first bundle (the setup) is worth nearly the whole game, the last one the end-of-game scoring that no bundle
    # scored
    total = FIXTURE["final"][0]
    first, last = ex.value[0], ex.value[-1]
    assert abs(first.target * VALUE_SCALE - (total - mine[0].steps[-1].score_after)) < 1e-4
    assert abs(last.target * VALUE_SCALE - (total - mine[-1].steps[-1].score_after)) < 1e-4
    assert last.target * VALUE_SCALE > 40, "the end-of-game scoring (the gold tiles) is part of what the last bundle is worth"
    assert all(v.target >= 0 for v in ex.value), "a seat never loses points in this game"
    targets = [v.target for v in ex.value]
    assert targets == sorted(targets, reverse=True), "what is left to gain only goes down as the game goes on"


def test_a_weight_of_zero_makes_no_example() -> None:
    assert not examples_from_log(OPTIONS, FIXTURE["actions"], FIXTURE["rng_encoding"], policy_weight=0.0, value_weight=0.0).policy
    only_value = examples_from_log(OPTIONS, FIXTURE["actions"], FIXTURE["rng_encoding"], policy_weight=0.0)
    assert not only_value.policy and only_value.value
    only_policy = examples_from_log(OPTIONS, FIXTURE["actions"], FIXTURE["rng_encoding"], value_weight=0.0)
    assert only_policy.policy and not only_policy.value


def test_the_weights_can_depend_on_the_seat() -> None:
    ex = examples_from_log(Options(players=2, seed=3), random_actions(Options(players=2, seed=3), 120), policy_weight=lambda seat: 2.0 if seat == 0 else 0.0)
    assert ex.policy and all(p.weight == 2.0 for p in ex.policy)


def random_actions(options: Options, n: int) -> list[dict]:  # type: ignore[type-arg]
    res = arena.play_game([bots.heuristic(), bots.greedy()], options.seed, random.Random(options.seed), {})
    return res.actions[:n]


def test_games_of_bots_make_examples_and_the_value_labels_need_a_finished_game() -> None:
    opts = Options(players=2, seed=5)
    res = arena.play_game([bots.heuristic(), bots.heuristic()], 5, random.Random(5), {})
    assert res.finished and res.actions
    full = examples_from_log(opts, res.actions)
    assert full.finished and len(full.policy) == len(res.actions) and full.value
    cut = examples_from_log(opts, res.actions[:60])
    assert not cut.finished and len(cut.policy) == 60 and not cut.value, "no value label before the end of the game"


# --- the rule for games of people against the model (the owner, 2026-10-21) -----------------------------------------------------------------------


def test_a_game_that_the_model_lost_counts_with_more_weight_for_the_moves_of_the_person() -> None:
    policy, value = game_weights([180, 230], model_seats={0})  # the model is seat 0 and scored less
    assert policy == {0: 0.0, 1: 3.0}, "the person's moves are imitated, the model's are not"
    assert value == {0: 1.0, 1: 1.0}, "the positions of both seats give value labels"


def test_a_game_that_the_model_won_or_tied_is_skipped() -> None:
    assert game_weights([240, 200], model_seats={0}) == ({0: 0.0, 1: 0.0}, {0: 0.0, 1: 0.0})
    assert game_weights([200, 200], model_seats={1}) == ({0: 0.0, 1: 0.0}, {0: 0.0, 1: 0.0})


def test_a_game_without_the_model_counts_once() -> None:
    assert game_weights([100, 90], model_seats=set()) == ({0: 1.0, 1: 1.0}, {0: 1.0, 1: 1.0})


def test_the_weights_of_a_lost_game_can_be_set() -> None:
    policy, value = game_weights([10, 20, 30], model_seats={0}, lost_weight=5.0, value_lost_weight=2.0)
    assert policy == {0: 0.0, 1: 5.0, 2: 5.0} and value == {0: 2.0, 1: 2.0, 2: 2.0}


# --- the result of the game as a target (the win head) ------------------------------------------------------------------------------------------
def test_every_position_of_a_game_carries_the_result_of_the_whole_game() -> None:
    """A turn that set up a win many turns later is credited for it: each position after a bundle is labelled with how the game ended for its seat."""
    opts = Options(players=2, seed=5)
    res = arena.play_game([bots.heuristic(), bots.greedy()], 5, random.Random(5), {})
    assert res.finished
    by_seat: dict[int, set[float]] = {0: set(), 1: set()}
    for seat in (0, 1):
        ex = examples_from_log(opts, res.actions, value_weight=lambda s, seat=seat: 1.0 if s == seat else 0.0)
        by_seat[seat] = {v.win for v in ex.value}
    assert all(len(labels) == 1 for labels in by_seat.values()), "one label for all the positions of a seat"
    a, b = by_seat[0].pop(), by_seat[1].pop()
    if res.scores[0] == res.scores[1]:
        assert a == b == 0.5
    else:
        assert {a, b} == {0.0, 1.0}
        assert a == (1.0 if res.scores[0] > res.scores[1] else 0.0)


def test_the_label_is_a_win_a_shared_first_place_or_a_loss() -> None:
    """The engine's `winners` decides (it also knows the solo rule: the player wins only with more points than the rival)."""
    from seti_engine import engine

    from seti_ai.bundle_data import win_label

    state = engine.start(Options(players=2, seed=1)).state
    alone = state.model_copy(update={"winners": [1]})
    assert (win_label(alone, 1), win_label(alone, 0)) == (1.0, 0.0)
    shared = state.model_copy(update={"winners": [0, 1]})
    assert win_label(shared, 0) == win_label(shared, 1) == 0.5
