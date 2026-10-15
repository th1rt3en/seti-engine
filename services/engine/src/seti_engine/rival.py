"""The solo rival: its resources, its action deck and the procedures of every action card.

Spec: solo.md (SOLO-01 to SOLO-20, SOLO-ALIEN-01 to SOLO-ALIEN-04), solo-rival-cards.md (SOLO-RIVAL-01 to SOLO-RIVAL-11), ambiguities A-002,
A-010 to A-014 and the proposals A-023 to A-025. The rival is the second entry of `GameState.players`; the human player is the first.
It takes its turn by itself inside the engine's turn loop, so the rival never waits for a decision.
"""

from __future__ import annotations

from typing import Any

from . import arkhos, cards, effects, objectives, rewards, rng, solar, species, tables, techs
from .models import GameState, PlayerState, Probe, RivalState

Events = list[dict[str, Any]]
TRACK = [
    "blue-dot",
    "blue-link",
    "blue-branch",
    "blue-cross",
    "pink-dot",
    "pink-link",
    "pink-branch",
    "pink-cross",
    "orange-dot",
    "orange-link",
    "orange-branch",
    "orange-cross",
]  # SOLO-DATA-11, clockwise; the growth icon lies between the last and the first
TRACK_CATEGORY = {"blue": "computer", "pink": "telescope", "orange": "probe"}
ADVANCED = [f"S.{i}" for i in range(5, 15)]  # A-010
SPECIES_CARD = {
    "mascamites": "S.15",
    "anomalies": "S.16",
    "oumuamua": "S.17",
    "centaurians": "S.18",
    "exertians": "S.19",
    "glyphids": "SE.2",  # the species cards of the expansion (A-033)
    "arkhos": "SE.3",
    "amoeba": "SE.4",
}
COMPUTER_SPACES = 6
COMPUTER_PUBLICITY = 2  # the second space gives 1 publicity (SOLO-DATA-12)
COMPUTER_PROGRESS = 4  # the fourth gives 4 progress
MOON_ORDER = {"jupiter": ["Callisto", "Ganymede", "Europa", "Io"], "saturn": ["Titan", "Enceladus"]}  # left to right (A-024, ruled)
TECH_BONUS_EXCLUDED = ("launch", "data")  # SOLO-18: never the free launch nor the 2 data of a tech
EXPANSION_START_CARD = "SE.1"  # EXP-SOLO-02 (the card prints "S.1"; the id differs from the base S.1)
RIVAL_MESSAGE_RESERVE = 2  # the leftover message tiles (SOLO-ALIEN-02)


def rv(s: GameState) -> RivalState:
    assert s.rival is not None
    return s.rival


def player(s: GameState) -> PlayerState:
    return s.players[rv(s).index]


def is_rival(s: GameState, index: int) -> bool:
    return s.rival is not None and s.rival.index == index


# ---------------------------------------------------------------------------------------------------------------------------------
# setup (SOLO-02 to SOLO-05)
# ---------------------------------------------------------------------------------------------------------------------------------


def setup_solo(s: GameState, difficulty: int) -> None:
    board = next(b for b in tables.solo_boards()["boards"] if difficulty in b["stars"])
    deck = rng.shuffled(s, ["S.1", "S.2", "S.3", "S.4"])
    if s.options.expansion:  # EXP-SOLO-02: the extra starting card is shuffled into the starting deck
        deck = rng.shuffled(s, [*deck, EXPANSION_START_CARD])
    advanced = rng.shuffled(s, list(ADVANCED))
    if difficulty >= 3:  # SOLO-05: one random advanced card goes into the starting deck
        deck = rng.shuffled(s, [*deck, advanced.pop(0)])
    s.rival = RivalState(index=1, progress=TRACK.index(board["start_space"]), deck=deck, advanced=advanced)
    objectives.setup(s, difficulty)


def reshuffle(s: GameState) -> None:
    """A-023 (ruled): when the rival passes, its used action cards are shuffled back into its deck for the next round."""
    r = rv(s)
    r.deck = rng.shuffled(s, [*r.deck, *r.used])
    r.used = []


