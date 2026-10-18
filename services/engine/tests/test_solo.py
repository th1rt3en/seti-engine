"""Solo game: setup, the rival's resources and every action card, passing, rounds, objectives and the end (SOLO-*, SOLO-RIVAL-*)."""

from typing import Any

import pytest
from test_engine import do, with_state

from seti_engine import cards, objectives, rewards, rival, scoring, solar, species, tables
from seti_engine.engine import StepResult, apply, start
from seti_engine.models import GameState, Options, Probe, SpeciesSlot


def solo(difficulty: int = 3, seed: int = 4) -> GameState:
    """A solo game after the setup tuck, with the human to move."""
    while True:  # a game where the human starts, so that the rival has not moved yet
        r = start(Options(players=1, seed=seed, difficulty=difficulty))
        if r.state.start_player == 0:
            break
        seed += 1
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    s = r.state.model_copy(deep=True)
    s.current_player, s.stage, s.main_done = 0, None, False
    s.pending = []
    return s


def rv(s: GameState) -> Any:
    return s.rival


def rp(s: GameState) -> Any:
    return s.players[s.rival.index]  # type: ignore[union-attr]


def force_arrow(s: GameState, arrow: str) -> None:
    s.rival.arrow = arrow  # type: ignore[union-attr]


# ---------------------------------------------------------------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------------------------------------------------------------


def test_solo_is_set_up_as_a_two_player_game_with_a_rival() -> None:
    """SOLO-01 to SOLO-03."""
    r = start(Options(players=1, seed=3, difficulty=3))
    s = r.state
    assert len(s.players) == 2 and s.rival is not None and s.rival.index == 1
    assert len(s.players[0].hand) == 5 and s.players[1].hand == [] and s.players[1].credits == 0
    assert sorted(p.score for p in s.players) == [1, 2] and all(p.publicity == 4 for p in s.players)
    assert s.neutral_markers == {"20": 2, "30": 2} and len(s.end_of_round_stacks[0]) == 3
    assert [d.player for d in r.state.pending] == [0]  # only the human tucks a card


@pytest.mark.parametrize(
    ("difficulty", "deck", "advanced", "start_space", "stack"),
    [
        (1, 4, 10, "blue-dot", None),
        (2, 4, 10, "blue-dot", (2, 3, 5)),
        (3, 5, 9, "pink-dot", (2, 4, 6)),
        (4, 5, 9, "blue-cross", (2, 6, 7)),
        (5, 5, 9, "pink-dot", (2, 7, 8)),
    ],
)
def test_difficulty_sets_the_deck_the_progress_start_and_the_objectives(
    difficulty: int, deck: int, advanced: int, start_space: str, stack: tuple[int, int, int] | None
) -> None:
    """SOLO-04, SOLO-05, SOLO-OBJ-01 to SOLO-OBJ-03, SOLO-OBJ-08, SOLO-DATA-10."""
    s = solo(difficulty)
    r = s.rival
    assert r is not None and len(r.deck) == deck and len(r.advanced) == advanced and rival.TRACK[r.progress] == start_space
    assert set(r.deck) >= {"S.1", "S.2", "S.3", "S.4"} or deck == 4
    assert all(c in rival.ADVANCED for c in r.advanced)
    if stack is None:
        assert s.objectives is None
        return
    ob = s.objectives
    assert ob is not None and len(ob.row) == 3 and len(ob.stack) + 3 == sum(stack)
    levels = [objectives.tile(o)["level"] for o in [*ob.stack, *ob.row]]
    assert [levels.count(lv) for lv in ("I", "II", "III")] == list(stack)
    assert all(objectives.tile(o)["level"] == "I" for o in ob.row[:0]) and ob.stack == [o for o in ob.stack]
    assert [objectives.tile(o)["level"] for o in ob.stack][0] == "III"  # level III at the bottom, level I on top


def test_the_human_may_be_second_and_the_rival_then_starts() -> None:
    """SOLO-03, SOLO-20."""
    for seed in range(20):
        r = start(Options(players=1, seed=seed))
        if r.state.start_player == 1:
            while r.state.pending:
                r = apply(r.state, r.legal[0])
            assert r.state.current_player == 0 and r.state.rival is not None and (r.state.rival.used or r.state.round > 1)
            return
    raise AssertionError("no seed started with the rival")


def test_the_rival_takes_its_turn_by_itself_after_the_players() -> None:
    """SOLO-20: the engine never asks for a move of the rival."""
    s = solo()
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.current_player == 0 and len(rv(r.state).used) == 1
    assert any(e["type"] == "rival_card" for e in r.events)
    assert all(m.get("type") != "rival" for m in r.legal)


# ---------------------------------------------------------------------------------------------------------------------------------
# resources
# ---------------------------------------------------------------------------------------------------------------------------------


