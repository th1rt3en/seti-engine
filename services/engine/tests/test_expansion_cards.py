"""The 42 main-deck cards of the Space Agencies expansion (EXP-03), one test each: SA.1 to SA.42 (the card numbers printed on them)."""

from typing import Any

import pytest
from test_cards import give, put_probe, ready, settle
from test_engine import do, with_state

from seti_engine import card_defs, cards, solar, tables
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import GameState, MissionState, Probe


def go(s: GameState, n: int, answer: bool = True) -> StepResult:
    """Play SA.n as the main action; `answer` settles the decisions with their first legal move."""
    give(s, f"SA.{n}")
    r = do(with_state(s), "play_card", card=f"SA.{n}")
    return settle(r) if answer else r


def me(r: StepResult) -> Any:
    return r.state.players[r.state.current_player]


def probe_at(s: GameState, ring: int, sector: int, pid: str, player: int | None = None) -> None:
    s.probes.append(Probe(id=pid, player=s.current_player if player is None else player, ring=ring, sector=sector))


def other(s: GameState) -> int:
    return 1 - s.current_player


def hand_of(s: GameState, *ids: str) -> None:
    s.players[s.current_player].hand = list(ids)


def test_all_42_cards_are_defined_and_playable() -> None:  # EXP-03
    ids = [f"SA.{n}" for n in range(1, 43)]
    assert all(tables.cards()[c]["deck"] == "expansion" and cards.playable(c) for c in ids)
    assert len([c for c in tables.cards() if c.startswith("SA.")]) == 42


@pytest.mark.parametrize("n", range(1, 43))
def test_every_card_can_be_played_and_ends_in_the_right_place(n: int) -> None:  # EXP-03, PLAY-02
    s = ready(credits=9, energy=9)
    probe_at(s, *solar.earth(s), "e1")
    put_probe(s, "jupiter", "j1")
    s.planets["mars"].orbiters = [s.current_player]
    s.players[s.current_player].orbiters["mars"] = 1
    r = go(s, n)
    st, p, cid = r.state, me(r), f"SA.{n}"
    assert not st.queue and st.playing is None
    d = card_defs.CARDS[cid]
    if "mission" in d:
        assert cid in [m.card for m in p.missions] + p.completed_missions
    elif "end" in d:
        assert cid in p.end_cards
    else:
        assert cid in st.discard or cid in p.hand  # a few return to the hand


def test_sa1_reusable_lander_returns_when_the_planet_had_a_lander() -> None:  # SA.1
    s = ready()
    put_probe(s, "venus")
    s.planets["venus"].landers = [other(s)]
    r = go(s, 1)
    assert "SA.1" in me(r).hand and me(r).landers["venus"] == 1
    s = ready()
    put_probe(s, "venus")
    r = go(s, 1)
    assert "SA.1" not in me(r).hand and "SA.1" in r.state.discard


def test_sa2_tracking_satellite_gives_the_icon_once_per_card_shown() -> None:  # SA.2
    s = ready()
    hand_of(s, "SA.2", "SA.3", "SA.5", "SA.1")  # corners: data (SA.2 itself is played), publicity, publicity, publicity
    r = go(s, 2, answer=False)
    assert r.state.pending[0].kind == "corner_pick"
    data = me(r).data_pool
    r = apply(r.state, {"type": "corner_pick", "kind": "publicity"})
    assert me(r).publicity == 5 + 3
    assert me(r).data_pool == data


def test_sa3_deep_space_network_gives_three_signal_tokens() -> None:  # SA.3
    assert me(go(ready(), 3)).signal_tokens == 3


def test_sa4_breakthrough_message() -> None:  # SA.4
    r = go(ready(), 4)
    assert me(r).signal_tokens == 1 and me(r).movement == 1


def test_sa5_servicing_mission_returns_next_to_earth_only() -> None:  # SA.5
    s = ready()
    ring, sector = solar.adjacent(*solar.earth(s))[0]
    probe_at(s, ring, sector, "n1")
    r = go(s, 5)
    assert "SA.5" in me(r).hand and me(r).movement == 1
    r = go(ready(), 5)
    assert "SA.5" not in me(r).hand


