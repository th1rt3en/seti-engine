"""Playing cards: the step interpreter, quick and triggerable missions, turn effects and end-of-game scoring cards.

Spec: cards-and-missions.md (CARD-01 to CARD-48), actions.md (PLAY-01, PLAY-02, FREE-07, FREE-08), faq.md (FAQ-30, FAQ-31, FAQ-C*).
The effect of a card is a list of steps (card_defs.py). `play` puts the steps in `state.queue`; `run_queue` runs them in order and stops
whenever a step needs a decision (it appends a `Decision`; the engine calls `run_queue` again when the decision is resolved).
"""

from __future__ import annotations

import copy
from collections import deque
from typing import Any

from . import alien_steps, card_defs, effects, objectives, rewards, solar, tables, techs
from .models import Decision, GameState, MissionState, PlayerState

Action = dict[str, Any]
Events = list[dict[str, Any]]
SECTOR_COLORS = ("yellow", "red", "blue", "black")


def card_cost(cid: str) -> int:
    return int(tables.cards()[cid]["cost"])


def playable(cid: str) -> bool:
    d = card_defs.CARDS.get(cid)
    return d is not None and "todo" not in d


# ---------------------------------------------------------------------------------------------------------------------------------
# playing a card (PLAY-01, PLAY-02)
# ---------------------------------------------------------------------------------------------------------------------------------


def pays_energy(cid: str) -> bool:
    return bool(tables.cards()[cid]["species"] == "centaurians")  # ALIEN-CEN-02: Centaurian cards cost energy


def play_moves(s: GameState, p: PlayerState) -> list[Action]:
    return [
        {"type": "play_card", "card": c}
        for c in dict.fromkeys(p.hand)
        if playable(c) and (p.energy if pays_energy(c) else p.credits) >= card_cost(c)
    ]


def play(s: GameState, p: PlayerState, cid: str, events: Events) -> None:
    """PLAY-01: pay the cost, then resolve the effect. The card goes to the discard pile afterwards unless it stays (PLAY-02)."""
    cost = card_cost(cid)
    if pays_energy(cid):
        effects.pay(p, energy=cost)
    else:
        effects.pay(p, credits=cost)
    p.hand.remove(cid)
    s.playing = cid
    s.action_sectors = []
    s.play_return = False
    s.queue = copy.deepcopy(card_defs.CARDS[cid].get("fx", []))
    events.append({"type": "play_card", "player": p.index, "card": cid})
    m = card_defs.CARDS[cid].get("mission")
    if m:  # A-019: a mission is in play from the moment its card is played, so its own effect can trigger it
        p.missions.append(MissionState(card=cid, kind=m["kind"], used=[False] * len(m.get("circles", []))))
    if cost > 0 and not pays_energy(cid):
        fire(s, p, [{"e": "play_cost", "cost": cost}], events)  # FAQ-C106


def finish_play(s: GameState, p: PlayerState, events: Events) -> None:
    """PLAY-02, CARD-10, CARD-20, CARD-30: place the played card."""
    cid = s.playing
    assert cid is not None
    s.playing = None
    d = card_defs.CARDS[cid]
    if s.play_return:  # #120 Orbiting Lagrange Point
        s.play_return = False
        p.hand.append(cid)
    elif "mission" in d or any(m.card == cid for m in p.message_cards):
        pass  # already in front of the player (A-019, ALIEN-CEN-02)
    elif "end" in d:
        p.end_cards.append(cid)
    elif cid not in p.tucked:  # #91 to #93 tuck themselves
        s.discard.append(cid)


def run_queue(s: GameState, events: Events) -> None:
    """Run the queued steps until a decision is needed or the effect is done."""
    p = s.players[s.current_player]
    while s.queue and not s.pending:
        step = s.queue.pop(0)
        run_step(s, p, step, events)
    if not s.queue and not s.pending and s.playing is not None:
        finish_play(s, p, events)


# ---------------------------------------------------------------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------------------------------------------------------------


