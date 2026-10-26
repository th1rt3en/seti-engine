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

from . import amoeba, card_defs, effects, glyphids, projection, replay, solar, species, tables

# 3: the cards played by round (`card.<id>.r<round>`) and the parts of the final score (`final.<part>`);
# 4: what each resource was spent on (`spend.<what>.<resource>`, the `cost` scopes of the trail), the quick start cards kept (`quick.<id>`)
# 5: the costs inside card effects, of Exertian cards and of organizations, and the exofossils (gained and spent) are counted too
# 6: the resource of a tucked card is income (`gain.income`), and what the actions gave is told by action (`gainmove.<action>.<resource>`)
# 7: the movement spent is told by what it moved into (`spend.move_<planet|asteroid|comet|earth|empty|capsule>.move`), the movement lost
# at the
# end of the turn, the exofossils left over (`spend.leftover.exofossil`), the glyph tokens as a resource (`gain.<source>.token`,
# `spend.decipher.token`), and the publicity and data income of each round (`incomerate.r<round>.publicity|data`)
# 8: the quick start cards that were offered (`quickoffered.<id>`), for the keep rate
VERSION = 8
SECURITY_CARDS = frozenset(str(x["id"]) for x in tables.arkhos()["security"])
MAIN_ACTIONS = ("launch", "scan", "analyze", "research", "orbit", "land", "play_card", "pass")
RESOURCES = ("credit", "energy", "card", "publicity", "data", "vp", "move", "exofossil", "token")
# the sources of a gain that belong to one species (the others name it: {"kind": "alien", "species": ..., "what": ...})
ALIEN_SOURCES = {"explore": "arkhos", "glyph": "glyphids", "anomaly": "anomalies"}


def alien_source(src: dict[str, Any]) -> tuple[str, str] | None:
    """The species and the part of its rules that a gain came from (`arkhos` `minor`, `glyphids` `translation`, `amoeba` `group` ...)."""
    kind = src.get("kind")
    if kind == "explore":
        return "arkhos", str(src.get("level"))
    if kind == "glyph":
        return "glyphids", "translation"
    if kind == "anomaly":
        return "anomalies", "token"
    if kind == "alien":
        return str(src["species"]), str(src.get("what", "effect"))
    return None


def gain_counts(c: Counter[str], e: dict[str, Any], action: str | None = None) -> None:
    """What one `gains` event adds: the data, the publicity of the sectors and signals, and every resource by the source that gave it."""
    src = e["source"].get("kind", "other")
    alien = alien_source(e["source"])
    what = str(e["source"].get("what")) if src == "cost" else src  # a cost is told by what it paid for (launch, scan, trade ...)
    for res, amount in e["changes"].items():
        if amount < 0 and res in RESOURCES:
            c[f"spend.{what}.{res}"] += -amount
        if res == "data":
            c["data.gained" if amount > 0 else "data.lost"] += abs(amount)
        if res == "publicity" and src in ("sector", "signal"):
            c[f"publicity.{src}"] += amount
        if res in RESOURCES and amount > 0:
            c[f"gain.{src}.{res}"] += amount
            if src == "move" and action is not None:
                c[f"gainmove.{action}.{res}"] += amount  # what the actions gave, by action (the page names them under Others)
            if alien is not None:
                c[f"alien.{alien[0]}.{alien[1]}.{res}"] += amount
        if alien is not None and res == "publicity" and amount > 0:
            c[f"publicity.alien.{alien[0]}"] += amount  # what the aliens gave, by species (the page adds them up)


def alien_end(c: Counter[str], end: Any, p: Any) -> None:
    """What the state at the end of the game says about a player and the species that were discovered."""
    for sl in end.species:
        if sl.species and sl.discovered:
            c[f"alien.{sl.species}.games"] = 1  # its averages are over the players of the games where it was discovered
    c["oumuamua.orbiters"] = p.orbiters.get("oumuamua", 0)
    c["oumuamua.landers"] = p.landers.get("oumuamua", 0)
    row = next((r for r in end.final_scores if r["player"] == p.index), None)
    if row is not None:  # where the final score came from: board, end-of-game cards, gold tiles, Exertian cards, glyph tokens
        for part in ("board", "cards", "gold", "exertian", "glyphs", "loss"):
            c[f"final.{part}"] = int(row[part])
    if row is not None and species.exertian_slot(end) is not None:  # ALIEN-EXE-06, ALIEN-EXE-07
        c["exertians.danger"] = species.danger(end, p)
        c["exertians.danger.cards"] = species.cards_danger(p)
        c["exertians.danger.board"] = species.board_danger(end, p)
        c["exertians.played"] = len(p.exertian_played)
        c["exertians.loss"] = int(row["loss"])
    if row is not None and glyphids.slot_index(end) is not None:  # EXP-GLY-07
        c["glyphids.leftover"] = len(p.glyphs)
        c["glyphids.leftover.vp"] = int(row["glyphs"])


