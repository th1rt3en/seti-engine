"""Steps, decisions and conditions that only alien cards use (ET.1 to ET.40; the Exertian cards play by the species rules).

Spec: aliens.md (ALIEN-MASC-*, ALIEN-ANO-*, ALIEN-OUM-*, ALIEN-CEN-*), faq.md (FAQ-C201, FAQ-C215, FAQ-C220, FAQ-C221, FAQ-C231).
`run_step` is called by cards.run_step for the step types it does not know; `decision_moves` and `resolve_decision` do the same
for decisions.
"""

from __future__ import annotations

import copy
from typing import Any

from . import card_defs, effects, rewards, solar, species, tables
from .models import Decision, GameState, MessageCard, PlayerState

Action = dict[str, Any]
Events = list[dict[str, Any]]
CARD_MESSAGE_BASE = 30_000  # entries of GameState.crossed from this value are message cards reaching their marker (ALIEN-CEN-02)


# ---------------------------------------------------------------------------------------------------------------------------------
# anomalies
# ---------------------------------------------------------------------------------------------------------------------------------


def anomaly_tokens(s: GameState) -> list[dict[str, Any]]:
    i = next((k for k, sl in enumerate(s.species) if sl.species == "anomalies" and sl.discovered), None)
    return [] if i is None else list(s.species[i].extra["tokens"])


def next_anomaly(s: GameState) -> dict[str, Any] | None:
    """FAQ-54: the anomaly Earth reaches next, counting sectors in the direction of the rotation (an anomaly in Earth's sector is last)."""
    earth = solar.earth(s)[1]
    toks = anomaly_tokens(s)
    if not toks:
        return None
    return min(toks, key=lambda t: ((t["sector"] - earth) % 8) or 8)


def anomaly_at_earth(s: GameState) -> bool:
    earth = solar.earth(s)[1]
    return any(t["sector"] == earth for t in anomaly_tokens(s))


# ---------------------------------------------------------------------------------------------------------------------------------
# Centaurian message cards (ALIEN-CEN-02, ALIEN-CEN-03)
# ---------------------------------------------------------------------------------------------------------------------------------


def place_message(s: GameState, p: PlayerState, events: Events) -> None:
    """ALIEN-CEN-02: a marker 15 points ahead of the player's score. The card stays in front of the player and is not a mission."""
    cid = s.playing
    assert cid is not None
    target = p.score + species.MESSAGE_LEAD
    p.message_cards.append(MessageCard(target=target, card=cid))
    events.append({"type": "message_card_placed", "player": p.index, "card": cid, "target": target})


def resolve_message(s: GameState, p: PlayerState, target: int, events: Events) -> None:
    """The player reached the marker: resolve the green part of the card, and discard it unless it turned into income (ALIEN-CEN-02)."""
    mc = next(m for m in p.message_cards if m.target == target)
    p.message_cards.remove(mc)
    became_income = False
    for r in card_defs.CARDS[mc.card]["green"]:
        if r["t"] == "tuck_self":
            p.tucked.append(mc.card)
            effects.gain_income_resource(s, p, tables.cards()[mc.card]["income"])  # FAQ-C231: the increase pays at once
            became_income = True
        else:
            rewards.grant(s, p, [r], events)
    if not became_income:
        s.discard.append(mc.card)
    events.append({"type": "message_resolved", "player": p.index, "card": mc.card, "target": mc.target})


# ---------------------------------------------------------------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------------------------------------------------------------


def run_step(s: GameState, p: PlayerState, st: dict[str, Any], events: Events) -> bool:
    t = st["t"]
    if t == "message":
        place_message(s, p, events)
    elif t == "orbit_land_free":
        from . import cards  # noqa: PLC0415

        if cards.land_free_moves(s, p, {}):  # a probe on a planet's space (the same condition as for orbiting)
            s.pending.append(Decision(kind="orbit_land_free", player=p.index, data={"collect": st.get("collect", False)}))
    elif t == "collect_sample":
        options = species.samples_on(s, st["planet"])
        if options:
            s.pending.append(Decision(kind="mascamite_sample", player=p.index, data={"mode": "collect", "planets": [st["planet"]]}))
    elif t == "sample_peek":
        planets = _peek_planets(s, p, st.get("probe", False))
        if planets:
            s.pending.append(Decision(kind="mascamite_sample", player=p.index, data={"mode": "peek", "planets": planets}))
    elif t == "sig_next_anomaly":
        tok = next_anomaly(s)
        if tok is not None:
            rewards.mark_signal(s, p, tok["sector"], events)
    elif t == "next_anomaly_reward":
        tok = next_anomaly(s)
        if tok is not None:
            faces = next(x for x in species.board_data("anomalies")["tokens"] if x["column"] == tok["color"])["sides"]
            rewards.grant(s, p, faces[tok["side"]], events)
    elif t == "anomaly_signal_vp":
        sectors = {tok["sector"] for tok in anomaly_tokens(s)}  # FAQ-C220: every signal the player has there, including this card's
        effects.gain_score(s, p, st.get("n", 1) * sum(sec.markers.count(p.index) for i, sec in enumerate(s.sectors) if i in sectors))
    elif t == "take_row_all":
        row, s.card_row = s.card_row, []
        p.hand += row
        effects.refill_card_row(s)
    elif t == "part_of_life":
        s.aside = [c for c in (effects.draw_from_deck(s) for _ in range(3)) if c is not None]  # FAQ-C215
        if s.aside:
            s.pending.append(Decision(kind="pol_corner", player=p.index))
    elif t == "optional":
        s.pending.append(Decision(kind="optional", player=p.index, data={k: v for k, v in st.items() if k != "t"}))
    elif t == "sig_twice":
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": "any", "times": st.get("n", 2)}))
    else:
        return False
    return True