def run_step(s: GameState, p: PlayerState, st: dict[str, Any], events: Events) -> None:
    t = st["t"]
    n = st.get("n", 1)
    if t in (
        "vp",
        "data",
        "energy",
        "credit",
        "publicity",
        "card_any",
        "card_random",
        "tuck",
        "signal_color",
        "trace",
        "launch",
        "exofossil",
        "exofossil_pay",
        "signal_oumuamua",
        "signal_any",
    ):
        if t == "trace":
            _trace_step(s, p, st)
        else:
            rewards.grant(s, p, [st], events)
    elif t == "move":
        p.movement += n
    elif t == "rotate":
        techs.rotate_solar_system(s, events)
        fire_pushed(s, events)
    elif t == "research":
        _research_step(s, p, st)
    elif t == "scan_free":
        techs.start_scan(
            s,
            p,
            free=True,
            ctx={
                "vp_color": st.get("vp_color"),
                "vp": st.get("vp", 0),
                "vp_tile": st.get("vp_tile", 0),
                "exo_if_tile": st.get("exo_if_tile", False),
            },
        )
        fire(s, p, [{"e": "scan"}], events)
    elif t == "land_free":
        opts = {k: v for k, v in st.items() if k not in ("t", "n")}
        if land_free_moves(s, p, opts):
            s.pending.append(Decision(kind="land_free", player=p.index, data=opts))
    elif t == "sig_star":
        idx = next(i for i, sec in enumerate(s.sectors) if sec.star == st["star"])
        for _ in range(n):
            rewards.mark_signal(s, p, idx, events)
    elif t == "sig_planet":
        pos = solar.find_cell(s, f"PLANET:{st['planet'].upper()}")
        assert pos is not None
        for _ in range(n):
            rewards.mark_signal(s, p, pos[1], events)
    elif t == "sig_earth":
        for _ in range(n):
            rewards.mark_signal(s, p, solar.earth(s)[1], events)
    elif t == "sig_any":
        s.pending += [Decision(kind="signal", player=p.index, data={"color": "any"}) for _ in range(n)]
    elif t == "sig_each_color":
        s.pending += [Decision(kind="signal", player=p.index, data={"color": c, "nodata": st.get("nodata", False)}) for c in SECTOR_COLORS]
    elif t == "sig_probe":
        if any(pr.player == p.index for pr in s.probes):
            s.pending.append(
                Decision(kind="pick_probe", player=p.index, data={"n": n, "nbrs": st.get("nbrs", False), "nodata": st.get("nodata", False)})
            )
    elif t == "probes_sig":
        if s.probes:
            s.pending.append(Decision(kind="gop", player=p.index, data={"left": n, "chosen": []}))
    elif t == "row_scan":
        s.queue[0:0] = [{"t": "row_pick"} for _ in range(min(n, len(s.card_row)))]
    elif t == "row_pick":
        if s.card_row:
            s.pending.append(Decision(kind="row_pick", player=p.index))
    elif t == "refill_row":
        effects.refill_card_row(s)
    elif t == "hand_signals":
        if any(tables.cards()[c].get("sector") for c in p.hand):
            s.pending.append(Decision(kind="hand_signal", player=p.index, data={"left": n}))
    elif t == "deck_signals":
        s.queue[0:0] = [{"t": "deck_signal"} for _ in range(n)]
    elif t == "deck_signal":
        cid = effects.draw_from_deck(s)
        if cid is not None:
            s.discard.append(cid)
            s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[cid]["sector"]}))
    elif t == "unique_sector_vp":
        effects.gain_score(s, p, n * len(set(s.action_sectors)))
    elif t == "if":
        if cond_ok(s, p, st["cond"]):
            s.queue[0:0] = copy.deepcopy(st["then"])
    elif t == "watch":
        _watch(s, p, st["w"], events)
    elif t == "per":
        count = _count(s, p, st["count"])
        if count:
            r = dict(st["r"])
            r["n"] = r.get("n", 1) * count
            rewards.grant(s, p, [r], events)
    elif t == "tuck_self":
        cid = s.playing
        assert cid is not None
        p.tucked.append(cid)
        effects.gain_income_resource(s, p, tables.cards()[cid]["income"])  # FAQ-C091: an income increase pays at once
    elif t == "grant":
        s.pending.append(Decision(kind="take_card", player=p.index, data={"reveal": True}))
    elif t == "clean_space":
        for cid in list(s.card_row):
            s.card_row.remove(cid)
            s.discard.append(cid)
            gain_corner(s, p, cid)
        effects.refill_card_row(s)
    elif t == "remove_orbiter":
        if remove_orbiter_moves(s, p):
            s.pending.append(Decision(kind="remove_orbiter", player=p.index, data={"r": st["r"]}))
    elif t == "remove_lander":
        if remove_lander_moves(s, p):
            s.pending.append(Decision(kind="remove_lander", player=p.index, data={"r": st["r"]}))
    elif t == "trace_same":
        slots = sorted({sl for sl, k in p.trace_log if k == st["kind"]})
        if slots:
            s.pending.append(Decision(kind="trace", player=p.index, data={"color": st["kind"], "slots": slots}))
    elif t == "trace_vp":
        s.pending.append(Decision(kind="trace", player=p.index, data={"color": "any", "then_vp": st["vp"]}))
    elif t == "optimal":
        er, es = solar.earth(s)
        count = sum(
            1
            for r in range(1, 5)
            if r != er  # FAQ-C133: the other spaces of Earth's sector, away from the Sun (up to 3)
            if solar.visible(s, r, es)[1] == "COMET" or solar.visible(s, r, es)[1].startswith("PLANET:")
        )
        p.movement += count
    elif t == "osiris":
        if any(pr.player == p.index for pr in s.probes):
            s.pending.append(Decision(kind="pick_probe", player=p.index, data={"osiris": True}))
    elif t == "lagrange":
        if any(pr.player == p.index for pr in s.probes):
            s.pending.append(Decision(kind="pick_probe", player=p.index, data={"n": 1, "lagrange": True}))
    elif not alien_steps.run_step(s, p, st, events):
        raise ValueError(f"unknown step {t}")


