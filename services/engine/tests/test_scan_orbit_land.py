"""Orbit, land, scan, signals, sector completion and life traces (ORBIT, LAND, SCAN, SECTOR, LIFE rules)."""

from typing import Any

from test_engine import begin, decisions, do, with_state

from seti_engine import effects, rewards, solar
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import GameState, Probe


def put_probe_on(s: GameState, planet: str) -> str:
    """Place the current player's probe on the named planet's current space."""
    ring, sector = solar.find_cell(s, f"PLANET:{planet.upper()}")  # type: ignore[misc]
    s.probes.append(Probe(id="t1", player=s.current_player, ring=ring, sector=sector))
    return "t1"


def setup_at(planet: str, credits: int = 5, energy: int = 5) -> tuple[StepResult, int]:
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].credits, s.players[pl].energy = credits, energy
    put_probe_on(s, planet)
    return with_state(s), pl


def settle(r: StepResult) -> StepResult:
    """Answer pending decisions with the first legal move until none are left."""
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    return r


def test_orbit_costs_and_first_orbiter_bonus() -> None:
    """ORBIT-01 to ORBIT-04, ORBIT-05, INCOME-02, BOARD-30, FAQ-10: the probe leaves the board for good."""
    r, pl = setup_at("venus")
    before = r.state.players[pl].score
    r1 = do(r, "orbit", probe="t1")
    assert r1.state.players[pl].credits == 4 and r1.state.players[pl].energy == 4
    r2 = settle(r1)
    p = r2.state.players[pl]
    assert not r2.state.probes and p.orbiters == {"venus": 1}
    assert p.score == before + 3 + 6  # first orbit 3 + Venus orbit reward 6 VP
    assert r2.state.planets["venus"].orbiters == [pl]
    assert len(p.tucked) == 2  # ORBIT-05: the tuck effect (the player may also decline)


def test_second_orbiter_gets_no_first_bonus() -> None:
    """ORBIT-04: only the first player to orbit scores 3."""
    r, pl = setup_at("venus")
    r.state.planets["venus"].orbiters.append(1 - pl)
    r.state.planets["venus"].first_orbiter = 1 - pl
    before = r.state.players[pl].score
    r2 = settle(do(r, "orbit", probe="t1"))
    assert r2.state.players[pl].score == before + 6


def test_orbit_needs_credit_and_energy() -> None:
    """ORBIT-01."""
    r, _ = setup_at("venus", credits=0)
    assert not [m for m in legal_moves(r.state) if m["type"] == "orbit"]
    r, _ = setup_at("venus", energy=0)
    assert not [m for m in legal_moves(r.state) if m["type"] == "orbit"]


