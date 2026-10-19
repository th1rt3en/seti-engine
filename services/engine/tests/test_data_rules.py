"""Data tests: the engine's tables against the rules that describe them (docs/spec/untested-rules.md). Counts, names and structure."""

from collections import Counter

from test_engine import begin

from seti_engine import rival, solar, species, tables, techs
from seti_engine.engine import start
from seti_engine.models import Options

STARS = {"Kepler 22", "Proxima Centauri", "Sirius A", "Barnard's Star", "Procyon", "Vega", "61 Virginis", "Beta Pictoris"}


def test_the_solar_system_has_four_rings_of_eight_spaces_with_earth_planets_comets_and_asteroids() -> None:  # BOARD-01
    s = begin(2).state
    kinds = Counter(solar.visible(s, ring, sector)[1] for ring in range(1, 5) for sector in range(8))
    assert sum(kinds.values()) == 32 and kinds["EARTH"] == 1
    planets = {k for k in kinds if k.startswith("PLANET:")}
    assert planets >= {
        "PLANET:MERCURY",
        "PLANET:VENUS",
        "PLANET:MARS",
        "PLANET:JUPITER",
        "PLANET:SATURN",
        "PLANET:URANUS",
        "PLANET:NEPTUNE",
    }
    assert kinds["COMET"] >= 1 and kinds["ASTEROID"] >= 1
    assert "SUN" not in kinds  # MOVE-03: the Sun is not a space


def test_every_start_lays_out_eight_sectors_with_one_star_each_and_two_of_each_color() -> None:  # BOARD-02, BOARD-03, SCAN-03
    for seed in range(1, 41):
        s = start(Options(players=2, seed=seed)).state
        assert len(s.sectors) == 8 and {sec.star for sec in s.sectors} == STARS
        assert Counter(sec.color for sec in s.sectors) == {"yellow": 2, "red": 2, "blue": 2, "black": 2}
        assert solar.find_cell(s, "EARTH") is not None


def test_the_eight_stars_and_their_data_slots() -> None:  # BOARD-03, BOARD-21
    stars = [st for b in tables.stars()["boards"] for st in b["stars"]]
    assert {st["name"] for st in stars} == STARS and len(stars) == 8
    assert all(4 <= st["capacity"] <= 6 for st in stars)  # 4 to 6 tokens per star
    assert Counter(st["color"] for st in stars) == {"yellow": 2, "red": 2, "blue": 2, "black": 2}


def test_every_star_has_a_reward_for_the_first_and_for_later_wins() -> None:  # BOARD-23
    kinds = {"vp", "credit", "energy", "publicity", "data", "card_any", "card_random", "trace", "launch", "move", "tuck", "signal_token"}
    for b in tables.stars()["boards"]:
        for st in b["stars"]:
            for key in ("first_win", "later_win"):
                assert st[key] and all(r["t"] in kinds for r in st[key])
    common = tables.stars()["star_common"]  # BOARD-22: 1 publicity for each contributor, 2 points for the second position
    assert common["each_contributor"] == [{"n": 1, "t": "publicity"}] and common["second_position"] == [{"n": 2, "t": "vp"}]


def test_publicity_icons_are_on_planets_and_comets_but_not_on_earth() -> None:  # BOARD-04, MOVE-05
    assert solar.has_publicity_icon("COMET") and solar.has_publicity_icon("PLANET:MARS")
    assert not solar.has_publicity_icon("EARTH") and not solar.has_publicity_icon("ASTEROID")


def test_the_planetary_board_lists_each_planet_with_its_rewards() -> None:  # BOARD-05, BOARD-30, BOARD-31, BOARD-32
    planets = tables.planets()["planets"]
    assert {"MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE"} <= set(planets)
    order = [planets[n]["order"] for n in ("MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE")]
    assert order == sorted(order)  # the planets go outwards from the Sun
    for name, p in planets.items():
        assert p["orbit"] and p["land"] and (name == "PLUTO" or p["first_orbit"])  # Pluto has no first-orbiter bonus (PROMO-02)
    pluto = planets["PLUTO"]  # owner ruling A-001: 11 points, 3 publicity and a trace of any kind; 11 points, 4 data and a yellow trace
    assert pluto["orbit"] == [{"n": 11, "t": "vp"}, {"n": 3, "t": "publicity"}, {"kind": "any", "n": 1, "t": "trace"}]
    assert pluto["land"] == [{"n": 11, "t": "vp"}, {"n": 4, "t": "data"}, {"kind": "yellow", "n": 1, "t": "trace"}]
    assert planets["MARS"]["first_land_data"] == [2, 1]  # Mars has two first-lander spaces
    assert all(len(planets[n]["first_land_data"]) == 1 for n in ("MERCURY", "VENUS", "JUPITER", "SATURN"))
    assert len(planets["MARS"]["moons"]) == 1  # Phobos and Deimos share one moon space