def _trace_step(s: GameState, p: PlayerState, st: dict[str, Any]) -> None:
    for _ in range(st.get("n", 1)):
        data: dict[str, Any] = {"color": st["kind"]}
        if st.get("slots") == "all_kinds":
            data["slots"] = [sl for sl in range(2) if {k for x, k in p.trace_log if x == sl} >= {"pink", "yellow", "blue"}]
            if not data["slots"]:
                return
        s.pending.append(Decision(kind="trace", player=p.index, data=data))


def _research_step(s: GameState, p: PlayerState, st: dict[str, Any]) -> None:
    cat = st["cat"]
    cats = {"any": ("probe", "telescope", "computer"), "probe_telescope": ("probe", "telescope")}.get(cat, (cat,))
    stacks = [
        i
        for i, ts in enumerate(s.tech_stacks)
        if ts.category in cats
        and ts.tiles
        and techs.tech_name(ts.category, ts.glyph) not in p.techs  # TECHACT-07
        and (
            not st.get("copy") or any(techs.tech_name(ts.category, ts.glyph) in q.techs for q in s.players if q.index != p.index)
        )  # FAQ-C081
    ]
    if stacks:  # TECHACT-06: with all techs of the type already owned the tech part is ignored
        s.pending.append(
            Decision(kind="research_tech", player=p.index, data={"stacks": stacks, **{k: v for k, v in st.items() if k not in ("t", "n")}})
        )


def land_free_moves(s: GameState, p: PlayerState, opts: dict[str, Any]) -> list[Action]:
    """Landing from a card effect (#12, #13, #16): no energy cost; the card may lift the moon tech and the occupied-space limits."""
    out: list[Action] = []
    for pr in s.probes:
        if pr.player != p.index or pr.capsule:
            continue
        planet = solar.planet_of(solar.visible(s, pr.ring, pr.sector)[1])
        if planet not in s.planets:
            continue
        out.append({"type": "land_free", "probe": pr.id})
        if opts.get("any_moon") or "probe-cross" in p.techs:
            for moon in planet_moons(planet):
                if opts.get("occupied") or moon not in s.planets[planet].moon_landers:
                    out.append({"type": "land_free", "probe": pr.id, "moon": moon})
    return out


def remove_orbiter_moves(s: GameState, p: PlayerState) -> list[Action]:
    """#15, A-018: the player picks any of their own orbiters; one on the first-orbiter space is a separate choice (FAQ-C015)."""
    out: list[Action] = []
    for planet, st in s.planets.items():
        mine = st.orbiters.count(p.index)
        if not mine:
            continue
        if st.first_orbiter == p.index:
            out.append({"type": "remove_orbiter", "planet": planet, "first": True})
        if mine > (1 if st.first_orbiter == p.index else 0):
            out.append({"type": "remove_orbiter", "planet": planet, "first": False})
    return out


def remove_lander_moves(s: GameState, p: PlayerState) -> list[Action]:
    """#84, A-018: any of the player's own landers on a planet or moon; one on a first-lander space is a separate choice (FAQ-C084)."""
    out: list[Action] = []
    for planet, st in s.planets.items():
        mine = st.landers.count(p.index)
        owned = [k for k, o in enumerate(st.first_land_owners) if o == p.index]
        out += [{"type": "remove_lander", "planet": planet, "slot": k} for k in owned]
        if mine > len(owned):
            out.append({"type": "remove_lander", "planet": planet, "slot": None})
        out += [{"type": "remove_lander", "planet": planet, "moon": m} for m, owner in st.moon_landers.items() if owner == p.index]
    return out


