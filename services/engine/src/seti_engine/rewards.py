"""Rewards, signals, sector completion and life traces.

Spec: actions.md (SCAN-*, LIFE-*), board-and-sectors.md (SECTOR-01 to SECTOR-22), milestones-and-scoring.md, faq.md (FAQ-01, FAQ-41).
A reward is a dict from the data files, e.g. {"t": "vp", "n": 3} or {"t": "trace", "kind": "yellow", "n": 1}. Rewards that need a choice
append a `Decision` to `state.pending`; the engine resolves them in order.
"""

from __future__ import annotations

from typing import Any

from . import effects, objectives, solar, tables
from .models import Decision, GameState, PlayerState

Events = list[dict[str, Any]]
TRACE_COLORS = ("pink", "yellow", "blue")  # LIFE-01; column order of the three discovery spaces
DISCOVERY_VP = (5, 3)  # BOARD-40: left slot 5 VP, right slot 3 VP, each with 1 publicity
OVERFLOW_VP = 3  # LIFE-01
NEUTRAL = -1  # EXP-QS-03: the marker color of the neutral quick start pieces


def grant(
    s: GameState, p: PlayerState, rewards: list[dict[str, Any]], events: Events, planet: str | None = None, slot: int | None = None
) -> None:
    from . import arkhos, cards, glyphids, rival, species  # noqa: PLC0415 - these import this module

    if rival.is_rival(s, p.index):  # SOLO-10: the rival takes rewards in its own way
        rival.grant(s, rewards, events, planet, slot)
        return

    """Give the rewards in order. `planet` names the planet for "signal in a sector with this planet" rewards; `slot` is the species slot
    for "alien card" rewards."""
    for r in rewards:
        t, n = r["t"], r.get("n", 1)
        if t == "vp":
            effects.gain_score(s, p, n)
        elif t == "data":
            effects.gain_data(s, p, n)
        elif t == "energy":
            p.energy += n
        elif t == "credit":
            p.credits += n
        elif t == "publicity":
            effects.gain_publicity(s, p, n)
        elif t == "card_random":
            for _ in range(n):
                effects.draw_random_card(s, p)
        elif t == "card_any":
            s.pending += [Decision(kind="take_card", player=p.index) for _ in range(n)]
        elif t == "tuck":
            s.pending += [Decision(kind="income_tuck", player=p.index) for _ in range(n)]  # INCOME-01; FAQ-01: may be declined
        elif t == "move":
            p.movement += n
        elif t == "signal_token":
            p.signal_tokens += n  # EXP-SIG-01
        elif t == "vp_empty_species_space":  # AM.14: 1 VP for each empty space of the species board
            for sl in s.species:
                if sl.species == r["species"]:
                    effects.gain_score(s, p, sum(1 for spaces in sl.board.values() for m in spaces if not m))
        elif t == "scan_free":  # a free scan from an exploration reward
            cards.run_step(s, p, {"t": "scan_free"}, events)
        elif t == "organelle":  # AM.17: a mission circle whose reward is one organelle of a section (EXP-AMO-04)
            from . import amoeba  # noqa: PLC0415 - amoeba imports this module

            amoeba.request_pick(s, p, r["color"])
        elif t == "organelles":  # EXP-AMO-03: the organelle bonuses of a marked space are gained by species.mark_board_space
            pass
        elif t == "glyph_space":  # the token of a Glyphids board space is taken by the marking (species.mark_board_space)
            pass
        elif t == "glyph_resource":  # EXP-GLY-06: the resource of a deciphered glyph
            glyphids.glyph_resource(s, p, r["glyph"], events)
        elif t == "explore_minor" or t == "explore_major":  # EXP-ARK-04: reveal the next exploration card, gain its minor or major reward
            for _ in range(n):
                arkhos.explore(s, p, t.removeprefix("explore_"), events)
        elif t == "explore":
            arkhos.explore(s, p, r["level"], events)
        elif t == "research":  # a free research (rotate, then take a tech) from an exploration reward
            cards.run_step(s, p, {"t": "rotate"}, events)
            cards.run_step(s, p, {"t": "research", "cat": r.get("cat", "any")}, events)
        elif t == "exofossil":
            species.gain_exofossil(s, p, n)
        elif t == "exofossil_pay":
            p.exofossils -= n
            species.return_exofossils(s, n)
        elif t == "sample_peek":  # a Mascamite mission reward: look at Jupiter's or Saturn's samples and gain one's reward
            planets = [pl for pl in species.SAMPLE_PLANETS if species.samples_on(s, pl)]
            if planets:
                s.pending.append(Decision(kind="mascamite_sample", player=p.index, data={"mode": "peek", "planets": planets}))
        elif t == "signal_any":
            s.pending += [Decision(kind="signal", player=p.index, data={"color": "any"}) for _ in range(n)]
        elif t == "signal_oumuamua":
            idx = species.oumuamua_sector(s)
            assert idx is not None
            for _ in range(n):
                mark_signal(s, p, idx, events)
        elif t == "alien_card":
            assert slot is not None
            if s.species[slot].deck or s.species[slot].face_up is not None:  # ALIEN-05: with no cards left the icon has no effect
                s.pending += [Decision(kind="take_alien_card", player=p.index, data={"slot": slot}) for _ in range(n)]
        elif t == "launch":
            for _ in range(n):
                effects.launch_probe(s, p, events, nolimit=r.get("nolimit", False))  # TECH-PT01, FAQ-C009
        elif t == "signal_planet":
            assert planet is not None
            pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
            assert pos is not None
            for _ in range(n):
                mark_signal(s, p, pos[1], events)
        elif t == "signal_color":
            s.pending += [Decision(kind="signal", player=p.index, data={"color": r["color"]}) for _ in range(n)]
        elif t == "trace":
            s.pending += [Decision(kind="trace", player=p.index, data={"color": r["kind"]}) for _ in range(n)]
        else:
            raise ValueError(f"unknown reward {t}")


