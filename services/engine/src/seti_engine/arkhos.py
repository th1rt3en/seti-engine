"""Arkhos, a species of the Space Agencies expansion: the exploration deck, the security cards and the security levels.

Spec: docs/spec/expansion.md (EXP-ARK-01 to EXP-ARK-08). Data: docs/spec/data/expansion-arkhos.json (a transcription of the pictures, owner
check pending, A-040 to A-042). The rival does not play with the new species yet (EXP-ARK-08, A-033).
"""

from __future__ import annotations

from typing import Any

from . import rewards, rng, tables
from .models import Decision, GameState, PlayerState, SpeciesSlot

Events = list[dict[str, Any]]
COLORS = ("pink", "yellow", "blue")
ASIDE = 4  # EXP-ARK-01: 4 of the 9 exploration cards are set aside, the other 5 form the deck
DECK = 5


def slot_index(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "arkhos" and sl.discovered), None)


def discover(s: GameState, slot: SpeciesSlot, owners: list[int], events: Events) -> None:
    """EXP-ARK-01, EXP-ARK-03: shuffle the exploration cards, set 4 aside; one minor reward per marker; deal the security cards."""
    ids = [c["id"] for c in tables.arkhos()["exploration"]]
    order = rng.shuffled(s, ids)
    slot.extra["explore_aside"] = order[:ASIDE]
    slot.extra["explore_deck"] = order[ASIDE:]
    slot.extra["explore_discard"] = []
    for p in s.players:  # EXP-ARK-03, EXP-ARK-08: 1 random card of each trace color in front of every player, the rival too
        p.security = {c: rng.choice(s, [x["id"] for x in tables.arkhos()["security"] if x["trace"] == c]) for c in COLORS}
    events.append({"type": "arkhos_discovered", "slot": s.species.index(slot)})
    from . import rival  # noqa: PLC0415 - rival imports this module

    for pl in owners:  # EXP-ARK-01: a minor exploration reward for each marker on a discovery space
        if rival.is_rival(s, pl):
            rival.advance(s, 1, events)  # EXP-ARK-08: the rival gains an advance for contributing
        else:
            explore(s, s.players[pl], "minor", events)


def explore(s: GameState, p: PlayerState, level: str, events: Events) -> None:
    """EXP-ARK-02, EXP-ARK-04: reveal the next exploration card and gain its minor or major reward. With the deck empty the revealed
    cards and the four set aside are shuffled into a new deck of 5, the rest are set aside again."""
    i = slot_index(s)
    if i is None:
        return
    extra = s.species[i].extra
    if not extra["explore_deck"]:
        pool = rng.shuffled(s, [*extra["explore_discard"], *extra["explore_aside"]])
        extra["explore_deck"], extra["explore_aside"], extra["explore_discard"] = pool[:DECK], pool[DECK:], []
    cid = extra["explore_deck"].pop(0)
    extra["explore_discard"].append(cid)
    card = next(c for c in tables.arkhos()["exploration"] if c["id"] == cid)
    events.append({"type": "explore", "player": p.index, "card": cid, "level": level})
    rewards.grant(s, p, card[level], events)


def access(p: PlayerState) -> int:
    """EXP-ARK-05, EXP-ARK-06: the highest security level the player may mark. Each breached card opens one more level; without
    security cards left in front of them (all breached) every space is open."""
    return 3 if not p.security else 3 - len(p.security)


def on_overflow(s: GameState, p: PlayerState, slot: int, color: str) -> None:
    """EXP-ARK-06: marking an overflow space of Arkhos lets the player breach their security card of that color."""
    from . import rival  # noqa: PLC0415 - rival imports this module

    if s.species[slot].species == "arkhos" and rival.is_rival(s, p.index):
        # EXP-ARK-08: a breach effect is an advance for the rival; it breaches only by playing its Arkhos card
        if s.rival is not None and s.rival.breaching:
            p.security.pop(color, None)
        else:
            rival.advance(s, 1)
        return
    if s.species[slot].species == "arkhos" and color in p.security:
        s.pending.append(Decision(kind="breach", player=p.index, data={"color": color}))


def breach_moves(s: GameState, d: Decision) -> list[dict[str, Any]]:
    return [{"type": "breach"}, {"type": "skip_breach"}]


def breach(s: GameState, p: PlayerState, d: Decision, a: dict[str, Any]) -> None:
    if a["type"] == "breach":
        p.hand.append(p.security.pop(d.data["color"]))  # EXP-ARK-07: in the hand it counts toward the hand limit
