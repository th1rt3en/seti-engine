"""Steps, decisions, conditions, counts and end-of-game scoring that only the 42 main-deck cards of the Space Agencies expansion use
(docs/spec/expansion.md, EXP-03; data in docs/spec/data/expansion-deck.json and card_defs.py).

`run_step`, `cond_ok`, `count`, `end_points`, `decision_moves` and `resolve_decision` are called by cards.py for what it does not know
itself, the way alien_steps.py is.
"""

from __future__ import annotations

from typing import Any

from . import effects, rewards, solar, tables, trail
from .models import Decision, GameState, PlayerState

Action = dict[str, Any]
Events = list[dict[str, Any]]
CORNERS = ("publicity", "data", "move")  # the free-action corners a card can show (SA.2)
SECTOR_COLORS = ("yellow", "red", "blue", "black")


def _probe_cell(s: GameState, pr: Any) -> str:
    cell: str = solar.visible(s, pr.ring, pr.sector)[1]
    return cell


def _own_probes(s: GameState, p: PlayerState) -> list[Any]:
    return [pr for pr in s.probes if pr.player == p.index and not pr.capsule]


# ---------------------------------------------------------------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------------------------------------------------------------


def run_step(s: GameState, p: PlayerState, st: dict[str, Any], events: Events) -> bool:
    t = st["t"]
    if t == "return_card":  # SA.1, SA.5, SA.14: the card goes back to the hand instead of the discard pile (PLAY-02)
        s.play_return = True
    elif t == "hold":
        # EXP-SA5-01 (owner, 2026-10-23): the "then, if ..." of SA.5 and SA.38 comes after the player had the chance to use the movement
        # just gained (a free action may interrupt the card, FREE-00): it waits while the condition is false and a probe can still move
        from . import cards  # noqa: PLC0415 - cards imports this module

        if p.movement > 0 and _own_probes(s, p) and not cards.cond_ok(s, p, st["cond"]):
            s.pending.append(Decision(kind="hold", player=p.index))
    elif t == "show_corner":  # SA.2
        s.pending.append(Decision(kind="corner_pick", player=p.index))
    elif t == "paid_media":  # SA.17
        if p.credits >= 1:
            s.pending.append(Decision(kind="spend_credit", player=p.index))
    elif t == "restructure":  # SA.28
        if p.hand:
            s.pending.append(Decision(kind="restructure", player=p.index))
    elif t == "return_mission":  # SA.29
        if p.missions:
            s.pending.append(Decision(kind="return_mission", player=p.index, data={"r": st["r"]}))
    elif t == "discard_corner_none":
        pass
    elif t == "discard_corner":  # SA.20
        if any(tables.cards()[c]["species"] is None for c in p.hand):
            s.pending.append(Decision(kind="discard_corner", player=p.index, data={"times": st.get("times", 3)}))
    elif t == "discard_hand":  # SA.32
        with trail.cost(s, "discard_hand"):
            s.discard += p.hand
            p.hand = []
    elif t == "set_publicity":  # SA.18
        p.publicity = st.get("to", 0)
    elif t == "sig_each_marked":  # SA.37: a signal in each sector where the player already has one, without the data
        for i in [i for i, sec in enumerate(s.sectors) if p.index in sec.markers]:
            rewards.mark_signal(s, p, i, events, data=False)
    elif t == "sig_in_rich_sector":  # SA.22: signals in a sector where the player has at least 3
        sectors = [i for i, sec in enumerate(s.sectors) if sec.markers.count(p.index) >= st["min"]]
        if sectors:
            s.pending.append(
                Decision(kind="signal", player=p.index, data={"color": "any", "sectors": sectors, "times": st["n"], "nodata": True})
            )
    elif t == "energy_per_probe":  # SA.27
        if p.energy == 0:
            p.energy += len(_own_probes(s, p))
    elif t == "glyph_group":  # GL.1, GL.2, GL.8, GL.9: choose one group of glyph icons (EXP-GLY-06)
        from . import glyphids  # noqa: PLC0415

        done = glyphids.deciphered(s)
        if any(g in done for group in st["groups"] for g in group):
            s.pending.append(Decision(kind="glyph_group", player=p.index, data={"groups": st["groups"]}))
    elif t == "dlr":  # SE DE 04: a reward by the color of the sector the probe was launched in (Earth's sector)
        color = s.sectors[solar.earth(s)[1]].color
        reward = {
            "yellow": {"t": "move", "n": 2},
            "blue": {"t": "data", "n": 2},
            "red": {"t": "publicity", "n": 2},
            "black": {"t": "vp", "n": 6},
        }[color]
        rewards.grant(s, p, [reward], events)
    elif t == "orbit_free":  # SA.30
        s.pending.append(Decision(kind="orbit_land_free", player=p.index, data={"orbit_only": True}))
    else:
        return False
    return True