def test_sa6_live_landing_broadcast_marks_a_signal_where_you_landed() -> None:  # SA.6
    s = ready()
    pr = put_probe(s, "mars")
    before = len(s.sectors[pr.sector].markers)
    r = go(s, 6)
    assert len(r.state.sectors[pr.sector].markers) >= before + 1 and me(r).landers["mars"] == 1 and me(r).movement >= 1


def test_sa7_twin_probes_researches_a_probe_tech_and_has_a_quick_mission() -> None:  # SA.7
    s = ready()
    r = go(s, 7)
    assert any(t.startswith("probe-") for t in me(r).techs)
    st = r.state.model_copy(deep=True)
    assert {"type": "complete_mission", "card": "SA.7"} not in legal_moves(st)
    put_probe(st, "venus", "v1")
    put_probe(st, "mars", "m1")
    assert {"type": "complete_mission", "card": "SA.7"} in legal_moves(st)


def test_sa8_quantum_data_storage_scores_remaining_data() -> None:  # SA.8
    r = go(ready(), 8)
    assert any(t.startswith("computer-") for t in me(r).techs) and "SA.8" in me(r).end_cards
    p = me(r)
    p.data_pool = 4
    assert cards.end_points(r.state, p) == 12


def test_sa9_lunar_crater_researches_a_telescope_tech_and_asks_for_3_sector_wins() -> None:  # SA.9
    r = go(ready(), 9)
    assert any(t.startswith("telescope-") for t in me(r).techs)
    st = r.state.model_copy(deep=True)
    assert {"type": "complete_mission", "card": "SA.9"} not in legal_moves(st)
    for i in range(3):
        st.sectors[i].winners.append(st.current_player)
    assert {"type": "complete_mission", "card": "SA.9"} in legal_moves(st)


def test_sa10_first_human_in_space_scores_remaining_publicity() -> None:  # SA.10
    s = ready(publicity=0)
    r = go(s, 10)
    assert me(r).publicity == 10 and "SA.10" in me(r).end_cards
    me(r).publicity = 7
    assert cards.end_points(r.state, me(r)) == 7


def test_sa11_psyche_probe_launches_and_has_the_asteroid_mission() -> None:  # SA.11
    s = ready(publicity=0)
    r = go(s, 11)
    assert any(pr.player == r.state.current_player for pr in r.state.probes) and me(r).publicity == 1
    st = r.state.model_copy(deep=True)
    put_probe(st, "ASTEROID", "a1")
    assert {"type": "complete_mission", "card": "SA.11"} in legal_moves(st)


def test_sa12_two_planet_flyby_gives_3_vp_for_two_different_planets() -> None:  # SA.12
    s = ready()
    r = go(s, 12)
    st, p = r.state, me(r)
    assert p.movement == 2
    score = p.score
    cards.on_move(st, p, 2, 2, "PLANET:VENUS", [])
    assert p.score == score
    cards.on_move(st, p, 2, 2, "PLANET:MARS", [])
    cards.on_move(st, p, 2, 2, "PLANET:JUPITER", [])
    assert p.score - score == 3  # once


def test_sa13_jcmt_scans_and_gives_a_signal_token() -> None:  # SA.13
    s = ready()
    r = go(s, 13, answer=False)
    assert r.state.scan_steps and me(r).signal_tokens == 0  # the scan comes first
    for _ in range(40):  # finish the scan without using a signal token
        if not r.state.pending:
            break
        r = apply(r.state, next(m for m in r.legal if m["type"] != "scan_token"))
    assert me(r).signal_tokens == 1 and not r.state.scan_steps


def test_sa14_reusable_rocket_returns_when_another_player_is_on_earth() -> None:  # SA.14
    s = ready()
    probe_at(s, *solar.earth(s), "o1", other(s))
    r = go(s, 14)
    assert "SA.14" in me(r).hand and any(pr.player == r.state.current_player for pr in r.state.probes)
    r = go(ready(), 14)
    assert "SA.14" not in me(r).hand


def test_sa15_iterative_engineering_gains_the_tile_bonus_again() -> None:  # SA.15
    s = ready(energy=0)
    st = s.tech_stacks[0]
    st.tiles[0] = "energy"
    energy_before = s.players[s.current_player].energy
    r = go(s, 15, answer=False)
    r = apply(r.state, {"type": "take_tech", "stack": 0})
    r = settle(r)
    assert me(r).energy - energy_before >= 2