def research_moves(d: Decision) -> list[Action]:
    return [{"type": "take_tech", "stack": i} for i in d.data["stacks"]]


def take_free_tech(s: GameState, p: PlayerState, d: Decision, a: Action, events: Events) -> None:
    st = s.tech_stacks[a["stack"]]
    name = techs.tech_name(st.category, st.glyph)
    other_has = any(name in q.techs for q in s.players if q.index != p.index)
    techs.take_tech(s, p, a["stack"], events, tile_bonus=not d.data.get("copy"), first_bonus=not d.data.get("copy"))
    if d.data.get("then_vp_per_tech"):
        effects.gain_score(s, p, d.data["then_vp_per_tech"] * sum(1 for t in p.techs if t.startswith(st.category + "-")))
    if d.data.get("copy_bonus") and other_has:
        rewards.grant(s, p, d.data["copy_bonus"], events)
    fire(s, p, [{"e": "tech", "cat": st.category}], events)


# ---------------------------------------------------------------------------------------------------------------------------------
# counts and conditions
# ---------------------------------------------------------------------------------------------------------------------------------


def _count(s: GameState, p: PlayerState, what: str) -> int:
    cards = tables.cards()
    if what == "hand_move_corner":
        return sum(1 for c in p.hand if any(k == "move" for k, _ in cards[c]["free"]))
    if what.startswith("hand_income_"):
        return sum(1 for c in p.hand if cards[c]["income"] == what.removeprefix("hand_income_"))
    if what.startswith("tucked_income_"):
        return sum(1 for c in p.tucked if cards[c]["income"] == what.removeprefix("tucked_income_"))
    if what == "publicity":
        return p.publicity
    raise ValueError(what)


def planet_moons(planet: str) -> list[str]:
    return list(tables.planet_info(planet)["moons"])


def _at(p: PlayerState, planet: str, orbiters: bool = True, landers: bool = True, moons: bool = True) -> int:
    n = 0
    if orbiters:
        n += p.orbiters.get(planet, 0)
    if landers:
        n += p.landers.get(planet, 0)
        if moons:
            n += sum(p.landers.get(m, 0) for m in planet_moons(planet))
    return n


def distance_from_earth(s: GameState, ring: int, sector: int) -> int:
    """Number of moves between a space and Earth's space (ambiguity A-017: the spec does not say how spaces are counted)."""
    start = solar.earth(s)
    seen = {start}
    q: deque[tuple[tuple[int, int], int]] = deque([(start, 0)])
    while q:
        pos, d = q.popleft()
        if pos == (ring, sector):
            return d
        for nxt in solar.adjacent(*pos):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return 99


def cond_ok(s: GameState, p: PlayerState, c: dict[str, Any]) -> bool:
    k = c["c"]
    n: int = c.get("n", 0)
    alien = alien_steps.cond_ok(s, p, c)
    if alien is not None:
        return alien
    if k == "orbland":
        planets = [c["planet"]] if c["planet"] else list(s.planets)
        total = sum(_at(p, pl, not c["landers_only"], not c["orbiters_only"], c["moons"]) for pl in planets)
        return bool(total >= n)
    if k == "both":
        return all(_at(p, pl) >= 1 for pl in c["planets"])
    if k == "same_planet":
        return any(p.orbiters.get(pl, 0) >= 1 and _at(p, pl, False, True, True) >= 1 for pl in s.planets)
    if k == "wins":
        return sum(sec.winners.count(p.index) for sec in s.sectors if c["color"] in (None, sec.color)) >= n
    if k == "wins_same":
        return any(sec.winners.count(p.index) >= n for sec in s.sectors)
    if k == "traces":
        return sum(1 for _, kind in p.trace_log if kind == c["kind"]) >= n
    if k == "each_species":
        return all(any(sl == i and kind == c["kind"] for sl, kind in p.trace_log) for i in range(len(s.species)))
    if k == "single_species_all":
        return any({kind for sl, kind in p.trace_log if sl == i} >= {"pink", "yellow", "blue"} for i in range(len(s.species)))
    if k == "sig_sectors":
        return sum(1 for sec in s.sectors if p.index in sec.markers) >= n
    if k == "techs":
        return sum(1 for t in p.techs if t.startswith(c["cat"] + "-")) >= n
    if k == "probe_on":
        return any(_probe_on(s, pr, c["where"]) for pr in s.probes if pr.player == p.index)
    if k == "probe_far":
        return any(distance_from_earth(s, pr.ring, pr.sector) >= n for pr in s.probes if pr.player == p.index)
    if k == "hand_empty":
        return not p.hand
    if k == "score":
        return p.score >= n
    if k == "publicity":
        return p.publicity >= n
    raise ValueError(k)


