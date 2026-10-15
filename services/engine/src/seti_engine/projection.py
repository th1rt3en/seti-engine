"""What one player may see of a game (CLAUDE.md rule 6): the state with the hidden parts blanked, and the counts of what was blanked.

Hidden from everyone but the owner: hands, held Exertian cards and the Exertian cards played face down.
Hidden from everyone: the draw deck and its order, the contents of the end-of-round stacks, the identity of undiscovered species,
the species decks, the sample tokens on the planets, the tech tiles under the top one of each stack (the top tile lies bonus side up for all
to see, SETUP-16), the rival's deck order, the objectives stack and the random generator state.
The server must send a client only `project(state, viewer)`, never the state itself.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import engine, move_notes, orgs, species, tables
from .models import GameState, PlayerState

HIDDEN = "?"  # a hidden card, tile or token


class Counts(BaseModel):
    """How many of the hidden things there are."""

    deck: int
    end_of_round_stacks: list[int]
    hands: list[int]  # cards in each player's hand
    exertian_hands: list[int]
    exertian_played: list[int]
    species_decks: list[int]
    rival_deck: int = 0
    objective_stack: int = 0


# the income card itself (ROUND-02, INCOME-03); each tucked card adds its own (INCOME-01)
INCOME_BASE = {"credit": 3, "energy": 2, "card": 1}
INCOME_KINDS = ("credit", "energy", "card")


class PlayerTracker(BaseModel):
    """What the tracker beside the board shows for one player. Everything here is public information."""

    income: dict[
        str, int
    ]  # per round: credit, energy, card (the income card plus tucked cards); with an organization also publicity, data and signal
    tucked: dict[str, int]  # how many cards are tucked for each kind of income
    missions_done: int  # completed missions (CARD-16)
    end_cards: int  # end-of-game scoring cards in front of the player (CARD-20)
    score: int
    # Exertian danger (ALIEN-EXE-06). The board part and the number of cards played are public; the danger of the played cards
    # is None unless the viewer is this player, because the cards lie face down until the end of the game.
    danger_board: int = 0
    exertian_played: int = 0
    danger_cards: int | None = None


def tracker(state: GameState, p: PlayerState, viewer: int | None = None) -> PlayerTracker:
    """INCOME-01, INCOME-03, ROUND-02: the income a player gets at the end of each round, by kind. The solo rival has none (A-025)."""
    rival_player = state.rival is not None and p.index == state.rival.index
    tucked = {k: sum(1 for c in p.tucked if tables.cards()[c]["income"] == k) for k in INCOME_KINDS}
    if (
        p.organization is not None
    ):  # EXP-ORG-08, A-031: the organization's income card (with data, publicity, signal tokens) plus the tucked cards
        income = orgs.income_of(p)
    else:
        income = {k: 0 if rival_player else INCOME_BASE[k] + tucked[k] for k in INCOME_KINDS}
    return PlayerTracker(
        income=income,
        tucked=tucked,
        missions_done=len(p.completed_missions),
        end_cards=len(p.end_cards),
        score=p.score,
        danger_board=species.board_danger(state, p),
        exertian_played=len(p.exertian_played),
        danger_cards=species.cards_danger(p) if viewer == p.index else None,
    )


class ReachCell(BaseModel):
    """A space a probe can reach: the movement it takes and a cheapest path (the spaces entered, the last one is `to`)."""

    to: tuple[int, int]
    cost: int
    path: list[tuple[int, int]]
    label: str = ""  # what lies on the space `to`, in words


class ProbeReach(BaseModel):
    probe: str
    cells: list[ReachCell]
    label: str = ""  # what lies on the space the probe is on now, in words


class View(BaseModel):
    """The state as one viewer sees it. `viewer` is None for a spectator. `legal` is empty unless the viewer is the one to act."""

    viewer: int | None
    state: GameState
    counts: Counts
    trackers: list[PlayerTracker] = Field(default_factory=list)  # one per player, in seat order
    to_act: int | None
    legal: list[dict[str, Any]] = Field(default_factory=list)
    # where the viewer's probes can go with their movement plus all their energy (FREE-01); empty unless the viewer may move now
    reach: list[ProbeReach] = Field(default_factory=list)
    # what each legal move means (where, cost, rewards), in the order of `legal`, for the confirmation on the page (move_notes.py)
    notes: list[dict[str, Any] | None] = Field(default_factory=list)


def _label_of(state: GameState, probe_id: str) -> str:
    probe = next(p for p in state.probes if p.id == probe_id)
    return move_notes.space_label(state, probe.ring, probe.sector)


def to_act(state: GameState) -> int | None:
    """The player the engine is waiting for, if any."""
    if state.phase == "finished":
        return None
    if state.pending:
        return state.pending[0].player
    return state.current_player if state.phase == "play" else None


def project(state: GameState, viewer: int | None) -> View:
    s = state.model_copy(deep=True)
    counts = Counts(
        deck=len(s.deck),
        end_of_round_stacks=[len(x) for x in s.end_of_round_stacks],
        hands=[len(p.hand) for p in s.players],
        exertian_hands=[len(p.exertian_hand) for p in s.players],
        exertian_played=[len(p.exertian_played) for p in s.players],
        species_decks=[len(sl.deck) for sl in s.species],
        rival_deck=len(s.rival.deck) if s.rival else 0,
        objective_stack=len(s.objectives.stack) if s.objectives else 0,
    )
    s.rng_state = 0
    s.deck = [HIDDEN] * len(s.deck)
    s.end_of_round_stacks = [[HIDDEN] * len(x) for x in s.end_of_round_stacks]
    for pr in s.probes:
        if pr.capsule and (viewer is None or pr.player != viewer):
            pr.sample = -1  # a collected sample stays face down until it is delivered (ALIEN-MASC-04)
    for p in s.players:
        if p.index != viewer:
            p.hand = [HIDDEN] * len(p.hand)
            p.exertian_hand = [HIDDEN] * len(p.exertian_hand)
            p.exertian_played = [HIDDEN] * len(p.exertian_played)
            p.security = {c: HIDDEN for c in p.security}  # face-down, only the trace color shows (EXP-ARK-03)
            if p.org_data.get("fs_card"):
                p.org_data["fs_card"] = HIDDEN  # Futurespan's prepared card lies face down
            p.offered_orgs = [HIDDEN] * len(p.offered_orgs)  # EXP-ORG-04: the cards offered at setup are the player's secret
            p.offered_quick = [HIDDEN] * len(p.offered_quick)
    for slot in s.species:
        slot.deck = [HIDDEN] * len(slot.deck)
        if not slot.discovered:
            slot.species = HIDDEN
            slot.extra = {}
        else:
            _hide_tokens(slot.extra)
            if "supply" in slot.extra and slot.species == "glyphids":
                slot.extra["supply"] = [HIDDEN] * len(slot.extra["supply"])  # EXP-GLY-03: the face-down stack of glyph tokens
            for key in ("explore_deck", "explore_aside"):  # EXP-ARK-01: the order and the cards set aside are secret
                if key in slot.extra:
                    slot.extra[key] = [HIDDEN] * len(slot.extra[key])
    s.undo, s.undo_log = None, []  # UNDO-01: the state to go back to holds the hands and the decks; nobody is shown it
    for d in s.stashed:
        if d.player != viewer:
            d.data = {}
    for st in s.tech_stacks:
        st.tiles = st.tiles[:1] + [HIDDEN] * max(0, len(st.tiles) - 1)  # SETUP-16: only the top tile of a stack shows its bonus
    if s.rival is not None:
        s.rival.deck = [HIDDEN] * len(s.rival.deck)
        s.rival.advanced = [HIDDEN] * len(s.rival.advanced)
    if s.objectives is not None:
        s.objectives.stack = [HIDDEN] * len(s.objectives.stack)
    actor = to_act(state)
    for d in s.pending:
        if d.player != viewer:
            d.data = {}
    if actor != viewer:
        s.aside = []
    legal = engine.legal_moves(state) if viewer is not None and actor == viewer else []
    trackers = [tracker(state, p, viewer) for p in state.players]
    reach: list[ProbeReach] = []
    if legal and viewer is not None and not state.pending and state.phase == "play":
        reach = [
            ProbeReach(
                probe=pid,
                label=_label_of(state, pid),
                cells=[ReachCell(to=to, cost=cost, path=path, label=move_notes.space_label(state, *to)) for to, cost, path in cells],
            )
            for pid, cells in engine.move_reach(state, state.players[viewer])
        ]
    notes = move_notes.notes(state, legal) if legal else []
    return View(viewer=viewer, state=s, counts=counts, trackers=trackers, to_act=actor, legal=legal, reach=reach, notes=notes)


def _hide_tokens(extra: dict[str, Any]) -> None:
    """Mascamite samples lie face down on Jupiter and Saturn: show how many, not which."""
    samples = extra.get("samples")
    if isinstance(samples, dict):
        extra["samples"] = {planet: [-1] * len(tokens) for planet, tokens in samples.items()}