# ---------------------------------------------------------------------------------------------------------------------------------
# resources (SOLO-10 to SOLO-17)
# ---------------------------------------------------------------------------------------------------------------------------------


def advance(s: GameState, n: int, events: Events | None = None) -> None:
    """SOLO-13, SOLO-12: move clockwise; crossing the growth icon adds a random advanced card on top of the deck."""
    r = rv(s)
    for _ in range(n):
        r.progress = (r.progress + 1) % len(TRACK)
        if r.progress == 0 and r.advanced:  # A-012: with none left, nothing happens
            r.deck.insert(0, r.advanced.pop(0))
            if events is not None:
                events.append({"type": "rival_grows"})
        elif r.progress == 0 and s.options.expansion:  # EXP-SOLO-07: no advanced card left to gain, so one more advance instead
            r.progress = 1


def gain_vp(s: GameState, n: int, events: Events | None = None) -> None:
    effects.gain_score(s, player(s), n)


def gain_data(s: GameState, n: int = 1) -> None:
    """SOLO-17: data goes into the computer first; a covered space pays its benefit; then the unlimited pool."""
    r, p = rv(s), player(s)
    for _ in range(n):
        if r.computer < COMPUTER_SPACES:
            r.computer += 1
            if r.computer == COMPUTER_PUBLICITY:
                effects.gain_publicity(s, p)
            elif r.computer == 4:
                advance(s, COMPUTER_PROGRESS)
        else:
            p.data_pool += 1


def grant(s: GameState, rws: list[dict[str, Any]], events: Events, planet: str | None = None, slot: int | None = None) -> None:
    """What the rival does with rewards: no credits, energy or cards (they become progress), no choices (SOLO-10, SOLO-11)."""
    p = player(s)
    for r in rws:
        t, n = r["t"], r.get("n", 1)
        if t == "vp":
            gain_vp(s, n, events)
        elif t == "publicity":
            effects.gain_publicity(s, p, n)
        elif t == "data":
            gain_data(s, n)
        elif t in ("energy", "credit", "card_any", "card_random", "alien_card"):
            advance(s, n, events)  # one space for each credit, energy and card gained
        elif t == "tuck":
            advance(s, 4 * n, events)  # SOLO-11
        elif t == "exofossil":
            species.gain_exofossil(s, p, n)
        elif t == "trace":
            for _ in range(n):
                trace(s, r["kind"], events)
        elif t == "signal_planet":
            assert planet is not None
            pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
            assert pos is not None
            for _ in range(n):
                rewards.mark_signal(s, p, pos[1], events, allow_tile=False)
        elif t == "signal_color":
            for _ in range(n):
                _signal(s, rewards.sectors_of_color(s, r["color"]), events)
        elif t in ("signal_any",):
            for _ in range(n):
                _signal(s, list(range(len(s.sectors))), events)
        elif t == "signal_oumuamua":  # SOLO-ALIEN-01: always on the tile
            for _ in range(n):
                species.mark_tile(s, p, events)
        elif t == "signal_token":
            advance(s, n, events)  # EXP-GLY-08: a signal token is an advance for the rival
        elif t in ("explore_minor", "explore_major"):
            for _ in range(n):
                arkhos.explore(s, p, t.removeprefix("explore_"), events)
        elif t == "explore":
            arkhos.explore(s, p, r["level"], events)
        elif t in (
            "move",
            "launch",
            "exofossil_pay",
            "sample_peek",
            "organelle",
            "organelles",
            "glyph_space",
            "glyph_resource",
            "scan_free",
            "research",
            "vp_empty_species_space",
        ):
            continue  # nothing for the rival


# ---------------------------------------------------------------------------------------------------------------------------------
# choices (SOLO-RIVAL-02, SOLO-RIVAL-11, SOLO-15)
# ---------------------------------------------------------------------------------------------------------------------------------


def pick(s: GameState, options: list[Any]) -> Any:
    """The decision arrow: the leftmost option when it points left, the rightmost when it points right (SOLO-RIVAL-02)."""
    return options[0] if rv(s).arrow == "left" else options[-1]


