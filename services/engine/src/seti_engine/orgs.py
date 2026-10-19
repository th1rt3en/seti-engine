"""The Space Agencies organization module: organizations, quick start cards, their income and their once-per-round powers.

Spec: docs/spec/expansion.md (EXP-ORG-*, EXP-QS-*), data in docs/spec/expansion-data.md. Ambiguities: A-031, A-036, A-037.
Not yet implemented (listed in the report and in expansion.md): Orbital Dynamics' free action, Cosmos Strategy Group's and Helion Assembly's
reward spaces, Xenolab's action tiles, Futurespan Institute's prepared card.
"""

from __future__ import annotations

import itertools
from typing import Any

from . import effects, rewards, rng, solar, tables, trail
from .models import Decision, GameState, PlayerState

Events = list[dict[str, Any]]
Action = dict[str, Any]

SETUP_KINDS = frozenset({"choose_org", "choose_quick", "setup_tuck"})
# the first game tip (EXP-ORG-05, A-030): organizations 1 to 4 are dealt one each
BEGINNER_ORGS = ("orbital_dynamics", "fenwick_research_center", "stratus_core", "deep_sky_survey")
FIRST_ROUND = 2  # EXP-ORG-02: rounds 2 to 5 are played
RESEARCH_COST_FENWICK = 5  # Fenwick Research Center: only 5 publicity to research a tech (EXP-ORG-13)


STAR_NAMES = {
    "barnards_star": "Barnard's Star",
    "proxima_centauri": "Proxima Centauri",
    "sirius_a": "Sirius A",
    "procyon": "Procyon",
    "kepler_22": "Kepler 22",
    "sixty_one_virginis": "61 Virginis",
    "beta_pictoris": "Beta Pictoris",
    "vega": "Vega",
}


def by_id(org: str) -> dict[str, Any]:
    found: dict[str, Any] = tables.organizations()[org]
    return found


def in_use(s: GameState) -> bool:
    return s.options.organizations


# ---------------------------------------------------------------------------------------------------------------------------------
# setup (EXP-ORG-03, EXP-ORG-04, EXP-QS-03)
# ---------------------------------------------------------------------------------------------------------------------------------


def deal(s: GameState, order: list[int]) -> None:
    """EXP-ORG-03: 2 random organizations, 3 random quick start cards and 4 main deck cards for each player,
    in turn order. Round 2 is the first
    round played (EXP-ORG-02), so the end-of-round pile of round 1 is not dealt."""
    s.round = FIRST_ROUND
    opts = s.options
    orgs = list(tables.organizations())
    quick = sorted(tables.quick_start_cards())
    if opts.neutral_quick_start:  # EXP-QS-03: 4 revealed cards, marked with neutral pieces
        s.neutral_quick = rng.shuffled(s, quick)[:4]
        quick = [q for q in quick if q not in s.neutral_quick]
        for cid in s.neutral_quick:
            place_marks(s, None, cid)
    if opts.beginner_organizations:  # EXP-ORG-05
        pool = rng.shuffled(s, list(BEGINNER_ORGS))
        per_org, per_quick = 1, 2
    else:
        pool = rng.shuffled(s, orgs)
        per_org, per_quick = 2, 3
    quick = rng.shuffled(s, quick)
    for k, pl in enumerate(order):
        p = s.players[pl]
        if opts.sandbox:  # D33: the sandbox player chooses freely among every organization and every quick start card
            p.offered_orgs = sorted(orgs)
            p.offered_quick = sorted(quick)
        else:
            p.offered_orgs = pool[k * per_org : (k + 1) * per_org]
            p.offered_quick = quick[k * per_quick : (k + 1) * per_quick]
        p.hand = [s.deck.pop() for _ in range(4)]
        p.credits = p.energy = p.publicity = 0
    for pl in order:
        p = s.players[pl]
        s.pending.append(Decision(kind="choose_org", player=pl))
        s.pending.append(Decision(kind="choose_quick", player=pl))  # EXP-ORG-04: the two cards are kept in one choice (owner, 2026-10-16)


def choose_moves(s: GameState, d: Decision) -> list[Action]:
    p = s.players[d.player]
    if d.kind == "choose_org":
        return [{"type": "choose_org", "org": o} for o in p.offered_orgs]
    cards = sorted(p.offered_quick)
    keep = min(2, len(cards))
    return [{"type": "choose_quick", "cards": list(pair)} for pair in itertools.combinations(cards, keep)]


