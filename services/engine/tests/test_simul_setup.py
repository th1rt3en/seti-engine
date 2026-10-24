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
    assert [m["type"] for m in projection.project(r.state, 1, previews=False).legal] == ["setup_unlock"]  # and can only unlock
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
    # EXP-ORG-07, EXP-ORG-14: the starts are done; now everybody who tucks cards chooses them at the same time
    assert r.state.phase == "setup" and all(d.kind == "setup_choice" and d.data["step"] == "tuck" for d in r.state.pending)
    owing = {p.index for p in r.state.players if p.tucks_owed}
    assert {d.player for d in r.state.pending} == owing == set(projection.acting(r.state))
    assert not any(d.kind == "setup_start" for d in r.state.pending)


def dump(state: GameState) -> dict[str, Any]:
    d = state.model_dump()
    d["options"].pop("simul_setup")
    for p in d["players"]:
        for k in ("setup_org", "setup_quick", "setup_locked"):
            p.pop(k)
    return d


def finish_tucks(r: StepResult) -> StepResult:
    """The tucks: the simultaneous ones (the first cards of the hand, then the lock) or the one-by-one ones of the older flow."""
    while r.state.phase == "setup":
        if r.state.pending[0].kind == "setup_choice":
            seat = r.state.pending[0].player
            r = apply(r.state, pick(r, seat, "choose_tucks"))
            r = apply(r.state, pick(r, seat, "setup_lock"))
        else:
            r = apply(r.state, min((m for m in r.legal if m["type"] == "tuck"), key=lambda m: m["card"]))
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
            seq = apply(seq.state, min((m for m in seq.legal if m["type"] == "tuck"), key=lambda m: m["card"]))
    seq = finish_tucks(seq)
    assert simul.state.phase == "play" and seq.state.phase == "play"
    # the tucks come after all the starts now, so what is drawn by income may differ; the choices and their effects are the same
    for a, b in zip(simul.state.players, seq.state.players, strict=True):
        assert (a.organization, a.quick_start, len(a.tucked)) == (b.organization, b.quick_start, len(b.tucked))


def test_the_flag_is_off_by_default_and_needs_2_players() -> None:
    assert Options(players=2).simul_setup is False
    with pytest.raises(ValueError):
        Options(players=1, simul_setup=True)
    seq = new(2, simul=False)
    assert [d.kind for d in seq.state.pending][:2] == ["choose_org", "choose_quick"]
    assert legal_moves(seq.state) and "seat" not in legal_moves(seq.state)[0]


def test_a_player_who_has_locked_in_may_unlock_while_somebody_else_has_not() -> None:  # EXP-ORG-14
    r = new(3)
    r = lock_in(r, 1)
    assert any(m["type"] == "setup_unlock" and m["seat"] == 1 for m in r.legal)
    assert not any(m["type"] == "setup_unlock" and m["seat"] == 0 for m in r.legal)  # seat 0 has not locked in
    v = projection.project(r.state, 1, previews=False)
    assert [m["type"] for m in v.legal] == ["setup_unlock"] and 1 not in v.acting  # not one to act, but may unlock
    org, quick = r.state.players[1].setup_org, r.state.players[1].setup_quick
    r = apply(r.state, {"type": "setup_unlock", "seat": 1})
    assert r.events == [{"type": "setup_unlocked", "player": 1}]
    p = r.state.players[1]
    assert not p.setup_locked and (p.setup_org, p.setup_quick) == (org, quick)  # the choices are kept
    assert sorted(projection.acting(r.state)) == [0, 1, 2]
    assert any(m["type"] == "setup_lock" and m["seat"] == 1 for m in r.legal)  # and can be locked again at once
    assert any(m["type"] == "choose_org" and m["seat"] == 1 for m in r.legal)  # or changed


def test_nobody_can_unlock_when_everybody_else_has_locked_in_and_the_last_lock_ends_the_setup() -> None:  # EXP-ORG-14
    r = new(2)
    r = lock_in(r, 1)
    r = lock_in(r, 0)  # the last lock: the setup is resolved at once, so there is nobody to unlock for
    assert not any(m["type"] == "setup_unlock" for m in r.legal)
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "setup_unlock", "seat": 1})


