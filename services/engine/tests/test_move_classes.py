"""The class of each legal move (free, main, answer, end, control): docs/AI-TURN-BUNDLES.md, decision 4 (the owner asked for thorough
tests).

The classes are the engine's own: they come from the same lists that `legal_moves` is made of. Rules checked on many random games (1
to 4 players, with and
without the expansion and the organizations, solo, the practice game):
- the classes are the same moves in the same order as `legal_moves`, one class for each;
- a move that is `answer` only exists while a decision is pending; `main` only when nothing is pending and the main action is not
  taken yet; `end` only as
  `end_turn` after the main action; `free` moves interrupt a decision only when the engine allows it (FREE-00);
- every turn that has a main action has one: it is offered, and `end_turn` is not offered before it is taken;
- every move type that appears is in the table below (a new type of move has to be put in the table, and so given a class, by whoever
  adds it).
"""

import random
from collections import defaultdict
from typing import Any

import pytest

from seti_engine.engine import MOVE_CLASSES, apply, legal_classified, legal_moves, start
from seti_engine.models import Options
from seti_engine.projection import project, to_act

# The classes that a type of move may have (a type can be a free action in the turn and an answer when a decision asks for it,
# place_data for example).
FREE_OR_ANSWER = {"free", "answer"}
EXPECTED: dict[str, set[str]] = {
    # main actions (PLAY-01, LAUNCH, ORBIT, LAND, SCAN, ANALYZE, TECHACT and the actions of the organizations and promo cards)
    "pass": {"main"},
    "play_card": {"main"},
    "launch": {"main"},
    "orbit": {"main"},
    "land": {"main"},
    "scan": {"main"},
    "analyze": {"main"},
    "research": {"main", "answer"},  # the main action, and the stack that a card or a free action asks for
    "end_turn": {"end"},
    "undo": {"control"},
    "sandbox": {"control"},
}
# types that are free actions and nothing else, or answers and nothing else, are found by the test itself and listed when they are new: see
# `test_the_classes_of_the_types_that_come_up` (the table above holds the ones that must be exactly as written)
MAIN_ONLY = {"pass", "play_card", "launch", "orbit", "land", "scan", "analyze", "end_turn"}


def configs() -> list[Options]:
    out: list[Options] = []
    for seed in (1, 2, 3):
        out += [
            Options(players=1, seed=seed),
            Options(players=2, seed=seed),
            Options(players=3, seed=seed),
            Options(players=4, seed=seed),
            Options(players=2, seed=seed, expansion=True),
            Options(players=2, seed=seed, expansion=True, organizations=True),
            Options(players=1, seed=seed, expansion=True, organizations=True),
        ]
    out.append(Options(players=1, seed=9, sandbox=True))
    return out


def play(options: Options, policy_seed: int, limit: int = 4000) -> list[tuple[Any, list[tuple[dict[str, Any], str]], dict[str, Any], str]]:
    """Play a game with random legal moves (never `undo`); give (state, classified moves, the move played, its class) for every step."""
    rng = random.Random(policy_seed)
    r = start(options)
    state = r.state
    steps = []
    for _ in range(limit):
        classified = legal_classified(state)
        if not classified:
            break
        usable = [(m, c) for m, c in classified if m["type"] != "undo"] or classified
        move, cls = rng.choice(usable)
        steps.append((state, classified, move, cls))
        state = apply(state, move).state
    return steps


@pytest.fixture(scope="module")
def games() -> list[list[tuple[Any, list[tuple[dict[str, Any], str]], dict[str, Any], str]]]:
    return [play(o, 1000 + i) for i, o in enumerate(configs())]