def resolve_choice(s: GameState, p: PlayerState, d: Decision, a: Action, events: Events) -> None:
    """EXP-ORG-04: the player keeps the organization and 2 of the quick start cards; the rest return to the box. Once the last choice is
    made
    the player's starting resources and quick start cards are resolved (EXP-ORG-06, EXP-ORG-07)."""
    if d.kind == "choose_org":
        p.organization = a["org"]
        p.offered_orgs = []
        events.append({"type": "organization", "player": p.index, "org": a["org"]})
        return
    p.quick_start = list(a["cards"])
    p.offered_quick = []
    start(s, p, events)


def start(s: GameState, p: PlayerState, events: Events) -> None:
    """EXP-ORG-06, EXP-ORG-07, EXP-QS-01, EXP-QS-02: the quick start cards' top halves, then the starting resources, then the tucks. Any
    resolution that needs a choice is put in front of the player's own tuck."""
    assert p.organization is not None
    org = by_id(p.organization)
    for cid in p.quick_start:
        place_marks(s, p, cid)  # EXP-QS-01: no benefits
    with trail.scope(s, {"kind": "organization", "org": p.organization}):  # the log shows the organization apart from each quick start card
        for _ in range(org["probes"]):  # EXP-ORDER-01: the launches are printed before the resources in the header of Orbital Dynamics
            effects.launch_probe(s, p, events)
        res = org["starting_resources"]
        p.credits += res["credit"]
        p.energy += res["energy"]
        p.publicity += res["publicity"]
        effects.gain_data(s, p, res["data"])
        for _ in range(res["card"]):
            effects.draw_random_card(s, p)
    for cid in p.quick_start:  # EXP-QS-02: the bottom half
        with trail.scope(s, {"kind": "quick_start", "card": cid}):
            lower(s, p, cid)
    if p.organization == "mission_relay":  # EXP-ORG-13: the lowest-scoring space of the Mission tile
        g = next(g for g in s.gold_tiles if g.tile == "Mission")
        g.low_markers.append(p.index)
        p.gold_markers.append("Mission")
    if p.organization == "xenolab":
        p.org_data["tiles"] = {"launch": True, "scan": True, "research": True}
    tucks = min(org["tuck_income_cards"], len(p.hand))
    source = {"kind": "organization", "org": p.organization}
    s.pending[0:0] = [Decision(kind="setup_tuck", player=p.index, source=source) for _ in range(tucks)]  # EXP-ORG-07: one by one


def place_marks(s: GameState, p: PlayerState | None, cid: str) -> None:
    """EXP-QS-01, EXP-QS-03: the markers of the top half, without any benefit. `p` None is the neutral color (index -1)."""
    who = rewards.NEUTRAL if p is None else p.index
    for m in tables.quick_start_cards()[cid]["marks"]:
        if "starName" in m:
            index = next(i for i, sec in enumerate(s.sectors) if sec.star == STAR_NAMES[m["starName"]])
            for _ in range(m["count"]):
                if len(s.sectors[index].markers) < s.sectors[index].capacity:
                    s.sectors[index].markers.append(who)
                    s.sectors[index].data_remaining -= 1
        elif "planet" in m:
            st = s.planets[m["planet"]]
            st.orbiters.append(who)  # A-036 (a): it takes the first orbiter space, and the bonus is lost
            if st.first_orbiter is None:
                st.first_orbiter = who
            if p is not None:
                p.orbiters[m["planet"]] = p.orbiters.get(m["planet"], 0) + 1
        elif "trace" in m:
            slot = s.species[m["alienIndex"] - 1]
            colors = ("pink", "yellow", "blue")
            i = colors.index(m["trace"])
            if slot.discovery_spaces[i] is None:
                slot.discovery_spaces[i] = "n" if p is None else f"p{p.index}"
            elif p is not None:  # A-036 (b): a taken discovery space sends the trace to the overflow space of its color (neutral: lost)
                slot.overflow.append(who)
                slot.overflow_kinds.append(m["trace"])
            if p is not None:
                p.trace_log.append((m["alienIndex"] - 1, m["trace"]))