def _probe_on(s: GameState, pr: Any, where: str) -> bool:
    cell = solar.visible(s, pr.ring, pr.sector)[1]
    if where == "asteroid":
        return bool(cell == "ASTEROID")
    if where == "comet":
        return bool(cell == "COMET")
    if where == "asteroid_adjacent_earth":
        return bool(cell == "ASTEROID" and (pr.ring, pr.sector) in solar.adjacent(*solar.earth(s)))
    raise ValueError(where)


# ---------------------------------------------------------------------------------------------------------------------------------
# missions (CARD-10 to CARD-16)
# ---------------------------------------------------------------------------------------------------------------------------------


def mission_moves(s: GameState, p: PlayerState) -> list[Action]:
    """FREE-07: complete a conditional mission whose condition is met (never forced, CARD-11), or deliver a sample (ALIEN-MASC-04)."""
    out: list[Action] = [
        {"type": "complete_mission", "card": m.card}
        for m in p.missions
        if m.kind == "quick" and cond_ok(s, p, card_defs.CARDS[m.card]["mission"]["cond"])
    ]
    for m in p.missions:
        if m.kind == "deliver":
            dest = solar.earth(s) if card_defs.CARDS[m.card]["mission"]["dest"] == "earth" else solar.find_cell(s, "PLANET:MARS")
            out += [
                {"type": "deliver_sample", "card": m.card, "capsule": pr.id}
                for pr in s.probes
                if pr.player == p.index and pr.capsule and (pr.ring, pr.sector) == dest
            ]
    return out


def deliver(s: GameState, p: PlayerState, cid: str, capsule: str, events: Events) -> None:
    """ALIEN-MASC-04: deliver the capsule: the token's reward (twice for #ET.7), the card's reward, and the card is a completed mission."""
    from . import species  # noqa: PLC0415

    m = next(x for x in p.missions if x.card == cid)
    mission = card_defs.CARDS[cid]["mission"]
    p.missions.remove(m)
    p.completed_missions.append(cid)
    species.deliver_sample(s, p, capsule, events, times=2 if mission.get("twice") else 1)
    rewards.grant(s, p, mission["r"], events)
    fire(s, p, [{"e": "mission_done"}], events)


def complete_quick(s: GameState, p: PlayerState, cid: str, events: Events) -> None:
    m = next(x for x in p.missions if x.card == cid)
    p.missions.remove(m)
    p.completed_missions.append(cid)
    events.append({"type": "mission_completed", "player": p.index, "card": cid})
    rewards.grant(s, p, card_defs.CARDS[cid]["mission"]["r"], events)
    fire(s, p, [{"e": "mission_done"}], events)


def rotate_everything(s: GameState, events: Events) -> None:
    """Rotate the solar system and resolve what it sets off: pushed probes and the anomalies (ROTATE-01 to ROTATE-04, ALIEN-ANO-02)."""
    from . import species  # noqa: PLC0415

    techs.rotate_solar_system(s, events)
    fire_pushed(s, events)
    species.after_rotation(s, events)


def fire(s: GameState, p: PlayerState, evs: list[dict[str, Any]], events: Events) -> None:
    """FREE-08, CARD-12, CARD-14, FAQ-31: things the player did can cover one circle of a triggerable mission (the player may decline).
    The same things can mark a task of the solo objectives (SOLO-OBJ-04)."""
    objectives.on_event(s, p, evs)
    options: list[list[Any]] = []
    for m in p.missions:
        if m.kind != "trigger":
            continue
        for i, circ in enumerate(card_defs.CARDS[m.card]["mission"]["circles"]):
            if not m.used[i] and any(_matches(circ["on"], e) for e in evs):
                options.append([m.card, i])
    if options:
        s.pending.insert(0, Decision(kind="mission_trigger", player=p.index, data={"options": options}))


def _matches(spec: dict[str, Any], ev: dict[str, Any]) -> bool:
    if spec["e"] != ev["e"]:
        return False
    for key in ("planet", "cat", "kind", "color", "cost", "corner"):
        if key in spec and spec[key] != "*" and spec[key] != ev.get(key):
            return False
    if spec.get("own_turn") and not ev.get("own_turn"):
        return False
    if spec["e"] == "visit" and spec["planet"] == "*":
        return ev.get("planet") not in (None, "earth")
    return True


