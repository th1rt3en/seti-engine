"""What one player may see of a game (CLAUDE.md rule 6): the state with the hidden parts blanked, and the counts of what was blanked.

Hidden from everyone but the owner: hands, held Exertian cards and the Exertian cards played face down.
Hidden from everyone: the draw deck and its order, the contents of the end-of-round stacks, the identity of undiscovered species,
the species decks, the sample tokens on the planets, the order of the tech tiles in their stacks, the rival's deck order, the objectives
stack and the random generator state.
The server must send a client only `project(state, viewer)`, never the state itself.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import engine
from .models import GameState

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


class View(BaseModel):
    """The state as one viewer sees it. `viewer` is None for a spectator. `legal` is empty unless the viewer is the one to act."""

    viewer: int | None
    state: GameState
    counts: Counts
    to_act: int | None
    legal: list[dict[str, Any]] = Field(default_factory=list)


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
    for p in s.players:
        if p.index != viewer:
            p.hand = [HIDDEN] * len(p.hand)
            p.exertian_hand = [HIDDEN] * len(p.exertian_hand)
            p.exertian_played = [HIDDEN] * len(p.exertian_played)
    for slot in s.species:
        slot.deck = [HIDDEN] * len(slot.deck)
        if not slot.discovered:
            slot.species = HIDDEN
            slot.extra = {}
        else:
            _hide_tokens(slot.extra)
    for st in s.tech_stacks:
        st.tiles = [HIDDEN] * len(st.tiles)
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
    return View(viewer=viewer, state=s, counts=counts, to_act=actor, legal=legal)


def _hide_tokens(extra: dict[str, Any]) -> None:
    """Mascamite samples lie face down on Jupiter and Saturn: show how many, not which."""
    samples = extra.get("samples")
    if isinstance(samples, dict):
        extra["samples"] = {planet: [-1] * len(tokens) for planet, tokens in samples.items()}