def _pick_sector(s: GameState, candidates: list[int]) -> int:
    """SOLO-RIVAL-08: win the sector, else score the second marker, else the sector with the most markers; ties favor the bigger sector."""
    me = rv(s).index

    def wins(i: int) -> bool:
        sec = s.sectors[i]
        return sec.data_remaining == 1 and len(sec.markers) < sec.capacity and rewards._ranking([*sec.markers, me])[0] == me

    def second(i: int) -> bool:
        return len(s.sectors[i].markers) == 1 and s.sectors[i].capacity > 1

    for rule in (wins, second):
        pool = [i for i in candidates if rule(i)]
        if pool:
            return max(pool, key=lambda i: (s.sectors[i].capacity, -i))
    return max(candidates, key=lambda i: (s.sectors[i].markers.count(me), s.sectors[i].capacity, -i))


def _signal(s: GameState, candidates: list[int], events: Events) -> None:
    rewards.mark_signal(s, player(s), _pick_sector(s, candidates), events, allow_tile=False)


def trace(s: GameState, kind: str, events: Events, only_slot: int | None = None) -> None:
    """SOLO-RIVAL-11: the lowest available space of that color on either species; the overflow space only when the rest are full."""
    p = player(s)
    colors = list(rewards.TRACE_COLORS) if kind == "any" else [kind]
    options: list[tuple[int, int, dict[str, Any]]] = []
    for i, slot in enumerate(s.species):
        if only_slot not in (None, i):
            continue
        for c in colors:
            if not slot.discovered:
                if slot.discovery_spaces[rewards.TRACE_COLORS.index(c)] is None:
                    options.append((len(rewards.TRACE_COLORS) + 2, i, {"slot": i, "space": "discovery", "color": c}))  # below the board
                continue
            free = [
                m
                for m in species.board_moves(s, p, i, (c,))
                if m["space"] == "board" and _rival_can_pay(s, slot.species, c, m["index"]) and _rival_wants(s, i, c, m["index"])
            ]
            if free:
                k = max(m["index"] for m in free)
                options.append((k, i, {"slot": i, "space": "board", "color": c, "index": k}))
    if options:
        lowest = max(o[0] for o in options)
        best = [o for o in options if o[0] == lowest]
        arkhos_first = [o for o in best if s.species[o[1]].species == "arkhos"]
        best = arkhos_first or best  # EXP-ARK-08: with equally low spaces on both species the rival prefers Arkhos
        chosen = pick(s, sorted(best, key=lambda o: (o[1], colors.index(o[2]["color"]))))
        action = chosen[2]
    else:
        slots = [i for i in range(len(s.species)) if only_slot in (None, i)]
        action = {"slot": pick(s, slots), "space": "overflow", "color": colors[0]}
    rewards.place_trace(s, p, action, events)


def _rival_wants(s: GameState, slot_index: int, color: str, k: int) -> bool:
    """EXP-GLY-08: an upper space of the Glyphids board whose token is gone (it is empty) is ignored; EXP-AMO-06: Amoeba spaces that would
    give the bonuses of 1 organelle or none are ignored. (Spaces of Arkhos that the rival cannot reach are left out by
    `species.board_moves`, EXP-ARK-08.)"""
    slot = s.species[slot_index]
    if slot.species == "glyphids":
        space = next(c for c in species.board_data("glyphids")["columns"] if c["color"] == color)["spaces"][k]
        return not space.get("well") or f"board:{color}:{k}" in slot.extra.get("tokens", {})
    if slot.species == "amoeba":
        from . import amoeba  # noqa: PLC0415 - amoeba imports rewards

        return len(amoeba.in_section(slot.extra, color)) >= 2
    return True


