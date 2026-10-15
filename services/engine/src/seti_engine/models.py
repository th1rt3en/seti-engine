"""Game state models. The state is plain data (JSON-serializable) and is copied, never shared, between engine calls."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

COLORS = ["green", "red", "purple", "white"]
SECTOR_COLORS = ["red", "yellow", "blue", "black"]
TECH_CATEGORIES = ["probe", "telescope", "computer"]
GLYPHS = ["dot", "link", "branch", "cross"]
PLANET_ORDER = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]
SPECIES_BASE = ["anomalies", "centaurians", "exertians", "mascamites", "oumuamua"]
SPECIES_EXPANSION = ["arkhos", "glyphids", "amoeba"]  # EXP-03: the new species the engine can play (Glyphids and Amoeba follow)

Phase = Literal["setup", "play", "finished"]


class Options(BaseModel):
    players: int = Field(ge=1, le=4)  # 1 is the solo game against the rival (SOLO-01)
    difficulty: int = Field(default=3, ge=1, le=5)  # solo only: the number of gold stars (SOLO-04)
    promo_cards: bool = False  # PLAN.md D23: SE EN 01 and SE EN 02 are shuffled into the deck when on
    promo_set_2: bool = False  # PROMO-04: SE EN 03 and SE DE 04 are shuffled into the deck when on
    # PLAN.md D33: a practice game for one player, without the rival, in which cards, resources and the discs can be added or changed freely
    sandbox: bool = False
    # PLAN.md D35 (docs/spec/expansion.md): the Space Agencies expansion. `expansion` puts signal tokens in the game (and, as their data
    # is supplied,
    # the 42 cards and 3 species, A-028, A-032); `organizations` (needs `expansion`) is the organization module with quick start cards and
    # 4 rounds;
    # `neutral_quick_start` (needs `expansion`, 1 or 2 players) marks the neutral pieces of 4 quick start cards before the players choose
    expansion: bool = False
    organizations: bool = False
    neutral_quick_start: bool = False
    beginner_organizations: bool = False  # EXP-ORG-05: the first game tip (organizations 1 to 4, 2 quick start cards)
    # sandbox only: the two face-down alien species, left to right; None leaves a slot to chance (SANDBOX-06)
    sandbox_species: list[str | None] = Field(default_factory=lambda: list[str | None]([None, None]))
    seed: int = 0

    @model_validator(mode="after")
    def _sandbox_is_solo(self) -> Options:
        if self.sandbox and self.players != 1:
            raise ValueError("the sandbox is a game for one player")
        if (self.organizations or self.neutral_quick_start) and not self.expansion:
            raise ValueError("organizations and neutral quick start cards are part of the expansion")
        if self.beginner_organizations and not self.organizations:
            raise ValueError("the beginner organizations are an option of the organization module")
        if self.neutral_quick_start and self.players > 2:
            raise ValueError("the neutral quick start cards are for games of 1 or 2 players")
        chosen = [x for x in self.sandbox_species if x is not None]
        if len(self.sandbox_species) != 2 or any(x not in SPECIES_BASE for x in chosen) or len(set(chosen)) != len(chosen):
            raise ValueError("sandbox_species lists two different base species, or null for chance")
        if chosen and not self.sandbox:
            raise ValueError("the species can only be chosen in the sandbox")
        return self


class Probe(BaseModel):
    id: str
    player: int
    ring: int  # 1..4, ring 1 is next to the Sun
    sector: int  # 0..7
    capsule: bool = False  # a Mascamite sample capsule: moves like a probe, never orbits or lands (ALIEN-MASC-03)
    sample: int | None = None  # the sample token under a capsule


class ComputerTech(BaseModel):
    tech: str  # e.g. "computer-dot"
    lower_filled: bool = False


class MissionState(BaseModel):
    """A mission card in front of a player (CARD-10 to CARD-16). `used` marks the covered circles of a triggerable mission."""

    card: str
    kind: str  # "quick" or "trigger"
    used: list[bool] = Field(default_factory=list)


class MessageCard(BaseModel):
    """A Centaurian card in front of a player waiting for its message marker to be reached (ALIEN-CEN-02)."""

    target: int
    card: str


class PlayerState(BaseModel):
    index: int
    color: str
    score: int = 0
    publicity: int = 4
    credits: int = 0
    energy: int = 0
    data_pool: int = 0
    movement: int = 0  # movement points available this turn (A-015)
    hand: list[str] = Field(default_factory=list)
    tucked: list[str] = Field(default_factory=list)  # cards tucked under the income card, in order
    techs: list[str] = Field(default_factory=list)  # "probe-dot", "telescope-link", ...
    computer: list[bool] = Field(default_factory=lambda: [False] * 6)  # top row, filled left to right
    computer_techs: dict[int, ComputerTech] = Field(default_factory=dict)  # top-row position (0,2,4,5) -> tech
    passed: bool = False
    probes_launched: int = 0
    gold_markers: list[str] = Field(default_factory=list)  # names of gold tiles this player marked
    sector_wins: int = 0
    orbiters: dict[str, int] = Field(default_factory=dict)  # planet -> count
    landers: dict[str, int] = Field(default_factory=dict)  # planet or moon -> count
    missions: list[MissionState] = Field(default_factory=list)  # CARD-10: face-up missions still to complete
    completed_missions: list[str] = Field(default_factory=list)  # CARD-16: face down
    kept_cards: list[str] = Field(default_factory=list)  # cards kept in front of the player, no mission or end card (SE EN 01)
    signal_tokens: int = 0  # EXP-SIG-01: unlimited supply
    glyphs: list[str] = Field(default_factory=list)  # Glyphids (EXP-GLY-04): the glyph tokens not yet placed on the translation board
    # Arkhos (EXP-ARK-03): trace color -> the security card still in front of the player
    security: dict[str, str] = Field(default_factory=dict)
    # the organization module (EXP-ORG-*): the organization, the 2 + 3 cards offered at setup (only the player sees them),
    # the quick start cards chosen
    organization: str | None = None
    offered_orgs: list[str] = Field(default_factory=list)
    offered_quick: list[str] = Field(default_factory=list)
    quick_start: list[str] = Field(default_factory=list)
    org_used: bool = False  # the once per round ability has been used this round (EXP-ORG-10)
    org_marks: list[str] = Field(default_factory=list)  # reward spaces marked on Cosmos Strategy Group or Helion Assembly (EXP-ORG-11)
    org_data: dict[str, Any] = Field(
        default_factory=dict
    )  # per organization: the Futurespan card and token, the Xenolab tiles, a stored card corner
    end_cards: list[str] = Field(default_factory=list)  # CARD-20: end-of-game scoring cards in front of the player
    exertian_hand: list[str] = Field(default_factory=list)  # Exertian cards held (not in hand, ALIEN-EXE-02)
    exertian_played: list[str] = Field(default_factory=list)  # Exertian cards played face down (ALIEN-EXE-01)
    message_cards: list[MessageCard] = Field(default_factory=list)  # oldest first (ALIEN-CEN-03)
    exofossils: int = 0  # 'Oumuamua tokens (ALIEN-OUM-02)
    messages: list[int] = Field(default_factory=list)  # Centaurian message milestones: score targets, oldest first (ALIEN-CEN-03)
    trace_log: list[tuple[int, str]] = Field(default_factory=list)  # (species slot, kind) of every life trace marked (CARD-46)


class SectorState(BaseModel):
    star: str
    color: str
    capacity: int
    data_remaining: int
    markers: list[int] = Field(default_factory=list)  # player indices in placement order (excess markers included)
    winners: list[int] = Field(default_factory=list)  # markers placed beside the star after wins


class TechStack(BaseModel):
    category: str
    glyph: str
    tiles: list[str]  # bonus keys, top of the stack first: "vp3", "card", "energy", "publicity"
    two_point_tile: bool = True


class GoldTile(BaseModel):
    tile: str  # "Tech", "Mission", "Income", "Other"
    side: str  # "A" or "B"
    markers: list[int] = Field(default_factory=list)  # players in the order they chose it
    low_markers: list[int] = Field(default_factory=list)  # Mission Relay starts on the lowest-scoring space (EXP-ORG-13)


class SpeciesSlot(BaseModel):
    species: str  # hidden until discovered
    discovered: bool = False
    discovery_spaces: list[str | None] = Field(default_factory=lambda: [None, None, None])  # type: ignore[arg-type]  # "p0".."p3" or "n"
    overflow: list[int] = Field(default_factory=list)  # players who used an overflow space
    overflow_kinds: list[str] = Field(default_factory=list)  # the color of the overflow space each of those markers sits on (A-017, A-022)
    complete: bool = False  # all three discovery spaces are full; the species is revealed once the turn is over (ALIEN-01)
    board: dict[str, list[list[int]]] = Field(default_factory=dict)  # color -> spaces -> markers (players) on the species board
    deck: list[str] = Field(default_factory=list)  # the species' card deck, top = last
    face_up: str | None = None  # the face-up card beside the deck (ALIEN-05)
    extra: dict[str, Any] = Field(default_factory=dict)  # per-species state (anomaly tokens, message rewards, ...)


class PlanetState(BaseModel):
    orbiters: list[int] = Field(default_factory=list)  # player indices in order of arrival (first = first orbiter)
    landers: list[int] = Field(default_factory=list)
    first_orbit_taken: bool = False
    first_orbiter: int | None = None  # player whose orbiter covers the first-orbiter space (ORBIT-04, FAQ-C015)
    first_land_data_taken: list[bool] = Field(default_factory=list)
    first_land_owners: list[int | None] = Field(default_factory=list)  # player whose lander covers each first-lander space
    moon_landers: dict[str, int] = Field(default_factory=dict)  # moon -> player


class Decision(BaseModel):
    """Something the engine waits for a player to choose before play continues."""

    kind: str
    player: int
    data: dict[str, Any] = Field(default_factory=dict)


class RivalState(BaseModel):
    """The solo rival (SOLO-*): it is the second entry of `GameState.players`, with its own bookkeeping here."""

    index: int
    progress: int  # position on the 12-space progress track (SOLO-DATA-11)
    deck: list[str] = Field(default_factory=list)  # action deck, top first
    used: list[str] = Field(default_factory=list)  # action cards played this round
    advanced: list[str] = Field(default_factory=list)  # advanced action cards not yet gained (SOLO-05, SOLO-12)
    computer: int = 0  # data on the rival's computer, 0 to 6 (its unlimited data pool is `PlayerState.data_pool`, SOLO-17)
    techs: list[str] = Field(default_factory=list)  # stored techs (SOLO-18)
    arrow: str = "left"  # decision arrow of the card being resolved
    messages_in_reserve: int = 0  # Centaurian message tokens the rival may still place (SOLO-ALIEN-02)


class ObjectiveState(BaseModel):
    """The player's objectives in the solo game (SOLO-OBJ-*)."""

    stack: list[str] = Field(default_factory=list)  # top = last
    row: list[str] = Field(default_factory=list)  # up to 3 revealed objectives
    marks: dict[str, list[bool]] = Field(default_factory=dict)  # objective id -> tasks marked
    pile: list[str] = Field(default_factory=list)  # completed objectives not yet spent
    long_term: list[str] = Field(
        default_factory=list
    )  # EXP-SOLO-04, EXP-SOLO-06: the two long-term tiles in play (their marks are in `marks`)


