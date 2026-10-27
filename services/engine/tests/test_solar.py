"""Solar system: stacking, adjacency, rotation and pushed probes (BOARD-10 to BOARD-16, ROTATE-01 to ROTATE-05, A-007)."""

import pytest

from seti_engine import solar
from seti_engine.models import GameState, Options, Probe
from seti_engine.setup import new_game


def fresh(angles=(0, 0, 0)) -> GameState:
    s = new_game(Options(players=2, seed=1))
    s.disc_angles = list(angles)
    return s


def test_every_space_has_a_visible_cell() -> None:
    s = fresh()
    for ring in range(1, 5):
        for sector in range(8):
            assert solar.visible(s, ring, sector)[1] != "NULL"


@pytest.mark.parametrize("angles", [(0, 0, 0), (1, 2, 3), (7, 0, 4), (3, 3, 3)])
def test_earth_and_each_planet_appear_once(angles) -> None:
    s = fresh(angles)
    cells = [solar.visible(s, r, c)[1] for r in range(1, 5) for c in range(8)]
    for wanted in ["EARTH", *[f"PLANET:{p}" for p in ("MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE")]]:
        assert cells.count(wanted) == 1, wanted


def test_planets_stay_in_their_rings() -> None:
    """Disc 1 carries Mercury, Venus, Earth (ring 1); disc 2 Mars (ring 2); disc 3 Jupiter and Saturn (ring 3); the base Uranus, Neptune."""
    s = fresh((2, 5, 1))
    rings = {
        name: solar.find_cell(s, f"PLANET:{name}")[0] for name in ("MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE")
    }
    assert rings == {"MERCURY": 1, "VENUS": 1, "MARS": 2, "JUPITER": 3, "SATURN": 3, "URANUS": 4, "NEPTUNE": 4}
    assert solar.earth(s)[0] == 1


def test_adjacency() -> None:
    """BOARD-16: same ring neighbours (sector 7 touches 0), same sector neighbouring rings, nothing diagonal, nothing past ring 4."""
    assert set(solar.adjacent(1, 0)) == {(1, 7), (1, 1), (2, 0)}
    assert set(solar.adjacent(4, 7)) == {(4, 6), (4, 0), (3, 7)}
    assert set(solar.adjacent(2, 3)) == {(2, 2), (2, 4), (1, 3), (3, 3)}


def test_rotation_order_and_amount() -> None:
    """ROTATE-02 / BOARD-10 / BOARD-11: disc 1, then discs 2+1, then 3+2+1, one eighth turn each."""
    s = fresh()
    solar.rotate(s)
    assert s.disc_angles == [1, 0, 0]
    solar.rotate(s)
    assert s.disc_angles == [2, 1, 0]
    solar.rotate(s)
    assert s.disc_angles == [3, 2, 1] and s.rotations == 3
    solar.rotate(s)
    assert s.disc_angles == [4, 2, 1]


def test_a_rotation_moves_content_counter_clockwise() -> None:
    s = fresh()
    mercury = solar.find_cell(s, "PLANET:MERCURY")
    solar.rotate(s)  # disc 1 only
    after = solar.find_cell(s, "PLANET:MERCURY")
    assert after == (mercury[0], (mercury[1] + 1) % 8)


def test_a_full_cycle_returns_the_discs() -> None:
    s = fresh((2, 6, 3))
    for _ in range(24):
        solar.rotate(s)
    assert s.disc_angles == [2, 6, 3]


def test_probe_on_a_rotating_disc_rides_along() -> None:
    s = fresh()
    ring, sector = solar.find_cell(s, "PLANET:VENUS")
    s.probes.append(Probe(id="p", player=0, ring=ring, sector=sector))
    solar.rotate(s)  # disc 1 rotates and Venus is on disc 1
    assert (s.probes[0].ring, s.probes[0].sector) == (ring, (sector + 1) % 8)
    assert solar.visible(s, s.probes[0].ring, s.probes[0].sector)[1] == "PLANET:VENUS"