def cover(s: GameState, p: PlayerState, cid: str, circle_index: int, events: Events) -> None:
    m = next(x for x in p.missions if x.card == cid)
    m.used[circle_index] = True
    events.append({"type": "mission_circle", "player": p.index, "card": cid, "circle": circle_index})
    rewards.grant(s, p, card_defs.CARDS[cid]["mission"]["circles"][circle_index]["r"], events)
    if all(m.used):  # CARD-15
        p.missions.remove(m)
        p.completed_missions.append(cid)
        events.append({"type": "mission_completed", "player": p.index, "card": cid})
        fire(s, p, [{"e": "mission_done"}], events)


# ---------------------------------------------------------------------------------------------------------------------------------
# turn effects: flybys, slingshot, asteroids, same ring, completed sectors (FAQ-C019 to FAQ-C026, FAQ-C123, FAQ-C125)
# ---------------------------------------------------------------------------------------------------------------------------------


def _watch(s: GameState, p: PlayerState, w: dict[str, Any], events: Events) -> None:
    if w["k"] == "complete_sector" and s.turn_completed:
        rewards.grant(s, p, w["r"], events)
        return
    s.turn_fx.append({**copy.deepcopy(w), "player": p.index, "done": False, "seen": []})


def fx_active(s: GameState, kind: str) -> bool:
    return any(w["k"] == kind and w["player"] == s.current_player for w in s.turn_fx)


def on_sector_completed(s: GameState, events: Events) -> None:
    s.turn_completed = True
    for w in s.turn_fx:
        if w["k"] == "complete_sector" and not w["done"]:
            w["done"] = True
            rewards.grant(s, s.players[w["player"]], w["r"], events)


def on_move(s: GameState, p: PlayerState, old_ring: int, new_ring: int, cell: str, events: Events) -> None:
    """A probe of the player moved onto a space (FAQ-18: only a move onto the space is a visit)."""
    if old_ring == new_ring:
        _fire_fx(s, p, "same_ring", None, events)
    planet = solar.planet_of(cell) if cell.startswith("PLANET:") else ("earth" if cell == "EARTH" else None)
    if planet:
        _fire_fx(s, p, "visit", planet, events)
        _unique_planet(s, p, planet, events)
    elif cell == "ASTEROID":
        _fire_fx(s, p, "visit_asteroids", None, events)
    elif cell == "COMET":
        _fire_fx(s, p, "visit_comet", None, events)
    evs = _visit_events(planet, cell, own_turn=s.current_player == p.index)
    if evs:
        fire(s, p, evs, events)


def _visit_events(planet: str | None, cell: str, own_turn: bool) -> list[dict[str, Any]]:
    if planet and planet != "earth":
        return [{"e": "visit", "planet": planet}]
    if cell == "ASTEROID":
        return [{"e": "visit_asteroids", "own_turn": own_turn}]
    if cell == "COMET":
        return [{"e": "visit_comet"}]
    return []


def _fire_fx(s: GameState, p: PlayerState, kind: str, planet: str | None, events: Events) -> None:
    for w in s.turn_fx:
        if w["player"] != p.index or w["done"] or w["k"] != kind:
            continue
        if kind == "visit" and w["planet"] != planet:
            continue
        w["done"] = True  # FAQ-C020, FAQ-C123: once per turn
        rewards.grant(s, p, w["r"], events)


def _unique_planet(s: GameState, p: PlayerState, planet: str, events: Events) -> None:
    for w in s.turn_fx:
        if w["k"] == "unique_planets" and w["player"] == p.index and planet not in w["seen"]:
            w["seen"].append(planet)  # FAQ-C025: each planet counts once, Earth included
            rewards.grant(s, p, w["r"], events)


def fire_pushed(s: GameState, events: Events) -> None:
    """Probes pushed by a rotation visit the space they were pushed to (CARD-13). Called by the engine after a rotation."""
    for player, cell in s.pushed:
        p = s.players[player]
        planet = solar.planet_of(cell) if cell.startswith("PLANET:") else None
        evs = _visit_events(planet, cell, own_turn=s.current_player == player)
        if evs:
            fire(s, p, evs, events)
    s.pushed = []