def _rival_can_pay(s: GameState, species_name: str, color: str, k: int) -> bool:
    """SOLO-ALIEN-02, SOLO-ALIEN-01: data costs only with a full computer and enough data left; exofossils only when it has enough."""
    space = next(c for c in species.board_data(species_name)["columns"] if c["color"] == color)["spaces"][k]
    p = player(s)
    for c in space.get("cost", []):
        if c["t"] == "data" and not (rv(s).computer == COMPUTER_SPACES and p.data_pool >= c["n"]):
            return False
        if c["t"] != "data" and p.exofossils < c["n"]:
            return False
    return True


# ---------------------------------------------------------------------------------------------------------------------------------
# milestones and discoveries (SOLO-14, SOLO-15, SOLO-ALIEN-*)
# ---------------------------------------------------------------------------------------------------------------------------------


def choose_gold(s: GameState, events: Events) -> None:
    """SOLO-15: only the first (best) slot of a tile; the leftmost or the rightmost tile that still has it, by the arrow."""
    free = [g for g in s.gold_tiles if not g.markers]
    if free:
        g = pick(s, free)
        g.markers.append(rv(s).index)
        player(s).gold_markers.append(g.tile)
        events.append({"type": "rival_gold", "tile": g.tile})


def choose_message(s: GameState, events: Events) -> None:
    """SOLO-ALIEN-02: the leftmost or rightmost reward still available, by the arrow."""
    i = species.message_slot(s)
    assert i is not None
    hexes = [m["hex"] for m in species.message_moves(s)]
    if hexes:
        species.reach_message(s, player(s), pick(s, hexes), events)


def on_discovery_markers(s: GameState, n: int, events: Events) -> None:
    """SOLO-10, SOLO-ALIEN-03: a card the rival would get for a discovery marker is a space of progress instead."""
    advance(s, n, events)


# ---------------------------------------------------------------------------------------------------------------------------------
# the rival's turn (SOLO-RIVAL-01, SOLO-19, SOLO-20)
# ---------------------------------------------------------------------------------------------------------------------------------


def take_turn(s: GameState, events: Events) -> None:
    r = rv(s)
    s.main_done = True
    if not r.deck:
        _pass(s, events)
        return
    cid = r.deck.pop(0)
    card = tables.rival_cards()[cid]
    r.arrow = card["dir"]
    events.append({"type": "rival_card", "card": cid})
    spent = cid
    for action in card["actions"]:
        if action["kind"] == "species_check":
            slot = action["discoveredSpecies"] - 1
            if slot < len(s.species) and s.species[slot].discovered:
                spent = SPECIES_CARD[s.species[slot].species]  # SOLO-RIVAL-09: the card is replaced by the species card
                _resolve_card(s, tables.rival_cards()[spent], events)
                break
            continue
        if _do(s, action, events):
            break
    r.used.append(spent)
    s.stage = "turn_end"


def _resolve_card(s: GameState, card: dict[str, Any], events: Events) -> None:
    rv(s).arrow = card["dir"]
    for action in card["actions"]:
        if _do(s, action, events):
            return


def _pass(s: GameState, events: Events) -> None:
    """SOLO-19: no cards left, the rival passes: it takes the top end-of-round card (1 progress); the first to pass rotates the system."""
    p = player(s)
    p.passed = True
    reshuffle(s)  # before the end-of-round card, whose progress may add an advanced card on top
    events.append({"type": "rival_pass"})
    if not s.first_pass_done:
        s.first_pass_done = True
        cards.rotate_everything(s, events)
    if s.round <= 4:
        stack = s.end_of_round_stacks[s.round - 1]
        if stack:
            s.discard.append(stack.pop())
            advance(s, 1, events)
        if len(stack) == 1 and all(q.passed for q in s.players):  # the last to pass discards the leftover (PASS-04)
            s.discard.append(stack.pop())
    s.stage = "turn_end"


def _do(s: GameState, a: dict[str, Any], events: Events) -> bool:
    k = a["kind"]
    if k == "analyze":
        return _analyze(s, a, events)
    if k == "launch":
        return _launch(s, a, events)
    if k == "tech":
        return _tech(s, a, events)
    if k == "probe":
        return _probe(s, a, events)
    if k == "telescope":
        _telescope(s, a, events)
        return True
    if k == "trace_advance":  # EXP-SOLO-02: a life trace of any color, then 1 advance for each gold star of the difficulty
        trace(s, a["color"], events)
        advance(s, s.options.difficulty, events)
        return True
    if k == "text":
        return _text(s, a, events)
    return False


