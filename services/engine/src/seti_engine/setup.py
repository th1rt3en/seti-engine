"""Game setup. Spec: docs/spec/setup.md (SETUP-10 to SETUP-38), A-003, A-004, A-008.

Order of random draws (all from the seeded generator, so a game is reproducible from `Options`):
 1. sector board order (4 boards), 2. disc angles (3), 3. alien species (2 of 5), 4. gold tile sides (4), 5. tech stack orders (12),
 6. deck shuffle, then the card row, the end-of-round stacks, each player's 5 cards, 7. the starting player.
"""

from __future__ import annotations

from . import orgs, rival, rng, species, tables
from .models import (
    COLORS,
    GLYPHS,
    PLANET_ORDER,
    SPECIES_BASE,
    SPECIES_EXPANSION,
    TECH_CATEGORIES,
    Decision,
    GameState,
    GoldTile,
    Options,
    PlanetState,
    PlayerState,
    SectorState,
    SpeciesSlot,
    TechStack,
)

BONUS_ORDER = ["vp3", "card", "energy", "publicity"]
GOLD_TILE_NAMES = ["Tech", "Mission", "Income", "Other"]


def _sandbox_species(options: Options, drawn: list[str]) -> list[str]:
    """SANDBOX-06: the species the player chose keep their slot; a slot left to chance takes the next species of the random order."""
    wanted = options.sandbox_species
    spare = [x for x in drawn if x not in wanted]
    return [w if w is not None else spare.pop(0) for w in wanted]


def new_game(options: Options) -> GameState:
    state = GameState(options=options, rng_state=rng.seed_state(options.seed), players=[])
    solo = options.players == 1 and not options.sandbox  # SOLO-01: set up as for two players (the sandbox has no rival, D33)
    n = 2 if solo else options.players

    # sector boards (stars come in pairs, BOARD-20): a random order of the four boards around the board
    boards = tables.stars()["boards"]
    order = rng.shuffled(state, [b["id"] for b in boards])
    state.sector_order = order
    by_id = {b["id"]: b for b in boards}
    for board_id in order:
        for star in by_id[board_id]["stars"]:
            state.sectors.append(
                SectorState(star=star["name"], color=star["color"], capacity=star["capacity"], data_remaining=star["capacity"])
            )

    # discs: any rotation of the three discs is a legal start (owner, A-007)
    state.disc_angles = [rng.below(state, 8) for _ in range(3)]

    # two of the five alien species, hidden (SETUP-11)
    pool = [
        *SPECIES_BASE,
        *(SPECIES_EXPANSION if options.expansion and not solo else []),
    ]  # EXP-03; the rival does not know them yet (A-033)
    drawn = rng.shuffled(state, pool)
    picked = _sandbox_species(options, drawn) if options.sandbox else drawn[:2]  # SANDBOX-06: the sandbox can choose them
    state.species = [SpeciesSlot(species=s, board=species.new_board(s)) for s in picked]

    # gold scoring tiles: random side up (SETUP-19)
    state.gold_tiles = [GoldTile(tile=t, side=rng.choice(state, ["A", "B"])) for t in GOLD_TILE_NAMES]

    # tech stacks: 12 stacks, each 4 tiles shuffled, a 2-point tile on top (SETUP-16)
    for cat in TECH_CATEGORIES:
        for glyph in GLYPHS:
            state.tech_stacks.append(TechStack(category=cat, glyph=glyph, tiles=rng.shuffled(state, list(BONUS_ORDER))))

    # neutral milestones (SETUP-20): 2 markers at each of 20 and 30 for 2 players, 1 each for 3 players, none for 4
    per = {1: 2, 2: 2, 3: 1, 4: 0}[n]
    state.neutral_markers = {"20": per, "30": per}

    # planets
    pdata = tables.planets()["planets"]
    for name in PLANET_ORDER:
        slots = len(pdata[name.upper()]["first_land_data"])
        state.planets[name] = PlanetState(first_land_data_taken=[False] * slots, first_land_owners=[None] * slots)

    # deck
    deck_ids = [
        cid
        for cid, c in tables.cards().items()
        if c["deck"] == "base" or (c["deck"] == "promo" and options.promo_cards) or (c["deck"] == "expansion" and options.expansion)
    ]
    deck_ids.sort(key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, x))  # fixed order before the shuffle
    state.deck = rng.shuffled(state, deck_ids)
    state.card_row = [state.deck.pop() for _ in range(3)]
    # end-of-round stacks: dealt face down from the main deck at setup (A-003), 1 more card than players each, rounds 1 to 4
    for r in range(4):  # EXP-ORG-03: with organizations only the stacks of rounds 2 to 4 are prepared
        skip = options.organizations and r == 0
        state.end_of_round_stacks.append([] if skip else [state.deck.pop() for _ in range(n + 1)])

    # players (SETUP-30 to SETUP-38)
    for i in range(n):
        is_rival = solo and i == 1
        p = PlayerState(index=i, color=COLORS[i], credits=0 if is_rival else 4, energy=0 if is_rival else 3, publicity=4)
        if not is_rival and not options.organizations:  # the rival has no hand and no resources (SOLO-10); organizations deal 4 cards below
            p.hand = [state.deck.pop() for _ in range(5)]
        state.players.append(p)

    state.start_player = rng.below(state, n)
    state.current_player = state.start_player
    for rank in range(n):  # starting scores 1, 2, 3, 4 by turn order (SETUP-32)
        state.players[(state.start_player + rank) % n].score = rank + 1

    if options.organizations:  # EXP-ORG-03, EXP-ORG-04: organizations and quick start cards instead of the income card
        orgs.deal(state, [(state.start_player + rank) % n for rank in range(n)])
        return state
    # each player tucks one card for income, in turn order: the engine waits for each choice (SETUP-36, FAQ-01)
    for rank in range(n):
        pl = (state.start_player + rank) % n
        if not (solo and pl == 1):
            state.pending.append(Decision(kind="setup_tuck", player=pl))
    if solo:
        rival.setup_solo(state, options.difficulty)
    return state
