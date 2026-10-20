"""The projected view."""

from seti_engine.models import Options
from seti_engine.projection import project
from seti_engine.setup import new_game


def test_the_view_says_where_each_planet_lies_now() -> None:
    """The highlight of a visit goes to the space of the solar system where the planet lies at this moment (the discs turn)."""
    from seti_engine import solar

    s = new_game(Options(players=2, seed=3))
    cells = project(s, 0).planet_cells
    assert cells["mars"] == list(solar.find_cell(s, "PLANET:MARS") or ())
    assert set(cells) <= set(s.planets)


def test_a_gain_that_does_not_fit_is_in_the_log() -> None:
    """RES-01, RES-02: publicity stops at 10 and the data pool at 6; the events say how much was lost and what caused it."""
    from seti_engine import effects, trail

    s = new_game(Options(players=2, seed=3))
    p = s.players[0]
    p.publicity, p.data_pool = 9, 5
    with trail.scope(s, {"kind": "card", "card": "1"}):
        effects.gain_publicity(s, p, 3)
        effects.gain_data(s, p, 4)
    assert (p.publicity, p.data_pool) == (10, 6)
    caps = [e for e in trail.events_of(s) if e["type"] == "capped"]
    assert [(e["kind"], e["n"]) for e in caps] == [("publicity", 2), ("data", 3)]
    assert all(e["player"] == 0 and e["source"] == {"kind": "card", "card": "1"} for e in caps)


def test_the_view_has_the_solar_system_after_the_next_rotation_and_the_game_is_not_changed() -> None:
    """ROTATE-02: the preview turns the discs on a copy; the probes of the discs that turn ride along."""
    from seti_engine import solar

    s = new_game(Options(players=2, seed=3))
    s.phase = "play"  # the preview is made while the game is being played
    before = s.model_dump()
    v = project(s, 0)
    assert s.model_dump() == before  # the game itself is not turned
    pv = v.rotation_preview
    assert pv is not None and pv.disc == 1 and pv.disc_angles == [(a + (1 if i < 1 else 0)) % 8 for i, a in enumerate(s.disc_angles)]
    copy = s.model_copy(deep=True)
    solar.rotate(copy)
    assert pv.planet_cells == {k: list(solar.find_cell(copy, f"PLANET:{k.upper()}") or ()) for k in pv.planet_cells}
    assert [p["id"] for p in pv.probes] == [p.id for p in s.probes]
