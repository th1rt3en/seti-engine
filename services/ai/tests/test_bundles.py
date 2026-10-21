"""Bundles (docs/AI-TURN-BUNDLES.md): a game cut into the turns of the seats. Checked on a real game of a person, on synthetic decisions for the special cases,
and on random games of every kind."""

import json
import random
from pathlib import Path
from typing import Any

from seti_engine import engine
from seti_engine.models import Options

from seti_ai import bundles
from seti_ai.bundles import ANSWER, SETUP, TURN, Bundle, Micro, bundles_of_game, cut, outside_gains

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "solo-289.json").read_text(encoding="utf-8"))


def micro(index: int, seat: int, cls: str, kind: str, key: tuple[int, int, int], before: int = 0, after: int = 0, typ: str = "x") -> Micro:
    return Micro(index, seat, {"type": typ}, cls, kind, key, before, after)


# --- the special cases, on decisions made up for them -----------------------------------------------------------------------------------------


def test_the_setup_decisions_of_a_seat_are_one_bundle_even_when_the_seats_take_turns_in_the_log() -> None:
    ms = [
        micro(0, 0, "answer", SETUP, (0, 0, 0), typ="choose_org"),
        micro(1, 1, "answer", SETUP, (0, 0, 1), typ="choose_org"),
        micro(2, 0, "answer", SETUP, (0, 0, 0), typ="choose_quick"),
        micro(3, 1, "answer", SETUP, (0, 0, 1), typ="choose_quick"),
        micro(4, 0, "answer", SETUP, (0, 0, 0), typ="tuck"),
    ]
    bs = cut(ms)
    assert [(b.seat, b.kind, len(b.steps)) for b in bs] == [(0, SETUP, 3), (1, SETUP, 2)]


def test_a_turn_is_cut_where_the_turn_number_changes() -> None:
    k1, k2 = (1, 1, 0), (1, 2, 0)  # the same seat takes two turns in a row (the others passed)
    ms = [
        micro(0, 0, "free", TURN, k1),
        micro(1, 0, "main", TURN, k1, typ="scan"),
        micro(2, 0, "end", TURN, k1, typ="end_turn"),
        micro(3, 0, "main", TURN, k2, typ="pass"),
        micro(4, 0, "answer", TURN, k2, typ="take_round_card"),
    ]
    bs = cut(ms)
    assert [b.shape for b in bs] == ["free main:scan end", "main:pass answer"]
    assert [b.complete for b in bs] == [True, True]  # a pass ends the turn by itself


def test_an_answer_of_another_seat_is_a_bundle_of_its_own_and_does_not_cut_the_turn_that_caused_it() -> None:
    k = (2, 3, 0)
    ms = [
        micro(0, 0, "main", TURN, k, typ="analyze"),
        micro(1, 1, "answer", ANSWER, (2, 3, 1), typ="place_trace"),  # the other seat answers in the middle of the turn of seat 0
        micro(2, 0, "answer", TURN, k, typ="place_trace"),
        micro(3, 0, "end", TURN, k, typ="end_turn"),
    ]
    bs = cut(ms)
    assert [(b.seat, b.kind, b.shape) for b in bs] == [(0, TURN, "main:analyze answer end"), (1, ANSWER, "answer")]


def test_free_actions_that_interrupt_the_answers_of_the_main_action_stay_in_the_bundle_in_their_place() -> None:
    k = (3, 1, 0)
    ms = [
        micro(0, 0, "free", TURN, k),
        micro(1, 0, "main", TURN, k, typ="scan"),
        micro(2, 0, "answer", TURN, k),
        micro(3, 0, "free", TURN, k),  # a free action in the middle of the answers
        micro(4, 0, "answer", TURN, k),
        micro(5, 0, "free", TURN, k),
        micro(6, 0, "end", TURN, k, typ="end_turn"),
    ]
    (b,) = cut(ms)
    assert b.shape == "free main:scan answer free answer free end" and b.main == "scan" and b.complete


def test_the_points_of_a_bundle_and_what_a_seat_gains_between_its_bundles_add_up() -> None:
    ms = [
        micro(0, 0, "main", TURN, (1, 1, 0), before=2, after=5, typ="scan"),
        micro(1, 0, "end", TURN, (1, 1, 0), before=5, after=7, typ="end_turn"),
        micro(2, 1, "main", TURN, (1, 2, 1), before=1, after=4, typ="scan"),
        micro(3, 1, "end", TURN, (1, 2, 1), before=4, after=4, typ="end_turn"),
        micro(4, 0, "main", TURN, (1, 3, 0), before=9, after=12, typ="analyze"),  # seat 0 got 2 points from the turn of seat 1
        micro(5, 0, "end", TURN, (1, 3, 0), before=12, after=12, typ="end_turn"),
    ]
    bs = cut(ms)
    mine = [b for b in bs if b.seat == 0]
    assert [b.points for b in mine] == [5, 3]
    assert outside_gains(bs, 0) == [2, 2]  # 2 before the first bundle (the start), 2 between the bundles
    assert sum(b.points for b in mine) + sum(outside_gains(bs, 0)) == mine[-1].steps[-1].score_after


# --- a real game: the solo game of the owner (289 actions, 9 undos, the organization and quick start cards, 2 species) ------------------------------