# ---------------------------------------------------------------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------------------------------------------------------------


def _analyze(s: GameState, a: dict[str, Any], events: Events) -> bool:
    """SOLO-RIVAL-04."""
    r, p = rv(s), player(s)
    if r.computer < COMPUTER_SPACES:
        return False
    r.computer = 0
    gain_vp(s, a.get("cardBenefitVp", 0), events)
    trace(s, "blue", events)  # the life trace shown on its board
    advance(s, 1, events)  # and 1 energy
    while p.data_pool > 0 and r.computer < COMPUTER_SPACES:  # move the pool data into the computer, with each space's benefit
        p.data_pool -= 1
        gain_data(s, 1)
        if r.computer == COMPUTER_SPACES:
            break
    computer_techs = [t for t in r.techs if t.startswith("computer-")]
    if computer_techs:  # only one tech, even with several
        r.techs.remove(computer_techs[0])
        gain_vp(s, 3, events)
        advance(s, 1, events)
    events.append({"type": "rival_analyze"})
    return True


def _launch(s: GameState, a: dict[str, Any], events: Events) -> bool:
    """SOLO-RIVAL-05."""
    r, p = rv(s), player(s)
    earth = solar.earth(s)
    if any(pr.player == r.index and not pr.capsule and (pr.ring, pr.sector) == earth for pr in s.probes):
        return False
    s.probe_counter += 1
    s.probes.append(Probe(id=f"probe{s.probe_counter}", player=r.index, ring=earth[0], sector=earth[1]))
    effects.gain_publicity(s, p, a.get("publicity", 1))
    advance(s, a.get("progress", 0), events)
    events.append({"type": "rival_launch"})
    return True


def choose_tech(s: GameState) -> int | None:
    """SOLO-RIVAL-06: from the progress marker clockwise, the first tech whose stack has its 2-point tile; else the first available."""
    r = rv(s)
    order = [TRACK[(r.progress + k) % len(TRACK)] for k in range(len(TRACK))]
    available: list[int] = []
    for name in order:
        color, glyph = name.split("-")
        cat = TRACK_CATEGORY[color]
        for i, st in enumerate(s.tech_stacks):
            if st.category == cat and st.glyph == glyph and st.tiles and techs.tech_name(cat, glyph) not in r.techs:
                available.append(i)
    for i in available:
        if s.tech_stacks[i].two_point_tile:
            return i
    return available[0] if available else None


def _tech(s: GameState, a: dict[str, Any], events: Events) -> bool:
    r, p = rv(s), player(s)
    cost = a.get("costPublicity", 0)
    if p.publicity < cost or choose_tech(s) is None:
        return False
    p.publicity -= cost
    cards.rotate_everything(s, events)  # whenever the rival gains a tech, the solar system advances (rotation first, as for a player)
    idx = choose_tech(s)
    assert idx is not None
    st = s.tech_stacks[idx]
    tile = st.tiles.pop(0)
    if st.two_point_tile:
        st.two_point_tile = False
        gain_vp(s, 2, events)
    name = techs.tech_name(st.category, st.glyph)
    r.techs.append(name)
    extra = [x for x in techs._stack_extra(st.category, st.glyph) if x["t"] not in TECH_BONUS_EXCLUDED]
    grant(s, [techs.TILE_BONUS[tile], *extra], events)
    advance(s, a.get("progress", 0), events)
    events.append({"type": "rival_tech", "tech": name})
    return True


