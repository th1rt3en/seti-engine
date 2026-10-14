"""The facts the page needs for a confirmation (move_notes.py): where a move is, its cost and what it gives (LAND-01, ORBIT-01, LIFE-03)."""

from test_engine import begin, decisions, with_state

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
    legal = decisions(legal_moves(s))
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
    legal = decisions(legal_moves(s))
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


def test_a_trade_for_credit_or_energy_can_be_taken_back() -> None:
    """UNDO-01: back to exactly the state before the trade; a trade for a card from the deck shows a card and has no undo."""
    from seti_engine.engine import apply

    s, pl = at_planet("mars")
    s.players[pl].credits, s.players[pl].energy = 4, 0
    base = with_state(s)
    assert {"type": "undo"} not in base.legal  # nothing to take back yet
    traded = apply(base.state, {"type": "exchange", "give": "credit", "get": "energy"})
    assert traded.state.players[pl].credits == 2 and traded.state.players[pl].energy == 1
    assert {"type": "undo"} in traded.legal
    back = apply(traded.state, {"type": "undo"})
    assert back.state.model_dump(exclude={"undo", "undo_log"}) == s.model_dump(
        exclude={"undo", "undo_log"}
    )  # the state before, to the last field
    assert back.state.undo is None and {"type": "undo"} not in back.legal
    card = apply(back.state, {"type": "exchange", "give": "credit", "get": "card", "source": "deck"})
    assert {"type": "undo"} not in card.legal and card.state.undo is None


def test_the_view_never_carries_the_state_to_go_back_to() -> None:
    from seti_engine.engine import apply

    s, pl = at_planet("mars")
    s.players[pl].credits = 4
    traded = apply(with_state(s).state, {"type": "exchange", "give": "credit", "get": "energy"})
    assert traded.state.undo is not None
    for viewer in (pl, 1 - pl, None):
        assert projection.project(traded.state, viewer).state.undo is None


def test_taking_an_alien_card_says_which_species_and_which_card_lies_face_up() -> None:
    """The page asks 'confirm taking random card?' (the top of the deck) or 'confirm taking <card>?' (the card that lies face up)."""
    from seti_engine.models import Decision

    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.species[1].deck = ["ET.1", "ET.2"]
    s.species[1].face_up = "ET.3"
    s.pending = [Decision(kind="take_alien_card", player=pl, data={"slot": 1})]
    legal = decisions(legal_moves(s))
    notes = projection.move_notes.notes(s, legal)
    by_source = {m["source"]: n for m, n in zip(legal, notes, strict=True)}
    assert by_source["deck"] == {
        "slot": 1,
        "alien": "deck",
        "card": None,
        "irreversible": True,
    }  # the top of the deck is a reveal  # the card on the deck is not named
    assert by_source["face_up"] == {"slot": 1, "alien": "face_up", "card": "ET.3", "irreversible": True}  # its replacement is a reveal


def test_a_signal_in_the_sector_of_oumuamua_names_the_sector_and_tells_the_tile_from_the_sector() -> None:
    """ALIEN-OUM-03: the same sector, two places: the sector itself and the tile of 'Oumuamua."""
    from seti_engine import species
    from seti_engine.models import Decision

    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.species[0].species = "oumuamua"
    species._discover(s, 0, [])
    s.pending = [Decision(kind="oumuamua_signal", player=pl, data={})]
    legal = decisions(legal_moves(s))
    notes = projection.move_notes.notes(s, legal)
    by_where = {m["where"]: n for m, n in zip(legal, notes, strict=True)}
    sector = species.oumuamua_sector(s)
    assert by_where["sector"] == {"sector": sector, "star": s.sectors[sector].star, "color": s.sectors[sector].color}  # type: ignore[index]
    assert by_where["tile"]["oumuamua_tile"] is True and by_where["tile"]["sector"] == sector
