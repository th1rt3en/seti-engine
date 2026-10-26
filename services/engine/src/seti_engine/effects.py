"""Basic effects: gaining and paying resources, scoring with milestone detection, drawing and tucking cards.

Spec: setup.md, turn-structure.md (RES-01 to RES-06, INCOME-01 to INCOME-05), milestones-and-scoring.md (MILE-01 to MILE-11).
"""

from __future__ import annotations

from typing import Any

from . import rng, solar, tables, trail
from .models import Decision, GameState, PlayerState, Probe

PUBLICITY_CAP = 10  # SETUP-37 / RES-02
DATA_POOL_CAP = 6  # RES-01
MILESTONES = (20, 25, 30, 50, 70)  # MILE-02, MILE-05; only the first lap of the score track counts (MILE-04)


def record_lost(state: GameState, p: PlayerState, kind: str, n: int, source: dict[str, Any] | None = None) -> None:
    """A gain that did not fit (publicity at 10, data pool at 6): the log says so (trail.py names the cause). Changes no rule."""
    if n > 0:
        rec: dict[str, Any] = {"player": p.index, "lost": {kind: n}, "changes": {}}
        if source is not None:
            rec["source"] = source
        state.trail.append(rec)


def gain_publicity(state: GameState, p: PlayerState, n: int = 1) -> None:
    record_lost(state, p, "publicity", p.publicity + n - PUBLICITY_CAP)  # RES-02
    p.publicity = min(PUBLICITY_CAP, p.publicity + n)


def gain_data(state: GameState, p: PlayerState, n: int = 1) -> None:
    from . import rival  # noqa: PLC0415 - rival imports this module

    if rival.is_rival(state, p.index):  # SOLO-17: the rival's data goes to its computer, then to its unlimited pool
        rival.gain_data(state, n)
        return
    """Data beyond the pool limit is discarded (RES-01). During their own turn a player whose pool would overflow may first place pool data
    into the computer (owner ruling, 2026-10-14): the gain waits in a `data_overflow` decision until they are done."""
    if state.phase == "play" and p.index == state.current_player and p.data_pool + n > DATA_POOL_CAP and can_place_data(p):
        last = state.pending[-1] if state.pending else None
        if last is not None and last.kind == "data_overflow" and last.player == p.index:
            last.data["n"] += n  # several gains in one effect are one choice
        else:
            state.pending.append(Decision(kind="data_overflow", player=p.index, data={"n": n}))
        return
    record_lost(state, p, "data", p.data_pool + n - DATA_POOL_CAP)  # RES-01
    p.data_pool = min(DATA_POOL_CAP, p.data_pool + n)


def can_place_data(p: PlayerState) -> bool:
    """FREE-03, TECH-21: the player has a pool data and a computer space (or a computer tech's lower space) to put it in."""
    from . import techs  # noqa: PLC0415 - techs imports this module

    return (p.data_pool >= 1 and not all(p.computer)) or bool(techs.lower_moves(p))


def gain_score(state: GameState, p: PlayerState, n: int) -> None:
    """Add points and remember which milestones were reached or passed; they are resolved at the end of the turn (MILE-01)."""
    from . import species  # noqa: PLC0415 - species imports this module's neighbours

    before = p.score
    p.score += n
    if p.messages or p.message_cards:
        species.check_messages(state, p, before)
    species.check_exertian_milestones(state, p, before)
    for m in MILESTONES:
        if before < m <= p.score and before < 100:
            state.crossed.append((p.index, m))


def draw_from_deck(state: GameState) -> str | None:
    """Top card of the deck; an empty deck is rebuilt by shuffling the discard pile (RES-04)."""
    if not state.deck and state.discard:
        state.deck = rng.shuffled(state, state.discard)
        state.discard = []
    return state.deck.pop() if state.deck else None


def draw_random_card(state: GameState, p: PlayerState) -> str | None:
    cid = draw_from_deck(state)
    if cid is not None:
        p.hand.append(cid)
        state.trail.append({"player": p.index, "draw": cid, "source": {}, "changes": {}})  # `draw_card` event (trail.events_of)
    return cid