# ---------------------------------------------------------------------------------------------------------------------------------
# signals and sectors
# ---------------------------------------------------------------------------------------------------------------------------------


def mark_signal(s: GameState, p: PlayerState, index: int, events: Events, data: bool = True, allow_tile: bool = True) -> None:
    """SECTOR-01 to SECTOR-05, SECTOR-10: replace the leftmost data with the player's marker. `data` False sends the data to the supply
    instead of the player (FAQ-C118). In 'Oumuamua's sector the player chooses the sector or the tile (ALIEN-OUM-03)."""
    from . import cards, species  # noqa: PLC0415 - these import this module

    if allow_tile and index == species.oumuamua_sector(s):
        s.pending.append(Decision(kind="oumuamua_signal", player=p.index, data={"sector": index, "nodata": not data}))
        return

    sec = s.sectors[index]
    pos = len(sec.markers)
    sec.markers.append(p.index)
    s.action_sectors.append(index)
    completed = False
    if pos < sec.capacity:
        sec.data_remaining -= 1
        if data:
            effects.gain_data(s, p, 1)  # SECTOR-01, SECTOR-02
        if pos == 1:
            effects.gain_score(s, p, 2)  # SECTOR-03
        if sec.data_remaining == 0 and index not in s.completed:
            s.completed.append(index)  # SECTOR-10: resolved after the main action
            completed = True
    events.append({"type": "signal", "player": p.index, "sector": index})
    if s.scan_ctx and s.scan_ctx.get("vp_color") == sec.color:
        effects.gain_score(s, p, s.scan_ctx["vp"])  # FAQ-C051: e.g. #53 gives 2 points per yellow signal of the scan
    if completed:
        cards.on_sector_completed(s, events)
    cards.fire(s, p, [{"e": "signal", "color": sec.color}], events)  # FAQ-C116


def sectors_of_color(s: GameState, color: str) -> list[int]:
    return [i for i, sec in enumerate(s.sectors) if sec.color == color]


def _ranking(markers: list[int], exclude: int | None = None) -> list[int]:
    """Players ordered by markers, most first; a tie goes to the player whose marker was placed later (SECTOR-11)."""
    players = {m for m in markers if m != exclude}
    count = {q: sum(1 for m in markers if m == q) for q in players}
    last = {q: max(i for i, m in enumerate(markers) if m == q) for q in players}
    return sorted(players, key=lambda q: (-count[q], -last[q]))