def test_a_lock_and_an_unlock_that_cross_end_the_same_way_in_either_order() -> None:  # EXP-ORG-14 (the room runs one move at a time)
    r = new(2)
    r = lock_in(r, 1)
    for _ in range(2):
        r = apply(r.state, pick(r, 0, "choose_org")) if not r.state.players[0].setup_org else r
        r = apply(r.state, pick(r, 0, "choose_quick")) if not r.state.players[0].setup_quick else r
    base = r
    # the lock of seat 0 first: the setup is resolved, the unlock of seat 1 is then refused
    a = apply(base.state, {"type": "setup_lock", "seat": 0})
    assert not any(d.kind == "setup_choice" and not d.data for d in a.state.pending)  # only the tucks are left to choose
    with pytest.raises(IllegalAction):
        apply(a.state, {"type": "setup_unlock", "seat": 1})
    # the unlock of seat 1 first: both choose again; the lock of seat 0 then waits for seat 1
    b = apply(base.state, {"type": "setup_unlock", "seat": 1})
    b = apply(b.state, {"type": "setup_lock", "seat": 0})
    assert [d.player for d in b.state.pending] == [1] and not b.state.players[1].setup_locked
    b = apply(b.state, {"type": "setup_lock", "seat": 1})
    assert not any(d.kind == "setup_choice" and not d.data for d in b.state.pending)


def at_tucks(players: int = 2, seed: int = 7) -> StepResult:
    r = new(players, seed)
    for seat in range(players):
        r = lock_in(r, seat)
    return r


def test_the_tucks_are_chosen_together_in_secret_and_tucked_when_all_have_locked_in() -> None:  # EXP-ORG-07, EXP-ORG-14
    r = at_tucks()
    seats = [d.player for d in r.state.pending]
    assert seats and all(m["seat"] in seats for m in r.legal)
    first, second = seats[0], seats[-1]
    r = apply(r.state, pick(r, second, "choose_tucks"))
    chosen = r.state.players[second].setup_tucks
    assert len(chosen) == r.state.players[second].tucks_owed
    assert projection.project(r.state, first, previews=False).state.players[second].setup_tucks == []  # nobody else sees them
    assert r.state.players[second].tucked == []  # nothing is tucked yet
    r = apply(r.state, pick(r, second, "setup_lock"))
    if first != second:
        assert r.state.phase == "setup" and r.state.players[second].tucked == []
        r = apply(r.state, pick(r, first, "choose_tucks"))
        r = apply(r.state, pick(r, first, "setup_lock"))
    assert r.state.phase == "play" and not r.state.pending
    assert [e["player"] for e in r.events if e["type"] == "tuck"]  # announced when the last one locks in
    assert all(p.setup_tucks == [] and p.tucks_owed == 0 for p in r.state.players)
    assert all(len(p.tucked) >= 1 for p in r.state.players if p.organization != "xenolab")


def test_a_tuck_needs_the_exact_number_of_cards_and_can_be_changed_or_unlocked() -> None:  # EXP-ORG-07, EXP-ORG-14
    r = at_tucks(3)
    seats = [d.player for d in r.state.pending]
    seat = seats[0]
    assert not any(m["type"] == "setup_lock" and m["seat"] == seat for m in r.legal)  # nothing chosen yet
    a, b = [m for m in r.legal if m["type"] == "choose_tucks" and m["seat"] == seat][:2]
    assert len(a["cards"]) == r.state.players[seat].tucks_owed
    r = apply(r.state, a)
    r = apply(r.state, b)  # changed its mind
    assert r.state.players[seat].setup_tucks == b["cards"]
    r = apply(r.state, pick(r, seat, "setup_lock"))
    if len(seats) > 1:
        assert any(m["type"] == "setup_unlock" and m["seat"] == seat for m in r.legal)
        r = apply(r.state, pick(r, seat, "setup_unlock"))
        assert r.state.pending[-1].data["step"] == "tuck"  # it chooses its tucks again, not its organization
        assert any(m["type"] == "choose_tucks" and m["seat"] == seat for m in r.legal)


def test_without_organizations_each_player_tucks_their_card_at_the_same_time() -> None:  # SETUP-36, EXP-ORG-14 (owner, 2026-10-24)
    r = start(Options(players=3, seed=3, simul_setup=True))
    assert r.state.phase == "setup" and [d.kind for d in r.state.pending] == ["setup_choice"] * 3
    assert sorted(projection.acting(r.state)) == [0, 1, 2]
    assert {m["type"] for m in r.legal} == {"choose_tucks"}  # one card each, chosen by every player on their own
    hands = [len(p.hand) for p in r.state.players]
    for seat in (2, 0, 1):  # in any order: nobody waits for another
        r = apply(r.state, pick(r, seat, "choose_tucks"))
        assert r.state.players[seat].tucked == []  # secret until all have locked in
        r = apply(r.state, pick(r, seat, "setup_lock"))
    assert r.state.phase == "play" and not r.state.pending
    assert all(len(p.tucked) == 1 for p in r.state.players)
    assert all(len(p.hand) >= h - 1 for p, h in zip(r.state.players, hands, strict=True))
