"""What each tech did for a player, counted from the replay of a game (stats.tech_use). Every case plays the real move through the
engine and counts it with the
state before and after, so the shapes of the engine's events are the ones that are counted."""

from collections import Counter
from typing import Any

import pytest
from test_engine import do
from test_scan_orbit_land import settle, setup_at
from test_stats import file_of, play
from test_tech_scan import scan_ready

from seti_engine import solar, stats
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import ComputerTech, GameState, Probe

PREFIX = "techuse."


def counted(before: GameState, r: StepResult, seat: int, action: dict[str, Any]) -> Counter[str]:
    c: Counter[str] = Counter()
    stats.tech_use(c, before, r.state, seat, action, r.events)
    return Counter({k: v for k, v in c.items() if v})


def test_nothing_is_counted_for_a_move_that_no_tech_changes() -> None:
    r = scan_ready()
    pl = r.state.current_player
    move = next(m for m in r.legal if m["type"] == "scan_earth")
    assert counted(r.state, do(r, "scan_earth", sector=move["sector"]), pl, move) == Counter()


# --- orange (probe) techs
# -----------------------------------------------------------------------------------------------------------------------


def a_probe_beside_an_asteroid(s: GameState, pl: int) -> tuple[GameState, dict[str, Any]]:
    """A state with a probe of the player next to the asteroid field, and the move into it."""
    goal = solar.find_cell(s, "ASTEROID")
    assert goal is not None
    for ring in range(1, 6):
        for sector in range(8):
            t = s.model_copy(deep=True)
            t.probes = [Probe(id="t1", player=pl, ring=ring, sector=sector)]
            t.players[pl].movement = 9
            for m in legal_moves(t):
                if m["type"] == "move_probe" and tuple(m["to"]) == goal:
                    return t, m
    raise AssertionError("no probe can move into the asteroid field")


def test_asteroid_skimmer_counts_the_moves_into_an_asteroid_after_the_tech() -> None:  # TECH-PT02
    r = scan_ready()
    pl = r.state.current_player
    s, move = a_probe_beside_an_asteroid(r.state, pl)
    s.pending = []
    assert counted(s, apply(s, move), pl, move) == Counter(), "without the tech nothing is counted"
    s.players[pl].techs.append("probe-link")
    assert counted(s, apply(s, move), pl, move) == Counter({"techuse.probe-link.asteroids": 1})
    elsewhere = next(m for m in legal_moves(s) if m["type"] == "move_probe" and tuple(m["to"]) != tuple(move["to"]))
    assert counted(s, apply(s, elsewhere), pl, elsewhere) == Counter(), "a move to another space is not an asteroid move"


def test_soft_landers_count_the_landing_actions() -> None:  # TECH-PT03
    r, pl = setup_at("mercury", energy=2)
    move = {"type": "land", "probe": "t1"}
    assert counted(r.state, _land(r, move), pl, move) == Counter()  # without the tech nothing is counted
    r2, pl = setup_at("mercury", energy=2)
    r2.state.players[pl].techs.append("probe-branch")
    assert counted(r2.state, _land(r2, move), pl, move) == Counter({"techuse.probe-branch.lands": 1})


def _land(r: StepResult, move: dict[str, Any]) -> StepResult:
    """The landing with enough energy and an orbiter of another player there, so that the move is legal with and without the tech."""
    s = r.state.model_copy(deep=True)
    s.players[s.current_player].energy = 9
    s.planets["mercury"].orbiters.append(1 - s.current_player)
    return settle(apply(s, move))


def test_moon_rover_counts_the_landings_on_a_moon_not_the_landings_on_the_planet() -> None:  # TECH-PT04
    r, pl = setup_at("jupiter", energy=9)
    r.state.players[pl].techs.append("probe-cross")
    on_moon = {"type": "land", "probe": "t1", "moon": "Io"}
    r2 = settle(apply(r.state, on_moon))
    assert counted(r.state, r2, pl, on_moon) == Counter({"techuse.probe-cross.moons": 1})
    on_planet = {"type": "land", "probe": "t1"}
    if on_planet in legal_moves(r.state):
        r3 = settle(apply(r.state, on_planet))
        assert "techuse.probe-cross.moons" not in counted(r.state, r3, pl, on_planet)
    r4, pl = setup_at("jupiter", energy=9)  # without the tech a moon cannot be landed on
    assert on_moon not in legal_moves(r4.state)


# --- pink (telescope) techs
# ---------------------------------------------------------------------------------------------------------------------


def test_earth_scope_counts_the_scans_of_a_sector_next_to_earth() -> None:  # TECH-TT01
    r = scan_ready("telescope-dot")
    pl = r.state.current_player
    e = solar.earth(r.state)[1]
    here = {"type": "scan_earth", "sector": e}
    assert counted(r.state, do(r, "scan_earth", sector=e), pl, here) == Counter()
    for side in ((e - 1) % 8, (e + 1) % 8):
        move = {"type": "scan_earth", "sector": side}
        assert counted(r.state, do(r, "scan_earth", sector=side), pl, move) == Counter({"techuse.telescope-dot.adjacent": 1})