# ---------------------------------------------------------------------------------------------------------------------------------
# conditions and counts
# ---------------------------------------------------------------------------------------------------------------------------------


def cond_ok(s: GameState, p: PlayerState, c: dict[str, Any]) -> bool | None:
    k = c["c"]
    if k == "probes_planets":  # SA.7: probes in space at n different planets (Earth does not count)
        cells = {_probe_cell(s, pr) for pr in _own_probes(s, p)}
        return bool(sum(1 for x in cells if x.startswith("PLANET:") and x != "PLANET:EARTH") >= c["n"])
    if k == "species_colors_board":  # AM.14: a trace of each color on the species board or its overflow spaces (not the discovery spaces)
        i = next((i for i, sl in enumerate(s.species) if sl.species == c["species"]), None)
        if i is None:
            return False
        slot = s.species[i]
        return all(
            any(p.index in m for m in slot.board.get(col, []))
            or any(o == p.index and kind == col for o, kind in zip(slot.overflow, slot.overflow_kinds, strict=True))
            for col in ("pink", "yellow", "blue")
        )
    if k == "publicity_eq":  # SA.16
        return bool(p.publicity == c["n"])
    if k == "no_resources":  # SA.28: 0 credits, 0 energy and no cards in hand
        return p.credits == 0 and p.energy == 0 and not p.hand
    if k == "data_total":  # SA.35: data in the computer and in the data pool
        lower = sum(1 for t in p.computer_techs.values() if t.lower_filled)  # EXP-SA35-01: the lower spaces count (ANALYZE-02)
        return bool(sum(p.computer) + lower + p.data_pool >= c["n"])
    if k == "probe_shared":  # SA.38: a probe on a space with another probe
        spaces = [(pr.ring, pr.sector) for pr in s.probes if not pr.capsule]
        return any(spaces.count((pr.ring, pr.sector)) >= 2 for pr in _own_probes(s, p))
    if k == "adjacent_earth":  # SA.5: a probe on a space adjacent to Earth
        near = solar.adjacent(*solar.earth(s))
        return bool(any((pr.ring, pr.sector) in near for pr in _own_probes(s, p)))
    if k == "other_on_earth":  # SA.14: another player has a probe on Earth
        return bool(any(pr.player != p.index and not pr.capsule and (pr.ring, pr.sector) == solar.earth(s) for pr in s.probes))
    return None


def count(s: GameState, p: PlayerState, what: str) -> int | None:
    if what == "tech_computer":  # SA.30
        return sum(1 for t in p.techs if t.startswith("computer-"))
    if what == "max_tech_type":  # SA.34: techs of the type the player has the most of
        return max((sum(1 for t in p.techs if t.startswith(cat + "-")) for cat in ("probe", "telescope", "computer")), default=0)
    return None