def lower(s: GameState, p: PlayerState, cid: str) -> None:
    """EXP-QS-02: the bottom half of a quick start card."""
    for e in tables.quick_start_cards()[cid]["lower"]:
        kind, n = e["effect"], e["n"]
        if kind == "score":
            effects.gain_score(s, p, n)
        elif kind == "card":
            for _ in range(n):
                effects.draw_random_card(s, p)
        else:
            rewards.grant(s, p, [{"t": kind, "n": n}], [])
    income = tables.quick_start_cards()[cid].get("income_increase")
    if income:  # SR.15 and SR.16 are tucked as income at once (see tables.cards)
        p.tucked.append(cid)  # A-036 (d): its resource is gained at once, like any tuck (INCOME-01)
        effects.gain_income_resource(s, p, tables.cards()[cid]["income"])


# ---------------------------------------------------------------------------------------------------------------------------------
# income (EXP-ORG-08, A-031)
# ---------------------------------------------------------------------------------------------------------------------------------


def gain_income(s: GameState, p: PlayerState) -> None:
    """EXP-ORG-08, A-031: the organization's income plus the resource of every tucked card; the once-per-round marker is
    removed (EXP-ORG-10)."""
    assert p.organization is not None
    inc = by_id(p.organization)["income"]
    p.credits += inc["credit"]
    p.energy += inc["energy"]
    effects.gain_publicity(s, p, inc["publicity"])
    effects.gain_data(s, p, inc["data"])
    p.signal_tokens += inc["signalToken"]
    for _ in range(inc["card"]):
        effects.draw_random_card(s, p)
    for cid in p.tucked:
        effects.gain_income_resource(s, p, tables.cards()[cid]["income"])
    p.org_used = False


def income_of(p: PlayerState) -> dict[str, int]:
    """The income by kind for the tracker, including signal tokens."""
    out = {"credit": 0, "energy": 0, "card": 0, "publicity": 0, "data": 0, "signal": 0}
    if p.organization is None:
        return out
    inc = by_id(p.organization)["income"]
    for k in ("credit", "energy", "card", "publicity", "data"):
        out[k] += inc[k]
    out["signal"] += inc["signalToken"]
    for cid in p.tucked:
        out[tables.cards()[cid]["income"]] += 1
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# passive powers (EXP-ORG-09)
# ---------------------------------------------------------------------------------------------------------------------------------


def research_cost(p: PlayerState, base: int) -> int:
    return RESEARCH_COST_FENWICK if p.organization == "fenwick_research_center" else base


def analyze_free(p: PlayerState) -> bool:
    return p.organization == "deep_sky_survey"


def on_launch(s: GameState, p: PlayerState, events: Events) -> None:
    """Sentinel Probe Network: when you launch a probe, mark a signal in that probe's sector."""
    if p.organization == "sentinel_probe_network":
        rewards.mark_signal(s, p, solar.earth(s)[1], events)


HELION_SPACES = {"probe": "energy", "telescope": "signal_token", "computer": "data"}  # EXP-ORG-11, A-038
COSMOS_SPACES = {"credit": ("yellow", "black"), "publicity": ("red", "black"), "data": ("blue", "black")}  # A-038


def on_tech(s: GameState, p: PlayerState, category: str) -> None:
    """Turing Systems: when you research a computer tech, gain 1 publicity. Helion Assembly: when you develop a tech you may mark the
    matching reward space (EXP-ORG-11)."""
    if p.organization == "turing_systems" and category == "computer":
        effects.gain_publicity(s, p)
    if (
        p.organization == "helion_assembly" and HELION_SPACES[category] not in p.org_marks
    ):  # the owner: the reward is gained and the space blocked
        p.org_marks.append(HELION_SPACES[category])
        rewards.grant(s, p, [{"t": HELION_SPACES[category]}], [])


def mark_moves(s: GameState, d: Decision) -> list[Action]:
    return [*({"type": "org_mark", "space": x} for x in d.data["spaces"]), {"type": "org_skip"}]


def resolve_mark(s: GameState, p: PlayerState, a: Action) -> None:
    """Mark a reward space of Cosmos Strategy Group or Helion Assembly and gain its reward (1 of the resource, A-038)."""
    if a["type"] == "org_skip":
        return
    space = a["space"]
    p.org_marks.append(space)
    rewards.grant(s, p, [{"t": space}], [])


