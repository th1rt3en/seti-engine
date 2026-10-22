"""Statistics of a finished game: for each player, what they did, counted from the replay of the game.

The Worker stores the result of this module for every game that was played to its end (table `game_stats`); the site averages it over
the games that match a filter (players, expansion, rated). It is pure: the same options and the same actions always give the same
numbers, so the statistics of old games can be made again whenever a counter is added. It is a record of what happened, not a rule:
nothing in the game reads it.

Two sources are used. The state at the end of the game says what a player ended with (orbiters and landers, tucked cards, techs, traces,
missions). The steps say what happened on the way (the actions, what each source gave, the sector wins, the signals, the income of each
round). Counters are plain numbers under flat names such as `action.launch` or `incomerate.r2.credit`; a counter that is zero is left out.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import card_defs, effects, projection, replay, solar, tables

VERSION = 2
MAIN_ACTIONS = ("launch", "scan", "analyze", "research", "orbit", "land", "play_card", "pass")
RESOURCES = ("credit", "energy", "card", "publicity", "data", "vp", "move")
# the sources of a gain that belong to one species (the others name it: {"kind": "alien", "species": ...})
ALIEN_SOURCES = {"explore": "arkhos", "glyph": "glyphids", "anomaly": "anomalies"}
# Counted apart: a probe launched, an orbiter or a lander placed by something other than the main action of that name
# (a card effect, a reward, an organization, the quick start ...).


def tech_use(c: Counter[str], before: Any, after: Any, seat: int, action: dict[str, Any], events: list[dict[str, Any]]) -> None:
    """What the techs did for a player, counted from one step of the game: `techuse.<tech>.<what>` (zero is left out). Only what
    happens while the player
    has the tech counts, that is after they researched it (a tech that Turing Systems borrows counts for the turn). The first tech of
    each type
    (the Twin Probes, `probe-dot`, whose effect is a number of probes) is not counted, nor is the Mercury Scope's cost: the number of
    times is the count.

    - Asteroid Skimmer (`probe-link`): `asteroids`, the probes that moved into an asteroid space;
    - Soft Landers (`probe-branch`): `lands`, the landing actions (each saves 1 energy);
    - Moon Rover (`probe-cross`): `moons`, the landings on a moon;
    - Earth Scope (`telescope-dot`): `adjacent`, the scans of a sector next to the sector of Earth;
    - Mercury Scope (`telescope-link`): `mercury`, the signals in Mercury's sector for 1 publicity;
    - Card Scope (`telescope-branch`): `discards`, the cards of the hand discarded for a signal;
    - Scan Booster (`telescope-cross`): `launches` (1 energy each) and `moves` (the free movement);
    - the four computer techs: `top`, the times that the upper space (2 points) was filled, `vp`, the points that gave, and `bottom`,
      the times that
      the lower space (the credit, the energy, the card or the 2 publicity) was filled."""
    me = before.players[seat]
    kind = action.get("type")

    def active(tech: str) -> bool:
        return effects.tech_active(me, tech)

    if kind == "move_probe" and "to" in action and active("probe-link"):
        if _cell_kind(before, int(action["to"][0]), int(action["to"][1])) == "asteroid":
            c["techuse.probe-link.asteroids"] += 1
    elif kind == "land" and active("probe-branch"):
        c["techuse.probe-branch.lands"] += 1
    elif kind == "scan_earth" and active("telescope-dot"):
        if int(action["sector"]) != solar.earth(before)[1]:
            c["techuse.telescope-dot.adjacent"] += 1
    elif kind == "scan_mercury" and active("telescope-link"):
        c["techuse.telescope-link.mercury"] += 1
    elif kind == "scan_hand_discard" and active("telescope-branch"):
        c["techuse.telescope-branch.discards"] += 1
    elif kind == "scan_probe" and active("telescope-cross"):
        c["techuse.telescope-cross.launches" if action.get("mode") == "launch" else "techuse.telescope-cross.moves"] += 1
    for e in events:
        if e.get("player") != seat:
            continue
        if e["type"] == "land" and "moon" in e and active("probe-cross"):
            c["techuse.probe-cross.moons"] += 1
        elif e["type"] == "place_data":
            slot = after.players[seat].computer_techs.get(int(e["position"]))
            if slot is not None:
                c[f"techuse.{slot.tech}.top"] += 1
                c[f"techuse.{slot.tech}.vp"] += 2  # TECH-20: the upper space of a computer tech gives 2 points
        elif e["type"] == "place_lower":
            c[f"techuse.{after.players[seat].computer_techs[int(e['slot'])].tech}.bottom"] += 1


def _cell_kind(state: Any, ring: int, sector: int) -> str:
    """What lies on a space of the solar system: a planet by name, a comet, an asteroid field ... (the space a probe moved onto)."""
    cell = solar.visible(state, ring, sector)[1]
    planet = solar.planet_of(cell)
    return planet if planet is not None else cell.lower()


def game_stats(file: dict[str, Any]) -> dict[str, Any]:
    """The statistics of a game from its archive (the `seti-game-log/1` file: the header with the options, and the actions in order)."""
    counts: dict[int, Counter[str]] = {}
    org_offered: dict[int, list[str]] = {}
    org_picked: dict[int, str] = {}
    final: Any = None
    before: Any = None
    for n, entry, result in replay.steps(file):
        state = result.state
        final = result
        if n == 0:
            counts = {p.index: Counter() for p in state.players}
            before = state
            continue
        assert entry is not None
        seat = projection.to_act(before)
        if seat is None:
            continue
        action = entry["action"]
        rnd = before.round
        if state.round != before.round or (state.phase == "finished" and before.phase != "finished"):
            for p in before.players:  # the income that each player has at the end of this round (INCOME-01), by round
                if p.index in counts:
                    for kind, amount in projection.tracker(before, p).income.items():
                        if kind in ("credit", "energy", "card"):
                            counts[p.index][f"incomerate.r{rnd}.{kind}"] = amount
        if seat in counts:
            kind = action.get("type")
            if kind in MAIN_ACTIONS:
                counts[seat][f"action.{kind}"] += 1
            if kind == "choose_org":
                org_offered[seat] = list(before.players[seat].offered_orgs)
                org_picked[seat] = str(action.get("org"))
            if kind == "move_probe" and "to" in action:
                where = _cell_kind(before, int(action["to"][0]), int(action["to"][1]))
                moved = [
                    e["changes"].get("publicity", 0)
                    for e in result.events
                    if e["type"] == "gains" and e["player"] == seat and e["source"].get("kind") == "move"
                ]
                counts[seat][f"visit.{where}"] += 1
                if sum(moved):
                    counts[seat][f"publicity.visit.{where}"] += sum(moved)
        if seat in counts:
            tech_use(counts[seat], before, state, seat, action, result.events)
        basic_done: set[str] = set()  # the launch that the launch action itself made (the first launch of the step)
        # orbiters and landers placed in this step: the main action of that name places one, anything else is another source
        for q in state.players:
            if q.index in counts and q.index < len(before.players):
                old = before.players[q.index]
                for name, key, attr in (("orbit", "orbits.other", "orbiters"), ("land", "lands.other", "landers")):
                    placed = sum(getattr(q, attr).values()) - sum(getattr(old, attr).values())
                    if placed > 0:
                        counts[q.index][key] += placed - (1 if q.index == seat and action.get("type") == name else 0)
        for e in result.events:
            t = e["type"]
            who = e.get("player")
            if who not in counts:
                continue
            c = counts[who]
            if t == "launch":
                if who == seat and action.get("type") == "launch" and not basic_done:
                    basic_done.add(t)  # the launch action itself
                else:
                    c["probes.launched.other"] += 1
            if t == "gains":
                src = e["source"].get("kind", "other")
                for res, amount in e["changes"].items():
                    if res == "data":
                        c["data.gained" if amount > 0 else "data.lost"] += abs(amount)
                    if res == "publicity" and src in ("sector", "signal"):
                        c[f"publicity.{src}"] += amount
                    if res in RESOURCES and amount > 0:
                        c[f"gain.{src}.{res}"] += amount
                    if res == "publicity" and amount > 0 and (species := ALIEN_SOURCES.get(src) or e["source"].get("species")):
                        c[f"publicity.alien.{species}"] += amount  # what the aliens gave, by species (the page adds them up)
            elif t == "place_data":
                c["data.computer"] += 1
            elif t == "sector_won":
                c[f"sectorwin.{state.sectors[int(e['sector'])].color}"] += 1
            elif t == "signal":
                c[f"signal.{state.sectors[int(e['sector'])].color}"] += 1
            elif t == "launch":
                c["probes.launched"] += 1
            elif t == "draw_card":
                c["cards.drawn"] += 1
            elif t == "play_card":
                c["cards.played"] += 1
                card = card_defs.CARDS.get(str(e["card"]), {})
                if "mission" in card:
                    c["missions.played"] += 1
                if "end" in card:
                    c["endcards.played"] += 1
            elif t == "mission_completed":
                c["missions.completed"] += 1
            elif t == "endgame_card":
                c["endcards.points"] += int(e["points"])
            elif t == "endgame_gold":
                tile = f"{e['tile']}-{e['side']}"
                c[f"gold.{tile}.points"] += int(e["points"])
                c[f"gold.{tile}.times"] += 1
        before = state
    assert final is not None
    end = final.state
    players: list[dict[str, Any]] = []
    for p in end.players:
        if end.rival is not None and p.index == end.rival.index:
            continue  # the solo rival is no player
        c = counts[p.index]
        c["orbiters"] = sum(p.orbiters.values())
        c["landers"] = sum(p.landers.values())
        for card in p.tucked:
            c[f"tucked.{tables.cards()[card]['income']}"] += 1
        for _slot, color in p.trace_log:
            c[f"trace.{color}"] += 1
        for tech in p.techs:
            c[f"tech.{tech}"] += 1
            c[f"techcat.{tech.split('-')[0]}"] += 1
        c["missions.done_end"] = len(p.completed_missions)
        c["stats.version"] = VERSION  # the page counts the newer counters (techuse, from effects) over the rows that have this mark only
        players.append(
            {
                "seat": p.index,
                "org": org_picked.get(p.index, p.organization),
                "org_offered": org_offered.get(p.index, []),
                "counters": {k: v for k, v in sorted(c.items()) if v},
            }
        )
    return {
        "version": VERSION,
        "expansion": bool(end.options.expansion),
        "species": [sl.species for sl in end.species if sl.species],
        "rounds": end.round,
        "players": players,
    }