def end_points(s: GameState, p: PlayerState, e: dict[str, Any]) -> int | None:
    w, n = e["what"], e["n"]
    if w == "per_data":  # SA.8
        return int(n * p.data_pool)
    if w == "per_publicity":  # SA.10
        return int(n * p.publicity)
    if w == "per_planets_orb_or_land":  # SA.39: planets (not moons) with an orbiter or a lander
        return int(n * sum(1 for planet in s.planets if p.orbiters.get(planet, 0) > 0 or p.landers.get(planet, 0) > 0))
    if w == "glyph_most":  # GL.1 (EXP-GLY-07 style): points for each token of the glyph type the player has the most of
        return int(n * max((p.glyphs.count(g) for g in set(p.glyphs)), default=0))
    if w == "glyph_set":  # GL.9: points for each glyph in the player's largest set of different glyphs
        return int(n * len(set(p.glyphs)))
    if w == "per_planets_two_landers":  # SA.31 (owner): planets with 2 of the player's landers, moons not counted
        return int(n * sum(1 for planet in s.planets if p.landers.get(planet, 0) >= 2))
    if w == "sig_all_colors":  # SA.41: a signal in a sector of each of the four colors
        got = {sec.color for sec in s.sectors if p.index in sec.markers}
        return n if got >= set(SECTOR_COLORS) else 0
    if w == "signals_each_sector":  # SA.42: a signal or a won sector in each sector
        return n if all(p.index in sec.markers or p.index in sec.winners for sec in s.sectors) else 0
    return None


# ---------------------------------------------------------------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------------------------------------------------------------


def decision_moves(s: GameState, d: Decision) -> list[Action] | None:
    p = s.players[d.player]
    if d.kind == "corner_pick":
        return [{"type": "corner_pick", "kind": k} for k in CORNERS]
    if d.kind == "glyph_group":
        return [{"type": "glyph_group", "group": i} for i in range(len(d.data["groups"]))]
    if d.kind == "hold":
        return [{"type": "hold_done"}]
    if d.kind == "spend_credit":
        return [{"type": "spend_credit"}, {"type": "spend_done"}]
    if d.kind == "restructure":
        return [{"type": "restructure_card", "card": c} for c in dict.fromkeys(p.hand)] + [{"type": "restructure_done"}]
    if d.kind == "return_mission":
        return [{"type": "return_mission", "card": m.card} for m in p.missions]
    if d.kind == "discard_corner":
        picks = [{"type": "discard_corner", "card": c} for c in dict.fromkeys(p.hand) if tables.cards()[c]["species"] is None]
        return picks or [{"type": "discard_corner_none"}]  # a free action may have used up the cards since the card was played
    return None


def resolve_decision(s: GameState, p: PlayerState, d: Decision, a: Action, events: Events) -> bool:
    from . import cards  # noqa: PLC0415 - cards imports this module

    t = a["type"]
    if t == "corner_pick":  # SA.2: once for each card shown from the hand that has the icon in its free-action corner
        n = sum(1 for c in p.hand if any(k == a["kind"] for k, _ in tables.cards()[c]["free"]))
        if a["kind"] == "publicity":
            effects.gain_publicity(s, p, n)
        elif a["kind"] == "data":
            effects.gain_data(s, p, n)
        else:
            p.movement += n
    elif t == "glyph_group":
        from . import glyphids  # noqa: PLC0415

        for g in d.data["groups"][a["group"]]:  # a repeated glyph gives its resource twice (A-045)
            glyphids.glyph_resource(s, p, g, events)
    elif t == "spend_credit":  # SA.17
        with trail.cost(s, "spend_credit"):
            p.credits -= 1
        effects.gain_score(s, p, 2)
        effects.gain_publicity(s, p, 2)
        if p.credits >= 1:
            s.pending.insert(0, Decision(kind="spend_credit", player=p.index))
    elif t == "spend_done" or t == "hold_done":
        pass
    elif t == "restructure_card":  # SA.28: a discarded card gives its income resource
        with trail.cost(s, "restructure"):
            p.hand.remove(a["card"])
            s.discard.append(a["card"])
        effects.gain_income_resource(s, p, tables.cards()[a["card"]]["income"])
        if p.hand:
            s.pending.insert(0, Decision(kind="restructure", player=p.index))
    elif t == "restructure_done":
        pass
    elif t == "return_mission":  # SA.29
        m = next(x for x in p.missions if x.card == a["card"])
        p.missions.remove(m)
        p.hand.append(m.card)
        rewards.grant(s, p, d.data["r"], events)
    elif t == "discard_corner":  # SA.20
        with trail.cost(s, "corner_discard"):
            p.hand.remove(a["card"])
            s.discard.append(a["card"])
        for _ in range(d.data["times"]):
            cards.gain_corner(s, p, a["card"])
    else:
        return False
    return True