def test_mercury_scope_counts_the_signals_in_the_sector_of_mercury() -> None:  # TECH-TT03
    r = scan_ready("telescope-link")
    pl = r.state.current_player
    move = {"type": "scan_mercury"}
    assert counted(r.state, do(r, "scan_mercury"), pl, move) == Counter({"techuse.telescope-link.mercury": 1})


def test_card_scope_counts_the_cards_of_the_hand_discarded_for_a_signal() -> None:  # TECH-TT02
    r = scan_ready("telescope-branch")
    pl = r.state.current_player
    move = next(m for m in r.legal if m["type"] == "scan_hand_discard")
    assert counted(r.state, do(r, "scan_hand_discard", card=move["card"]), pl, move) == Counter({"techuse.telescope-branch.discards": 1})


def test_scan_booster_counts_the_launches_and_the_free_movements_apart() -> None:  # TECH-TT04, FAQ-22
    r = scan_ready("telescope-cross")
    pl = r.state.current_player
    launch = {"type": "scan_probe", "mode": "launch"}
    move = {"type": "scan_probe", "mode": "move"}
    assert counted(r.state, do(r, "scan_probe", mode="launch"), pl, launch) == Counter({"techuse.telescope-cross.launches": 1})
    assert counted(r.state, do(r, "scan_probe", mode="move"), pl, move) == Counter({"techuse.telescope-cross.moves": 1})


def test_a_scan_step_is_not_counted_without_the_tech_of_that_step() -> None:  # the moves cannot be made, so they are counted for nobody
    r = scan_ready("telescope-link")
    pl = r.state.current_player
    assert not [m for m in r.legal if m["type"] in ("scan_hand_discard", "scan_probe")]
    assert counted(r.state, do(r, "scan_mercury"), pl, {"type": "scan_mercury"}).get("techuse.telescope-branch.discards", 0) == 0


# --- blue (computer) techs
# ----------------------------------------------------------------------------------------------------------------------

COMPUTER_TECHS = ("computer-dot", "computer-link", "computer-branch", "computer-cross")


@pytest.mark.parametrize("tech", COMPUTER_TECHS)
def test_a_computer_tech_counts_its_two_points_and_its_bottom_bonus(tech: str) -> None:  # TECH-20, TECH-CT01 to TECH-CT04
    r = scan_ready()
    s = r.state.model_copy(deep=True)
    s.pending = []
    pl = s.current_player
    p = s.players[pl]
    p.computer = [False] * 6
    p.computer_techs = {0: ComputerTech(tech=tech)}  # the top row space 0 is the upper space of the tech
    p.techs.append(tech)
    p.data_pool = 2
    score = p.score
    top = {"type": "place_data"}
    r1 = apply(s, top)
    assert r1.state.players[pl].score == score + 2
    assert counted(s, r1, pl, top) == Counter({f"techuse.{tech}.top": 1, f"techuse.{tech}.vp": 2})
    lower = {"type": "place_lower", "slot": 0}
    assert lower in legal_moves(r1.state)
    r2 = apply(
        r1.state, lower
    )  # not settled: the events of the move itself are the ones that are counted (a card may be asked for after it)
    assert counted(r1.state, r2, pl, lower) == Counter({f"techuse.{tech}.bottom": 1})


def test_a_data_on_a_space_that_is_not_a_tech_is_not_counted() -> None:  # TECH-20
    r = scan_ready()
    s = r.state.model_copy(deep=True)
    s.pending = []
    pl = s.current_player
    s.players[pl].computer = [False] * 6
    s.players[pl].computer_techs = {}
    s.players[pl].data_pool = 1
    assert counted(s, apply(s, {"type": "place_data"}), pl, {"type": "place_data"}) == Counter()


# --- over whole games
# ---------------------------------------------------------------------------------------------------------------------------

VALID = {
    "probe-link": {"asteroids"},
    "probe-branch": {"lands"},
    "probe-cross": {"moons"},
    "telescope-dot": {"adjacent"},
    "telescope-link": {"mercury"},
    "telescope-branch": {"discards"},
    "telescope-cross": {"launches", "moves"},
    **{t: {"top", "vp", "bottom"} for t in COMPUTER_TECHS},
}


def test_the_counters_of_whole_games_are_only_for_the_techs_that_the_player_has_and_agree_with_each_other() -> None:
    seen: Counter[str] = Counter()
    for seed in range(3, 15):
        options, actions = play(seed, 2)
        for p in stats.game_stats(file_of(options, actions))["players"]:
            c = p["counters"]
            for key, n in c.items():
                if not key.startswith(PREFIX):
                    continue
                tech, what = key[len(PREFIX) :].rsplit(".", 1)
                assert what in VALID[tech], key  # a name that is counted, and never the first tech of a type
                assert c.get(f"tech.{tech}", 0) >= 1, f"{key} is counted but the player has no {tech} at the end"
                seen[key] += n
            for tech in COMPUTER_TECHS:
                assert c.get(f"techuse.{tech}.vp", 0) == 2 * c.get(f"techuse.{tech}.top", 0)
    assert not any(k.startswith("techuse.probe-dot") for k in seen)
    assert len(seen) >= 6, "the random games use several of the techs, so the counters are exercised end to end"
