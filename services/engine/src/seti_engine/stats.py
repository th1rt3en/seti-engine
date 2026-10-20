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

from . import card_defs, projection, replay, solar, tables

VERSION = 1
MAIN_ACTIONS = ("launch", "scan", "analyze", "research", "orbit", "land", "play_card", "pass")
RESOURCES = ("credit", "energy", "card", "publicity", "data", "vp", "move")


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
        for e in result.events:
            t = e["type"]
            who = e.get("player")
            if who not in counts:
                continue
            c = counts[who]
            if t == "gains":
                src = e["source"].get("kind", "other")
                for res, amount in e["changes"].items():
                    if res == "data":
                        c["data.gained" if amount > 0 else "data.lost"] += abs(amount)
                    if res == "publicity" and src in ("sector", "signal"):
                        c[f"publicity.{src}"] += amount
                    if res in RESOURCES and amount > 0:
                        c[f"gain.{src}.{res}"] += amount
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
