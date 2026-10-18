"""What a legal move means, for the page: where it happens, what it costs and what it gives.

The page offers the moves of the engine and asks for a confirmation in words ("confirm landing on Mars for 3 energy?"). The facts for
those words come from here, so that the page works out no rule. `notes` returns one entry for each legal move, in the same order (None for
a move that needs no note). Nothing here changes the state or the moves.
"""

from typing import Any

from . import engine, orgs, rewards, solar, species, tables, techs
from .models import GameState

Note = dict[str, Any] | None


def space_label(state: GameState, ring: int, sector: int) -> str:
    """What lies on a space of the solar system, in words, for the confirmation of a move: 'Mars', 'an asteroid field', 'empty space'."""
    cell = solar.visible(state, ring, sector)[1]
    planet = solar.planet_of(cell)
    if planet is not None:
        return planet.capitalize()
    if cell == "EARTH":
        return "Earth"
    if cell == "ASTEROID":
        return "an asteroid field"
    if cell == "COMET":
        return "a comet"
    return "empty space"


def _probe_planet(state: GameState, probe_id: str, at: str | None = None) -> tuple[str | None, Any]:
    probe = next((p for p in state.probes if p.id == probe_id), None)
    if probe is None:
        return None, None
    return at or engine.planet_at(state, probe), probe


def _trace_rewards(state: GameState, move: dict[str, Any]) -> list[dict[str, Any]]:
    slot = state.species[move["slot"]]
    space = move["space"]
    if space == "overflow":
        return [{"t": "vp", "n": rewards.OVERFLOW_VP}]  # LIFE-01
    if space == "discovery":
        return [{"t": "vp", "n": rewards.DISCOVERY_VP[move["slot"]]}, {"t": "publicity", "n": 1}]  # LIFE-03, BOARD-40
    if space == "board":
        column = next(c for c in species.board_data(slot.species)["columns"] if c["color"] == move["color"])
        return list(column["spaces"][move["index"]]["rewards"])
    if space == "sample":  # ALIEN-MASC-05
        token = slot.extra["sample_spaces"][move["index"]]["token"]
        return list(species.sample_faces()[token])
    return []


def note(state: GameState, move: dict[str, Any]) -> Note:
    kind = move["type"]
    if kind in ("orbit", "orbit_free", "land", "land_free"):
        planet, probe = _probe_planet(state, move["probe"], move.get("at"))
        if planet is None:
            return None
        free = kind.endswith("_free")
        action = "orbit" if kind.startswith("orbit") else "land"
        cost: dict[str, int] = {}
        if not free:
            owner = state.players[probe.player]
            if action == "orbit":
                cost = {"credit": 1, "energy": 1}  # ORBIT-01
            else:
                cost = {"energy": engine.land_cost(state, owner, planet)}  # LAND-01
        return {"action": action, "planet": planet, "moon": move.get("moon"), "free": free, "cost": cost}
    if kind == "choose_land_slot" and state.pending:  # LAND-04: Mars has two first-lander spaces with different amounts of data
        planet = state.pending[0].data["planet"]
        return {"land_data": {"planet": planet, "slot": move["slot"], "data": tables.planet_info(planet)["first_land_data"][move["slot"]]}}
    if kind in ("mark_signal", "scan_earth", "resolve_sector"):
        sector = state.sectors[move["sector"]]
        found: dict[str, Any] = {"sector": move["sector"], "star": sector.star, "color": sector.color}
        if kind == "resolve_sector":  # TURN-05: the sector that is resolved next, picked on the board
            found["resolve"] = True
        return found
    if kind == "signal_where":  # ALIEN-OUM-03: a signal in the sector with 'Oumuamua: in the sector, or on the tile
        at = species.oumuamua_sector(state)
        if at is None:
            return None
        sector = state.sectors[at]
        note: dict[str, Any] = {"sector": at, "star": sector.star, "color": sector.color}
        if move["where"] == "tile":
            note["oumuamua_tile"] = True
        return note
    if kind == "research":  # TECHACT-01: the publicity it costs, which an organization can lower (Fenwick Research Center: 5, EXP-ORG-13)
        actor = state.pending[0].player if state.pending else state.current_player
        return {"cost": {"publicity": orgs.research_cost(state.players[actor], techs.RESEARCH_COST)}}
    if kind == "take_alien":  # the top of the deck of a species (hidden), or the card that lies face up
        slot_index = state.pending[0].data["slot"]
        face_up = state.species[slot_index].face_up
        return {"slot": slot_index, "alien": move["source"], "card": face_up if move["source"] == "face_up" else None}
    if kind == "pick_sample":  # ALIEN-MASC-02: the player looks at the samples on the planet; only the actor is sent these notes
        return {"planet": move["planet"], "rewards": list(species.sample_faces()[move["sample"]])}
    if kind == "deliver_sample":  # ALIEN-MASC-04: the token under the capsule and the card's own reward
        capsule = next(pr for pr in state.probes if pr.id == move["capsule"])
        return {"capsule": capsule.id, "rewards": list(species.sample_faces()[capsule.sample or 0])}
    if kind == "place_trace":
        slot = state.species[move["slot"]]
        return {
            "slot": move["slot"],
            "species": slot.species if slot.discovered else None,
            "color": move["color"],
            "space": move["space"],
            "rewards": _trace_rewards(state, move),
        }
    return None


def notes(state: GameState, legal: list[dict[str, Any]]) -> list[Note]:
    """One note per legal move. A move that would show something hidden (a card drawn from the deck, the round pile, a species, the next
    tech tile) and so cannot be taken back is marked `irreversible`, so that the page warns before it (UNDO-01)."""
    out: list[Note] = []
    for m in legal:
        n = note(state, m)
        if engine.reveals(state, m):
            n = {**(n or {}), "irreversible": True}
        out.append(n)
    return out