def refill_card_row(state: GameState) -> None:
    while len(state.card_row) < 3:
        cid = draw_from_deck(state)
        if cid is None:
            return
        state.card_row.append(cid)


def take_from_row_or_deck(state: GameState, p: PlayerState, source: str, events: list[dict[str, Any]] | None = None) -> str | None:
    """`source` is 'deck' or 'row:<index>'. A card taken from the row is replaced at once (RES-04, A-026): only that one, so a gap that a
    running scan has left in the row stays until the scan is finished (SCAN-03)."""
    if source == "deck":
        return draw_random_card(state, p)
    idx = int(source.split(":")[1])
    cid = state.card_row.pop(idx)
    p.hand.append(cid)
    if events is not None:  # a card of the display is face up: the log names it (a card from the deck stays hidden)
        events.append({"type": "take_display_card", "player": p.index, "card": cid, "source": source})
    replacement = draw_from_deck(state)
    if replacement is not None:
        state.card_row.append(replacement)
    return cid


def gain_income_resource(state: GameState, p: PlayerState, kind: str, n: int = 1) -> None:
    """The resource a tucked card (or the income card) gives: credit, energy, card (random from the deck), publicity or data."""
    if kind == "credit":
        p.credits += n
    elif kind == "energy":
        p.energy += n
    elif kind == "card":
        for _ in range(n):
            draw_random_card(state, p)
    elif kind == "publicity":
        gain_publicity(state, p, n)
    elif kind == "data":
        gain_data(state, p, n)
    else:
        raise ValueError(kind)


def tuck_card(state: GameState, p: PlayerState, card: str) -> None:
    """Tuck a card under the income card and gain its resource at once (INCOME-01)."""
    with trail.cost(state, "tuck"):
        p.hand.remove(card)
        p.tucked.append(card)
    with trail.scope(state, {"kind": "income", "what": "tuck"}):  # the resource of the tucked card is income, apart from the action
        gain_income_resource(state, p, tables.cards()[card]["income"])


def pay(p: PlayerState, credits: int = 0, energy: int = 0, publicity: int = 0) -> bool:
    if p.credits < credits or p.energy < energy or p.publicity < publicity:
        return False
    p.credits -= credits
    p.energy -= energy
    p.publicity -= publicity
    return True


def tech_active(p: PlayerState, name: str) -> bool:
    """Can the player use the ability of the tech? A tech that Helion Assembly has set beside its board still counts as owned for
    everything else,
    and one that Turing Systems borrows for the turn can be used without being owned (EXP-ORG-13)."""
    return (name in p.techs and name not in p.org_data.get("disabled", [])) or name in p.org_data.get("borrowed", [])


def probe_limit(p: PlayerState) -> int:
    extra = 1 if p.organization == "orbital_dynamics" else 0  # Orbital Dynamics: the limit of probes in space is 1 higher (EXP-ORG-13)
    return (2 if tech_active(p, "probe-dot") else 1) + extra  # LAUNCH-02, LAUNCH-03


def launch_probe(state: GameState, p: PlayerState, events: list[dict[str, object]], nolimit: bool = False) -> bool:
    """Put a probe on Earth if the player is under the probe limit (LAUNCH-01); card #9 ignores the limit (FAQ-C009)."""
    from . import cards, orgs  # noqa: PLC0415 - these import this module

    if not nolimit and sum(1 for pr in state.probes if pr.player == p.index and not pr.capsule) >= probe_limit(p):
        return False
    ring, sector = solar.earth(state)
    state.probe_counter += 1
    probe = Probe(id=f"probe{state.probe_counter}", player=p.index, ring=ring, sector=sector)
    state.probes.append(probe)
    events.append({"type": "launch", "player": p.index, "probe": probe.id})
    cards.fire(state, p, [{"e": "launch"}], events)  # FAQ-C117
    orgs.on_launch(state, p, events)  # Sentinel Probe Network (EXP-ORG-13)
    return True