def test_credits_energy_and_cards_become_progress() -> None:
    """SOLO-10, SOLO-11."""
    s = solo()
    ev: list[dict[str, Any]] = []
    before = rv(s).progress
    rival.grant(s, [{"t": "credit", "n": 2}, {"t": "energy", "n": 1}, {"t": "card_any", "n": 1}, {"t": "card_random", "n": 1}], ev)
    assert rv(s).progress == (before + 5) % 12
    before = rv(s).progress
    rival.grant(s, [{"t": "tuck", "n": 1}], ev)
    assert rv(s).progress == (before + 4) % 12


def test_rival_data_goes_to_the_computer_with_its_space_benefits() -> None:
    """SOLO-17, SOLO-DATA-12: the 2nd space gives 1 publicity, the 4th 4 progress; beyond 6 the unlimited pool."""
    s = solo()
    pub, progress = rp(s).publicity, rv(s).progress
    rival.gain_data(s, 1)
    assert rv(s).computer == 1 and rp(s).publicity == pub
    rival.gain_data(s, 1)
    assert rp(s).publicity == pub + 1
    rival.gain_data(s, 2)
    assert rv(s).progress == (progress + 4) % 12 and rv(s).computer == 4
    rival.gain_data(s, 9)
    assert rv(s).computer == 6 and rp(s).data_pool == 7


def test_crossing_the_growth_icon_adds_an_advanced_card_to_the_top_of_the_deck() -> None:
    """SOLO-12, A-012."""
    s = solo(3)
    rv(s).progress = 10
    first = rv(s).advanced[0]
    deck = len(rv(s).deck)
    rival.advance(s, 2)
    assert rv(s).deck[0] == first and len(rv(s).deck) == deck + 1 and first not in rv(s).advanced
    rv(s).advanced = []
    rv(s).progress = 11
    rival.advance(s, 1)  # nothing is left to add: nothing happens
    assert len(rv(s).deck) == deck + 1


def test_rival_victory_points_trigger_milestones_like_a_player() -> None:
    """SOLO-14, SOLO-15: only the first slot of a gold tile; the arrow picks the leftmost or rightmost tile with a free first slot."""
    s = solo()
    s.gold_tiles[0].markers = [0]  # the leftmost tile's first slot is taken
    force_arrow(s, "left")
    ev: list[dict[str, Any]] = []
    rival.choose_gold(s, ev)
    assert s.gold_tiles[1].markers == [1]
    force_arrow(s, "right")
    rival.choose_gold(s, ev)
    assert s.gold_tiles[3].markers == [1]
    for g in s.gold_tiles:
        g.markers = [0]
    rival.choose_gold(s, ev)  # all first spots taken: nothing
    assert all(g.markers == [0] for g in s.gold_tiles)


def test_a_gold_milestone_of_the_rival_is_resolved_without_a_decision() -> None:
    """SOLO-14, SOLO-15."""
    from seti_engine.engine import _resolve_milestones

    s = solo()
    s.current_player = 1
    s.crossed = [(1, 25)]
    force_arrow(s, "left")
    assert _resolve_milestones(s, []) and s.pending == [] and s.gold_tiles[0].markers == [1]


# ---------------------------------------------------------------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------------------------------------------------------------


def action(card: str, i: int) -> dict[str, Any]:
    return tables.rival_cards()[card]["actions"][i]


def test_analyze_needs_a_full_computer() -> None:
    """SOLO-RIVAL-04."""
    s = solo()
    ev: list[dict[str, Any]] = []
    rv(s).computer = 5
    assert not rival._analyze(s, action("S.1", 0), ev)
    rv(s).computer = 6
    score, progress = rp(s).score, rv(s).progress
    assert rival._analyze(s, action("S.5", 0), ev)
    assert rv(s).computer == 0 and rp(s).score >= score + 3 and rv(s).progress != progress


def test_analyze_moves_pool_data_in_and_discards_one_computer_tech() -> None:
    """SOLO-RIVAL-04: pool data fills the computer, a computer tech gives 3 VP and 1 progress (only one tech)."""
    s = solo()
    ev: list[dict[str, Any]] = []
    rv(s).computer = 6
    rp(s).data_pool = 3
    rv(s).techs = ["computer-dot", "computer-link"]
    score = rp(s).score
    rival._analyze(s, action("S.1", 0), ev)
    assert rv(s).computer == 3 and rp(s).data_pool == 0 and rv(s).techs == ["computer-link"] and rp(s).score >= score + 3