def test_probe_on_the_base_does_not_move_when_nothing_covers_it() -> None:
    s = fresh()
    ring, sector = solar.find_cell(s, "PLANET:URANUS")
    s.probes.append(Probe(id="p", player=0, ring=ring, sector=sector))
    for _ in range(6):
        solar.rotate(s)
        assert solar.visible(s, s.probes[0].ring, s.probes[0].sector)[1] == "PLANET:URANUS" or (s.probes[0].ring, s.probes[0].sector) != (
            ring,
            sector,
        )


def _pushed_case():
    """Find a state where a probe on a static cell gets covered by a rotating disc's solid cell, by brute force over angles and cells."""
    for a1 in range(8):
        for a2 in range(8):
            for a3 in range(8):
                for ring in (1, 2, 3):
                    for sector in range(8):
                        s = fresh((a1, a2, a3))
                        k0 = solar.visible(s, ring, sector)[0]
                        if k0 <= s.rotations % 3 + 1:
                            continue
                        s.probes.append(Probe(id="p", player=0, ring=ring, sector=sector))
                        gains = solar.rotate(s)
                        if (s.probes[0].ring, s.probes[0].sector) != (ring, sector):
                            return (a1, a2, a3), (ring, sector), s, gains
    raise AssertionError("no push scenario found")


def test_a_probe_in_a_cutout_is_pushed_along_the_rotation() -> None:
    """A-007 point 3: a solid cell of a rotating disc arriving over a probe pushes it one space, counter-clockwise, for free."""
    angles, (ring, sector), s, _ = _pushed_case()
    assert (s.probes[0].ring, s.probes[0].sector) == (ring, (sector + 1) % 8)


def test_pushed_probe_gains_publicity_on_an_icon_space() -> None:
    """MOVE-06: a probe pushed onto a comet or planet gains publicity for its owner."""
    found = False
    for a1 in range(8):
        for a2 in range(8):
            for a3 in range(8):
                for ring in (1, 2, 3):
                    for sector in range(8):
                        s = fresh((a1, a2, a3))
                        if solar.visible(s, ring, sector)[0] <= s.rotations % 3 + 1:
                            continue
                        s.probes.append(Probe(id="p", player=1, ring=ring, sector=sector))
                        gains = solar.rotate(s)
                        if gains:
                            assert gains == [(1, "pushed")]
                            assert solar.has_publicity_icon(solar.visible(s, s.probes[0].ring, s.probes[0].sector)[1])
                            found = True
    assert found


def test_a_probe_pushed_onto_asteroids_gains_publicity_with_the_skimmer() -> None:  # TECH-PT03, MOVE-07, ROTATE-03 (owner, 2026-10-27)
    """The tech gives 1 publicity when a probe moves onto asteroids; a push is a free move, so the owner gains it, also on another's turn."""
    from seti_engine import techs

    seen = {"with": 0, "without": 0}
    for a1 in range(8):
        for a2 in range(8):
            for a3 in range(8):
                for ring in (1, 2, 3):
                    for sector in range(8):
                        for tech in (True, False):
                            s = fresh((a1, a2, a3))
                            if solar.visible(s, ring, sector)[0] <= s.rotations % 3 + 1:
                                continue
                            s.probes.append(Probe(id="p", player=1, ring=ring, sector=sector))
                            if tech:
                                s.players[1].techs.append("probe-link")
                            before = s.players[1].publicity
                            techs.rotate_solar_system(s, [])
                            landed = solar.visible(s, s.probes[0].ring, s.probes[0].sector)[1]
                            if landed == "ASTEROID" and (s.probes[0].ring, s.probes[0].sector) != (ring, sector):
                                gained = s.players[1].publicity - before
                                assert gained == (1 if tech else 0)
                                seen["with" if tech else "without"] += 1
    assert seen["with"] > 0 and seen["without"] > 0


def test_oumuamua_tile_is_a_cutout_until_discovered() -> None:
    s = fresh((0, 0, 0))
    cells_before = [solar.visible(s, 3, c)[1] for c in range(8)]
    assert "PLANET:OUMUAMUA" not in cells_before
    s.oumuamua_placed = True
    cells_after = [solar.visible(s, 3, c)[1] for c in range(8)]
    assert cells_after.count("PLANET:OUMUAMUA") == 1
