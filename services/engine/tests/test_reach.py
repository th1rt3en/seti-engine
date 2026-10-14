"""Where a probe can go with movement and energy (MOVE-01, MOVE-02, FREE-01): the reach of a view follows the costs of the single steps."""

from test_engine import begin

from seti_engine import projection, solar
from seti_engine.engine import apply, move_reach
from seti_engine.models import GameState, Probe


def with_probe(energy: int, movement: int, ring: int = 2, sector: int = 3) -> tuple[GameState, int]:
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].energy, s.players[pl].movement = energy, movement
    s.probes.append(Probe(id="t1", player=pl, ring=ring, sector=sector))
    return s, pl


def walk(s: GameState, cost: int, path: list[tuple[int, int]]) -> GameState:
    """Do what the page does: convert energy as needed, then step along the path."""
    pl = s.current_player
    for _ in range(max(0, cost - s.players[pl].movement)):
        s = apply(s, {"type": "move_energy"}).state
    for ring, sector in path:
        s = apply(s, {"type": "move_probe", "probe": "t1", "to": [ring, sector]}).state
    return s


def cells_of(s: GameState, pl: int) -> list[tuple[tuple[int, int], int, list[tuple[int, int]]]]:
    return next(cells for pid, cells in move_reach(s, s.players[pl]) if pid == "t1")


def test_every_reachable_space_is_reached_by_its_path_for_exactly_its_cost() -> None:
    s, pl = with_probe(energy=6, movement=1)
    cells = cells_of(s, pl)
    assert len(cells) > 8
    for to, cost, path in cells:
        assert path[-1] == to and cost >= len(path)
        after = walk(s, cost, path)
        mine = next(p for p in after.probes if p.id == "t1")
        assert (mine.ring, mine.sector) == to
        spent = (s.players[pl].energy - after.players[pl].energy) + (s.players[pl].movement - after.players[pl].movement)
        assert spent == cost, (to, cost, spent)


def test_the_reach_never_exceeds_the_budget_and_grows_with_energy() -> None:
    small, pl = with_probe(energy=0, movement=2)
    big, _ = with_probe(energy=4, movement=2)
    low = {to: c for to, c, _ in cells_of(small, pl)}
    high = {to: c for to, c, _ in cells_of(big, pl)}
    assert max(low.values()) <= 2 and max(high.values()) <= 6
    assert set(low) < set(high)
    assert all(high[c] == low[c] for c in low)  # a space that was reachable costs the same


def test_leaving_an_asteroid_costs_one_more() -> None:
    """MOVE-02: the reach follows the same cost as a single step."""
    s, pl = with_probe(energy=0, movement=1)
    asteroid = next((r, c) for r in range(1, 5) for c in range(8) if solar.visible(s, r, c)[1] == "ASTEROID")
    s.probes[-1].ring, s.probes[-1].sector = asteroid
    assert cells_of(s, pl) == []  # 1 movement is not enough to leave an asteroid
    s.players[pl].movement = 2
    assert {cost for _, cost, path in cells_of(s, pl) if len(path) == 1} == {2}


def test_the_view_carries_the_reach_only_when_the_viewer_may_move() -> None:
    s, pl = with_probe(energy=3, movement=0)
    mine = projection.project(s, pl)
    assert [r.probe for r in mine.reach] == ["t1"] and mine.reach[0].cells
    assert projection.project(s, 1 - pl).reach == []  # not the player to act
    assert projection.project(s, None).reach == []


def test_the_reach_names_what_lies_on_each_space() -> None:
    """The page asks 'confirm ... to move a probe from Mars to empty space?': the words come with the reach."""
    s, pl = with_probe(energy=4, movement=1)
    view = projection.project(s, pl)
    reach = next(r for r in view.reach if r.probe == "t1")
    known = {"Earth", "an asteroid field", "a comet", "empty space", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"}
    assert reach.label in known
    assert reach.cells and {c.label for c in reach.cells} <= known
