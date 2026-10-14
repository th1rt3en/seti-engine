"""The facts the page needs for a confirmation (move_notes.py): where a move is, its cost and what it gives (LAND-01, ORBIT-01, LIFE-03)."""

from test_engine import begin

from seti_engine import projection, solar
from seti_engine.engine import legal_moves
from seti_engine.models import GameState, Probe


def at_planet(planet: str) -> tuple[GameState, int]:
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    ring, sector = next((r, c) for r in range(1, 5) for c in range(8) if solar.planet_of(solar.visible(s, r, c)[1]) == planet)
    s.probes.append(Probe(id="t1", player=pl, ring=ring, sector=sector))
    s.players[pl].energy, s.players[pl].credits = 5, 3
    return s, pl


def note_of(s: GameState, kind: str, **kw: object) -> dict | None:
    legal = legal_moves(s)
    notes = projection.move_notes.notes(s, legal)
    i = next(i for i, m in enumerate(legal) if m["type"] == kind and all(m.get(k) == v for k, v in kw.items()))
    return notes[i]


def test_orbit_and_land_notes_say_the_planet_and_the_cost() -> None:
    s, _ = at_planet("mars")
    orbit = {"action": "orbit", "planet": "mars", "moon": None, "free": False, "cost": {"credit": 1, "energy": 1}}
    land = {"action": "land", "planet": "mars", "moon": None, "free": False, "cost": {"energy": 3}}
    assert note_of(s, "orbit", probe="t1") == orbit
    assert note_of(s, "land", probe="t1") == land


def test_landing_costs_one_less_with_an_orbiter_there() -> None:
    """LAND-02: the note follows the engine's cost, it does not work one out."""
    s, pl = at_planet("mars")
    s.planets["mars"].orbiters = [1 - pl]
    assert note_of(s, "land", probe="t1")["cost"] == {"energy": 2}  # type: ignore[index]


def test_views_carry_one_note_for_each_legal_move() -> None:
    s, pl = at_planet("mars")
    view = projection.project(s, pl)
    assert len(view.notes) == len(view.legal) > 0
    assert projection.project(s, 1 - pl).notes == []  # not the player to act


def test_trace_and_signal_notes() -> None:
    s = begin(2).state.model_copy(deep=True)
    s.pending = []
    from seti_engine.models import Decision

    pl = s.current_player
    s.pending.append(Decision(kind="trace", player=pl, data={"color": "any"}))
    legal = legal_moves(s)
    notes = projection.move_notes.notes(s, legal)
    discovery = [(m, n) for m, n in zip(legal, notes, strict=True) if m["space"] == "discovery"]
    assert discovery and all(n["species"] is None for _, n in discovery)  # nobody has seen the species yet
    left = next(n for m, n in discovery if m["slot"] == 0)
    right = next(n for m, n in discovery if m["slot"] == 1)
    assert left["rewards"] == [{"t": "vp", "n": 5}, {"t": "publicity", "n": 1}]  # LIFE-03, BOARD-40
    assert right["rewards"][0] == {"t": "vp", "n": 3}
    overflow = next(n for m, n in zip(legal, notes, strict=True) if m["space"] == "overflow")
    assert overflow["rewards"] == [{"t": "vp", "n": 3}]  # LIFE-01
    s.pending = [Decision(kind="signal", player=pl, data={"color": "any"})]
    legal = legal_moves(s)
    star = projection.move_notes.notes(s, legal)[0]
    assert star == {"sector": 0, "star": s.sectors[0].star, "color": s.sectors[0].color}


def test_a_step_reports_what_each_player_gained_or_lost_net() -> None:
    """The log of the page shows resource changes: one `delta` event for each player whose points or resources changed."""
    from seti_engine.engine import apply

    s, pl = at_planet("mars")
    s.players[pl].credits, s.players[pl].energy = 3, 5
    r = apply(s, {"type": "orbit", "probe": "t1"})
    deltas = [e for e in r.events if e["type"] == "delta" and e["player"] == pl]
    assert len(deltas) == 1
    changes = deltas[0]["changes"]
    assert changes["credit"] == -1 and changes["energy"] == -1  # ORBIT-01: the cost is part of the net change
    assert changes.get("vp", 0) >= 0
    assert all(v != 0 for v in changes.values())
    # a step that changes nothing reports nothing for the other player
    assert not [e for e in r.events if e["type"] == "delta" and e["player"] != pl]