def on_mission_played(s: GameState, p: PlayerState) -> None:
    """Mission Relay: when you play a card with a mission, gain 1 publicity."""
    if p.organization == "mission_relay":
        with trail.scope(s, {"kind": "organization", "org": "mission_relay", "what": "mission"}):  # the log shows it apart from the card
            effects.gain_publicity(s, p)


def on_card_played(s: GameState, p: PlayerState, cid: str, alien: bool) -> None:
    """Sentinel Probe Network keeps the corner of the last non-alien card played as a main action, for its free action."""
    if p.organization == "sentinel_probe_network" and not alien:
        p.org_data["corner"] = cid
    if p.organization == "cosmos_strategy_group":  # EXP-ORG-13: a card played as a main action may mark a matching reward space
        sector = tables.cards()[cid]["sector"]
        spaces = [x for x, colors in COSMOS_SPACES.items() if sector in colors and x not in p.org_marks]
        if spaces:
            s.pending.append(Decision(kind="org_mark", player=p.index, data={"spaces": spaces}))


XENO_TILES = {"launch": "blue", "scan": "yellow", "research": "pink"}  # A-037: the trace color that flips the tile active again


def on_trace(p: PlayerState, color: str) -> None:
    """Xenolab: when you gain the trace shown on an inactive tile, flip it back to active (the trace is still gained)."""
    if p.organization == "xenolab":
        for tile, c in XENO_TILES.items():
            if c == color:
                p.org_data["tiles"][tile] = True


def main_moves(s: GameState, p: PlayerState, can_launch: bool, research: list[Action]) -> list[Action]:
    """Xenolab's active tiles are discounted main actions (EXP-ORG-13); Futurespan's prepared card is played for free once the score reaches
    the token (EXP-ORG-12)."""
    out: list[Action] = []
    if p.organization == "xenolab":
        tiles = p.org_data["tiles"]
        if tiles["launch"] and p.credits >= 1 and can_launch:
            out.append({"type": "org_main", "org": "xenolab", "tile": "launch"})
        if tiles["scan"] and p.energy >= 2:
            out.append({"type": "org_main", "org": "xenolab", "tile": "scan"})
        if tiles["research"] and p.publicity >= 4:
            out += [{"type": "org_main", "org": "xenolab", "tile": "research", "stack": m["stack"]} for m in research]
    if p.organization == "futurespan_institute" and p.org_data.get("fs_card") and p.score >= p.org_data["fs_token"]:
        out.append({"type": "org_main", "org": "futurespan_institute"})
    return out


def end_turn(s: GameState, p: PlayerState) -> None:
    """The Sentinel corner and the borrowed Turing tech only last for the turn."""
    p.org_data.pop("corner", None)
    p.org_data.pop("od_left", None)
    p.org_data.pop("od_used", None)
    p.org_data.pop("borrowed", None)


# ---------------------------------------------------------------------------------------------------------------------------------
# once per round free actions (EXP-ORG-10)
# ---------------------------------------------------------------------------------------------------------------------------------


def _sources(s: GameState) -> list[str]:
    return ["deck", *(f"row:{i}" for i in range(len(s.card_row)))]


def prepare_cost(cid: str) -> int:
    """The cost of a card for Futurespan: credits, or energy for a Centaurian card (A-036 c)."""
    return int(tables.cards()[cid]["cost"])