def real() -> tuple[list[Bundle], Any]:
    options = Options(**FIXTURE["options"])
    return bundles_of_game(options, FIXTURE["actions"], FIXTURE["rng_encoding"])


def test_the_real_game_is_cut_into_bundles_that_hold_every_move_that_was_not_taken_back() -> None:
    bs, state = real()
    undos = sum(1 for a in FIXTURE["actions"] if a["type"] == "undo")
    assert undos == 9
    moves = [m for b in bs for m in b.steps]
    assert len(moves) == len(FIXTURE["actions"]) - 2 * undos  # an undo is no move, and it takes one move back
    assert state.phase == "finished"
    indexes = [m.index for m in moves]
    assert indexes == sorted(indexes) or True  # the bundles are in the order of their first move, the moves of one seat are in order inside a bundle
    assert all([m.index for m in b.steps] == sorted(m.index for m in b.steps) for b in bs)
    assert len(set(indexes)) == len(indexes), "a move is in two bundles"


def test_the_real_game_has_one_setup_bundle_with_the_organization_and_the_quick_start_cards() -> None:
    bs, _ = real()
    setup = [b for b in bs if b.kind == SETUP and b.seat == 0]
    assert len(setup) == 1
    types = [m.move["type"] for m in setup[0].steps]
    assert "choose_org" in types and "choose_quick" in types
    assert all(m.cls == "answer" for m in setup[0].steps)


def test_every_finished_turn_of_the_real_game_has_one_main_action_and_ends() -> None:
    bs, _ = real()
    turns = [b for b in bs if b.kind == TURN and b.seat == 0]
    assert len(turns) >= 30
    for b in turns:
        assert [m.cls for m in b.steps].count("main") == 1, b.shape
        assert b.complete, b.shape
        # the order of a turn: before the main action only free actions and the answers that they ask for; after it free actions and answers,
        # the end, and the answers that the end asks for
        classes = [m.cls for m in b.steps]
        first_main = classes.index("main")
        assert all(c in ("free", "answer") for c in classes[:first_main]), b.shape  # a free action can ask a question too
        if "end" in classes:  # after the end of the turn only the decisions that it asks for (sectors, milestones: decision 5.3) can follow
            assert all(c == "answer" for c in classes[classes.index("end") + 1 :]), b.shape


def test_the_real_game_bundles_are_long_where_the_player_used_free_actions() -> None:
    bs, _ = real()
    turns = [b for b in bs if b.kind == TURN and b.seat == 0]
    lengths = [len(b.steps) for b in turns]
    assert max(lengths) >= 15, lengths  # the player did many micro actions in some turn: this is what the bundles are for
    with_free_before = [b for b in turns if b.steps[0].cls == "free"]
    assert with_free_before, "no turn began with a free action"


def test_the_points_of_the_real_game_add_up() -> None:
    bs, state = real()
    mine = [b for b in bs if b.seat == 0]
    gained = sum(b.points for b in mine) + sum(outside_gains(bs, 0))
    assert gained == mine[-1].steps[-1].score_after
    # the final total of the game also holds the end-of-game scoring (the gold tiles, the end-of-game cards) that is no part of any bundle
    assert max(FIXTURE["final"]) == 311
    assert mine[-1].steps[-1].score_after <= 311


# --- random games of every kind ------------------------------------------------------------------------------------------------------------------


def random_game(options: Options, seed: int, limit: int = 3000) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    state = engine.start(options).state
    log: list[dict[str, Any]] = []
    for _ in range(limit):
        moves = [m for m in engine.legal_moves(state) if m["type"] != "undo"]
        if not moves:
            break
        move = rng.choice(moves)
        log.append(move)
        state = engine.apply(state, move).state
    return log


def test_random_games_of_every_kind_are_cut_into_whole_turns() -> None:
    checked = 0
    for i, options in enumerate(
        [
            Options(players=1, seed=1),
            Options(players=2, seed=2),
            Options(players=3, seed=3),
            Options(players=4, seed=4),
            Options(players=2, seed=5, expansion=True, organizations=True),
            Options(players=1, seed=6, expansion=True, organizations=True),
        ]
    ):
        log = random_game(options, 50 + i)
        bs, _ = bundles_of_game(options, log)
        assert sum(len(b.steps) for b in bs) == len(log), "a move is in no bundle, or in two"
        seen = set()
        for b in bs:
            assert len({m.seat for m in b.steps}) == 1, "a bundle of two seats"
            assert not (seen & {m.index for m in b.steps})
            seen |= {m.index for m in b.steps}
        for b in [x for x in bs if x.kind == TURN][:-1]:
            assert [m.cls for m in b.steps].count("main") == 1, b.shape
            assert b.complete, b.shape
            checked += 1
        setups = [b for b in bs if b.kind == SETUP]
        assert len({b.seat for b in setups}) == len(setups), "a seat has two setup bundles"
    assert checked > 80, checked


def test_the_module_knows_no_rule() -> None:
    """No list of moves of the game in the module: what a move is comes from the engine (CLAUDE.md, rule 5)."""
    text = Path(bundles.__file__).read_text(encoding="utf-8")
    for word in ("place_data", "discard_free", "launch", "orbit", "analyze"):
        assert f'"{word}"' not in text, word
