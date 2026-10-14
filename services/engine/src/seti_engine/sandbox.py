"""The solo sandbox (PLAN.md D33): a practice game for one player, without the rival, in which cards, resources and the discs of the solar
system can be changed freely. Nothing here is a rule of the game: it exists to try cards and situations out. The actions are only accepted
when `Options.sandbox` is set; the game is never rated.

Actions are not listed one by one in the legal moves (there are too many); one `sandbox` entry says what is possible.
    sandbox_add_card {card}            put the card in the player's hand
    sandbox_resource {resource, n}     add or (n < 0) remove credits, energy, data, publicity or exofossils
    sandbox_rotate {disc 1..3, step}   turn one disc by one step (1 or -1), with no reward for pushed probes
"""

from __future__ import annotations

from typing import Any

from . import effects, solar, species, tables
from .models import GameState, PlayerState

Action = dict[str, Any]
Events = list[dict[str, Any]]

RESOURCES = ("credit", "energy", "data", "publicity", "exofossil")
MAX_STEP = 50  # the most that one action changes a resource by
DATA_POOL_MAX = 6
PUBLICITY_MAX = 10


def is_sandbox_action(action: Action) -> bool:
    return str(action.get("type", "")).startswith("sandbox_")


def discovered_species(s: GameState) -> set[str]:
    return {sl.species for sl in s.species if sl.discovered}


def resources_available(s: GameState) -> list[str]:
    """SANDBOX-03: exofossils exist only when 'Oumuamua has been discovered."""
    return [r for r in RESOURCES if r != "exofossil" or species.oumuamua_slot(s) is not None]


def addable_cards(s: GameState) -> list[str]:
    """SANDBOX-02: every base card (and the promo cards when the game has them) and the alien cards of the species that are face up."""
    shown = discovered_species(s)
    out = []
    for cid, c in tables.cards().items():
        if c["deck"] == "promo" and not s.options.promo_cards:
            continue
        if c["deck"] not in ("base", "promo") and c["species"] not in shown:
            continue
        out.append(cid)
    return sorted(out, key=lambda x: (x.startswith("ET."), int(x.split(".")[-1]) if x.split(".")[-1].isdigit() else 0, x))


def marker(s: GameState) -> Action:
    """The one entry of the legal moves that tells the page what the sandbox offers."""
    return {"type": "sandbox", "resources": resources_available(s), "discs": [1, 2, 3], "cards": addable_cards(s)}


def check(s: GameState, a: Action) -> str | None:
    """SANDBOX-01, SANDBOX-05: why the action is not allowed, or None."""
    if not s.options.sandbox:
        return "this is not a sandbox game"
    if s.phase != "play" or s.pending:
        return "the sandbox can only be used between decisions, in the play phase"
    t = a["type"]
    if t == "sandbox_add_card":
        return None if a.get("card") in addable_cards(s) else "that card cannot be added (an alien card needs its species to be face up)"
    if t == "sandbox_resource":
        n = a.get("n")
        if a.get("resource") not in resources_available(s):
            return "that resource is not available"
        if not isinstance(n, int) or isinstance(n, bool) or n == 0 or abs(n) > MAX_STEP:
            return f"n must be a whole number from -{MAX_STEP} to {MAX_STEP}, not 0"
        return None
    if t == "sandbox_rotate":
        if a.get("disc") not in (1, 2, 3) or a.get("step") not in (1, -1):
            return "disc must be 1, 2 or 3 and step 1 or -1"
        return None
    return "unknown sandbox action"


def _remove_everywhere(s: GameState, cid: str) -> None:
    """A card that is added leaves the pile it was in, so that a card never exists twice (when it is somewhere that can be searched)."""
    for pile in (s.deck, s.discard, s.card_row, *s.end_of_round_stacks, s.aside):
        if cid in pile:
            pile.remove(cid)
            return
    for sl in s.species:
        if cid in sl.deck:
            sl.deck.remove(cid)
            return
        if sl.face_up == cid:
            sl.face_up = sl.deck.pop() if sl.deck else None
            return


def apply_action(s: GameState, a: Action, events: Events) -> None:
    p: PlayerState = s.players[s.current_player]
    t = a["type"]
    if t == "sandbox_add_card":
        cid = a["card"]
        _remove_everywhere(s, cid)
        if tables.cards()[cid]["species"] == "exertians":
            p.exertian_hand.append(cid)  # Exertian cards are not in the hand (ALIEN-EXE-02)
        else:
            p.hand.append(cid)
        effects.refill_card_row(s)
        events.append({"type": "sandbox", "what": "card", "card": cid})
    elif t == "sandbox_resource":
        kind, n = a["resource"], a["n"]
        if kind == "credit":
            p.credits = max(0, p.credits + n)
        elif kind == "energy":
            p.energy = max(0, p.energy + n)
        elif kind == "data":
            p.data_pool = min(DATA_POOL_MAX, max(0, p.data_pool + n))
        elif kind == "publicity":
            p.publicity = min(PUBLICITY_MAX, max(0, p.publicity + n))
        else:
            p.exofossils = max(0, p.exofossils + n)
        events.append({"type": "sandbox", "what": "resource", "resource": kind, "n": n})
    elif t == "sandbox_rotate":
        solar.rotate_discs(s, {a["disc"]}, a["step"])  # SANDBOX-04
        events.append({"type": "sandbox", "what": "rotate", "disc": a["disc"], "step": a["step"]})
