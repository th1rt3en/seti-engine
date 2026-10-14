"""Solar system geometry: stacking of the three discs on the fixed base, adjacency, rotation and pushed probes.

Spec: docs/spec/board-solar-system.md (owner-confirmed 2026-10-12), A-007, BOARD-10 to BOARD-16, ROTATE-01 to ROTATE-05.
Slot k of a wheel is the k*45 degree wedge; a rotation step moves the content of slot k to slot k+1 (counter-clockwise). A cell of disc d at
ring r, sector s is wheel[d][r][(s - angle[d]) % 8]. At ring r the visible cell is the first solid one among discs r to 3, then the base.
"""

from __future__ import annotations

from . import tables
from .models import GameState, Probe

OUMUAMUA_CELL = "PLANET:OUMUAMUA"


def _wheels() -> dict[str, dict[str, list[str]]]:
    wheels: dict[str, dict[str, list[str]]] = tables.solar()["wheels"]
    return wheels


def disc_angle(state: GameState, disc: int) -> int:
    return state.disc_angles[disc - 1] if disc <= 3 else 0


def cell_of_disc(state: GameState, disc: int, ring: int, sector: int) -> str | None:
    """The cell disc `disc` shows at (ring, sector), or None if the disc does not reach that ring."""
    rows = _wheels()[str(disc)]
    if str(ring) not in rows:
        return None
    slot = (sector - disc_angle(state, disc)) % 8
    cell = rows[str(ring)][slot]
    if state.oumuamua_placed and disc == 3 and ring == 3 and slot == tables.solar()["oumuamua_slot"]["slot"]:
        return OUMUAMUA_CELL
    return cell


def visible(state: GameState, ring: int, sector: int) -> tuple[int, str]:
    """(disc, cell) of the top-most non-cutout cell at (ring, sector)."""
    for disc in range(ring, 5):
        cell = cell_of_disc(state, disc, ring, sector)
        if cell is not None and cell != "NULL":
            return disc, cell
    raise ValueError(f"no space at ring {ring}, sector {sector}")  # the base has a cell everywhere


def cell_type(cell: str) -> str:
    return "PLANET" if cell.startswith("PLANET:") else cell


def planet_of(cell: str) -> str | None:
    return cell.split(":", 1)[1].lower() if cell.startswith("PLANET:") else None


def has_publicity_icon(cell: str) -> bool:
    """Planets other than Earth, and comets, give 1 publicity when visited (MOVE-05, BOARD-13)."""
    return cell == "COMET" or cell.startswith("PLANET:")


def adjacent(ring: int, sector: int) -> list[tuple[int, int]]:
    """Orthogonal neighbours: same ring, neighbouring sectors (sector 7 touches 0), and same sector, neighbouring rings (BOARD-16)."""
    out = [(ring, (sector - 1) % 8), (ring, (sector + 1) % 8)]
    if ring > 1:
        out.append((ring - 1, sector))
    if ring < 4:
        out.append((ring + 1, sector))
    return out


def find_cell(state: GameState, wanted: str) -> tuple[int, int] | None:
    """Current (ring, sector) of a cell such as 'EARTH' or 'PLANET:MARS'."""
    for ring in range(1, 5):
        for sector in range(8):
            if visible(state, ring, sector)[1] == wanted:
                return ring, sector
    return None


def earth(state: GameState) -> tuple[int, int]:
    pos = find_cell(state, "EARTH")
    assert pos is not None
    return pos


def probe_at(state: GameState, ring: int, sector: int) -> list[Probe]:
    return [p for p in state.probes if p.ring == ring and p.sector == sector]


def rotate(state: GameState) -> list[tuple[int, str]]:
    """Rotate the solar system once (ROTATE-02). Returns publicity gains as (player, reason) for probes pushed onto an icon space.
    Every pushed probe is also recorded in `state.pushed` as (player, cell), for triggerable missions (CARD-13).

    The disc to rotate cycles 1, 2, 3; rotating disc d also rotates every disc above it (discs 1..d). A probe rides along if the
    cell it stands on belongs to a rotating disc. A probe standing on a static disc's cell is untouched unless a solid cell of a rotating
    disc arrives over it, in which case it is pushed one space further in the rotation direction, for free (A-007).
    """
    rotating = state.rotations % 3 + 1
    gains = rotate_discs(state, set(range(1, rotating + 1)), 1)
    state.rotations += 1
    return gains


def rotate_discs(state: GameState, discs: set[int], step: int) -> list[tuple[int, str]]:
    """Turn the given discs by one step (+1 is the direction of a rotation, -1 the other way); see `rotate` for what happens to probes.
    The sandbox (D33) uses this for any disc and any direction."""
    before = {p.id: (visible(state, p.ring, p.sector)[0]) for p in state.probes}
    for d in discs:
        state.disc_angles[d - 1] = (state.disc_angles[d - 1] + step) % 8
    gains: list[tuple[int, str]] = []
    state.pushed = []
    for p in state.probes:
        k0 = before[p.id]
        if k0 in discs:
            p.sector = (p.sector + step) % 8  # the cell moved with its disc and carried the probe
            continue
        disc_now = visible(state, p.ring, p.sector)[0]
        if disc_now != k0 and disc_now in discs:  # a solid cell of a rotating disc arrived: pushed along the rotation
            p.sector = (p.sector + step) % 8
            cell = visible(state, p.ring, p.sector)[1]
            state.pushed.append((p.player, cell))
            if has_publicity_icon(cell):
                gains.append((p.player, "pushed"))
    return gains