def test_no_orbit_or_land_on_earth_or_empty_space() -> None:
    """ORBIT-01, LAND-01."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    s.players[s.current_player].credits = s.players[s.current_player].energy = 5
    ring, sector = solar.earth(s)
    s.probes.append(Probe(id="t1", player=s.current_player, ring=ring, sector=sector))
    assert not [m for m in legal_moves(s) if m["type"] in ("orbit", "land")]


def test_land_cost_and_first_lander_data() -> None:
    """LAND-01, LAND-03, LAND-04, LAND-06, BOARD-31."""
    r, pl = setup_at("mercury", energy=3)
    r2 = settle(do(r, "land", probe="t1"))
    p = r2.state.players[pl]
    assert p.energy == 0 and p.landers == {"mercury": 1}
    assert p.data_pool >= 3  # the first lander's data (3 at Mercury)
    assert p.score >= r.state.players[pl].score + 12
    assert any(sl.discovery_spaces[1] == f"p{pl}" or sl.overflow for sl in r2.state.species)  # one yellow trace was marked


def test_land_costs_less_with_an_orbiter_and_with_tech() -> None:
    """LAND-01, LAND-02."""
    r, pl = setup_at("mercury", energy=2)
    assert not [m for m in legal_moves(r.state) if m["type"] == "land"]
    r.state.planets["mercury"].orbiters.append(1 - pl)
    assert [m for m in legal_moves(r.state) if m["type"] == "land"]
    r, pl = setup_at("mercury", energy=2)
    r.state.players[pl].techs.append("probe-branch")
    assert [m for m in legal_moves(r.state) if m["type"] == "land"]


def test_moon_landing_needs_tech_and_one_lander_per_moon() -> None:
    """LAND-05, BOARD-32, TECH-PT04."""
    r, pl = setup_at("jupiter", energy=9)
    assert not [m for m in legal_moves(r.state) if m["type"] == "land" and "moon" in m]
    r.state.players[pl].techs.append("probe-cross")
    moons = [m for m in legal_moves(r.state) if m["type"] == "land" and "moon" in m]
    assert {m["moon"] for m in moons} == {"Io", "Europa", "Callisto", "Ganymede"}
    r2 = settle(do(r, "land", probe="t1", moon="Io"))
    assert r2.state.planets["jupiter"].moon_landers == {"Io": pl}
    assert r2.state.players[pl].energy == 9 - 3 + 4  # cost 3, Io gives 4 energy
    s = r2.state.model_copy(deep=True)
    s.main_done = False
    s.probes.append(Probe(id="t2", player=pl, ring=1, sector=0))
    put = solar.find_cell(s, "PLANET:JUPITER")
    assert put is not None
    s.probes[-1].ring, s.probes[-1].sector = put
    assert "Io" not in {m["moon"] for m in legal_moves(s) if m["type"] == "land" and "moon" in m}


def test_mars_first_two_landers_choose_a_data_space() -> None:
    """LAND-04: Mars has two first-lander data spaces."""
    r, pl = setup_at("mars", energy=3)
    r2 = do(r, "land", probe="t1")
    assert r2.state.pending[0].kind == "land_data_slot"
    from seti_engine.move_notes import note

    # the page shows the two spaces on the planet, each with its data: slot 0 gives 2, slot 1 gives 1
    amounts = {m["slot"]: note(r2.state, m)["land_data"]["data"] for m in r2.legal if m["type"] == "choose_land_slot"}  # type: ignore[index]
    assert amounts == {0: 2, 1: 1}
    r3 = settle(apply(r2.state, {"type": "choose_land_slot", "slot": 1}))
    assert r3.state.planets["mars"].first_land_data_taken == [False, True]


def test_second_signal_position_scores_two() -> None:
    """SECTOR-03, SECTOR-04, BOARD-22: markers replace the data from left to right; the second position of the data slot scores 2."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    ev: list[dict[str, Any]] = []
    pl = s.current_player
    rewards.mark_signal(s, s.players[1 - pl], 0, ev)
    before = s.players[pl].score
    rewards.mark_signal(s, s.players[pl], 0, ev)
    assert s.players[pl].score == before + 2


def test_excess_markers_get_no_data_but_count() -> None:
    """SECTOR-05, FAQ-13: marking a signal always works; with the slot full it is an excess signal."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    ev: list[dict[str, Any]] = []
    cap = s.sectors[0].capacity
    s.sectors[0].markers = [1 - pl] * (cap - 1)
    s.sectors[0].data_remaining = 1
    rewards.mark_signal(s, s.players[pl], 0, ev)
    assert s.sectors[0].data_remaining == 0 and s.completed == [0]
    pool = s.players[pl].data_pool
    rewards.mark_signal(s, s.players[pl], 0, ev)
    assert s.players[pl].data_pool == pool and len(s.sectors[0].markers) == cap + 1 and s.completed == [0]


def complete(s: GameState, index: int, markers: list[int]) -> StepResult:
    """Put `markers` (in placement order) into a sector with the last data left, then end the turn so the sector resolves."""
    sec = s.sectors[index]
    sec.markers = markers[:-1]
    sec.data_remaining = 1
    sec.capacity = len(markers)
    ev: list[dict[str, Any]] = []
    rewards.mark_signal(s, s.players[markers[-1]], index, ev)
    s.main_done = True
    s.current_player = markers[-1]
    return settle(do(with_state(s), "end_turn"))


def test_sector_winner_second_place_and_reset() -> None:
    """SECTOR-10 to SECTOR-15, BOARD-22: every contributor gains 1 publicity."""
    r = begin(3)
    s = r.state.model_copy(deep=True)
    pubs = [p.publicity for p in s.players]
    r2 = complete(s, 0, [0, 1, 0, 1, 0, 2])  # player 0: 3 markers, 1: 2, 2: 1
    st = r2.state
    assert st.sectors[0].winners == [0] and st.players[0].sector_wins == 1
    assert st.sectors[0].markers == [1]  # second place keeps one marker on the first space
    assert st.sectors[0].data_remaining == st.sectors[0].capacity - 1
    for q in range(3):
        assert st.players[q].publicity >= min(10, pubs[q] + 1)  # SECTOR-12 (contributors)
    assert st.completed == []


def test_sector_tie_goes_to_the_later_marker() -> None:
    """SECTOR-11, FAQ-16."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    r2 = complete(s, 3, [0, 1, 0, 1])
    assert r2.state.sectors[3].winners == [1]
    assert r2.state.sectors[3].markers == [0]


