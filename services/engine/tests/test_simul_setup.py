"""EXP-ORG-14 (owner, 2026-10-23): the organization and the quick start cards are chosen by all players at the same time, in secret, and
locked in; nothing is shown until all have locked in. Then the starts run in turn order, as when the choices were made one by one."""

from typing import Any

import pytest

from seti_engine import projection
from seti_engine.engine import IllegalAction, StepResult, apply, legal_moves, start
from seti_engine.models import GameState, Options


def new(players: int = 2, seed: int = 7, simul: bool = True) -> StepResult:
    return start(Options(players=players, seed=seed, expansion=True, organizations=True, simul_setup=simul))


def pick(r: StepResult, seat: int, kind: str) -> dict[str, Any]:
    return next(m for m in r.legal if m["type"] == kind and m.get("seat") == seat)


def lock_in(r: StepResult, seat: int) -> StepResult:
    r = apply(r.state, pick(r, seat, "choose_org"))
    r = apply(r.state, pick(r, seat, "choose_quick"))
    return apply(r.state, pick(r, seat, "setup_lock"))


def test_every_player_is_asked_at_once_and_each_move_names_its_seat() -> None:  # EXP-ORG-14
    r = new(3)
    assert [d.kind for d in r.state.pending] == ["setup_choice"] * 3
    assert projection.acting(r.state) == [d.player for d in r.state.pending]
    seats = {m["seat"] for m in r.legal}
    assert seats == {0, 1, 2}
    assert {m["type"] for m in r.legal} == {"choose_org", "choose_quick"}  # nothing to lock in before both are chosen


def test_a_player_sees_only_their_own_moves_and_is_the_one_to_act() -> None:  # EXP-ORG-14
    r = new()
    for seat in (0, 1):
        v = projection.project(r.state, seat, previews=False)
        assert v.to_act == seat and sorted(v.acting) == [0, 1]
        assert v.legal and all(m["seat"] == seat for m in v.legal)
    spectator = projection.project(r.state, None, previews=False)
    assert spectator.legal == [] and sorted(spectator.acting) == [0, 1]


def test_the_choices_can_be_made_in_any_order_and_changed_until_the_lock() -> None:  # EXP-ORG-14
    r = new()
    first = pick(r, 1, "choose_org")
    other = next(m for m in r.legal if m["type"] == "choose_org" and m["seat"] == 1 and m != first)
    r = apply(r.state, first)
    r = apply(r.state, other)  # changed its mind
    assert r.state.players[1].setup_org == other["org"]
    assert not any(m["type"] == "setup_lock" and m["seat"] == 1 for m in r.legal)  # the quick start cards are not chosen yet
    r = apply(r.state, pick(r, 1, "choose_quick"))
    assert any(m["type"] == "setup_lock" and m["seat"] == 1 for m in r.legal)
    r = apply(r.state, pick(r, 0, "choose_org"))  # the other seat chooses after: the order does not matter


def test_nothing_of_a_choice_is_shown_before_everybody_has_locked_in() -> None:  # EXP-ORG-14
    r = new()
    r = lock_in(r, 1)
    assert r.events and all(e["type"] == "setup_locked" for e in r.events)  # no organization is announced
    v0 = projection.project(r.state, 0, previews=False)
    p1 = v0.state.players[1]
    assert p1.setup_locked and p1.setup_org is None and p1.setup_quick == [] and p1.organization is None
    assert all(c == projection.HIDDEN for c in p1.offered_orgs + p1.offered_quick) or not (p1.offered_orgs + p1.offered_quick)
    assert r.state.players[1].setup_org is not None  # the engine keeps it
    assert [d.player for d in r.state.pending] == [0]  # the locked player is not asked any more
    assert projection.project(r.state, 1, previews=False).legal == []  # and has nothing to do but wait
    assert projection.project(r.state, 0, previews=False).legal  # the other still chooses


def test_a_locked_choice_cannot_be_changed_and_a_move_of_another_seat_is_not_legal() -> None:  # EXP-ORG-14
    r = new()
    old = pick(r, 1, "choose_org")
    r = lock_in(r, 1)
    with pytest.raises(IllegalAction):
        apply(r.state, old)
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "setup_lock", "seat": 0})  # seat 0 has chosen nothing yet
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "choose_org", "org": "not_an_org", "seat": 0})


def test_the_last_lock_makes_the_choices_public_and_the_starts_run_in_turn_order() -> None:  # EXP-ORG-14, EXP-ORG-06, EXP-ORG-07
    r = new()
    r = lock_in(r, 0)
    r = lock_in(r, 1)
    announced = [e["player"] for e in r.events if e["type"] == "organization"]
    assert sorted(announced) == [0, 1]
    assert all(p.organization is not None and p.setup_org is None and p.offered_orgs == [] for p in r.state.players)
    first = r.state.start_player
    assert r.state.pending[0].player == first and r.state.pending[0].kind == "setup_tuck"  # the first player's own tucks come first
    assert not any(d.kind in ("setup_choice", "setup_start") and d.player == first for d in r.state.pending)


def dump(state: GameState) -> dict[str, Any]:
    d = state.model_dump()
    d["options"].pop("simul_setup")
    for p in d["players"]:
        for k in ("setup_org", "setup_quick", "setup_locked"):
            p.pop(k)
    return d


def finish_tucks(r: StepResult) -> StepResult:
    while r.state.phase == "setup":
        r = apply(r.state, r.legal[0])
    return r


@pytest.mark.parametrize("players", [2, 3])
def test_the_result_is_the_same_as_when_the_choices_were_made_one_after_another(players: int) -> None:  # EXP-ORG-14
    """Same seed, same choices: the simultaneous setup ends in the state of the sequential one (the starts run in the same order)."""
    simul = new(players)
    chosen: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    for seat in range(players):
        chosen[seat] = (pick(simul, seat, "choose_org"), pick(simul, seat, "choose_quick"))
    for seat in reversed(range(players)):  # the locks come in another order than the turn order
        for m in chosen[seat]:
            simul = apply(simul.state, m)
        simul = apply(simul.state, pick(simul, seat, "setup_lock"))
    simul = finish_tucks(simul)

    seq = new(players, simul=False)
    order = [(seq.state.start_player + k) % players for k in range(players)]
    for seat in order:
        org, quick = chosen[seat]
        seq = apply(seq.state, {"type": "choose_org", "org": org["org"]})
        seq = apply(seq.state, {"type": "choose_quick", "cards": quick["cards"]})
        while seq.state.pending and seq.state.pending[0].kind == "setup_tuck":
            seq = apply(seq.state, seq.legal[0])
    seq = finish_tucks(seq)
    assert simul.state.phase == "play" and seq.state.phase == "play"
    assert dump(simul.state) == dump(seq.state)


def test_the_flag_is_off_by_default_and_needs_the_organizations() -> None:
    assert Options(players=2).simul_setup is False
    with pytest.raises(ValueError):
        Options(players=2, simul_setup=True)
    seq = new(2, simul=False)
    assert [d.kind for d in seq.state.pending][:2] == ["choose_org", "choose_quick"]
    assert legal_moves(seq.state) and "seat" not in legal_moves(seq.state)[0]
