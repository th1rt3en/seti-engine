"""Glyphids, a species of the Space Agencies expansion: glyph tokens on planets, sectors, techs and the board, and the translation board.

Spec: docs/spec/expansion.md (EXP-GLY-01 to EXP-GLY-08). Data: docs/spec/data/expansion-glyphids.json (a transcription of the pictures,
owner check pending, A-043 to A-046). The rival does not play with the new species yet (EXP-GLY-08, A-033).
"""

from __future__ import annotations

from typing import Any

from . import rewards, rng, tables
from .models import GameState, PlayerState, SpeciesSlot

Events = list[dict[str, Any]]


def data() -> dict[str, Any]:
    out: dict[str, Any] = tables.load("expansion-glyphids.json")
    return out


def slot_index(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "glyphids" and sl.discovered), None)


def setup(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    """EXP-GLY-02, EXP-GLY-03: the translation board strips go in a random side up; the glyph tokens are shuffled and one is put face up
    on each of the 6 designated board spaces, beside each planet, on each sector and on each tech stack with its 2-point tile."""
    d = data()
    slot.extra["sides"] = [rng.below(s, 2), rng.below(s, 2)]
    slot.extra["top"] = [None, None, None]
    slot.extra["bottom"] = [None, None, None, None]
    pool = rng.shuffled(s, [g for g in d["glyphs"] for _ in range(d["tokens_per_glyph"])])
    places = [f"board:{c['color']}:{k}" for c in d["board"]["columns"] for k, sp in enumerate(c["spaces"]) if sp.get("well")]
    places += [f"planet:{p}" for p in ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune")]
    places += [f"sector:{i}" for i in range(len(s.sectors))]
    places += [f"tech:{i}" for i, st in enumerate(s.tech_stacks) if st.two_point_tile]
    slot.extra["tokens"] = {pos: pool.pop() for pos in places}
    slot.extra["supply"] = pool
    events.append({"type": "glyphids_discovered", "slot": s.species.index(slot)})


def take(s: GameState, p: PlayerState, where: str, events: Events) -> None:
    """EXP-GLY-04: the player takes the token that lies at a place; nobody can gain a token from it again. The three upper wells of
    the board are replenished at once (with the supply empty they have no effect any more)."""
    i = slot_index(s)
    if i is None:
        return
    extra = s.species[i].extra
    g = extra["tokens"].pop(where, None)
    if g is None:
        return
    p.glyphs.append(g)
    events.append({"type": "glyph", "player": p.index, "glyph": g, "where": where})
    if where.startswith("board:") and where.endswith(":0") and extra["supply"]:
        extra["tokens"][where] = extra["supply"].pop()


def on_board_space(s: GameState, p: PlayerState, color: str, k: int, events: Events) -> None:
    take(s, p, f"board:{color}:{k}", events)


def translation_rows(s: GameState) -> tuple[list[list[dict[str, Any]]], list[list[dict[str, Any]]]]:
    return data()["translation"]["top"], data()["translation"]["bottom"]


def slot_reward(s: GameState, row: str, index: int) -> list[dict[str, Any]]:
    i = slot_index(s)
    assert i is not None
    sides = s.species[i].extra["sides"]
    top, bottom = translation_rows(s)
    reward: dict[str, Any] = (top[sides[0]] if row == "top" else bottom[sides[1]])[index]
    return [reward]


def deciphered(s: GameState) -> dict[str, tuple[str, int]]:
    """EXP-GLY-05: the glyph types that have been placed on the translation board, with their slots."""
    i = slot_index(s)
    if i is None:
        return {}
    extra = s.species[i].extra
    out: dict[str, tuple[str, int]] = {}
    for row in ("top", "bottom"):
        for k, g in enumerate(extra[row]):
            if g is not None:
                out[g] = (row, k)
    return out


def decipher_moves(s: GameState, p: PlayerState) -> list[dict[str, Any]]:
    """EXP-GLY-05: place one of the player's glyph tokens in an empty slot (top row slots only when both slots beneath are filled,
    A-044); a type that has been placed cannot be placed again."""
    i = slot_index(s)
    if i is None or not p.glyphs:
        return []
    extra = s.species[i].extra
    done = deciphered(s)
    needs = data()["translation"]["needs"]
    slots = [("bottom", k) for k, g in enumerate(extra["bottom"]) if g is None]
    slots += [("top", k) for k, g in enumerate(extra["top"]) if g is None and all(extra["bottom"][b] is not None for b in needs[str(k)])]
    return [{"type": "decipher", "glyph": g, "row": row, "index": k} for g in sorted(set(p.glyphs)) if g not in done for row, k in slots]


def decipher(s: GameState, p: PlayerState, a: dict[str, Any], events: Events) -> None:
    i = slot_index(s)
    assert i is not None
    p.glyphs.remove(a["glyph"])
    s.species[i].extra[a["row"]][a["index"]] = a["glyph"]
    events.append({"type": "decipher", "player": p.index, "glyph": a["glyph"], "row": a["row"], "index": a["index"]})
    rewards.grant(s, p, slot_reward(s, a["row"], a["index"]), events)


def glyph_resource(s: GameState, p: PlayerState, glyph: str, events: Events) -> None:
    """EXP-GLY-06: the icon of a glyph on a card gives the resource of its slot when the glyph has been deciphered, otherwise nothing."""
    where = deciphered(s).get(glyph)
    if where is not None:
        rewards.grant(s, p, slot_reward(s, where[0], where[1]), events)


def end_points(p: PlayerState) -> int:
    """EXP-GLY-07: the glyph tokens that were not placed score by sets of different types (1, 3, 5, 8, 11, 15 or 20 points); all sets."""
    counts = sorted((p.glyphs.count(g) for g in set(p.glyphs)), reverse=True)
    points = data()["set_points"]
    total = 0
    for layer in range(counts[0] if counts else 0):
        total += points[sum(1 for c in counts if c > layer)]
    return total