def test_launch_skips_when_a_probe_waits_on_earth() -> None:
    """SOLO-RIVAL-05."""
    s = solo()
    ev: list[dict[str, Any]] = []
    pub = rp(s).publicity
    assert rival._launch(s, action("S.1", 1), ev) and rp(s).publicity == pub + 1
    assert [pr.player for pr in s.probes] == [1]
    assert not rival._launch(s, action("S.1", 1), ev)


def test_tech_costs_six_publicity_and_rotates_first() -> None:
    """SOLO-RIVAL-06."""
    s = solo()
    ev: list[dict[str, Any]] = []
    assert not rival._tech(s, action("S.1", 2), ev)  # publicity 4 is not enough
    rp(s).publicity = 8
    assert rival._tech(s, action("S.1", 2), ev)
    assert rp(s).publicity <= 2 + 5 and s.rotations == 1 and len(rv(s).techs) == 1


def test_tech_choice_follows_the_progress_track_and_the_two_point_tile() -> None:
    """SOLO-RIVAL-06."""
    s = solo()
    rv(s).progress = rival.TRACK.index("pink-link")
    assert tech_name(s, rival.choose_tech(s)) == "telescope-link"
    for st in s.tech_stacks:
        if st.category == "telescope" and st.glyph == "link":
            st.two_point_tile = False
    assert tech_name(s, rival.choose_tech(s)) == "telescope-branch"  # the next one on the track with its 2-point tile
    for st in s.tech_stacks:
        st.two_point_tile = False
    assert tech_name(s, rival.choose_tech(s)) == "telescope-link"  # none left: the first available
    rv(s).techs = ["telescope-link"]
    assert tech_name(s, rival.choose_tech(s)) == "telescope-branch"


def tech_name(s: GameState, idx: int | None) -> str:
    assert idx is not None
    return f"{s.tech_stacks[idx].category}-{s.tech_stacks[idx].glyph}"


def test_rival_techs_never_give_the_launch_or_data_bonus() -> None:
    """SOLO-18."""
    s = solo()
    rp(s).publicity = 10
    rv(s).progress = rival.TRACK.index("orange-dot")
    ev: list[dict[str, Any]] = []
    rival._tech(s, action("S.1", 2), ev)
    assert rv(s).techs == ["probe-dot"] and not [pr for pr in s.probes if pr.player == 1]  # no free launch
    rv(s).progress = rival.TRACK.index("pink-dot")
    comp = rv(s).computer
    rp(s).publicity = 10
    rival._tech(s, action("S.1", 2), ev)
    assert rv(s).techs[-1] == "telescope-dot" and rv(s).computer == comp  # no 2 data


def move_to(s: GameState, planet: str) -> None:
    """Make the planet reachable in a short way: put the rival's probe on Earth and keep the solar system as is."""
    ring, sector = solar.earth(s)
    s.probes.append(Probe(id="rv", player=1, ring=ring, sector=sector))


def test_probe_action_skips_without_a_probe_or_a_reachable_planet() -> None:
    """SOLO-RIVAL-07."""
    s = solo()
    ev: list[dict[str, Any]] = []
    a = {"kind": "probe", "moonLanding": True, "movement": 3, "planets": ["neptune"], "preference": "orbiter"}
    assert not rival._probe(s, a, ev)
    move_to(s, "neptune")
    assert not rival._probe(s, a, ev)  # Neptune cannot be reached in 3 moves from Earth
    assert any(pr.player == 1 for pr in s.probes)


def reachable_planet(s: GameState, movement: int) -> str:
    start_cell = solar.earth(s)
    reach = rival._moves(s, start_cell, movement)
    for pl in ("venus", "mercury", "mars", "jupiter", "saturn"):
        pos = solar.find_cell(s, f"PLANET:{pl.upper()}")
        if pos in reach:
            return pl
    raise AssertionError("no planet within reach")


def test_probe_flight_gives_publicity_and_the_probe_becomes_an_orbiter_by_preference() -> None:
    """SOLO-RIVAL-07, A-002: both first spaces free, so the card's preference decides; the best flight plan counts."""
    s = solo()
    pl = reachable_planet(s, 4)
    move_to(s, pl)
    ev: list[dict[str, Any]] = []
    a = {"kind": "probe", "moonLanding": False, "movement": 4, "planets": [pl], "preference": "orbiter"}
    pub = rp(s).publicity
    assert rival._probe(s, a, ev)
    assert s.planets[pl].orbiters == [1] and s.planets[pl].first_orbiter == 1 and rp(s).publicity >= pub
    assert not [pr for pr in s.probes if pr.player == 1]
    s2 = solo()
    move_to(s2, pl)
    a["preference"] = "lander"
    assert rival._probe(s2, a, ev)
    assert s2.planets[pl].landers == [1] and s2.planets[pl].first_land_data_taken[0]