def _moves(s: GameState, start: tuple[int, int], movement: int) -> dict[tuple[int, int], int]:
    """Best publicity for each space the probe can reach with `movement` moves; leaving asteroids costs 1 extra (SOLO-RIVAL-07)."""
    best: dict[tuple[int, int], int] = {}

    def dfs(cell: tuple[int, int], left: int, pub: int) -> None:
        cost = 1 + (1 if solar.visible(s, *cell)[1] == "ASTEROID" else 0)
        if cost > left:
            return
        for nb in solar.adjacent(*cell):
            gain = 1 if solar.has_publicity_icon(solar.visible(s, *nb)[1]) else 0
            if pub + gain > best.get(nb, -1):
                best[nb] = pub + gain
            dfs(nb, left - cost, pub + gain)

    dfs(start, movement, 0)
    return best


def _probe(s: GameState, a: dict[str, Any], events: Events) -> bool:
    """SOLO-RIVAL-07."""
    r, p = rv(s), player(s)
    earth = solar.earth(s)
    probe = next((pr for pr in s.probes if pr.player == r.index and not pr.capsule and (pr.ring, pr.sector) == earth), None)
    if probe is None:
        return False
    plans: list[tuple[str, int]] = (
        [(x["planet"], x["movement"]) for x in a["movementByPlanet"]]
        if "movementByPlanet" in a
        else [(pl, a["movement"]) for pl in ([a["target"]] if "target" in a else a["planets"])]
    )
    glyph = species_slot_extra(s, "glyphids")
    for planet, movement in plans:
        pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
        if pos is None or planet not in s.planets:
            continue
        if a.get("glyphPlanets") and (glyph is None or f"planet:{planet}" not in glyph.get("tokens", {})):
            continue  # SE.2 (A-033): only the planets that still carry a glyph token
        reach = _moves(s, earth, movement)
        if pos in reach:
            effects.gain_publicity(s, p, reach[pos])
            s.probes.remove(probe)
            _arrive(s, planet, a, events)
            if a.get("takeSample"):  # S.15: the rival takes a sample from the planet it targeted (A-024)
                _take_sample(s, planet)
            return True
    return False


def species_slot_extra(s: GameState, name: str) -> dict[str, Any] | None:
    return next((sl.extra for sl in s.species if sl.species == name and sl.discovered), None)


def _arrive(s: GameState, planet: str, a: dict[str, Any], events: Events) -> None:
    """The probe becomes a lander on a moon, or the first orbiter or lander (SOLO-RIVAL-07, A-002)."""
    r, p = rv(s), player(s)
    st = s.planets[planet]
    info = tables.planet_info(planet)
    slot = species.oumuamua_slot(s) if planet == "oumuamua" else None
    probe_techs = [t for t in r.techs if t.startswith("probe-")]
    moons = [m for m in MOON_ORDER.get(planet, list(info["moons"])) if m in info["moons"] and m not in st.moon_landers]
    if a.get("moonLanding") and moons and probe_techs:
        moon = pick(s, moons)
        r.techs.remove(probe_techs[0])
        st.moon_landers[moon] = r.index
        p.landers[moon] = p.landers.get(moon, 0) + 1
        grant(s, info["moons"][moon], events, planet, slot)
        events.append({"type": "rival_land", "planet": planet, "moon": moon})
        return
    orbiter_first = st.first_orbiter is None
    lander_first = not st.first_land_data_taken[0]
    if a.get("landerOnly"):
        orbit = False
    elif orbiter_first != lander_first:
        orbit = orbiter_first
    else:
        orbit = a["preference"] == "orbiter"
    if orbit:
        st.orbiters.append(r.index)
        p.orbiters[planet] = p.orbiters.get(planet, 0) + 1
        if orbiter_first:
            st.first_orbiter = r.index
            grant(s, info["first_orbit"], events, planet, slot)
        grant(s, info["orbit"], events, planet, slot)
        events.append({"type": "rival_orbit", "planet": planet})
    else:
        st.landers.append(r.index)
        p.landers[planet] = p.landers.get(planet, 0) + 1
        if lander_first:
            st.first_land_data_taken[0] = True
            st.first_land_owners[0] = r.index
            gain_data(s, info["first_land_data"][0])
        grant(s, info["land"], events, planet, slot)
        events.append({"type": "rival_land", "planet": planet})