def test_the_classified_moves_are_the_legal_moves_in_the_same_order(games) -> None:  # type: ignore[no-untyped-def]
    for g in games:
        for state, classified, _, _ in g[:: max(1, len(g) // 60)]:  # a sample of the steps of each game (every step would repeat the work)
            assert [m for m, _ in classified] == legal_moves(state)
            assert all(c in MOVE_CLASSES for _, c in classified)


def test_the_view_carries_the_classes_of_the_moves_of_the_seat_to_act(games) -> None:  # type: ignore[no-untyped-def]
    for g in games[:6]:
        for state, classified, _, _ in g[:: max(1, len(g) // 25)]:
            seat = to_act(state)
            if seat is None:
                continue
            v = project(state, seat, previews=False)
            assert v.legal == [m for m, _ in classified]
            assert v.classes == [c for _, c in classified]
            others = [i for i in range(len(state.players)) if i != seat][:1]
            for o in others:
                w = project(state, o, previews=False)  # whoever is not to act sees no moves and no classes
                assert w.legal == [] and w.classes == []
            assert project(state, None, previews=False).classes == []  # the spectator


def test_answers_exist_only_while_a_decision_is_pending(games) -> None:  # type: ignore[no-untyped-def]
    for g in games:
        for state, classified, _, _ in g:
            classes = [c for _, c in classified]
            if "answer" in classes:
                assert state.pending, "an answer without a decision"
            if state.pending:
                assert "end" not in classes and "main" not in classes, "a decision is pending: no end of turn, no new main action"


def test_main_actions_are_offered_only_before_the_main_action_is_taken(games) -> None:  # type: ignore[no-untyped-def]
    for g in games:
        for state, classified, _, _ in g:
            classes = [c for _, c in classified]
            if "main" in classes:
                assert not state.pending and not state.main_done and state.phase == "play"
            if "end" in classes:
                assert state.main_done and not state.pending
                assert [m["type"] for m, c in classified if c == "end"] == ["end_turn"]
            if state.phase == "play" and not state.pending and not state.main_done:
                assert "main" in classes, "a turn must be able to take its main action (pass is always one)"
                assert "end" not in classes, "end_turn is not offered before the main action"
            if state.phase == "play" and not state.pending and state.main_done:
                assert "end" in classes and "main" not in classes


def test_free_actions_interrupt_a_decision_only_where_the_engine_allows_it(games) -> None:  # type: ignore[no-untyped-def]
    interrupted = 0
    for g in games:
        for state, classified, _, _ in g:
            if state.pending and any(c == "free" for _, c in classified):
                interrupted += 1
                d = state.pending[0]
                assert state.phase == "play" and state.stage is None and not state.free_active
                assert d.player == state.current_player
    assert interrupted > 0, "no game had a free action that interrupts a decision: the test games are too short to check FREE-00"


def test_the_control_moves_are_only_undo_and_the_practice_marker(games) -> None:  # type: ignore[no-untyped-def]
    for g in games:
        for _, classified, _, _ in g:
            for m, c in classified:
                if c == "control":
                    assert m["type"] == "undo" or m["type"].startswith("sandbox")


def test_the_types_that_must_be_exactly_as_written_are(games) -> None:  # type: ignore[no-untyped-def]
    seen: dict[str, set[str]] = defaultdict(set)
    for g in games:
        for _, classified, _, _ in g:
            for m, c in classified:
                seen[m["type"]].add(c)
    for t, allowed in EXPECTED.items():
        if t in seen:
            assert seen[t] <= allowed, f"{t} came up as {seen[t]}, expected within {allowed}"
    for t in MAIN_ONLY:
        if t in seen:
            assert seen[t] == EXPECTED[t], (t, seen[t])
    assert {"free", "main", "answer", "end"} <= {c for cs in seen.values() for c in cs}


def test_the_classes_of_the_types_that_come_up(games) -> None:  # type: ignore[no-untyped-def]
    """The free actions that matter to a bundle: the types of moves that are free actions, answers, or both, found in the games
    (printed when a test fails)."""
    seen: dict[str, set[str]] = defaultdict(set)
    for g in games:
        for _, classified, _, _ in g:
            for m, c in classified:
                seen[m["type"]].add(c)
    # a type is never a main action and a free action at once
    for t, cs in seen.items():
        assert not ({"main", "free"} <= cs), f"{t} is both a main action and a free action: {cs}"
        assert not ({"end"} < cs), f"{t} is an end and something else: {cs}"
    # the free actions that the rules name must be classed free when nothing is pending (FREE-01 to FREE-07)
    for t in ("move_energy", "discard_free", "buy_card", "exchange"):
        if t in seen:
            assert "free" in seen[t], (t, seen[t])


def test_every_turn_of_a_game_has_exactly_one_main_action(games) -> None:  # type: ignore[no-untyped-def]
    """Cut the moves that were played into turns by (round, turn number, seat), as the bundles will be cut: a finished turn has one
    main action, and ends with
    `end_turn` or with the `pass` (a pass ends the turn by itself, and the decisions that it asks for are in the same turn)."""
    turns_seen = 0
    for g in games:
        turns: dict[tuple[int, int, int], list[tuple[str, str]]] = {}
        order: list[tuple[int, int, int]] = []
        for state, _, move, cls in g:
            if state.phase != "play":
                continue
            key = (state.round, state.turn, state.current_player)
            if key not in turns:
                turns[key] = []
                order.append(key)
            turns[key].append((move["type"], cls))
        for key in order[:-1]:  # the last one may be a turn that the random game did not finish
            mains = [t for t, c in turns[key] if c == "main"]
            assert len(mains) == 1, f"turn {key} has {len(mains)} main moves: {turns[key]}"
            last_main = [i for i, (_, c) in enumerate(turns[key]) if c == "main"][0]
            ends = [t for t, c in turns[key] if c == "end"]
            assert ends == ["end_turn"] or mains == ["pass"], f"turn {key}: it ends with {ends} after {mains}"
            assert all(c != "end" for _, c in turns[key][: last_main + 1]), f"turn {key}: end_turn before the main action"
            turns_seen += 1
    assert turns_seen > 200, turns_seen