def test_sa16_astronaut_training_gives_publicity_and_a_zero_publicity_mission() -> None:  # SA.16
    s = ready(publicity=0)
    r = go(s, 16)
    assert me(r).publicity == 4
    st = r.state.model_copy(deep=True)
    assert {"type": "complete_mission", "card": "SA.16"} not in legal_moves(st)
    me(Ctx(st)).publicity = 0
    assert {"type": "complete_mission", "card": "SA.16"} in legal_moves(st)


class Ctx:
    """A tiny wrapper so that `me` works on a bare state."""

    def __init__(self, state: GameState) -> None:
        self.state = state


def test_sa17_paid_media_coverage_turns_credits_into_points_and_publicity() -> None:  # SA.17
    s = ready(credits=3, publicity=0)
    r = go(s, 17, answer=False)
    assert r.state.pending[0].kind == "spend_credit"
    score = me(r).score
    r = do(r, "spend_credit")
    r = do(r, "spend_credit")
    r = do(r, "spend_done")
    assert me(r).credits == 1 and me(r).score - score == 4 and me(r).publicity == 4


def test_sa18_contracted_research_copies_a_tech_someone_has() -> None:  # SA.18
    s = ready()
    s.players[other(s)].techs = ["probe-dot"]
    r = go(s, 18, answer=False)
    assert me(r).publicity == 0
    stacks = {m["stack"] for m in r.legal if m["type"] == "take_tech"}
    expected = {i for i, t in enumerate(s.tech_stacks) if f"{t.category}-{t.glyph}" == "probe-dot"}
    assert stacks == expected


def test_sa19_new_assignment_turns_an_orbiter_into_a_probe() -> None:  # SA.19
    s = ready()
    st = s.planets["mars"]
    st.orbiters, st.first_orbiter = [s.current_player], s.current_player
    s.players[s.current_player].orbiters["mars"] = 1
    r = go(s, 19)
    pos = solar.find_cell(r.state, "PLANET:MARS")
    assert me(r).orbiters["mars"] == 0 and any((pr.ring, pr.sector) == pos for pr in r.state.probes if pr.player == r.state.current_player)


def test_sa20_well_executed_project_repeats_a_corner_three_times() -> None:  # SA.20
    s = ready(publicity=0)
    hand_of(s, "SA.20", "SA.1")  # SA.1's corner is 1 publicity
    r = go(s, 20)
    assert me(r).publicity == 1 + 3


def test_sa21_orbital_refueling_triggers_at_a_planet_with_your_orbiter() -> None:  # SA.21
    s = ready()
    s.players[s.current_player].orbiters["mars"] = 1
    s.players[s.current_player].missions.append(MissionState(card="SA.21", kind="trigger", used=[False, False]))
    p = s.players[s.current_player]
    cards.fire(s, p, [{"e": "visit", "planet": "venus"}], [])
    assert not s.pending
    cards.fire(s, p, [{"e": "visit", "planet": "mars"}], [])
    assert s.pending[0].kind == "mission_trigger"


def test_sa22_tess_satellite_marks_two_signals_without_data() -> None:  # SA.22
    s = ready()
    pl = s.current_player
    s.sectors[2].markers = [pl, pl, pl]
    s.sectors[2].data_remaining = max(0, s.sectors[2].capacity - 3)
    data = s.players[pl].data_pool
    r = go(s, 22, answer=False)
    assert {m["sector"] for m in r.legal if m["type"] == "mark_signal"} == {2}
    r = do(r, "mark_signal", sector=2)
    assert r.state.sectors[2].winners == [pl] and me(r).data_pool == data  # the two signals completed the sector, which was resolved


def test_sa23_neutral_buoyancy_training() -> None:  # SA.23
    s = ready(publicity=0)
    r = go(s, 23)
    assert me(r).publicity == 1
    st, p = r.state, me(r)
    hand = len(p.hand)
    cards.fire(st, p, [{"e": "launch"}], [])
    r2 = apply(st, {"type": "cover", "card": "SA.23", "circle": 0})
    assert len(me(r2).hand) == hand + 1
    score = me(r2).score
    cards.fire(r2.state, me(r2), [{"e": "orbit_or_land"}], [])
    r3 = apply(r2.state, {"type": "cover", "card": "SA.23", "circle": 1})
    assert me(r3).score - score == 3