def _take_sample(s: GameState, planet: str) -> None:
    """S.15: a random sample of the planet goes face up on the species board; its reward is ignored."""
    i = species.mascamite_slot(s)
    tokens = species.samples_on(s, planet)
    if i is None or not tokens:
        return
    token = tokens[rng.below(s, len(tokens))]
    s.species[i].extra["samples"][planet].remove(token)
    s.species[i].extra["sample_spaces"].append(species.new_sample_space(token))


def _telescope(s: GameState, a: dict[str, Any], events: Events) -> None:
    """SOLO-RIVAL-08."""
    r, p = rv(s), player(s)
    earth_sector = solar.earth(s)[1]
    for _ in range(a["earthSignals"]):
        rewards.mark_signal(s, p, earth_sector, events, allow_tile=False)
    for _ in range(a.get("oumuamuaSignals", 0)):
        species.mark_tile(s, p, events)  # SOLO-ALIEN-01
    row_signals = a["cardRowSignals"]
    telescope = [t for t in r.techs if t.startswith("telescope-")]
    if telescope:  # an extra card-row signal for discarding a telescope tech
        r.techs.remove(telescope[0])
        row_signals += a.get("extraCardRowSignalWithTelescopeTech", 1)
    for _ in range(row_signals):
        if not s.card_row:
            break
        cid = pick(s, s.card_row)
        s.card_row.remove(cid)
        s.discard.append(cid)
        _signal(s, rewards.sectors_of_color(s, tables.cards()[cid]["sector"]), events)
    effects.refill_card_row(s)
    events.append({"type": "rival_telescope"})


def _text(s: GameState, a: dict[str, Any], events: Events) -> bool:
    """The special actions of the species cards (S.15 to S.19)."""
    r, p = rv(s), player(s)
    e = a["effect"]
    if e == "mascamites_sample":
        return False  # the sample is taken together with the landing of the same card (see _probe)
    if e == "anomalies_trace":
        from . import alien_steps  # noqa: PLC0415

        tok = alien_steps.next_anomaly(s)
        i = next((k for k, sl in enumerate(s.species) if sl.species == "anomalies"), None)
        if tok is None or i is None or species.anomaly_reward(s, s.species[i], tok["color"]) == r.index:
            return False
        trace(s, tok["color"], events, only_slot=i)
        gain_vp(s, 3, events)
        return True
    if e == "arkhos_breach":  # EXP-ARK-08: its only way to breach; the overflow space gives 3 VP (LIFE-01)
        i = next((k for k, sl in enumerate(s.species) if sl.species == "arkhos" and sl.discovered), None)
        if i is None:
            return False
        left = sorted(p.security)
        if left:
            color = left[rng.below(s, len(left))]
            r.breaching = True
            rewards.place_trace(s, p, {"slot": i, "space": "overflow", "color": color}, events)
            r.breaching = False
        for _ in range(2):
            arkhos.explore(s, p, "minor", events)
        return True
    if e == "amoeba_section":  # EXP-AMO-06 / A-033: a section with 3 organelles gives all its bonuses
        from . import amoeba  # noqa: PLC0415 - amoeba imports rewards

        i = amoeba.slot_index(s)
        if i is None:
            return False
        full = [c for c in ("pink", "yellow", "blue") if len(amoeba.in_section(s.species[i].extra, c)) == 3]
        if not full:
            return False
        amoeba.gain_section(s, p, pick(s, full), events)
        return True
    if e == "centaurians_countdown":
        if r.messages_in_reserve > 0 and not p.messages:
            r.messages_in_reserve -= 1
            species.add_message(s, p)
            advance(s, 1, events)
            return True
        return False
    if e == "exertians_danger_card":
        i = species.exertian_slot(s)
        if i is None:
            return False
        board = sum(m.count(r.index) for col in s.species[i].board.values() for m in col)
        if len(p.exertian_played) + board >= 5 or not s.species[i].deck:
            return False
        deck = s.species[i].deck
        p.exertian_played.append(deck.pop(rng.below(s, len(deck))))
        return True
    return False