def alien_events(c: Counter[str], e: dict[str, Any], before: Any, state: Any) -> None:
    """What the species did for a player in one event: `<species>.<what>` counters. The resources they gave are counted with the gains
    (`alien.<species>.<what>.<resource>`)."""
    t = e["type"]
    if t == "sample_delivered":
        c["mascamites.delivered"] += 1  # a delivery mission completed
    elif t == "anomaly":
        c["anomalies.won"] += 1
    elif t == "signal_tile":
        c["oumuamua.signals"] += 1
    elif t == "tile_resolved":
        c["oumuamua.wins"] += 1
    elif t == "message_reward":
        i = species.message_slot(before)
        taken = 0 if i is None else sum(1 for x in before.species[i].extra["covered"] if x is not None)
        c[f"centaurians.pick.{e['hex']}"] += 1
        c[f"centaurians.order.{e['hex']}"] += taken + 1  # the 1st to the 4th reward taken on the board, by anyone
    elif t == "message_card_placed":
        c["centaurians.cards.played"] += 1
    elif t == "message_resolved":
        c["centaurians.cards.completed"] += 1
    elif t == "explore":
        c[f"arkhos.explore.{e['level']}"] += 1
    elif t == "breach":
        c["arkhos.breach"] += 1
    elif t == "glyph":
        kind, _, rest = str(e["where"]).partition(":")
        if kind == "board":
            color, _, k = rest.partition(":")
            columns = {col["color"]: col["spaces"] for col in glyphids.data()["board"]["columns"]}
            kind = f"board_{columns[color][int(k)]['well']}"  # the upper and the lower wells of the board
        c[f"glyphids.token.{kind}"] += 1
    elif t == "decipher":
        c["glyphids.placed"] += 1
    elif t == "organelle":
        c[f"amoeba.single.{amoeba.color_of(str(e['space']))}"] += 1
    elif t == "organelles":
        c[f"amoeba.group.{e['color']}"] += 1
        c[f"amoeba.group.{e['color']}.tokens"] += len(e["spaces"])
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
        action = entry["action"]
        seat = projection.actor_of(before, action)  # in the simultaneous setup the move names its seat (EXP-ORG-14)
        if seat is None:
            continue
        rnd = before.round
        if state.round != before.round or (state.phase == "finished" and before.phase != "finished"):
            for p in before.players:  # the income that each player has at the end of this round (INCOME-01), by round
                if p.index in counts:
                    for kind, amount in projection.tracker(before, p).income.items():
                        if kind in ("credit", "energy", "card"):
                            counts[p.index][f"incomerate.r{rnd}.{kind}"] = amount
                    for kind in ("publicity", "data"):  # no base income: only the cards tucked for it
                        n = sum(1 for c in p.tucked if tables.cards()[c]["income"] == kind)
                        if n > 0:
                            counts[p.index][f"incomerate.r{rnd}.{kind}"] = n
        if seat in counts:
            kind = action.get("type")
            if kind in MAIN_ACTIONS:
                counts[seat][f"action.{kind}"] += 1
            if kind == "choose_quick":  # the quick start cards that were offered (a player may choose again: it is counted once)
                for cid in before.players[seat].offered_quick:
                    counts[seat][f"quickoffered.{cid}"] = 1
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
        for q in state.players:  # the exofossils that a player gained and spent in this step
            if q.index in counts and q.index < len(before.players):
                delta = q.exofossils - before.players[q.index].exofossils
                if delta:
                    counts[q.index]["oumuamua.exofossil.gained" if delta > 0 else "oumuamua.exofossil.spent"] += abs(delta)
        for e in result.events:
            t = e["type"]
            who = e.get("player")
            if who not in counts:
                continue
            c = counts[who]
            alien_events(c, e, before, state)
            if t == "launch":
                if who == seat and action.get("type") == "launch" and not basic_done:
                    basic_done.add(t)  # the launch action itself
                else:
                    c["probes.launched.other"] += 1
            if t == "gains":
                gain_counts(c, e, str(action.get("type")))
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
                c[f"card.{e['card']}.r{rnd}"] += 1  # a card of the main deck or of a species, by the round in which it was played
                card = card_defs.CARDS.get(str(e["card"]), {})
                if "mission" in card:
                    c["missions.played"] += 1
                    if card["mission"].get("kind") == "deliver":
                        c["mascamites.mission.played"] += 1
                if str(e["card"]) in SECURITY_CARDS:
                    c["arkhos.security.played"] += 1
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
        if p.exofossils > 0:
            c["spend.leftover.exofossil"] = p.exofossils  # wasted: the exofossils that are left at the end of the game
        for cid in p.quick_start:  # the quick start cards that the player kept (Space Agencies)
            c[f"quick.{cid}"] = 1
        alien_end(c, end, p)
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