def resolve_sector(s: GameState, index: int, events: Events) -> None:
    """SECTOR-11 to SECTOR-15: winner, publicity for contributors, second place stays, the rest return and the slot refills."""
    if index == -1:  # the 'Oumuamua tile (ALIEN-OUM-04)
        from . import species  # noqa: PLC0415 - species imports this module

        species.resolve_tile(s, events)
        return
    from . import glyphids  # noqa: PLC0415 - glyphids imports this module

    sec = s.sectors[index]
    star = _star(sec.star)
    ranking = _ranking(sec.markers, exclude=NEUTRAL)  # EXP-QS-04: the neutral color never wins
    winner = ranking[0]
    first = not sec.winners
    sec.winners.append(winner)  # SECTOR-14: the winner's marker beside the star stays; it never counts for the next win
    objectives.on_event(s, s.players[winner], [{"e": "win_sector", "color": sec.color}])  # SOLO-OBJ-04
    w = s.players[winner]
    w.sector_wins += 1
    glyphids.take(s, w, f"sector:{index}", events)  # EXP-GLY-04
    events.append({"type": "sector_won", "player": winner, "sector": index})
    for q in sorted(set(sec.markers) - {NEUTRAL}):
        effects.gain_publicity(s, s.players[q])  # SECTOR-12
    grant(s, w, star["first_win" if first else "later_win"], events)  # SECTOR-15, SECTOR-16
    second = _ranking(sec.markers, exclude=winner)  # SECTOR-13, EXP-QS-04: a neutral marker may stay as second
    sec.markers = [second[0]] if second else []
    sec.data_remaining = sec.capacity - len(sec.markers)


def _star(name: str) -> dict[str, Any]:
    for b in tables.stars()["boards"]:
        for st in b["stars"]:
            if st["name"] == name:
                found: dict[str, Any] = st
                return found
    raise KeyError(name)


# ---------------------------------------------------------------------------------------------------------------------------------
# life traces
# ---------------------------------------------------------------------------------------------------------------------------------


def trace_moves(s: GameState, d: Decision) -> list[dict[str, Any]]:
    """LIFE-01, FAQ-41: a free discovery space of the right color on either species, or an overflow space (always allowed).
    A discovered species also offers its board spaces of the matching color (LIFE-04)."""
    from . import species  # noqa: PLC0415 - species imports this module

    wanted: str = d.data["color"]
    colors = TRACE_COLORS if wanted == "any" else (wanted,)
    out: list[dict[str, Any]] = []
    for i, slot in enumerate(s.species):
        if "slots" in d.data and i not in d.data["slots"]:
            continue
        p = s.players[d.player]
        if slot.discovered:
            out += species.board_moves(s, p, i, colors)
        else:
            out += [
                {"type": "place_trace", "slot": i, "space": "discovery", "color": c}
                for c in colors
                if slot.discovery_spaces[TRACE_COLORS.index(c)] is None
            ]
        out += [{"type": "place_trace", "slot": i, "space": "overflow", "color": c} for c in colors]  # each overflow space has a color
    return out


def place_trace(s: GameState, p: PlayerState, a: dict[str, Any], events: Events) -> None:
    """Mark a trace on the space `a` names; it counts for the color of that space (CARD-46, A-017, A-022)."""
    from . import (
        arkhos,  # noqa: PLC0415 - arkhos imports this module
        cards,  # noqa: PLC0415 - cards imports this module
        orgs,  # noqa: PLC0415 - orgs imports this module
        species,  # noqa: PLC0415 - species imports this module
    )

    slot = s.species[a["slot"]]
    kind = a["color"]  # A-017, A-022: every space, overflow ones too, has a color; a trace counts for the color of its space
    p.trace_log.append((a["slot"], kind))
    orgs.on_trace(p, kind)  # Xenolab (EXP-ORG-13)
    if a["space"] == "board":
        species.mark_board_space(s, p, a["slot"], a["color"], a["index"], events)
    elif a["space"] == "sample":  # a Mascamite sample token on a blue space (ALIEN-MASC-05)
        species.mark_sample_space(s, p, a["slot"], a["index"], events)
    elif a["space"] == "overflow":
        slot.overflow.append(p.index)
        slot.overflow_kinds.append(kind)
        effects.gain_score(s, p, OVERFLOW_VP)
        arkhos.on_overflow(s, p, a["slot"], kind)  # EXP-ARK-06
    else:
        slot.discovery_spaces[TRACE_COLORS.index(a["color"])] = f"p{p.index}"
        effects.gain_score(s, p, DISCOVERY_VP[a["slot"]])  # LIFE-03
        effects.gain_publicity(s, p)
        if all(x is not None for x in slot.discovery_spaces):
            slot.complete = True  # ALIEN-01: revealed after the turn
    events.append({"type": "trace", "player": p.index, "slot": a["slot"], "space": a["space"]})
    s.last_trace_kind = kind
    cards.fire(s, p, [{"e": "trace", "kind": kind, "species": slot.species}], events)  # FAQ-C107 ("any" matches only the generic circles)
