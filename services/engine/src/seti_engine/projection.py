"""What one player may see of a game (CLAUDE.md rule 6): the state with the hidden parts blanked, and the counts of what was blanked.

Hidden from everyone but the owner: hands, held Exertian cards and the Exertian cards played face down (these are turned over, for
everybody, when the game is over).
Hidden from everyone: the draw deck and its order, the contents of the end-of-round stacks, the identity of undiscovered species,
the species decks, the sample tokens on the planets, the tech tiles under the top one of each stack (the top tile lies bonus side up for all
to see, SETUP-16), the rival's deck order, the objectives stack and the random generator state.
The server must send a client only `project(state, viewer)`, never the state itself.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import cards, engine, move_notes, orgs, scoring, solar, species, tables
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
    # what the gold scoring tiles and the end-of-game cards would give if the game ended now (END-10 to END-17); the sets can still grow
    gold_estimate: int = 0
    end_estimate: int = 0
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
        gold_estimate=0 if rival_player else scoring.gold_points(state, p),  # the rival does not score gold tiles (SOLO-END-01)
        end_estimate=cards.end_points(state, p),
        score=p.score,
        danger_board=species.board_danger(state, p),
        exertian_played=len(p.exertian_played),
        danger_cards=species.cards_danger(p) if viewer == p.index or state.phase == "finished" else None,
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


class RotationPreview(BaseModel):
    """What the solar system would look like after the next rotation (ROTATE-01 to ROTATE-03), for the preview panel.
    Nothing changes in the game. `disc` is the disc that turns (with every disc above it), `probes` the places of all probes afterwards,
    and `pushed` how many probes were pushed by a disc that arrived over them."""

    disc: int
    disc_angles: list[int]
    probes: list[dict[str, Any]]
    planet_cells: dict[str, list[int]]
    pushed: int = 0


ROTATION_PERIOD = 24  # 3 discs: after 24 rotations every disc is back at its angle (8 steps each)


def rotation_previews(state: GameState) -> list[RotationPreview]:
    """The solar system after each of the next rotations, one after the other, for as many as it takes to come round.
    It is made on a copy and in any phase of the game: nothing is played."""
    copy = state.model_copy(deep=True)
    out: list[RotationPreview] = []
    for _ in range(ROTATION_PERIOD):
        disc = copy.rotations % 3 + 1
        solar.rotate(copy)
        out.append(
            RotationPreview(
                disc=disc,
                disc_angles=list(copy.disc_angles),
                probes=[{"id": p.id, "player": p.player, "ring": p.ring, "sector": p.sector, "capsule": p.capsule} for p in copy.probes],
                planet_cells=_planet_cells(copy),
                pushed=len(copy.pushed),
            )
        )
    return out


class View(BaseModel):
    """The state as one viewer sees it. `viewer` is None for a spectator. `legal` is empty unless the viewer is the one to act."""

    viewer: int | None
    state: GameState
    counts: Counts
    trackers: list[PlayerTracker] = Field(default_factory=list)  # one per player, in seat order
    to_act: int | None
    legal: list[dict[str, Any]] = Field(default_factory=list)
    # the class of each legal move (free, main, answer, end, control: engine.MOVE_CLASSES), in the order of `legal`; for the AI, the
    # page may ignore it
    classes: list[str] = Field(default_factory=list)
    # where the viewer's probes can go with their movement plus all their energy (FREE-01); empty unless the viewer may move now
    reach: list[ProbeReach] = Field(default_factory=list)
    # what each legal move means (where, cost, rewards), in the order of `legal`, for the confirmation on the page (move_notes.py)
    notes: list[dict[str, Any] | None] = Field(default_factory=list)
    # where each planet lies on the solar system now (ring, sector); the discs turn, so it changes (a visit is a move onto it, FAQ-18)
    planet_cells: dict[str, list[int]] = Field(default_factory=dict)
    # the solar system after each of the next rotations (the first one is the next rotation), for the preview panel (nothing is played)
    rotation_previews: list[RotationPreview] = Field(default_factory=list)


def _planet_cells(state: GameState) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for ring in range(1, 5):
        for sector in range(8):
            name = solar.planet_of(solar.visible(state, ring, sector)[1])
            if name is not None and name in state.planets and name not in out:
                out[name] = [ring, sector]
    return out


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


def project(state: GameState, viewer: int | None, previews: bool = True) -> View:
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
            if s.phase != "finished":  # ALIEN-EXE-06: the cards played face down are turned over at the end of the game, for everybody
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
            if not any(sp for spaces in slot.board.values() for sp in spaces):  # the number of spaces of a board tells which species it is
                slot.board = {c: [[] for _ in range(5)] for c in ("pink", "yellow", "blue")}
        else:
            _hide_tokens(slot.extra, viewer)
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
    classified = engine.legal_classified(state) if viewer is not None and actor == viewer else []
    legal = [m for m, _ in classified]
    trackers = [tracker(state, p, viewer) for p in state.players]
    reach: list[ProbeReach] = []
    # the probes can be moved with a click when nothing is asked, and also in the middle of a decision that a free action may interrupt
    # (a mission that gives movement while a scan is going on): the legal moves say whether moving is allowed now
    can_move = any(m["type"] == "move_probe" for m in legal)
    if legal and viewer is not None and (not state.pending or can_move) and state.phase == "play":
        reach = [
            ProbeReach(
                probe=pid,
                label=_label_of(state, pid),
                cells=[ReachCell(to=to, cost=cost, path=path, label=move_notes.space_label(state, *to)) for to, cost, path in cells],
            )
            for pid, cells in engine.move_reach(state, state.players[viewer])
        ]
    notes = move_notes.notes(state, legal) if legal else []
    return View(
        viewer=viewer,
        state=s,
        counts=counts,
        trackers=trackers,
        to_act=actor,
        legal=legal,
        classes=[c for _, c in classified],
        reach=reach,
        notes=notes,
        planet_cells=_planet_cells(state),
        rotation_previews=rotation_previews(state) if previews else [],  # the offline training does not need them
    )


def _hide_tokens(extra: dict[str, Any], viewer: int | None) -> None:
    """Mascamite samples lie face down on Jupiter and Saturn: everyone sees how many, and a player also sees the tokens they have looked at
    (ALIEN-MASC-02); the others stay -1. What each player has seen is theirs alone."""
    seen = extra.pop("seen", {})
    known = set(seen.get(str(viewer), [])) if viewer is not None else set()
    samples = extra.get("samples")
    if isinstance(samples, dict):
        extra["samples"] = {planet: [t if t in known else -1 for t in tokens] for planet, tokens in samples.items()}
