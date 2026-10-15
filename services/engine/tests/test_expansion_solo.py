"""Solo game with the Space Agencies expansion (EXP-SOLO-01 to EXP-SOLO-06)."""

from seti_engine import cards, objectives, rival
from seti_engine.engine import apply, start
from seti_engine.models import GameState, Options


def new(difficulty: int = 3, seed: int = 3, **kw: bool) -> GameState:
    return start(Options(players=1, seed=seed, difficulty=difficulty, expansion=True, **kw)).state


def test_exp_solo_01_solo_with_organizations_is_set_up_as_two_players() -> None:
    r = start(Options(players=1, seed=3, expansion=True, organizations=True, neutral_quick_start=True))
    s = r.state
    assert len(s.players) == 2 and s.rival is not None
    assert len(s.players[0].offered_orgs) == 2 and not s.players[1].offered_orgs  # the rival gets no organization
    assert s.players[1].organization is None and not s.players[1].offered_quick
    assert len(s.neutral_quick) == 4
    assert all(d.player == 0 for d in s.pending)


def test_exp_solo_01_the_whole_choice_flow_reaches_the_first_turn() -> None:
    r = start(Options(players=1, seed=5, expansion=True, organizations=True))
    for _ in range(400):
        if not r.state.pending or r.state.pending[0].kind not in ("choose_org", "choose_quick", "setup_tuck"):
            break
        r = apply(r.state, r.legal[0])
    assert r.state.players[0].organization is not None and len(r.state.players[0].quick_start) == 2


def test_exp_solo_02_the_extra_card_is_in_the_rivals_deck() -> None:
    assert "SE.1" in new().rival.deck  # type: ignore[union-attr]
    base = start(Options(players=1, seed=3)).state
    assert "SE.1" not in base.rival.deck  # type: ignore[union-attr]


def test_exp_solo_02_it_marks_a_trace_and_advances_for_each_star() -> None:
    s = new(difficulty=2)
    before = s.rival.progress  # type: ignore[union-attr]
    ev: list[dict] = []  # type: ignore[type-arg]
    rival._do(s, {"kind": "trace_advance", "color": "any"}, ev)
    assert s.rival.progress == (before + 2) % len(rival.TRACK)  # type: ignore[union-attr]
    assert any(m for slot in s.species for col in slot.board.values() for m in col) or any(sl.discovery_spaces for sl in s.species)


def test_exp_solo_03_the_rival_starts_with_4_publicity() -> None:
    s = new()
    assert s.players[1].publicity == 4


def test_exp_solo_04_level_one_is_left_out_and_two_long_term_tiles_are_revealed() -> None:
    s = new(difficulty=4)
    ob = s.objectives
    assert ob is not None
    assert all(objectives.tile(o)["level"] == "II" for o in ob.row)
    assert not any(objectives.tile(o)["level"] == "I" for o in [*ob.row, *ob.stack])
    assert len(ob.long_term) == 2 and all(o.startswith("LT-") for o in ob.long_term)


def test_exp_solo_04_difficulty_one_has_no_objectives() -> None:
    assert new(difficulty=1).objectives is None


def test_exp_solo_06_tasks_follow_their_triggers() -> None:
    s = new()
    ob = s.objectives
    assert ob is not None
    ob.row = []
    ob.long_term = ["LT-1", "LT-2", "LT-3"]
    ob.marks = {k: [False] * 3 for k in ob.long_term}
    p = s.players[0]
    objectives.on_event(s, p, [{"e": "trace", "kind": "pink"}])
    assert ob.marks["LT-1"] == [True, False, False] and not any(d.kind == "objective_task" for d in s.pending)
    objectives.on_event(s, p, [{"e": "tuck_income"}])
    assert ob.marks["LT-2"] == [True, False, False]
    objectives.on_event(s, p, [{"e": "tech", "cat": "telescope"}])
    assert ob.marks["LT-3"] == [False, True, False]
    objectives.on_event(s, p, [{"e": "tech", "cat": "telescope"}])
    assert ob.marks["LT-3"] == [False, True, False]  # one tech of each type


def test_exp_solo_06_a_completed_tile_is_removed_and_never_spent() -> None:
    s = new()
    ob = s.objectives
    assert ob is not None
    ob.long_term = ["LT-1"]
    ob.marks["LT-1"] = [True, True, True]
    ob.pile = []
    objectives.end_turn(s)
    assert ob.long_term == [] and ob.pile == []


def test_exp_solo_06_each_open_task_advances_the_rival_after_rounds_two_to_four() -> None:
    for rnd, expected in ((1, 0), (2, 3), (4, 3), (5, 0)):
        s = new()
        ob = s.objectives
        assert ob is not None
        ob.row, ob.stack, ob.pile = [], [], ["x"] * 6
        ob.long_term = ["LT-1", "LT-2"]
        ob.marks = {"LT-1": [True, False, False], "LT-2": [True, True, False]}
        r = s.rival
        assert r is not None
        r.progress = 0
        r.advanced = []
        objectives.end_round(s, rnd, [])
        assert r.progress == expected, rnd


def test_exp_solo_06_uncompleted_long_term_tiles_are_not_scored_at_the_end() -> None:
    s = new()
    ob = s.objectives
    assert ob is not None
    ob.row, ob.stack = [], []
    ob.long_term = ["LT-1"]
    ob.marks = {"LT-1": [False] * 3}
    score = s.players[1].score
    objectives.end_round(s, 5, [])
    assert s.players[1].score == score


def test_exp_solo_05_starting_tucks_do_not_complete_tasks() -> None:
    r = start(Options(players=1, seed=5, expansion=True, organizations=True))
    for _ in range(400):
        if not r.state.pending or r.state.pending[0].kind not in ("choose_org", "choose_quick", "setup_tuck"):
            break
        r = apply(r.state, r.legal[0])
    ob = r.state.objectives
    assert ob is not None and not any(any(m) for oid, m in ob.marks.items() if oid in ob.long_term)
    assert cards is not None