class GameState(BaseModel):
    options: Options
    # the state before the last free exchange that can be taken back (UNDO-01); None once anything else is done. Never shown to a player.
    undo: dict[str, Any] | None = None
    # the actions taken since `undo` was saved, oldest first: taking the last one back replays the others on the saved state (UNDO-01)
    undo_log: list[dict[str, Any]] = Field(default_factory=list)
    # decisions of the main action that a free action has interrupted, waiting while the free action's own decisions are answered (FREE-00)
    stashed: list[Decision] = Field(default_factory=list)
    free_active: bool = False  # the decisions now pending belong to a free action, which no other free action may interrupt (FREE-00)
    rng_state: int
    phase: Phase = "setup"
    round: int = 1
    turn: int = 1  # the turn within the round: 1 for the first player's turn, +1 for each following turn (counts the rival's turns too)
    current_player: int = 0
    start_player: int = 0
    players: list[PlayerState]
    rival: RivalState | None = None  # the solo rival
    objectives: ObjectiveState | None = None
    # cards
    deck: list[str] = Field(default_factory=list)
    discard: list[str] = Field(default_factory=list)
    card_row: list[str] = Field(default_factory=list)
    end_of_round_stacks: list[list[str]] = Field(default_factory=list)  # index = round - 1, dealt face down at setup (A-003)
    # board
    sector_order: list[int] = Field(default_factory=list)  # sector board ids in clockwise-from-sector-0 order, 2 sectors per board
    sectors: list[SectorState] = Field(default_factory=list)
    disc_angles: list[int] = Field(default_factory=lambda: [0, 0, 0])  # 1/8 turns counter-clockwise of discs 1, 2, 3
    rotations: int = 0  # solar system rotations so far (next disc = rotations % 3 + 1)
    first_pass_done: bool = False  # this round
    oumuamua_placed: bool = False
    neutral_quick: list[str] = Field(default_factory=list)  # the quick start cards revealed for the neutral pieces (EXP-QS-03)
    pluto_owner: int | None = None  # the player who played the promo card SE EN 01: only they can orbit or land at Pluto (PROMO-02)
    probes: list[Probe] = Field(default_factory=list)
    planets: dict[str, PlanetState] = Field(default_factory=dict)
    tech_stacks: list[TechStack] = Field(default_factory=list)
    gold_tiles: list[GoldTile] = Field(default_factory=list)
    species: list[SpeciesSlot] = Field(default_factory=list)
    neutral_markers: dict[str, int] = Field(default_factory=dict)  # "20" / "30" -> markers left on the milestone
    # turn bookkeeping
    pending: list[Decision] = Field(default_factory=list)  # first entry is what the engine waits for
    crossed: list[tuple[int, int]] = Field(default_factory=list)  # (player, milestone) crossed this turn, to resolve at turn end
    probe_counter: int = 0
    stage: str | None = (
        None  # None, 'sectors' (resolving the sectors the main action completed), 'pass' (passing steps running) or 'turn_end'
    )
    pass_discard_checked: bool = False
    pass_rotated: bool = False
    pass_card_asked: bool = False
    completed: list[int] = Field(default_factory=list)  # sectors completed and not yet resolved: right after the main action (SECTOR-10)
    scan_steps: list[str] = Field(default_factory=list)  # steps of the running scan still to do (SCAN-01)
    aside: list[str] = Field(default_factory=list)  # cards drawn by #ET.15 and not yet placed
    queue: list[dict[str, Any]] = Field(default_factory=list)  # steps of the card being played, resolved in order (cards.py)
    playing: str | None = None  # the card being played as the main action
    action_sectors: list[int] = Field(default_factory=list)  # sectors marked by the current card (FAQ-C050)
    play_return: bool = False  # the played card returns to hand (#120)
    turn_fx: list[dict[str, Any]] = Field(default_factory=list)  # "this turn" effects of played cards
    turn_completed: bool = False  # a sector was completed this turn
    pushed: list[tuple[int, str]] = Field(default_factory=list)  # (player, cell) of probes pushed by the last rotation
    last_trace_kind: str = "any"  # kind of the last life trace marked
    scan_ctx: dict[str, Any] | None = None  # the running scan (None when no scan is running)
    main_done: bool = False  # the current player has taken their main action this turn
    final_scores: list[dict[str, Any]] = Field(default_factory=list)  # one row per player once the game is over (END-01)
    winners: list[int] = Field(default_factory=list)
    log: list[str] = Field(default_factory=list)
