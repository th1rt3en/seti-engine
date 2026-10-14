"""What a legal move means, for the page: where it happens, what it costs and what it gives.

The page offers the moves of the engine and asks for a confirmation in words ("confirm landing on Mars for 3 energy?"). The facts for
those words come from here, so that the page works out no rule. `notes` returns one entry for each legal move, in the same order (None for
a move that needs no note). Nothing here changes the state or the moves.
"""

from typing import Any

from . import engine, rewards, species
from .models import GameState

Note = dict[str, Any] | None


def _probe_planet(state: GameState, probe_id: str) -> tuple[str | None, Any]:
    probe = next((p for p in state.probes if p.id == probe_id), None)
    if probe is None:
        return None, None
    return engine.planet_at(state, probe), probe


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
        planet, probe = _probe_planet(state, move["probe"])
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
    if kind in ("mark_signal", "scan_earth"):
        sector = state.sectors[move["sector"]]
        return {"sector": move["sector"], "star": sector.star, "color": sector.color}
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
    return [note(state, m) for m in legal]