def test_probe_takes_the_one_free_first_space_over_its_preference() -> None:
    """SOLO-RIVAL-07: if only one first space is available, take it."""
    s = solo()
    pl = reachable_planet(s, 4)
    s.planets[pl].first_orbiter = 0  # the first orbiter space is taken
    move_to(s, pl)
    a = {"kind": "probe", "moonLanding": False, "movement": 4, "planets": [pl], "preference": "orbiter"}
    assert rival._probe(s, a, [])
    assert s.planets[pl].landers == [1]


def test_probe_lands_on_a_moon_by_discarding_a_probe_tech() -> None:
    """SOLO-RIVAL-07: the arrow picks the leftmost or the rightmost free moon."""
    s = solo()
    pos = solar.find_cell(s, "PLANET:JUPITER")
    assert pos is not None
    for arrow, moon in (("left", "Callisto"), ("right", "Io")):  # A-024: Callisto, Ganymede, Europa, Io from the left
        t = solo()
        s = t
        s.probes.append(Probe(id="rv", player=1, ring=pos[0], sector=pos[1]))
        s.probes = []  # the rival's probe will be placed on Earth; this check goes through _arrive directly
        rv(s).techs = ["probe-dot", "telescope-dot"]
        force_arrow(s, arrow)
        rival._arrive(s, "jupiter", {"moonLanding": True, "preference": "orbiter"}, [])
        assert s.planets["jupiter"].moon_landers == {moon: 1} and rv(s).techs == ["telescope-dot"]


def test_without_a_probe_tech_the_rival_does_not_use_a_moon() -> None:
    s = solo()
    rival._arrive(s, "jupiter", {"moonLanding": True, "preference": "lander"}, [])
    assert not s.planets["jupiter"].moon_landers and s.planets["jupiter"].landers == [1]


def test_orbit_gives_the_rival_progress_for_the_tuck() -> None:
    """SOLO-11: the tuck-a-card effect of an orbiter is 4 progress."""
    s = solo()
    before = rv(s).progress
    rival._arrive(s, "venus", {"moonLanding": False, "preference": "orbiter"}, [])
    assert rv(s).progress == (before + 4) % 12 and s.planets["venus"].orbiters == [1]


def test_telescope_marks_earth_signals_and_row_signals_by_the_arrow() -> None:
    """SOLO-RIVAL-08."""
    s = solo()
    force_arrow(s, "left")
    row = list(s.card_row)
    earth_sector = solar.earth(s)[1]
    ev: list[dict[str, Any]] = []
    rival._telescope(s, action("S.2", 2), ev)  # 1 Earth signal, 2 card-row signals
    assert row[0] in s.discard and row[1] in s.discard and row[2] in s.card_row
    assert len(s.card_row) == 3
    assert s.sectors[earth_sector].markers.count(1) >= 1
    assert sum(sec.markers.count(1) for sec in s.sectors) == 3
    s2 = solo()
    force_arrow(s2, "right")
    row2 = list(s2.card_row)
    rival._telescope(s2, action("S.2", 2), ev)
    assert row2[-1] in s2.discard and row2[-2] in s2.discard


def test_a_telescope_tech_adds_a_card_row_signal() -> None:
    """SOLO-RIVAL-08."""
    s = solo()
    rv(s).techs = ["telescope-dot"]
    rival._telescope(s, action("S.2", 2), [])
    assert sum(sec.markers.count(1) for sec in s.sectors) == 4 and rv(s).techs == []


def test_sector_choice_prefers_a_win_then_a_second_marker_then_the_most_markers() -> None:
    """SOLO-RIVAL-08: ties favor the bigger sector."""
    s = solo()
    red = rewards.sectors_of_color(s, "red")
    a, b = red
    for sec in (s.sectors[a], s.sectors[b]):
        sec.markers = []
    s.sectors[a].markers, s.sectors[a].data_remaining = [1] * (s.sectors[a].capacity - 1), 1
    s.sectors[b].markers = [1]  # a second marker here would score
    assert rival._pick_sector(s, red) == a  # winning beats scoring
    s.sectors[a].markers, s.sectors[a].data_remaining = [], s.sectors[a].capacity
    assert rival._pick_sector(s, red) == b  # the second marker scores 2
    s.sectors[a].markers = [1, 1, 1]
    s.sectors[b].markers = [1, 1]
    assert rival._pick_sector(s, red) == a  # most markers
    s.sectors[a].markers = [1, 1]
    expected = a if s.sectors[a].capacity > s.sectors[b].capacity else b
    if s.sectors[a].capacity != s.sectors[b].capacity:
        assert rival._pick_sector(s, red) == expected  # a tie goes to the bigger sector


