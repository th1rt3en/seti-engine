"""Technologies, the Research and Analyze actions, computer lower spaces and the scan steps (telescope techs).

Spec: actions.md (SCAN-*, ANALYZE-*, TECHACT-*), tech.md (TECH-*), board-tech-and-player.md (BOARD-70 to BOARD-74), faq.md (FAQ-22).
"""

from __future__ import annotations

from typing import Any

from . import effects, glyphids, orgs, rewards, solar, tables
from .models import ComputerTech, Decision, GameState, PlayerState

Action = dict[str, Any]
Events = list[dict[str, Any]]
COMPUTER_SLOTS = (0, 2, 4, 5)  # BOARD-72: top-row positions with a computer tech slot
TILE_BONUS = {
    "vp3": {"t": "vp", "n": 3},
    "card": {"t": "card_any", "n": 1},
    "energy": {"t": "energy", "n": 1},
    "publicity": {"t": "publicity", "n": 1},
}
RESEARCH_COST = 6  # TECHACT-01


probe_limit = effects.probe_limit
launch_probe = effects.launch_probe


def rotate_solar_system(s: GameState, events: Events) -> None:
    """ROTATE-01 to ROTATE-03: rotate, and pay publicity to probes pushed onto an icon space."""
    disc = s.rotations % 3 + 1
    for player, _why in solar.rotate(s):
        effects.gain_publicity(s, s.players[player])
        events.append({"type": "publicity", "player": player, "reason": "pushed"})
    events.append({"type": "rotate", "disc": disc})


# ---------------------------------------------------------------------------------------------------------------------------------
# research
# ---------------------------------------------------------------------------------------------------------------------------------


def tech_name(category: str, glyph: str) -> str:
    return f"{category}-{glyph}"


def research_moves(s: GameState, p: PlayerState, category: str | None = None) -> list[Action]:
    return [
        {"type": "research", "stack": i}
        for i, st in enumerate(s.tech_stacks)
        if st.tiles and tech_name(st.category, st.glyph) not in p.techs and (category is None or st.category == category)  # TECHACT-07
    ]


def take_tech(s: GameState, p: PlayerState, stack: int, events: Events, tile_bonus: bool = True, first_bonus: bool = True) -> str:
    """TECHACT-02 to TECHACT-05 (the rotation is done by the caller first). `tile_bonus` False is card #81 (FAQ-C081)."""
    st = s.tech_stacks[stack]
    tile = st.tiles.pop(0)
    if st.two_point_tile:  # TECHACT-03: the first taker discards the 2-point tile and scores 2
        st.two_point_tile = False
        if first_bonus:
            effects.gain_score(s, p, 2)
    name = tech_name(st.category, st.glyph)
    p.techs.append(name)
    events.append({"type": "tech", "player": p.index, "tech": name})
    orgs.on_tech(s, p, st.category)  # Turing Systems (EXP-ORG-13)
    glyphids.take(s, p, f"tech:{stack}", events)  # EXP-GLY-04
    extra = _stack_extra(st.category, st.glyph)
    rewards.grant(s, p, [*([TILE_BONUS[tile]] if tile_bonus else []), *extra], events)  # TECHACT-04
    if st.category == "computer":
        free = [pos for pos in COMPUTER_SLOTS if pos not in p.computer_techs]
        s.pending.append(Decision(kind="computer_slot", player=p.index, data={"tech": name, "slots": free}))
    return tile


def _stack_extra(category: str, glyph: str) -> list[dict[str, Any]]:
    for t in tables.tech_board()["stacks"][category]:
        if t["glyph"] == glyph:
            extra: list[dict[str, Any]] = t["extra_bonus"]
            return extra
    raise KeyError(glyph)


def place_computer_tech(s: GameState, p: PlayerState, d: Decision, slot: int) -> None:
    """TECHACT-05, TECH-23: the tech goes in any slot, even over data, without placing data."""
    p.computer_techs[slot] = ComputerTech(tech=d.data["tech"])


def lower_moves(p: PlayerState) -> list[Action]:
    """TECH-21: data goes to a lower space only if the space above it is filled."""
    if p.data_pool < 1:
        return []
    return [{"type": "place_lower", "slot": pos} for pos, t in p.computer_techs.items() if p.computer[pos] and not t.lower_filled]


def place_lower(s: GameState, p: PlayerState, slot: int, events: Events) -> None:
    p.data_pool -= 1
    p.computer_techs[slot].lower_filled = True
    tech = p.computer_techs[slot].tech
    lower = next(t["lower"] for t in tables.tech_board()["stacks"]["computer"] if tech_name("computer", t["glyph"]) == tech)
    rewards.grant(s, p, lower, events)  # TECH-20
    events.append({"type": "place_lower", "player": p.index, "slot": slot})


# ---------------------------------------------------------------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------------------------------------------------------------


def can_analyze(p: PlayerState) -> bool:
    return (p.energy >= 1 or orgs.analyze_free(p)) and all(p.computer)  # ANALYZE-01; Deep Sky Survey needs no energy (EXP-ORG-13)


