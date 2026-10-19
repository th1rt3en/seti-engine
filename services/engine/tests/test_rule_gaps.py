"""Tests that name rules which had code or a test without citing their ID (1.0 checklist, section A). One test per rule or small group."""

import json

from test_engine import begin, do, with_state

from seti_engine import effects, scoring, solar
from seti_engine.engine import FREE_TYPES, IllegalAction, apply, legal_moves, start
from seti_engine.models import Options, Probe

MAIN_TYPES = {"launch", "orbit", "land", "scan", "research", "analyze", "play_card", "pass"}


def test_the_sun_is_not_a_space() -> None:  # MOVE-03
    for ring in range(1, 5):
        for sector in range(8):
            assert all(1 <= r <= 4 for r, _ in solar.adjacent(ring, sector))  # nothing lies inside ring 1, so no way through the Sun
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.probes.append(Probe(id="x", player=pl, ring=1, sector=0))
    s.players[pl].movement = 5
    assert all(m["to"][0] >= 1 for m in legal_moves(s) if m["type"] == "move_probe")


def test_publicity_starts_on_4_and_is_capped_at_10() -> None:  # SETUP-34, SETUP-37, RES-02
    r = start(Options(players=2, seed=4))
    assert [p.publicity for p in r.state.players] == [4, 4]
    p = r.state.players[0]
    effects.gain_publicity(r.state, p, 5)
    assert p.publicity == 9
    effects.gain_publicity(r.state, p, 5)
    assert p.publicity == 10
    effects.gain_publicity(r.state, p, 1)  # a player with 10 publicity ignores effects that give more
    assert p.publicity == 10


def test_the_hand_is_limited_only_when_passing() -> None:  # RES-03, FAQ-06
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].hand = [*s.players[pl].hand, *s.deck[-6:]]
    s.deck = s.deck[:-6]
    assert len(s.players[pl].hand) > 4
    r = do(do(with_state(s), "launch"), "end_turn")
    assert not r.state.pending and len(r.state.players[pl].hand) > 4  # no discard when the turn simply ends
    r = do(with_state(s), "pass")
    assert r.state.pending and r.state.pending[0].kind == "discard_to_four"  # passing asks for it


def test_a_turn_has_exactly_one_main_action_and_free_actions_at_any_time() -> None:  # TURN-01, TURN-02
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].energy = 2
    before = legal_moves(s)
    assert {"launch", "pass"} <= {m["type"] for m in before}
    assert any(m["type"] == "move_energy" for m in before)  # a free action before the main action
    r = do(with_state(s), "launch")
    after = {m["type"] for m in r.legal}
    assert not after & MAIN_TYPES  # the main action is used
    assert "move_energy" in after and "end_turn" in after  # a free action after it
    assert all(t in FREE_TYPES or t in {"end_turn", "undo"} for t in after if t not in MAIN_TYPES)


def test_play_goes_clockwise_and_skips_players_who_passed() -> None:  # GAME-02
    r = begin(3)
    order = []
    first = r.state.current_player
    assert first == r.state.start_player  # the player with the starting marker opens the round
    for _ in range(3):
        order.append(r.state.current_player)
        r = do(do(r, "launch") if {"type": "launch"} in r.legal else r, "end_turn")
    assert order == [(first + k) % 3 for k in range(3)]
    # the second player passes: the turns that follow skip them
    r = begin(3)
    first = r.state.current_player
    r = do(do(r, "launch"), "end_turn")
    second = r.state.current_player
    r = do(r, "pass")
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    third = r.state.current_player
    assert third == (first + 2) % 3 and r.state.players[second].passed
    r = do(r, "pass") if {"type": "pass"} in r.legal else r
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    assert r.state.current_player == first  # back to the first player, the one who passed is skipped


def test_exofossils_cannot_be_traded_and_score_nothing() -> None:  # FAQ-42
    s = begin(2).state.model_copy(deep=True)
    s.players[0].exofossils = 4
    assert "exofossil" not in json.dumps(legal_moves(s))
    rows = scoring.final_scores(s)
    s.players[0].exofossils = 0
    assert [r["total"] for r in rows] == [r["total"] for r in scoring.final_scores(s)]


def test_no_milestone_is_reached_again_on_the_second_lap() -> None:  # MILE-04
    s = begin(2).state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.score = 110
    s.crossed = []
    effects.gain_score(s, p, 60)
    assert s.crossed == []


def test_neutral_milestones_are_ignored_with_four_players() -> None:  # MILE-07
    s = begin(4).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].score = 19
    effects.gain_score(s, s.players[pl], 2)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.neutral_markers == {} or not any(r.state.neutral_markers.values())
    assert r.state.species[0].discovery_spaces == [None, None, None]


def test_the_probe_limit_tech_does_not_launch_two_probes() -> None:  # FAQ-21
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].techs.append("probe-dot")
    r = do(with_state(s), "launch")
    assert len([p for p in r.state.probes if p.player == pl]) == 1
    assert {"type": "launch"} not in r.legal  # one main action: no second launch in the same turn
    try:
        do(r, "launch")
    except IllegalAction:
        pass
    else:
        raise AssertionError("a second launch in the same turn was accepted")


def test_the_probe_tech_gives_publicity_for_moving_to_asteroids() -> None:  # MOVE-07, TECH-PT03
    for tech, gain in ((None, 0), ("probe-link", 1)):
        s = begin(2).state.model_copy(deep=True)
        pl = s.current_player
        ring, sector = next((ri, se) for ri in range(1, 5) for se in range(8) if solar.visible(s, ri, se)[1] == "ASTEROID")
        near = next(n for n in solar.adjacent(ring, sector) if solar.visible(s, *n)[1] not in ("ASTEROID", "PLANET:MARS"))
        s.probes.append(Probe(id="x", player=pl, ring=near[0], sector=near[1]))
        s.players[pl].movement = 2
        s.players[pl].publicity = 4
        if tech:
            s.players[pl].techs.append(tech)
        r = do(with_state(s), "move_probe", probe="x", to=[ring, sector])
        assert r.state.players[pl].publicity == 4 + gain