def test_single_player_sector_has_no_second_place() -> None:
    """SECTOR-13."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    r2 = complete(s, 2, [0, 0, 0])
    assert r2.state.sectors[2].markers == [] and r2.state.sectors[2].data_remaining == r2.state.sectors[2].capacity


def test_sector_can_be_won_again_with_later_reward() -> None:
    """SECTOR-14, SECTOR-15, FAQ-12: the winner's marker beside the star does not count; rewards differ by order of winning."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    r2 = complete(s, 1, [0, 0, 0])
    s2 = r2.state.model_copy(deep=True)
    s2.phase, s2.stage, s2.pending = "play", None, []
    s2.players[0].passed = False
    r3 = complete(s2, 1, [1, 1, 1])
    assert r3.state.sectors[1].winners == [0, 1]


def test_trace_goes_to_a_discovery_space_or_overflow() -> None:
    """LIFE-01, LIFE-03, ALIEN-DATA-13: the discovery and overflow spaces are on the planetary board."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    ev: list[dict[str, Any]] = []
    from seti_engine.models import Decision

    s.pending = [Decision(kind="trace", player=pl, data={"color": "pink"})]
    moves = legal_moves(s)
    assert {"type": "place_trace", "slot": 0, "space": "overflow", "color": "pink"} in moves
    assert {"type": "place_trace", "slot": 1, "space": "discovery", "color": "pink"} in moves
    before = s.players[pl].score
    rewards.place_trace(s, s.players[pl], {"slot": 0, "space": "discovery", "color": "pink"}, ev)
    assert s.species[0].discovery_spaces[0] == f"p{pl}"
    assert s.players[pl].score == before + 5  # left slot: 5 VP and 1 publicity
    rewards.place_trace(s, s.players[pl], {"slot": 0, "space": "overflow", "color": "pink"}, ev)
    assert s.species[0].overflow == [pl] and s.players[pl].score == before + 8  # overflow: 3 VP


def test_any_trace_can_use_any_free_color() -> None:
    """LIFE-01: a universal trace stands for any of the three kinds."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    from seti_engine.models import Decision

    s.pending = [Decision(kind="trace", player=s.current_player, data={"color": "any"})]
    s.species[0].discovery_spaces[1] = "n"
    colors = {m["color"] for m in decisions(legal_moves(s)) if m["space"] == "discovery" and m["slot"] == 0}
    assert colors == {"pink", "blue"}


def test_three_discovery_spaces_complete_the_species() -> None:
    """ALIEN-01 (flag only; effects come with the species slice)."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    ev: list[dict[str, Any]] = []
    for c in ("pink", "yellow", "blue"):
        rewards.place_trace(s, s.players[0], {"slot": 1, "space": "discovery", "color": c}, ev)
    assert s.species[1].complete and not s.species[1].discovered
    assert effects.PUBLICITY_CAP == 10


def test_excess_data_is_discarded_but_the_marker_is_placed() -> None:  # SECTOR-02, RES-01, BOARD-70
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    p = s.players[pl]
    p.data_pool = 6
    p.computer = [True] * len(p.computer)  # nothing can be placed first, so the gain is simply cut at 6
    ev: list[dict[str, Any]] = []
    markers = len(s.sectors[0].markers)
    remaining = s.sectors[0].data_remaining
    rewards.mark_signal(s, p, 0, ev)
    assert p.data_pool == 6 and not s.pending
    assert len(s.sectors[0].markers) == markers + 1 and s.sectors[0].data_remaining == remaining - 1