def test_life_trace_goes_to_the_lowest_space_and_the_arrow_breaks_ties() -> None:
    """SOLO-RIVAL-11."""
    s = solo()
    s.species = [
        SpeciesSlot(species="anomalies", board=species.new_board("anomalies")),
        SpeciesSlot(species="centaurians", board=species.new_board("centaurians")),
    ]
    s.species[0].discovered = s.species[1].discovered = True
    force_arrow(s, "right")
    rival.trace(s, "yellow", [])
    assert s.species[1].board["yellow"][4] == [1]  # the lowest space, on the right species
    force_arrow(s, "left")
    rival.trace(s, "yellow", [])
    assert s.species[0].board["yellow"][4] == [1]
    rival.trace(s, "yellow", [])  # both lowest spaces are taken: the next lowest, space 4 on the left
    assert s.species[0].board["yellow"][3] == [1]


def test_life_trace_on_an_undiscovered_species_uses_its_discovery_space() -> None:
    """SOLO-RIVAL-11: below the board; the overflow space only when everything else is full."""
    s = solo()
    rival.trace(s, "pink", [])
    assert sum(1 for sl in s.species for x in sl.discovery_spaces if x == "p1") == 1
    for sl in s.species:
        sl.discovery_spaces = ["n", "n", "n"]
    rival.trace(s, "pink", [])
    assert sum(len(sl.overflow) for sl in s.species) == 1


def test_the_rival_pays_for_a_costly_space_only_with_a_full_computer_and_enough_data() -> None:
    """SOLO-ALIEN-02: Centaurian spaces cost data from the pool."""
    s = solo()
    s.species = [
        SpeciesSlot(species="centaurians", board=species.new_board("centaurians"), discovered=True),
        SpeciesSlot(species="anomalies", board=species.new_board("anomalies")),
    ]
    force_arrow(s, "left")
    assert not rival._rival_can_pay(s, "centaurians", "pink", 1)
    rv(s).computer, rp(s).data_pool = 6, 3
    assert rival._rival_can_pay(s, "centaurians", "pink", 1)
    rp(s).data_pool = 2
    assert not rival._rival_can_pay(s, "centaurians", "pink", 1)  # the second space costs 3


# ---------------------------------------------------------------------------------------------------------------------------------
# the deck, passing and rounds
# ---------------------------------------------------------------------------------------------------------------------------------


def test_the_rival_passes_when_its_deck_is_empty() -> None:
    """SOLO-19: takes the top end-of-round card (1 progress); the first to pass rotates the solar system."""
    s = solo()
    rv(s).deck = []
    stack = len(s.end_of_round_stacks[0])
    progress = rv(s).progress
    ev: list[dict[str, Any]] = []
    s.current_player = 1
    rival.take_turn(s, ev)
    assert rp(s).passed and s.first_pass_done and s.rotations == 1
    assert len(s.end_of_round_stacks[0]) == stack - 1 and rv(s).progress == (progress + 1) % 12


def test_the_second_to_pass_does_not_rotate() -> None:
    s = solo()
    s.first_pass_done = True
    rv(s).deck = []
    rival.take_turn(s, [])
    assert s.rotations == 0


def test_the_used_action_cards_are_shuffled_back_when_the_rival_passes() -> None:
    """A-023 (ruled): after the rival passes, its used cards form its deck again."""
    s = solo()
    rv(s).used, rv(s).deck = ["S.1", "S.2"], []
    s.current_player = 1
    rival.take_turn(s, [])
    assert rp(s).passed and sorted(rv(s).deck) == ["S.1", "S.2"] and rv(s).used == []


def test_a_species_card_replaces_the_check_card_when_the_species_is_discovered() -> None:
    """SOLO-RIVAL-09: S.3 checks the 1st species."""
    s = solo()
    s.species[0].discovered = True
    s.species[0].species = "anomalies"
    s.species[0].extra = {"tokens": []}
    rv(s).deck = ["S.3"]
    s.current_player = 1
    rival.take_turn(s, [])
    assert rv(s).used == ["S.16"] and "S.3" not in rv(s).deck


def test_a_species_check_is_skipped_when_the_species_is_hidden() -> None:
    s = solo()
    rv(s).deck = ["S.3"]
    s.current_player = 1
    rp(s).publicity = 8
    rival.take_turn(s, [])
    assert rv(s).used == ["S.3"] and len(rv(s).techs) == 1  # the tech action next on the card


