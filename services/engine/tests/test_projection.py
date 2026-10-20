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