def gain_corner(s: GameState, p: PlayerState, cid: str) -> None:
    """The free-action corner of a card (top-left), without discarding it."""
    for kind, n in tables.cards()[cid]["free"]:
        if kind == "move":
            p.movement += n
        elif kind == "publicity":
            effects.gain_publicity(s, p, n)
        elif kind == "data":
            effects.gain_data(s, p, n)
        elif kind == "score":
            effects.gain_score(s, p, n)


# ---------------------------------------------------------------------------------------------------------------------------------
# end of game (CARD-20, CARD-21, END-02)
# ---------------------------------------------------------------------------------------------------------------------------------


def end_points(s: GameState, p: PlayerState) -> int:
    total = 0
    for cid in p.end_cards:
        e = card_defs.CARDS[cid]["end"]
        w, n = e["what"], e["n"]
        if w == "per_wins":
            total += n * sum(sec.winners.count(p.index) for sec in s.sectors if sec.color == e["color"])
        elif w == "per_traces":
            total += n * sum(1 for _, k in p.trace_log if k == e["kind"])
        elif w == "per_techs":
            total += n * sum(1 for t in p.techs if t.startswith(e["cat"] + "-"))
        elif w == "per_orbland":
            total += n * _at(p, e["planet"])
        elif w == "per_signal_sectors":
            total += n * sum(1 for sec in s.sectors if p.index in sec.markers)
        elif w == "solvay":
            from . import scoring  # noqa: PLC0415

            total += scoring.solvay_points(s, p)
        elif w == "per_species_traces":
            i = alien_steps.slot_of(s, e["species"])
            assert i is not None
            total += n * markers_on_species(s, p, i)
        elif w == "probe_on_asteroid":
            if any(_probe_on(s, pr, "asteroid") for pr in s.probes if pr.player == p.index):
                total += n
        else:
            raise ValueError(w)
    return total


# ---------------------------------------------------------------------------------------------------------------------------------
# decisions raised by card steps
# ---------------------------------------------------------------------------------------------------------------------------------


def decision_moves(s: GameState, d: Decision) -> list[Action] | None:
    """Legal moves of the decisions that cards create, or None if `d` is not one of them."""
    p = s.players[d.player]
    if d.kind == "pick_probe":
        return [{"type": "pick_probe", "probe": pr.id} for pr in s.probes if pr.player == p.index]
    if d.kind == "gop":
        return [{"type": "gop", "probe": pr.id} for pr in s.probes if pr.id not in d.data["chosen"]] + [{"type": "gop_done"}]
    if d.kind == "row_pick":
        return [{"type": "row_pick", "source": f"row:{i}"} for i in range(len(s.card_row))]
    if d.kind == "hand_signal":
        picks = [{"type": "hand_signal", "card": c} for c in dict.fromkeys(p.hand) if tables.cards()[c].get("sector")]
        return [*picks, {"type": "hand_signal_done"}]
    if d.kind == "mission_trigger":
        # CARD-12, CARD-15: a circle that an earlier decision of the same action covered (or of a completed mission) is no longer offered
        open_circles = [(c, i) for c, i in d.data["options"] if any(m.card == c and not m.used[i] for m in p.missions)]
        return [{"type": "cover", "card": c, "circle": i} for c, i in open_circles] + [{"type": "decline_cover"}]
    if d.kind == "remove_orbiter":
        return remove_orbiter_moves(s, p)
    if d.kind == "remove_lander":
        return remove_lander_moves(s, p)
    alien = alien_steps.decision_moves(s, d)
    if alien is not None:
        return alien
    if d.kind == "slingshot":
        return [{"type": "slingshot_pick", "choice": "publicity"}, {"type": "slingshot_pick", "choice": "move"}]
    return None