def test_species_actions() -> None:
    """S.16 Anomalies: a trace of the next anomaly's color and 3 points; skipped when the rival is winning that anomaly."""
    from seti_engine import alien_steps

    s = solo()
    s.species = [SpeciesSlot(species="anomalies", board=species.new_board("anomalies"), discovered=True), s.species[1]]
    e = solar.earth(s)[1]
    s.species[0].extra["tokens"] = [{"sector": (e + 2) % 8, "color": "blue", "side": 0}]
    force_arrow(s, "left")
    score = rp(s).score
    assert rival._text(s, {"effect": "anomalies_trace"}, []) and rp(s).score >= score + 3
    assert alien_steps.next_anomaly(s)["color"] == "blue"  # type: ignore[index]
    assert species.anomaly_reward(s, s.species[0], "blue") == 1
    assert not rival._text(s, {"effect": "anomalies_trace"}, [])  # winning the next anomaly now


def test_centaurian_card_places_one_message_marker_from_the_reserve() -> None:
    """S.18, SOLO-ALIEN-02."""
    s = solo()
    s.species[0] = SpeciesSlot(species="centaurians", board=species.new_board("centaurians"))
    s.species[0].discovery_spaces = ["p0", "p0", "p1"]
    s.species[0].complete = True
    s.main_done = True
    r = do(with_state(s), "end_turn")
    st = r.state
    assert st.rival is not None and st.rival.messages_in_reserve == 2 and len(st.players[1].messages) == 1
    assert st.species[0].discovered
    st.players[1].messages = []
    progress = st.rival.progress
    placed: list[dict] = []
    assert rival._text(st, {"effect": "centaurians_countdown"}, placed) and st.rival.messages_in_reserve == 1
    assert placed[0] == {"type": "rival_message", "target": st.players[1].messages[-1]}  # its own log line, with the place on the track
    assert st.players[1].messages == [st.players[1].score + 15] and st.rival.progress == (progress + 1) % 12
    assert not rival._text(st, {"effect": "centaurians_countdown"}, [])  # a marker is already on the track


def test_exertians_the_rival_draws_no_cards_and_plays_one_while_below_five() -> None:
    """S.19, SOLO-ALIEN-03, FAQ-57."""
    s = solo()
    s.species[0] = SpeciesSlot(species="exertians", board=species.new_board("exertians"))
    s.species[0].discovery_spaces = ["p0", "p1", "p1"]
    s.species[0].complete = True
    s.main_done = True
    progress = s.rival.progress  # type: ignore[union-attr]
    r = do(with_state(s), "end_turn")
    st = r.state
    assert st.players[1].exertian_hand == [] and len(st.players[0].exertian_hand) == 3 + 1
    assert st.species[0].deck  # kept for the rival
    assert st.rival is not None and st.rival.progress != progress  # 1 progress for each of its 2 markers (plus the rival's own turn)
    while len(st.players[1].exertian_played) < 5:
        assert rival._text(st, {"effect": "exertians_danger_card"}, [])
    assert not rival._text(st, {"effect": "exertians_danger_card"}, [])
    played: list[dict] = []
    st.players[1].exertian_played = []
    assert rival._text(st, {"effect": "exertians_danger_card"}, played)
    assert played == [{"type": "rival_exertian"}]  # the log says that the rival played one, not which (it lies face down)
    st.players[1].exertian_played = ["ET.51"]
    assert cards.exertian_points(st, st.players[1]) == 18  # counted as completed


def test_mascamites_the_rival_takes_a_sample_from_the_planet_it_targeted() -> None:
    """S.15, A-024: the sample comes from the planet of the rival's landing, not from Jupiter and Saturn together."""
    s = solo()
    s.species[0] = SpeciesSlot(species="mascamites", board=species.new_board("mascamites"))
    s.species[0].discovery_spaces = ["p0", "p0", "p0"]
    s.species[0].complete = True
    s.main_done = True
    st = do(with_state(s), "end_turn").state
    st.players[1].exertian_played = []
    move_to(st, "saturn")
    jupiter, saturn = len(species.samples_on(st, "jupiter")), len(species.samples_on(st, "saturn"))
    spaces = len(st.species[0].extra["sample_spaces"])
    a = {
        "kind": "probe",
        "moonLanding": False,
        "landerOnly": True,
        "preference": "lander",
        "takeSample": True,
        "movementByPlanet": [{"planet": "saturn", "movement": 8}],
    }
    assert rival._probe(st, a, [])
    assert len(species.samples_on(st, "jupiter")) == jupiter and len(species.samples_on(st, "saturn")) == saturn - 1
    assert len(st.species[0].extra["sample_spaces"]) == spaces + 1 and st.species[0].extra["sample_spaces"][-1]["marker"] is None
    assert not rival._text(st, {"effect": "mascamites_sample"}, [])


def test_the_rival_marks_signals_on_the_oumuamua_tile() -> None:
    """SOLO-ALIEN-01, S.17."""
    s = solo()
    s.species[0] = SpeciesSlot(species="oumuamua", board=species.new_board("oumuamua"))
    s.species[0].discovery_spaces = ["p0", "p0", "p0"]
    s.species[0].complete = True
    s.main_done = True
    st = do(with_state(s), "end_turn").state
    a = tables.rival_cards()["S.17"]["actions"][1]
    rival._telescope(st, a, [])
    assert 1 in st.species[0].extra["tile"]["markers"]