def free_moves(s: GameState, p: PlayerState) -> list[Action]:
    if p.organization is None:
        return []
    o = p.organization
    base: Action = {"type": "org_free", "org": o}
    if o == "futurespan_institute":
        if not p.org_data.get("fs_card"):  # EXP-ORG-12: one prepared card at a time
            # A-052: costs 1 to 4 only; "ahead" is how far in front of the score the token is put, for the button
            return [{**base, "card": c, "ahead": 10 * prepare_cost(c) + 5} for c in dict.fromkeys(p.hand) if 1 <= prepare_cost(c) <= 4]
        if not p.org_used:  # once per round while the token is on the scoring track: 3 spaces farther, and a card
            return [{**base, "delay": True, "source": x} for x in _sources(s)]  # the card is picked in the same move: the row or the deck
        return []
    if p.org_used:
        return []
    if o == "fenwick_research_center" and p.publicity >= 1:
        return [{**base, "source": x} for x in _sources(s)]
    if o == "mission_relay" and p.publicity >= 2:
        return [{**base, "source": x} for x in _sources(s)]
    if o == "stratus_core" and s.card_row:
        return [base]
    if o == "deep_sky_survey" and p.hand and s.card_row:
        return [{**base, "card": c, "row": i} for c in dict.fromkeys(p.hand) for i in range(len(s.card_row))]
    if o == "cosmos_strategy_group":
        return [{**base, "source": x} for x in _sources(s)]
    if o == "helion_assembly" and p.hand:
        techs = [t for t in p.techs if t.startswith(("probe-", "telescope-")) and t not in p.org_data.get("disabled", [])]
        return [{**base, "tech": t} for t in techs]  # the card to tuck is chosen next, like any tuck (owner, 2026-10-16)
    if o == "sentinel_probe_network" and p.org_data.get("corner"):
        return [base]
    if o == "orbital_dynamics" and any(pr.player == p.index and not pr.capsule for pr in s.probes):
        return [base]  # A-039: two different probes move 1 step each
    if o == "turing_systems":
        names = sorted(
            f"{st.category}-{st.glyph}"
            for st in s.tech_stacks
            if st.category in ("probe", "telescope") and f"{st.category}-{st.glyph}" not in p.techs
        )
        return [{**base, "tech": n} for n in names]
    return []


def free_action(s: GameState, p: PlayerState, a: Action, events: Events) -> None:
    from . import cards  # noqa: PLC0415 - cards imports this module

    o = a["org"]
    if o == "futurespan_institute":
        if a.get("delay"):  # EXP-ORG-12
            p.org_used = True
            p.org_data["fs_token"] += 3
            # owner ruling, 2026-10-18: the card is taken from the card row or from the deck, like any card gained; the move names it
            effects.take_from_row_or_deck(s, p, a["source"], events)
        else:
            p.hand.remove(a["card"])
            p.org_data["fs_card"] = a["card"]
            p.org_data["fs_token"] = p.score + 10 * prepare_cost(a["card"]) + 5  # the card shows +15, +25, +35, +45 (A-052)
        events.append({"type": "org_free", "player": p.index, "org": o})
        return
    p.org_used = True
    events.append({"type": "org_free", "player": p.index, "org": o})
    if o == "fenwick_research_center":  # spend 1 publicity: a card, then its free-action corner
        p.publicity -= 1
        cid = effects.take_from_row_or_deck(s, p, a["source"], events)
        if cid is not None:
            cards.gain_corner(s, p, cid)
    elif o == "mission_relay":  # spend 2 publicity: a card, then the resource of its income corner
        p.publicity -= 2
        cid = effects.take_from_row_or_deck(s, p, a["source"], events)
        if cid is not None:
            effects.gain_income_resource(s, p, tables.cards()[cid]["income"])
    elif o == "stratus_core":  # the corners of all 3 cards of the row, in row order, without discarding them
        for cid in list(s.card_row):
            cards.gain_corner(s, p, cid)
    elif o == "deep_sky_survey":  # switch a card of the hand with a card of the row
        i = a["row"]
        p.hand.remove(a["card"])
        s.card_row[i], swapped = a["card"], s.card_row[i]
        p.hand.append(swapped)
    elif o == "cosmos_strategy_group":  # a card from the row or the deck, then every marked reward space is cleared
        effects.take_from_row_or_deck(s, p, a["source"], events)
        p.org_marks = []
    elif o == "helion_assembly":  # destroy a tech, tuck a card for income, clear the marked spaces
        p.org_data.setdefault("disabled", []).append(a["tech"])
        p.org_marks = []
        # then a card is tucked for its income, like any tuck
        s.pending.append(Decision(kind="helion_tuck", player=p.index, source={"kind": "organization", "org": o}))
    elif o == "orbital_dynamics":  # EXP-ORG-13, A-039: the steps are taken with od_step moves until the end of the turn
        p.org_data["od_left"], p.org_data["od_used"] = 2, []
    elif o == "sentinel_probe_network":
        cards.gain_corner(s, p, p.org_data.pop("corner"))
    elif o == "turing_systems":  # until the end of the turn, as if researched, without the immediate bonuses
        p.org_data["borrowed"] = [a["tech"]]