def resolve_decision(s: GameState, p: PlayerState, d: Decision, a: Action, events: Events) -> bool:
    """Apply the answer to a card decision; returns False if the action is not one of them."""
    t = a["type"]
    if t == "pick_probe":
        probe = next(pr for pr in s.probes if pr.id == a["probe"])
        if d.data.get("osiris"):  # FAQ-C017
            cell = solar.visible(s, probe.ring, probe.sector)[1]
            gain = 2 if cell == "ASTEROID" else 0
            gain += sum(1 for r, c in solar.adjacent(probe.ring, probe.sector) if solar.visible(s, r, c)[1] == "ASTEROID")
            effects.gain_data(s, p, gain)
            return True
        sectors = [probe.sector]
        for _ in range(d.data["n"]):
            rewards.mark_signal(s, p, probe.sector, events, data=not d.data.get("nodata"))
        if d.data.get("nbrs"):
            for sec in ((probe.sector - 1) % 8, (probe.sector + 1) % 8):
                rewards.mark_signal(s, p, sec, events)
        if d.data.get("lagrange") and s.sectors[sectors[0]].markers.count(p.index) == 1:  # FAQ-C120
            s.play_return = True
    elif t == "gop":
        probe = next(pr for pr in s.probes if pr.id == a["probe"])
        rewards.mark_signal(s, p, probe.sector, events)
        left = d.data["left"] - 1
        chosen = [*d.data["chosen"], probe.id]
        if left > 0 and len(chosen) < len(s.probes):
            s.pending.insert(0, Decision(kind="gop", player=p.index, data={"left": left, "chosen": chosen}))
    elif t == "gop_done":
        pass
    elif t == "row_pick":
        cid = s.card_row.pop(int(a["source"].split(":")[1]))
        s.discard.append(cid)
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[cid]["sector"]}))
    elif t == "hand_signal":
        p.hand.remove(a["card"])
        s.discard.append(a["card"])
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[a["card"]]["sector"]}))
        if d.data["left"] > 1:
            s.pending.append(Decision(kind="hand_signal", player=p.index, data={"left": d.data["left"] - 1}))
    elif t == "hand_signal_done":
        pass
    elif t == "cover":
        cover(s, p, a["card"], a["circle"], events)
    elif t == "decline_cover":
        pass
    elif t == "slingshot_pick":
        if a["choice"] == "move":
            p.movement += 1
        else:
            effects.gain_publicity(s, p)
    elif t == "remove_orbiter":
        st = s.planets[a["planet"]]
        st.orbiters.remove(p.index)
        p.orbiters[a["planet"]] -= 1
        if a["first"]:
            st.first_orbiter = None  # the space is free again; the other orbiters do not slide (FAQ-C015)
        rewards.grant(s, p, d.data["r"], events)
    elif t == "remove_lander":
        st = s.planets[a["planet"]]
        if "moon" in a:
            del st.moon_landers[a["moon"]]
            p.landers[a["moon"]] -= 1
        else:
            st.landers.remove(p.index)
            p.landers[a["planet"]] -= 1
            if a["slot"] is not None:
                st.first_land_data_taken[a["slot"]] = False  # FAQ-C084
                st.first_land_owners[a["slot"]] = None
        rewards.grant(s, p, d.data["r"], events)
    elif t == "take_tech":
        take_free_tech(s, p, d, a, events)
    elif not alien_steps.resolve_decision(s, p, d, a, events):
        return False
    return True


def markers_on_species(s: GameState, p: PlayerState, slot_index: int) -> int:
    """Traces a player has marked for a species: discovery spaces, overflow spaces and the board all count (LIFE-02, FAQ-41)."""
    slot = s.species[slot_index]
    n = sum(1 for x in slot.discovery_spaces if x == f"p{p.index}") + slot.overflow.count(p.index)
    return n + sum(m.count(p.index) for column in slot.board.values() for m in column)


def exertian_points(s: GameState, p: PlayerState) -> int:
    """ALIEN-EXE-06: the points of the played Exertian cards whose condition is fulfilled (revealed at the end of the game)."""
    from . import species  # noqa: PLC0415

    ex = species.exertian_slot(s)
    assert ex is not None or not p.exertian_played
    total = 0
    for cid in p.exertian_played:
        _, cond, points = species.EXERTIAN_CARDS[cid]
        k, n = cond["c"], cond["n"]
        if s.rival is not None and p.index == s.rival.index:
            ok = True  # SOLO-ALIEN-03: all of the rival's Exertian cards count as completed
        elif k in ("techs", "wins"):
            ok = cond_ok(s, p, cond)
        elif k == "orbiters":
            ok = sum(p.orbiters.values()) >= n
        elif k == "landers":
            ok = sum(p.landers.values()) >= n
        elif k == "one_planet":
            ok = any(_at(p, pl) >= n for pl in s.planets)
        elif k == "tucked":
            ok = len(p.tucked) >= n
        elif k == "traces_of":
            idx = ex if cond["which"] == "exertians" else next(i for i in range(len(s.species)) if i != ex)
            assert idx is not None
            ok = markers_on_species(s, p, idx) >= n
        elif k == "same_color":
            ok = any(sum(1 for _, kind in p.trace_log if kind == c) >= n for c in ("pink", "yellow", "blue"))
        elif k == "quick_missions":
            ok = sum(1 for c in p.completed_missions if card_defs.CARDS[c]["mission"]["kind"] == "quick") >= n
        else:
            raise ValueError(k)
        total += points if ok else 0
    return total