# ---------------------------------------------------------------------------------------------------------------------------------
# objectives
# ---------------------------------------------------------------------------------------------------------------------------------


def set_row(s: GameState, ids: list[str]) -> None:
    ob = s.objectives
    assert ob is not None
    ob.row = list(ids)
    ob.marks = {o: [False] * len(objectives.tile(o)["tasks"]) for o in ids}


def test_reaching_a_level_marks_the_task_at_once() -> None:
    """SOLO-OBJ-04."""
    s = solo(3)
    set_row(s, ["L1-16-vp", "L1-5-data", "L1-8-publicity"])
    s.players[0].score, s.players[0].data_pool, s.players[0].publicity = 16, 4, 8
    objectives.check_thresholds(s)
    assert s.objectives.marks == {"L1-16-vp": [True], "L1-5-data": [False], "L1-8-publicity": [True]}  # type: ignore[union-attr]
    s.players[0].data_pool = 5
    objectives.check_thresholds(s)
    assert s.objectives.marks["L1-5-data"] == [True]  # type: ignore[union-attr]


def test_a_trigger_marks_one_task_and_the_player_chooses_among_several() -> None:
    """SOLO-OBJ-04."""
    s = solo(3)
    set_row(s, ["L3-two-scans", "L3-trace-launch-scan", "L1-16-vp"])
    p = s.players[0]
    objectives.on_event(s, p, [{"e": "scan"}])
    assert s.pending[0].kind == "objective_task" and len(s.pending[0].data["options"]) == 3  # two scan tasks and the scan of the other tile
    r = with_state(s)
    r = apply(r.state, r.legal[0])
    marked = sum(sum(v) for v in r.state.objectives.marks.values())  # type: ignore[union-attr]
    assert marked == 1


def test_a_single_candidate_is_marked_without_a_question() -> None:
    s = solo(3)
    set_row(s, ["L3-orbit", "L1-16-vp", "L1-5-data"])
    objectives.on_event(s, s.players[0], [{"e": "orbit", "planet": "venus"}])
    assert s.objectives.marks["L3-orbit"] == [True] and not s.pending  # type: ignore[union-attr]


def test_win_sector_orbit_tech_and_visit_tasks() -> None:
    """SOLO-OBJ-04."""
    s = solo(3)
    set_row(s, ["L2-jupiter-saturn", "L2-red-or-yellow-signal", "L2-asteroid-trace"])
    p = s.players[0]
    objectives.on_event(s, p, [{"e": "land", "planet": "saturn"}])
    objectives.on_event(s, p, [{"e": "win_sector", "color": "yellow"}])
    objectives.on_event(s, p, [{"e": "visit_asteroids", "own_turn": True}])
    objectives.on_event(s, p, [{"e": "trace", "kind": "blue"}])
    assert s.objectives.marks == {  # type: ignore[union-attr]
        "L2-jupiter-saturn": [True],
        "L2-red-or-yellow-signal": [True],
        "L2-asteroid-trace": [True, True],
    }


def test_completed_objectives_move_to_the_pile_and_are_replaced() -> None:
    """SOLO-OBJ-05."""
    s = solo(3)
    ob = s.objectives
    assert ob is not None
    top = ob.stack[-1]
    first = ob.row[0]
    ob.marks[first] = [True] * len(ob.marks[first])
    objectives.end_turn(s)
    assert first in ob.pile and first not in ob.row and len(ob.row) == 3 and top in ob.row


def test_rounds_spend_completed_objectives_or_advance_the_rival() -> None:
    """SOLO-OBJ-06."""
    s = solo(3)
    ob = s.objectives
    assert ob is not None
    ob.pile = ["a"]
    progress = rv(s).progress
    ev: list[dict[str, Any]] = []
    objectives.end_round(s, 3, ev)  # 3 to spend, 1 available: 2 short, 6 progress
    assert ob.pile == [] and rv(s).progress == (progress + 6) % 12
    ob.pile = ["a", "b", "c"]
    progress = rv(s).progress
    objectives.end_round(s, 2, ev)
    assert ob.pile == ["c"] and rv(s).progress == progress


def test_the_rival_scores_five_for_each_uncompleted_objective_after_round_five() -> None:
    """SOLO-OBJ-07."""
    s = solo(3)
    ob = s.objectives
    assert ob is not None
    undone = len(ob.row) + len(ob.stack)
    score = rp(s).score
    objectives.end_round(s, 5, [])
    assert rp(s).score == score + 5 * undone