@pytest.mark.parametrize(("n", "cat", "check"), [(24, "probe", "launch"), (25, "telescope", "token"), (26, "computer", "data")])
def test_sa24_to_26_research_missions(n: int, cat: str, check: str) -> None:  # SA.24, SA.25, SA.26
    s = ready()
    s.players[s.current_player].techs = ["probe-dot"]  # the probe limit is 2, so that two launches fit
    r = go(s, n)
    st, p = r.state, me(r)
    assert p.publicity >= 1
    before = (len(st.probes), p.signal_tokens, p.data_pool)
    for circle in range(2):
        cards.fire(st, p, [{"e": "tech", "cat": cat}], [])
        st = apply(st, {"type": "cover", "card": f"SA.{n}", "circle": circle}).state
        p = st.players[st.current_player]
    after = (len(st.probes), p.signal_tokens, p.data_pool)
    gained = {"launch": after[0] - before[0], "token": after[1] - before[1], "data": after[2] - before[2]}[check]
    assert gained == 2
    cards.fire(st, p, [{"e": "tech", "cat": cat}], [])
    assert not st.pending  # both circles are used


def test_sa27_better_solar_panels() -> None:  # SA.27
    s = ready(energy=0)
    probe_at(s, 2, 1, "x1")
    probe_at(s, 3, 2, "x2")
    assert me(go(s, 27)).energy == 2
    s = ready(energy=3)
    probe_at(s, 2, 1, "x1")
    assert me(go(s, 27)).energy == 3


def test_sa28_restructuring_discards_for_income_and_has_a_quick_mission() -> None:  # SA.28
    s = ready(credits=1, energy=0)
    hand_of(s, "SA.28", "SA.1", "SA.3")  # SA.1 gives a credit, SA.3 an energy
    r = go(s, 28, answer=False)
    r = do(r, "restructure_card", card="SA.1")
    r = do(r, "restructure_card", card="SA.3")
    assert (me(r).credits, me(r).energy) == (1, 1)
    st = r.state.model_copy(deep=True)
    st.players[st.current_player].credits = st.players[st.current_player].energy = 0
    assert {"type": "complete_mission", "card": "SA.28"} in legal_moves(st)


def test_sa29_abandoned_mission_returns_a_mission_for_data() -> None:  # SA.29
    s = ready()
    s.players[s.current_player].missions.append(MissionState(card="SA.21", kind="trigger", used=[False, False]))
    data = s.players[s.current_player].data_pool
    r = go(s, 29)
    assert "SA.21" in me(r).hand and not me(r).missions and me(r).data_pool - data == 2


def test_sa30_akatsuki_orbiter_orbits_and_counts_computer_techs() -> None:  # SA.30
    s = ready(publicity=0)
    put_probe(s, "venus")
    s.players[s.current_player].techs = ["computer-a", "computer-b", "probe-dot"]
    data = s.players[s.current_player].data_pool
    r = go(s, 30)
    assert me(r).orbiters["venus"] == 1 and me(r).publicity >= 1 and me(r).data_pool - data >= 2


def test_sa31_ingenuity_helicopter_lands_and_scores_planets_with_two_landers() -> None:  # SA.31
    s = ready()
    put_probe(s, "venus")
    r = go(s, 31)
    p = me(r)
    assert p.landers["venus"] == 1 and "SA.31" in p.end_cards
    p.landers.update({"venus": 2, "mars": 2, "jupiter": 1})
    assert cards.end_points(r.state, p) == 12


def test_sa32_murep_idea_competition() -> None:  # SA.32
    s = ready(publicity=0)
    hand_of(s, "SA.32", "SA.1", "SA.3")
    r = go(s, 32)
    assert me(r).publicity == 1 and len(me(r).hand) == 2 and "SA.1" in r.state.discard and "SA.3" in r.state.discard


def test_sa33_delayed_launch_launches_when_you_pass() -> None:  # SA.33
    s = ready()
    r = go(s, 33)
    st = r.state
    st.main_done = False
    r = apply(st, {"type": "pass"})
    assert r.state.pending[0].kind == "mission_trigger"
    n = len(r.state.probes)
    r = apply(r.state, {"type": "cover", "card": "SA.33", "circle": 0})
    assert len(r.state.probes) == n + 1