def _peek_planets(s: GameState, p: PlayerState, with_probe: bool) -> list[str]:
    out: list[str] = []
    for planet in species.SAMPLE_PLANETS:
        if not species.samples_on(s, planet):
            continue
        pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
        if with_probe and not any(pr.player == p.index and not pr.capsule and (pr.ring, pr.sector) == pos for pr in s.probes):
            continue
        out.append(planet)
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------------------------------------------------------------


def decision_moves(s: GameState, d: Decision) -> list[Action] | None:
    p = s.players[d.player]
    if d.kind == "mascamite_sample":
        return [{"type": "pick_sample", "planet": pl, "sample": t} for pl in d.data["planets"] for t in species.samples_on(s, pl)]
    if d.kind == "pol_corner":
        return [{"type": "pol_pick", "card": c} for c in dict.fromkeys(s.aside)]
    if d.kind == "pol_income":
        return [{"type": "pol_pick", "card": c} for c in dict.fromkeys(s.aside)]
    if d.kind == "optional":
        can = p.exofossils >= d.data.get("exo", 0)
        return [{"type": "opt_yes"}, {"type": "opt_no"}] if can else [{"type": "opt_no"}]
    return None


def resolve_decision(s: GameState, p: PlayerState, d: Decision, a: Action, events: Events) -> bool:
    t = a["type"]
    if t == "pick_sample":
        if d.data["mode"] == "collect":
            species.collect_sample(s, p, a["planet"], a["sample"], events)
        else:  # peek: gain its reward and put it back (FAQ-C201)
            rewards.grant(s, p, species.sample_faces()[a["sample"]], events, slot=species.mascamite_slot(s))
    elif t == "pol_pick":
        s.aside.remove(a["card"])
        s.discard.append(a["card"])
        if d.kind == "pol_corner":
            cards_corner(s, p, a["card"])
            if s.aside:
                s.pending.insert(0, Decision(kind="pol_income", player=p.index))
        else:
            effects.gain_income_resource(s, p, tables.cards()[a["card"]]["income"])
            p.hand += s.aside  # the third card is kept
            s.aside = []
    elif t == "opt_yes":
        p.exofossils -= d.data.get("exo", 0)
        species.return_exofossils(s, d.data.get("exo", 0))
        rewards.grant(s, p, d.data["r"], events)
        if d.data.get("repeat") and p.exofossils >= d.data.get("exo", 0):
            s.pending.insert(0, copy.deepcopy(d))
    elif t == "opt_no":
        pass
    else:
        return False
    return True


def cards_corner(s: GameState, p: PlayerState, cid: str) -> None:
    from . import cards  # noqa: PLC0415

    cards.gain_corner(s, p, cid)


# ---------------------------------------------------------------------------------------------------------------------------------
# conditions and scoring helpers
# ---------------------------------------------------------------------------------------------------------------------------------


def slot_of(s: GameState, name: str) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == name), None)


def cond_ok(s: GameState, p: PlayerState, c: dict[str, Any]) -> bool | None:
    """Conditions of alien missions; None if `c` is not one of them."""
    k = c["c"]
    if k == "species_traces":
        i = slot_of(s, c["species"])
        n: int = c["n"]
        return i is not None and sum(1 for sl, kind in p.trace_log if sl == i and kind == c["kind"]) >= n
    if k == "species_all":
        i = slot_of(s, c["species"])
        return i is not None and bool({kind for sl, kind in p.trace_log if sl == i} >= {"pink", "yellow", "blue"})
    if k == "exofossils":
        need: int = c["n"]
        return p.exofossils >= need
    if k == "tile_marker":
        i = species.oumuamua_slot(s)
        return i is not None and p.index in s.species[i].extra["tile"]["markers"]
    if k == "paid_space":  # FAQ-C221: a marker on a space of the 'Oumuamua board that costs exofossils
        i = species.oumuamua_slot(s)
        if i is None:
            return False
        for col in species.board_data("oumuamua")["columns"]:
            for k2, space in enumerate(col["spaces"]):
                if space.get("cost") and p.index in s.species[i].board[col["color"]][k2]:
                    return True
        return False
    if k == "anomaly_at_earth":
        return anomaly_at_earth(s)
    return None