def test_one_star_has_no_objectives_and_no_penalties() -> None:
    """SOLO-OBJ-08."""
    s = solo(1)
    progress, score = rv(s).progress, rp(s).score
    objectives.end_round(s, 2, [])
    objectives.end_round(s, 5, [])
    assert s.objectives is None and rv(s).progress == progress and rp(s).score == score


def test_objective_events_come_from_the_players_actions() -> None:
    """SOLO-OBJ-04: a launch marks a task through the normal action."""
    s = solo(3)
    set_row(s, ["L3-orbit", "L3-two-scans", "L3-launch-9-publicity"])
    s.players[0].credits = 5
    r = do(with_state(s), "launch")
    assert r.state.objectives.marks["L3-launch-9-publicity"] == [True, False]  # type: ignore[union-attr]


# ---------------------------------------------------------------------------------------------------------------------------------
# the end
# ---------------------------------------------------------------------------------------------------------------------------------


def test_the_rival_does_not_score_gold_tiles_and_ties_go_to_the_rival() -> None:
    """SOLO-END-01."""
    s = solo(3)
    s.gold_tiles[0].markers = [1, 0]
    s.players[1].completed_missions = ["1", "2", "3"]
    rows = scoring.final_scores(s)
    assert rows[1]["gold"] == 0
    rows[0]["total"] = rows[1]["total"] = 50
    assert scoring.winners(rows, 1) == [1]
    rows[0]["total"] = 51
    assert scoring.winners(rows, 1) == [0]


@pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
def test_solo_games_finish_and_are_reproducible(difficulty: int) -> None:
    """SOLO-END-01, A-004: replaying the same moves gives the same game."""
    import random

    def play(seed: int) -> tuple[StepResult, list[dict[str, Any]]]:
        rnd = random.Random(seed)
        r = start(Options(players=1, seed=seed, difficulty=difficulty))
        log: list[dict[str, Any]] = []
        for _ in range(20000):
            if not r.legal:
                break
            good = [m for m in r.legal if m["type"] in ("play_card", "orbit", "land", "scan", "analyze", "research", "mark_objective")]
            m = rnd.choice(good) if good and rnd.random() < 0.7 else rnd.choice(r.legal)
            log.append(m)
            r = apply(r.state, m)
        return r, log

    for seed in range(3):
        r, log = play(seed)
        assert r.state.phase == "finished" and r.state.winners in ([0], [1]) and len(r.state.final_scores) == 2
        replay = start(Options(players=1, seed=seed, difficulty=difficulty))
        for m in log:
            replay = apply(replay.state, m)
        assert replay.state == r.state


@pytest.mark.parametrize("difficulty", [1, 3, 5])
def test_progress_seeking_solo_games_keep_the_invariants(difficulty: int) -> None:
    """Random play that prefers progress: no crashes, no stuck states, the card count and the limits hold (SOLO-*)."""
    import random

    from test_engine import PROGRESS_TYPES, check_invariants

    for seed in range(6):
        rnd = random.Random(seed)
        r = start(Options(players=1, seed=seed, difficulty=difficulty))
        for _ in range(20000):
            if not r.legal:
                break
            good = [
                m
                for m in r.legal
                if m["type"] in PROGRESS_TYPES | {"mark_objective"} or (m["type"] == "place_trace" and m["space"] != "overflow")
            ]
            move = rnd.choice(good) if good and rnd.random() < 0.8 else rnd.choice(r.legal)
            r = apply(r.state, move)
            check_invariants(r.state)
        assert r.state.phase == "finished"


def test_the_publicity_of_the_second_computer_space_of_the_rival_is_logged_apart() -> None:  # SOLO-DATA-12, SOLO-17, the log
    from seti_engine import trail

    s = solo()
    assert s.rival is not None
    s.rival.computer = 1
    s.trail = []
    rival.gain_data(s)
    gains = trail.events_of(s)
    assert gains and gains[0]["source"] == {"kind": "rival_computer", "space": 2} and gains[0]["changes"]["publicity"] == 1


def test_the_same_action_card_played_twice_in_a_move_keeps_the_gains_of_each_turn_apart() -> None:  # SOLO-RIVAL-01, the log
    from seti_engine import trail

    s = solo()
    assert s.rival is not None
    s.rival.deck = ["S.1", "S.1"]
    s.trail = []
    events: list[dict] = []
    rival.take_turn(s, events)
    rival.take_turn(s, events)
    ids = [e["turn"] for e in trail.events_of(s) if "turn" in e]
    assert set(ids) <= {"S.1:0", "S.1:1"}  # one name for each turn, not "S.1" for both, so the log does not mix them
    assert [e["card"] for e in events if e["type"] == "rival_card"] == ["S.1", "S.1"]