def analyze(s: GameState, p: PlayerState, events: Events) -> None:
    if not orgs.analyze_free(p):
        effects.pay(p, energy=1)
    p.computer = [False] * 6  # ANALYZE-02: every data token in the computer, bottom row too
    for t in p.computer_techs.values():
        t.lower_filled = False
    s.pending.append(Decision(kind="trace", player=p.index, data={"color": "blue"}))  # ANALYZE-03
    events.append({"type": "analyze", "player": p.index})


# ---------------------------------------------------------------------------------------------------------------------------------
# scan steps
# ---------------------------------------------------------------------------------------------------------------------------------


def _active_techs(p: PlayerState) -> list[str]:
    """The techs whose ability the player can use (see effects.tech_active)."""
    names = list(dict.fromkeys([*p.techs, *p.org_data.get("borrowed", [])]))
    return [t for t in names if effects.tech_active(p, t)]


def start_scan(s: GameState, p: PlayerState, free: bool = False, ctx: dict[str, Any] | None = None) -> None:
    """SCAN-01 to SCAN-05: the steps can be done in any order; telescope techs add optional steps (SCAN-04, TECH-10).
    `ctx` carries the extra points of cards such as #53 (FAQ-C051: only the base cost is skipped)."""
    s.scan_ctx = ctx or {}
    s.scan_steps = ["earth", "row"] + [
        f"tt:{t.split('-')[1]}" for t in _active_techs(p) if t.startswith("telescope-") and t != "telescope-dot"
    ]
    s.pending.append(Decision(kind="scan_step", player=p.index))


def scan_moves(s: GameState, p: PlayerState) -> list[Action]:
    out: list[Action] = []
    steps = s.scan_steps
    if "earth" in steps:
        earth = solar.earth(s)[1]
        sectors = [earth]
        if effects.tech_active(p, "telescope-dot"):  # TECH-TT01
            sectors += [(earth - 1) % 8, (earth + 1) % 8]
        out += [{"type": "scan_earth", "sector": i} for i in sectors]
    if "row" in steps:
        out += [{"type": "scan_discard", "source": f"row:{i}"} for i in range(len(s.card_row))]
    if p.signal_tokens > 0 and s.card_row:  # EXP-SIG-02: a signal token pays for one more row card and its signal, in any order
        out += [{"type": "scan_token", "source": f"row:{i}"} for i in range(len(s.card_row))]
    if "tt:branch" in steps:  # TECH-TT02
        out += [{"type": "scan_hand_discard", "card": c} for c in dict.fromkeys(p.hand) if tables.cards()[c].get("sector")]
    if "tt:link" in steps and p.publicity >= 1 and solar.find_cell(s, "PLANET:MERCURY"):  # TECH-TT03
        out.append({"type": "scan_mercury"})
    if "tt:cross" in steps and p.energy >= 1:  # TECH-TT04, FAQ-22
        out.append({"type": "scan_probe", "mode": "move"})
        if sum(1 for pr in s.probes if pr.player == p.index and not pr.capsule) < probe_limit(p):
            out.append({"type": "scan_probe", "mode": "launch"})
    if "earth" not in steps and ("row" not in steps or not s.card_row):
        out.append({"type": "scan_done"})
    return out


def resolve_scan(s: GameState, p: PlayerState, a: Action, events: Events) -> None:
    t = a["type"]
    if t == "scan_earth":
        s.scan_steps.remove("earth")
        rewards.mark_signal(s, p, a["sector"], events)
    elif t == "scan_discard":
        s.scan_steps.remove("row")
        cid = s.card_row.pop(int(a["source"].split(":")[1]))
        s.discard.append(cid)  # the row is refilled when the scan is finished (SCAN-03)
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[cid]["sector"]}))
    elif t == "scan_token":
        p.signal_tokens -= 1  # EXP-SIG-02
        cid = s.card_row.pop(int(a["source"].split(":")[1]))
        s.discard.append(cid)  # the row is refilled when the scan is finished, so two tokens at most fit the three cards of the row
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[cid]["sector"]}))
    elif t == "scan_hand_discard":
        s.scan_steps.remove("tt:branch")
        p.hand.remove(a["card"])
        s.discard.append(a["card"])
        s.pending.append(Decision(kind="signal", player=p.index, data={"color": tables.cards()[a["card"]]["sector"]}))
    elif t == "scan_mercury":
        s.scan_steps.remove("tt:link")
        effects.pay(p, publicity=1)
        pos = solar.find_cell(s, "PLANET:MERCURY")
        assert pos is not None
        rewards.mark_signal(s, p, pos[1], events)
    elif t == "scan_probe":
        s.scan_steps.remove("tt:cross")
        effects.pay(p, energy=1)
        if a["mode"] == "launch":
            launch_probe(s, p, events)
        else:
            p.movement += 1
    elif t == "scan_done":
        s.scan_steps = []
        if s.scan_ctx and s.scan_ctx.get("exo_if_tile") and s.scan_ctx.get("tile"):  # #ET.22
            effects.gain_score(s, p, 0)
            rewards.grant(s, p, [{"t": "exofossil", "n": 1}], events)
        s.scan_ctx = None
        effects.refill_card_row(s)
        return
    s.pending.append(Decision(kind="scan_step", player=p.index))  # the next step; after any signal choice already queued