def test_twelve_tech_stacks_of_four_tiles_with_the_four_bonuses() -> None:  # BOARD-50, BOARD-51, BOARD-72, BOARD-74, TECH-01
    stacks = tables.tech_board()["stacks"]
    assert set(stacks) == {"probe", "telescope", "computer"} and all(len(v) == 4 for v in stacks.values())
    assert all({t["glyph"] for t in v} == {"dot", "link", "branch", "cross"} for v in stacks.values())
    assert tables.tech_board()["bonuses_per_stack"] == [
        [{"n": 3, "t": "vp"}],
        [{"n": 1, "t": "card_any"}],
        [{"n": 1, "t": "energy"}],
        [{"n": 1, "t": "publicity"}],
    ]
    s = begin(2).state
    assert len(s.tech_stacks) == 12 and all(len(st.tiles) == 4 for st in s.tech_stacks)
    board = tables.player_board()  # BOARD-72, BOARD-74: the slots of the player board
    assert (
        board["probe_tech_slots"] == 4
        and board["telescope_tech_slots"] == 4
        and board["computer"]["tech_slots_under_spaces"] == [1, 3, 5, 6]
    )
    assert sum(len(st.tiles) for st in s.tech_stacks) == 48  # SETUP-03: 48 tech tiles


def test_the_rotation_counter_turns_ring_one_then_rings_one_and_two_then_all_three() -> None:  # BOARD-53, ROTATE-02
    s = begin(2).state.model_copy(deep=True)
    seen = []
    for _ in range(4):
        ev: list[dict[str, object]] = []
        techs.rotate_solar_system(s, ev)
        seen.append(next(e["disc"] for e in ev if e["type"] == "rotate"))
    assert seen == [1, 2, 3, 1]


def test_the_nonplayer_markers_by_number_of_players() -> None:  # BOARD-54, SETUP-20
    got = {n: start(Options(players=n, seed=1)).state.neutral_markers for n in (1, 2, 3, 4)}
    assert got == {1: {"20": 2, "30": 2}, 2: {"20": 2, "30": 2}, 3: {"20": 1, "30": 1}, 4: {"20": 0, "30": 0}}


def test_the_main_deck_and_the_supply_have_the_counts_of_the_box() -> None:  # SETUP-03
    assert sum(1 for c in tables.cards().values() if c["deck"] == "base") == 138
    assert len(tables.gold_tiles()["tiles"]) == 8  # 4 double-sided gold scoring tiles
    s = begin(2).state
    assert len(s.gold_tiles) == 4 and len(s.tech_stacks) == 12


def test_the_expansion_has_the_components_the_rulebook_lists() -> None:  # EXP-02
    assert len(tables.organizations()) == 11 and len(tables.quick_start_cards()) == 21
    assert sum(1 for c in tables.cards().values() if c["deck"] == "expansion") == 42
    assert len(tables.expansion_solo()["rival_cards"]) == 4 and len(tables.expansion_solo()["long_term"]) == 3


def test_the_mascamite_samples_and_the_exertian_cards_are_in_the_tables() -> None:  # ALIEN-DATA-03
    assert len(species.EXERTIAN_CARDS) == 15 and all(c.startswith("ET.") for c in species.EXERTIAN_CARDS)
    assert all(0 <= card[0] <= 9 for card in species.EXERTIAN_CARDS.values())  # the danger printed on the card
    assert len(species.SAMPLE_PLANETS) == 2 and set(species.SAMPLE_PLANETS) == {"jupiter", "saturn"}
    assert len(species.sample_faces()) == 7  # seven sample tokens, each with its own face


def test_the_rival_boards_and_the_progress_track() -> None:  # SOLO-DATA-01, SOLO-DATA-11
    boards = tables.solo_boards()
    assert len(boards["boards"]) == 4
    track = boards["progress_track_clockwise"]
    assert track == [f"{c}-{g}" for c in ("blue", "pink", "orange") for g in ("dot", "link", "branch", "cross")]
    assert list(rival.TRACK) == track  # the engine walks the same ring, clockwise
    assert all(b["start_space"] in track for b in boards["boards"])


def test_there_are_24_solo_objective_tiles_of_three_levels() -> None:  # SOLO-DATA-20
    tiles = tables.objectives()["objectives"]
    assert Counter(t["level"] for t in tiles) == {"I": 4, "II": 11, "III": 9}
    assert all(1 <= len(t["tasks"]) <= 3 for t in tiles)
