"""Amoeba, a species of the Space Agencies expansion: the organelle tokens, their bonuses and their mutation.

Spec: docs/spec/expansion.md (EXP-AMO-01 to EXP-AMO-06). Data: docs/spec/data/expansion-amoeba.json (the board picture and a transcription
of the cards, owner check pending, A-047 to A-049). The rival does not play with the new species yet (EXP-AMO-06, A-033).
"""

from __future__ import annotations

from typing import Any

from . import rewards, rng, tables, trail
from .models import Decision, GameState, PlayerState, SpeciesSlot

Events = list[dict[str, Any]]


def data() -> dict[str, Any]:
    out: dict[str, Any] = tables.load("expansion-amoeba.json")
    return out


def slot_index(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "amoeba" and sl.discovered), None)


def ring_of(space: str) -> list[str]:
    rings = data()["rings"]
    return [x[0] for x in rings["inner" if space.startswith("I") else "outer"]]


def color_of(space: str) -> str:
    color: str = next(c for ring in ("outer", "inner") for sp, c in data()["rings"][ring] if sp == space)
    return color


def setup(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    """EXP-AMO-02: the five organelle tokens are shuffled and dealt face up on the five marked spaces."""
    order = rng.shuffled(s, list(range(len(data()["organelles"]))))
    slot.extra["organelles"] = dict(zip(data()["rings"]["start"], order, strict=True))
    events.append({"type": "amoeba_discovered", "slot": s.species.index(slot), "organelles": dict(slot.extra["organelles"])})


def in_section(extra: dict[str, Any], color: str) -> list[str]:
    return sorted(sp for sp in extra["organelles"] if color_of(sp) == color)


def mutate(extra: dict[str, Any], spaces: list[str]) -> None:
    """EXP-AMO-05: the organelles that gave their bonuses move 1 space along the arrows (the outer ones clockwise, the inner one counter-
    clockwise), all at once; an occupied target is skipped, so an organelle goes on to the next empty space."""
    orgs: dict[str, int] = extra["organelles"]
    moving = {sp: orgs.pop(sp) for sp in spaces}
    for sp in sorted(moving, key=lambda x: ring_of(x).index(x), reverse=True):  # the one furthest along its ring goes first
        ring = ring_of(sp)
        k = ring.index(sp)
        for step in range(1, len(ring) + 1):
            target = ring[(k + step) % len(ring)]
            if target not in orgs:
                orgs[target] = moving[sp]
                break
        else:
            orgs[sp] = moving[sp]


def gain_section(s: GameState, p: PlayerState, color: str, events: Events) -> None:
    """EXP-AMO-03, EXP-AMO-05: the bonuses of all the organelles in the section of that color, then they mutate."""
    i = slot_index(s)
    if i is None:
        return
    extra = s.species[i].extra
    spaces = in_section(extra, color)
    for sp in spaces:
        with trail.scope(s, {"kind": "alien", "species": "amoeba"}):
            rewards.grant(s, p, data()["organelles"][extra["organelles"][sp]], events)
    events.append({"type": "organelles", "player": p.index, "color": color, "spaces": spaces})
    mutate(extra, spaces)


def pick_moves(s: GameState, d: Decision) -> list[dict[str, Any]]:
    i = slot_index(s)
    assert i is not None
    spaces = in_section(s.species[i].extra, d.data["color"])
    if not spaces:  # no organelle of that color: the player says so with a skip (the effect is lost)
        return [{"type": "skip_organelle", "color": d.data["color"]}]
    return [{"type": "pick_organelle", "space": sp} for sp in spaces]


def pick(s: GameState, p: PlayerState, a: dict[str, Any], events: Events) -> None:
    """EXP-AMO-04: a card's single organelle icon: the bonus of one organelle in the section of the icon's color, then it mutates."""
    i = slot_index(s)
    assert i is not None
    if a["type"] == "skip_organelle":
        events.append({"type": "organelle_skipped", "player": p.index, "color": a["color"]})
        return
    extra = s.species[i].extra
    with trail.scope(s, {"kind": "alien", "species": "amoeba"}):
        rewards.grant(s, p, data()["organelles"][extra["organelles"][a["space"]]], events)
    events.append({"type": "organelle", "player": p.index, "space": a["space"]})
    mutate(extra, [a["space"]])


def request_pick(s: GameState, p: PlayerState, color: str) -> None:
    i = slot_index(s)
    if i is not None:
        s.pending.append(Decision(kind="organelle", player=p.index, data={"color": color}))


def remove_moves(s: GameState, p: PlayerState) -> list[dict[str, Any]]:
    """EXP-AMO-04 (card ET.19): one of the player's markers on a space of the Amoeba board."""
    i = slot_index(s)
    if i is None:
        return []
    board = s.species[i].board
    return [{"type": "amoeba_remove", "color": c, "index": k} for c, spaces in board.items() for k, m in enumerate(spaces) if p.index in m]


def remove(s: GameState, p: PlayerState, a: dict[str, Any], events: Events) -> None:
    i = slot_index(s)
    assert i is not None
    s.species[i].board[a["color"]][a["index"]].remove(p.index)
    gain_section(s, p, a["color"], events)