def test_sa34_private_sector_investment_tucks_and_draws_per_tech() -> None:  # SA.34
    s = ready()
    s.players[s.current_player].techs = ["probe-dot", "probe-x", "computer-a"]
    r = go(s, 34, answer=False)
    hand = len(me(r).hand)
    card = next(m for m in r.legal if m["type"] == "tuck")["card"]
    r = do(r, "tuck", card=card)
    r = settle(r)
    assert len(me(r).hand) >= hand - 1 + 2 and card in me(r).tucked


def test_sa35_nasa_exoplanet_archive() -> None:  # SA.35
    r = go(ready(), 35)
    assert me(r).signal_tokens == 1
    st = r.state.model_copy(deep=True)
    p = st.players[st.current_player]
    assert {"type": "complete_mission", "card": "SA.35"} not in legal_moves(st)
    p.data_pool, p.computer = 6, [True] * 6
    assert {"type": "complete_mission", "card": "SA.35"} in legal_moves(st)
    p.data_pool, p.computer = 5, [True] * 6
    assert {"type": "complete_mission", "card": "SA.35"} not in legal_moves(st)


def test_sa36_big_ear_marks_a_yellow_a_red_and_a_blue_signal() -> None:  # SA.36
    s = ready()
    r = go(s, 36, answer=False)
    colors = []
    while r.state.pending:
        d = r.state.pending[0]
        colors.append(d.data["color"])
        r = apply(r.state, r.legal[0])
    assert sorted(colors) == ["blue", "red", "yellow"]


def test_sa37_pandora_satellite_marks_where_you_already_have_a_signal_without_data() -> None:  # SA.37
    s = ready()
    pl = s.current_player
    s.sectors[1].markers = [pl]
    s.sectors[4].markers = [other(s), pl]
    data = s.players[pl].data_pool
    r = go(s, 37)
    assert r.state.sectors[1].markers.count(pl) == 2 and r.state.sectors[4].markers.count(pl) == 2 and me(r).data_pool == data
    assert r.state.sectors[0].markers.count(pl) == 0


def test_sa38_space_rendezvous() -> None:  # SA.38
    s = ready(publicity=0)
    probe_at(s, 2, 3, "a")
    probe_at(s, 2, 3, "b", other(s))
    score = s.players[s.current_player].score
    r = go(s, 38)
    assert me(r).score - score == 3 and me(r).movement == 1
    r = go(ready(), 38)
    assert me(r).score == ready().players[r.state.current_player].score


def test_sa39_grand_tour_program() -> None:  # SA.39
    r = go(ready(), 39)
    p = me(r)
    assert p.movement == 2 and "SA.39" in p.end_cards
    p.orbiters = {"mars": 1}
    p.landers = {"venus": 1, "mars": 1, "io": 1}
    assert cards.end_points(r.state, p) == 4


def test_sa40_hall_effect_thruster() -> None:  # SA.40
    assert me(go(ready(), 40)).movement == 5


def test_sa41_exoplanet_survey() -> None:  # SA.41
    r = go(ready(publicity=0), 41)
    p = me(r)
    assert p.signal_tokens == 1 and p.publicity == 1 and "SA.41" in p.end_cards
    st = r.state
    assert cards.end_points(st, p) == 0
    for color in ("yellow", "red", "blue", "black"):
        i = next(k for k, sec in enumerate(st.sectors) if sec.color == color)
        st.sectors[i].markers.append(p.index)
    assert cards.end_points(st, p) == 4


def test_sa42_lofar_array() -> None:  # SA.42
    r = go(ready(), 42)
    st, p = r.state, me(r)
    assert "SA.42" in p.end_cards
    for sec in st.sectors:
        sec.markers = [x for x in sec.markers if x != p.index]
        sec.winners = [x for x in sec.winners if x != p.index]
    assert cards.end_points(st, p) == 0
    for sec in st.sectors[:7]:
        sec.markers.append(p.index)
    assert cards.end_points(st, p) == 0
    st.sectors[7].winners.append(p.index)  # a won sector counts as well
    assert cards.end_points(st, p) == 8
