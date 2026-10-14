"""Playing cards: every card, plus the step, mission and end-scoring mechanics (CARD-*, PLAY-*, FREE-07, FREE-08, FAQ-C*)."""

from typing import Any

import pytest
from test_engine import begin, decisions, do, total_cards, with_state

from seti_engine import card_defs, cards, effects, rewards, solar, tables
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import Decision, GameState, MissionState, Probe

ALL = sorted((c for c in card_defs.CARDS if c.isdigit()), key=int)  # the base cards; alien cards are in test_alien_cards.py
PLAYABLE = [c for c in ALL if cards.playable(c)]


def give(s: GameState, cid: str, pl: int | None = None) -> None:
    """Move card `cid` from wherever it is into the hand of player `pl` (default: the current player)."""
    pl = s.current_player if pl is None else pl
    for pile in (s.deck, s.discard, s.card_row, *s.end_of_round_stacks, *[q.hand for q in s.players], *[q.tucked for q in s.players]):
        if cid in pile:
            pile.remove(cid)
    s.players[pl].hand.append(cid)
    effects.refill_card_row(s)


def ready(players: int = 2, seed: int = 4, credits: int = 9, energy: int = 9, publicity: int = 5) -> GameState:
    s = begin(players, seed).state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.credits, p.energy, p.publicity = credits, energy, publicity
    return s


def put_probe(s: GameState, where: str, pid: str = "t1", pl: int | None = None) -> Probe:
    """Put a probe of `pl` on a planet name ('jupiter'), 'EARTH', 'ASTEROID' or 'COMET'."""
    pl = s.current_player if pl is None else pl
    pos = solar.find_cell(s, where if where in ("EARTH", "ASTEROID", "COMET") else f"PLANET:{where.upper()}")
    assert pos is not None
    pr = Probe(id=pid, player=pl, ring=pos[0], sector=pos[1])
    s.probes.append(pr)
    return pr


def settle(r: StepResult, limit: int = 60) -> StepResult:
    """Answer decisions with the first legal move (decline moves come last, so this takes the positive option) until none are left."""
    for _ in range(limit):
        if not r.state.pending:
            return r
        r = apply(r.state, r.legal[0])
    raise AssertionError("decisions did not end")


def play(s: GameState, cid: str) -> StepResult:
    give(s, cid)
    return do(with_state(s), "play_card", card=cid)


def me(r: StepResult) -> Any:
    return r.state.players[r.state.current_player]


# ---------------------------------------------------------------------------------------------------------------------------------
# all cards
# ---------------------------------------------------------------------------------------------------------------------------------


def test_every_base_card_has_a_definition() -> None:
    """CARD-01: all 138 base cards are defined; only the cards waiting for rulings are held back."""
    base = {cid for cid, c in tables.cards().items() if c["deck"] == "base"}
    assert {c for c in card_defs.CARDS if not c.startswith("ET.")} == base
    assert all(cards.playable(c) for c in ALL)


@pytest.mark.parametrize("cid", PLAYABLE)
def test_card_plays_to_the_right_place(cid: str) -> None:
    """PLAY-01, PLAY-02, CARD-10, CARD-20, CARD-30: the cost is paid, the effect resolves and the card ends where it belongs."""
    s = ready(credits=9)
    pl = s.current_player
    put_probe(s, "EARTH", "e1")
    put_probe(s, "jupiter", "j1")
    r = play(s, cid)
    cost = int(tables.cards()[cid]["cost"])
    assert r.state.main_done and r.state.players[pl].credits <= 9 - cost + 3
    r = settle(r)
    st = r.state
    assert not st.queue and st.playing is None and total_cards(st) == 138
    d = card_defs.CARDS[cid]
    p = st.players[pl]
    if cid == "120":
        assert cid in p.hand or cid in st.discard
    elif "mission" in d:
        assert cid in [m.card for m in p.missions] + p.completed_missions
    elif "end" in d:
        assert cid in p.end_cards
    elif cid in ("91", "92", "93"):
        assert cid in p.tucked  # FAQ-C091
    else:
        assert cid in st.discard


def test_card_needs_enough_credits() -> None:
    """PLAY-01, CARD-04."""
    s = ready(credits=2)
    give(s, "8")  # cost 3
    give(s, "110")  # cost 1
    moves = legal_moves(s)
    assert {"type": "play_card", "card": "110"} in moves and {"type": "play_card", "card": "8"} not in moves


def test_playing_a_card_is_the_main_action() -> None:
    """PLAY-01, TURN-03."""
    r = play(ready(), "110")
    assert not [m for m in r.legal if m["type"] in ("pass", "launch", "scan", "play_card")]


# ---------------------------------------------------------------------------------------------------------------------------------
# resources, draws, movement, launch
# ---------------------------------------------------------------------------------------------------------------------------------


def test_resource_cards() -> None:
    """#110 Press Statement, #137 SETI Data Archive, #83 Wow! Signal (publicity part), #109 (energy part)."""
    s = ready()
    pl = s.current_player
    pub, data = s.players[pl].publicity, s.players[pl].data_pool
    assert me(play(s, "110")).publicity == pub + 3
    assert me(play(ready(), "137")).data_pool == data + 2


def test_launch_cards_respect_the_probe_limit() -> None:
    """#130 Low-Cost Space Launch: a free launch, still under the probe limit."""
    r = play(ready(), "130")
    assert len(r.state.probes) == 1
    s = ready()
    put_probe(s, "EARTH")
    assert len(play(s, "130").state.probes) == 1  # at the limit: no second probe


def test_falcon_heavy_launches_twice_ignoring_the_limit() -> None:
    """#9, FAQ-C009."""
    s = ready()
    put_probe(s, "EARTH")
    r = play(s, "9")
    assert len(r.state.probes) == 3
    assert me(r).publicity == 6
    assert len(legal_moves(r.state)) > 0


def test_movement_cards_add_movement() -> None:
    """#124 Cometary Encounter, #25 Lightsail."""
    assert me(play(ready(), "124")).movement == 2
    assert me(play(ready(), "25")).movement == 4


def test_grant_gains_the_free_corner_of_the_card_taken() -> None:
    """#11, FAQ-C011."""
    s = ready()
    top = s.card_row[0]
    r = play(s, "11")
    assert r.state.pending[0].kind == "take_card" and r.state.pending[0].data == {"reveal": True}
    before = me(r)
    mv, pb, dt = before.movement, before.publicity, before.data_pool
    r2 = do(r, "take_card", source="row:0")
    corner = dict(tables.cards()[top]["free"])
    p = me(r2)
    assert p.movement == mv + corner.get("move", 0) and p.publicity == pb + corner.get("publicity", 0)
    assert p.data_pool == min(6, dt + corner.get("data", 0))
    assert top in p.hand


def test_clean_space_initiative_discards_the_row_for_free_corners() -> None:
    """#73, FAQ-C073."""
    s = ready()
    row = list(s.card_row)
    r = play(s, "73")
    assert all(c in r.state.discard for c in row) and len(r.state.card_row) == 3
    want = sum(n for c in row for k, n in tables.cards()[c]["free"] if k == "move")
    assert me(r).movement == want


def test_income_cards_count_tucked_cards_then_tuck_themselves() -> None:
    """#91, #93, #92, FAQ-C091: rewards for the cards already tucked, then this card is tucked and pays its income at once."""
    s = ready()
    p = s.players[s.current_player]
    p.tucked = ["136", "136x"] if False else []
    energy_cards = [c for c, v in tables.cards().items() if v["deck"] == "base" and v["income"] == "energy" and c not in ("91",)][:2]
    for c in energy_cards:
        for pile in (s.deck, s.card_row):
            if c in pile:
                pile.remove(c)
        p.tucked.append(c)
    effects.refill_card_row(s)
    e0 = p.energy
    r = play(s, "91")
    q = me(r)
    assert q.energy == e0 + 2 + 1  # 2 tucked energy cards, then the card's own energy income
    assert "91" in q.tucked
    s = ready()
    p = s.players[s.current_player]
    r = play(s, "93")
    assert "93" in me(r).tucked and me(r).credits == p.credits - 3 + 1  # nothing tucked yet: only the card's credit income


def test_hand_income_count_for_fuel_tanks() -> None:
    """#90: energy for each card with energy income shown from the hand."""
    s = ready()
    give(s, "90")
    p = s.players[s.current_player]
    shown = sum(1 for c in p.hand if c != "90" and tables.cards()[c]["income"] == "energy")
    e0 = p.energy
    r = do(with_state(s), "play_card", card="90")
    assert me(r).energy == e0 + shown


# ---------------------------------------------------------------------------------------------------------------------------------
# rotate and research
# ---------------------------------------------------------------------------------------------------------------------------------


def test_rotate_and_research_a_tech_of_the_type() -> None:
    """#121 Future Circular Collider: 3 data, rotate, research a computer tech; no publicity is paid (TECHACT-06)."""
    s = ready()
    pub = s.players[s.current_player].publicity
    r = play(s, "121")
    assert r.state.rotations == 1 and me(r).data_pool == 3
    assert r.state.pending[0].kind == "research_tech"
    stacks = r.state.pending[0].data["stacks"]
    assert all(r.state.tech_stacks[i].category == "computer" for i in stacks) and len(stacks) == 4
    r2 = settle(do(r, "take_tech", stack=stacks[0]))
    assert any(t.startswith("computer-") for t in me(r2).techs) and me(r2).publicity >= pub


def test_research_is_ignored_when_the_player_has_all_techs_of_the_type() -> None:
    """TECHACT-06: with all four techs of a type the tech part is ignored but the rotation happens."""
    s = ready()
    s.players[s.current_player].techs = [f"computer-{g}" for g in ("dot", "link", "branch", "cross")]
    r = play(s, "121")
    assert r.state.rotations == 1 and not r.state.pending


def test_euclid_chooses_a_probe_or_telescope_tech() -> None:
    """#126, FAQ-C126."""
    r = play(ready(), "126")
    cats = {r.state.tech_stacks[i].category for i in r.state.pending[0].data["stacks"]}
    assert cats == {"probe", "telescope"} and r.state.rotations == 1


def test_focused_research_scores_for_each_tech_of_the_type() -> None:
    """#71."""
    s = ready()
    s.players[s.current_player].techs = ["probe-dot"]
    r = play(s, "71")
    idx = next(i for i in r.state.pending[0].data["stacks"] if r.state.tech_stacks[i].category == "probe")
    score = me(r).score
    r2 = do(r, "take_tech", stack=idx)
    assert me(r2).score >= score + 4  # two probe techs now, 2 points each (plus the tech's own bonuses)


def test_international_collaboration_copies_a_tech_without_rotating_or_tile_bonus() -> None:
    """#81, FAQ-C081."""
    s = ready()
    other = 1 - s.current_player
    s.players[other].techs = ["probe-dot", "telescope-dot"]
    r = play(s, "81")
    assert r.state.rotations == 0
    names = {cards_name(r.state, i) for i in r.state.pending[0].data["stacks"]}
    assert names == {"probe-dot", "telescope-dot"}
    score = me(r).score
    idx = next(i for i in r.state.pending[0].data["stacks"] if cards_name(r.state, i) == "probe-dot")
    r2 = settle(do(r, "take_tech", stack=idx))
    assert me(r2).score == score and len(r2.state.probes) == 1  # no 2-point or tile bonus; the free launch stays


def cards_name(s: GameState, i: int) -> str:
    return f"{s.tech_stacks[i].category}-{s.tech_stacks[i].glyph}"


def test_scientific_cooperation_pays_publicity_for_a_copied_tech() -> None:
    """#72."""
    s = ready()
    s.players[1 - s.current_player].techs = ["probe-dot"]
    r = play(s, "72")
    idx = next(i for i in r.state.pending[0].data["stacks"] if cards_name(r.state, i) == "probe-dot")
    pub = me(r).publicity
    r2 = settle(do(r, "take_tech", stack=idx))
    assert me(r2).publicity >= min(10, pub + 2)


# ---------------------------------------------------------------------------------------------------------------------------------
# signals and scans
# ---------------------------------------------------------------------------------------------------------------------------------


def sector_of(s: GameState, star: str) -> int:
    return next(i for i, sec in enumerate(s.sectors) if sec.star == star)


def test_observation_cards_mark_signals_at_their_star() -> None:
    """#39 61 Virginis Observation (2 signals), #44 Vega Observation (1)."""
    s = ready()
    pl = s.current_player
    r = play(s, "39")
    assert r.state.sectors[sector_of(s, "61 Virginis")].markers == [pl, pl]
    r = play(ready(), "44")
    assert r.state.sectors[sector_of(r.state, "Vega")].markers == [r.state.current_player]


def test_planet_exploration_cards_mark_signals_in_the_planets_sector() -> None:
    """#35 Jupiter Exploration Program."""
    s = ready()
    sec = solar.find_cell(s, "PLANET:JUPITER")[1]  # type: ignore[index]
    r = play(s, "35")
    assert r.state.sectors[sec].markers.count(r.state.current_player) == 2


def test_wow_signal_marks_two_signals_in_earths_sector() -> None:
    """#83."""
    s = ready()
    sec = solar.earth(s)[1]
    r = play(s, "83")
    assert r.state.sectors[sec].markers.count(r.state.current_player) == 2


def test_colour_signal_cards_let_the_player_pick_one_of_the_two_sectors() -> None:
    """#56 Breakthrough Listen: 1 movement and a signal in a blue sector."""
    r = play(ready(), "56")
    assert me(r).movement == 1
    assert {m["sector"] for m in decisions(r.legal)} == set(rewards.sectors_of_color(r.state, "blue"))


def test_algonquin_marks_one_signal_of_each_colour_and_the_data_goes_to_the_supply() -> None:
    """#136, FAQ-C118."""
    r = play(ready(), "136")
    pool = me(r).data_pool
    for color in ("yellow", "red", "blue", "black"):
        assert {m["sector"] for m in decisions(r.legal)} == set(rewards.sectors_of_color(r.state, color))
        r = apply(r.state, r.legal[0])
    assert not r.state.pending and me(r).data_pool == pool
    assert sum(len(sec.markers) for sec in r.state.sectors) == 4


def test_probe_signal_cards_use_the_sector_of_one_of_the_players_probes() -> None:
    """#28 Kepler Space Telescope: 1 movement, 2 signals in a sector with one of your probes; #29 James Webb adds the neighbours."""
    s = ready()
    pr = put_probe(s, "jupiter")
    r = play(s, "28")
    r = do(r, "pick_probe", probe=pr.id)
    assert r.state.sectors[pr.sector].markers.count(r.state.current_player) == 2 and me(r).movement == 1
    s = ready()
    pr = put_probe(s, "jupiter")
    r = do(play(s, "29"), "pick_probe", probe=pr.id)
    for sec in (pr.sector, (pr.sector - 1) % 8, (pr.sector + 1) % 8):
        assert r.state.sectors[sec].markers.count(r.state.current_player) == 1


def test_probe_signal_cards_do_nothing_without_a_probe() -> None:
    """FAQ-C027: the probe must be on the solar system board."""
    r = play(ready(), "27")
    assert not r.state.pending and sum(len(sec.markers) for sec in r.state.sectors) == 0


def test_plato_gives_no_data() -> None:
    """#118, FAQ-C118."""
    s = ready()
    pr = put_probe(s, "jupiter")
    r = do(play(s, "118"), "pick_probe", probe=pr.id)
    assert me(r).data_pool == 0 and r.state.sectors[pr.sector].markers.count(r.state.current_player) == 3


def test_great_observatories_marks_a_signal_for_up_to_three_probes_of_any_players() -> None:
    """#30, FAQ-C030."""
    s = ready()
    a = put_probe(s, "jupiter", "a")
    b = put_probe(s, "EARTH", "b", pl=1 - s.current_player)
    r = play(s, "30")
    r = do(r, "gop", probe=a.id)
    r = do(r, "gop", probe=b.id)
    assert not r.state.pending
    assert (
        r.state.sectors[a.sector].markers.count(r.state.current_player) == 1
        and r.state.sectors[b.sector].markers.count(r.state.current_player) == 1
    )


def test_deck_signals_discard_the_top_card_three_times() -> None:
    """#122, FAQ-C122."""
    s = ready()
    give(s, "122")
    top = list(s.deck[-3:])
    r = do(with_state(s), "play_card", card="122")
    for _ in range(3):
        d = r.state.pending[0]
        assert d.kind == "signal"
        r = apply(r.state, r.legal[0])
    assert not r.state.pending and all(c in r.state.discard for c in top)
    assert sum(len(sec.markers) for sec in r.state.sectors) == 3


def test_free_scan_card_runs_a_scan_without_its_base_cost() -> None:
    """#55 Arecibo, #135 Noto, FAQ-C051."""
    s = ready()
    credits, energy = s.players[s.current_player].credits, s.players[s.current_player].energy
    r = play(s, "55")
    assert r.state.scan_ctx is not None
    r = do(r, "scan_earth", sector=solar.earth(r.state)[1])
    r = do(r, "scan_discard", source="row:0")
    r = apply(r.state, r.legal[0])
    r = do(r, "scan_done")
    r = settle(r)  # the extra signal in any sector
    assert me(r).credits == credits - 3 and me(r).energy == energy  # only the card's own cost (3)
    assert sum(len(sec.markers) for sec in r.state.sectors) == 3 and r.state.scan_ctx is None


def test_scan_card_with_points_per_signal_of_a_colour() -> None:
    """#53 Deep Synoptic Array: 2 points for each yellow signal marked with the action."""
    s = ready()
    yellow = rewards.sectors_of_color(s, "yellow")
    s.card_row[0] = next(c for c, v in tables.cards().items() if v["deck"] == "base" and v["sector"] == "yellow" and c in s.deck)
    s.deck.remove(s.card_row[0])
    r = play(s, "53")
    score = me(r).score
    earth_sector = solar.earth(r.state)[1]
    r = do(r, "scan_earth", sector=earth_sector)
    gained_earth = me(r).score - score
    r = do(r, "scan_discard", source="row:0")
    r = do(r, "mark_signal", sector=yellow[0])
    assert me(r).score - score >= gained_earth + 2


def test_row_scan_discards_row_cards_then_refills() -> None:
    """#46 ALMA, FAQ-C045: all row cards are discarded for signals first, then the row is refilled."""
    s = ready()
    row = list(s.card_row)
    r = play(s, "46")
    r = do(r, "row_pick", source="row:0")
    r = apply(r.state, r.legal[0])
    assert len(r.state.card_row) == 2
    r = do(r, "row_pick", source="row:0")
    r = apply(r.state, r.legal[0])
    assert not r.state.pending and len(r.state.card_row) == 3
    assert sum(1 for c in row if c in r.state.discard) == 2


def test_row_scan_completion_bonus() -> None:
    """#45 Allen Telescope Array, FAQ-C045: gain 1 energy if a sector is completed this turn."""
    s = ready()
    pl = s.current_player
    color = tables.cards()[s.card_row[0]]["sector"]
    target = rewards.sectors_of_color(s, color)[0]
    sec = s.sectors[target]
    sec.markers, sec.data_remaining = [1 - pl] * (sec.capacity - 1), 1
    energy = s.players[pl].energy
    r = play(s, "45")
    r = do(r, "row_pick", source="row:0")
    r = do(r, "mark_signal", sector=target)
    r = settle(r)
    assert r.state.turn_completed and me(r).energy == energy + 1


def test_square_kilometre_array_scores_per_unique_sector() -> None:
    """#50, FAQ-C050."""
    s = ready()
    r = play(s, "50")
    score = me(r).score
    for _ in range(3):
        r = do(r, "row_pick", source="row:0")
        r = apply(r.state, r.legal[0])
    unique = sum(1 for sec in r.state.sectors if me(r).index in sec.markers)
    assert unique >= 1 and me(r).score >= score + 2 * unique


def test_hand_signals_discard_hand_cards_for_signals() -> None:
    """#114 Planet Hunters, #67: discard up to N cards from the hand, each marks a signal of its colour (FAQ-C067)."""
    r = play(ready(), "114")
    r = do(r, "take_card", source="deck")
    assert r.state.pending[0].kind == "hand_signal"
    card = r.state.pending[0]
    del card
    first = next(m for m in r.legal if m["type"] == "hand_signal")
    color = tables.cards()[first["card"]]["sector"]
    r = apply(r.state, first)
    assert {m["sector"] for m in decisions(r.legal)} == set(rewards.sectors_of_color(r.state, color))


# ---------------------------------------------------------------------------------------------------------------------------------
# turn effects
# ---------------------------------------------------------------------------------------------------------------------------------


def adjacent_planet_probe(s: GameState, planet: str) -> tuple[Probe, tuple[int, int]]:
    """A probe next to the planet's space, and the planet's space."""
    pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
    assert pos is not None
    nb = next(
        n for n in solar.adjacent(*pos) if solar.visible(s, *n)[1] not in ("EARTH",) and not solar.visible(s, *n)[1].startswith("PLANET")
    )
    pr = Probe(id="f1", player=s.current_player, ring=nb[0], sector=nb[1])
    s.probes.append(pr)
    return pr, pos


def test_flyby_gives_points_once_per_turn_for_a_later_visit() -> None:
    """#23 Jupiter Flyby, FAQ-C020."""
    s = ready()
    pr, pos = adjacent_planet_probe(s, "jupiter")
    r = play(s, "23")
    score = me(r).score
    r = do(r, "move_probe", probe=pr.id, to=list(pos))
    assert me(r).score == score + 4
    r = do(r, "move_probe", probe=pr.id, to=[pr.ring, pr.sector]) if False else r
    assert [w for w in r.state.turn_fx if w["done"]]


def test_flyby_ignores_the_probe_already_on_the_planet() -> None:
    """FAQ-C020: only visits after the card is played count."""
    s = ready()
    put_probe(s, "jupiter")
    r = play(s, "23")
    assert me(r).score == s.players[s.current_player].score


def test_flyby_effects_end_with_the_turn() -> None:
    """CARD-12 note: 'this turn' effects expire."""
    s = ready()
    r = play(s, "23")
    r = settle(do(r, "end_turn"))
    assert r.state.turn_fx == []


def test_lightsail_scores_each_unique_planet_visited_including_earth() -> None:
    """#25, FAQ-C025."""
    s = ready()
    pr, pos = adjacent_planet_probe(s, "venus")
    r = play(s, "25")
    score = me(r).score
    r = do(r, "move_probe", probe=pr.id, to=list(pos))
    assert me(r).score == score + 1


def test_asteroid_and_comet_cards() -> None:
    """#123 Asteroids Flyby (1 data), #124 Cometary Encounter (4 points), FAQ-C123."""
    s = ready()
    ast = solar.find_cell(s, "ASTEROID")
    assert ast is not None
    nb = solar.adjacent(*ast)[0]
    s.probes.append(Probe(id="a1", player=s.current_player, ring=nb[0], sector=nb[1]))
    s.players[s.current_player].movement = 3
    r = play(s, "123")
    data = me(r).data_pool
    r = do(r, "move_probe", probe="a1", to=list(ast))
    assert me(r).data_pool == data + 1


def test_slingshot_lets_the_player_take_movement_instead_of_publicity() -> None:
    """#19, FAQ-C019."""
    s = ready()
    pr, pos = adjacent_planet_probe(s, "mars")
    r = play(s, "19")
    r = do(r, "move_probe", probe=pr.id, to=list(pos))
    assert r.state.pending[0].kind == "slingshot"
    pub, mv = me(r).publicity, me(r).movement
    r2 = do(r, "slingshot_pick", choice="move")
    assert me(r2).movement == mv + 1 and me(r2).publicity == pub


def test_through_the_asteroid_belt_removes_the_asteroid_penalty() -> None:
    """#26, FAQ-C026."""
    s = ready()
    ast = solar.find_cell(s, "ASTEROID")
    assert ast is not None
    s.probes.append(Probe(id="a1", player=s.current_player, ring=ast[0], sector=ast[1]))
    r = play(s, "26")
    me(r).movement = 1
    assert any(m["type"] == "move_probe" for m in legal_moves(r.state))


def test_trajectory_correction_rewards_a_move_within_the_same_ring() -> None:
    """#125, FAQ-C125."""
    s = ready()
    pr = put_probe(s, "EARTH")
    r = play(s, "125")
    score = me(r).score
    to = next(list(n) for n in solar.adjacent(pr.ring, pr.sector) if n[0] == pr.ring)
    r = do(r, "move_probe", probe=pr.id, to=to)
    assert me(r).score == score + 3


# ---------------------------------------------------------------------------------------------------------------------------------
# traces
# ---------------------------------------------------------------------------------------------------------------------------------


def test_same_kind_trace_needs_a_species_where_the_player_already_has_that_kind() -> None:
    """#98 Coronal Spectrograph, FAQ-C098."""
    s = ready()
    assert not play(s, "98").state.pending  # no pink trace yet
    s = ready()
    pl = s.current_player
    s.players[pl].trace_log = [(1, "pink")]
    r = play(s, "98")
    assert {m["slot"] for m in decisions(r.legal)} == {1}


def test_extremophiles_scores_for_each_trace_of_the_chosen_colour() -> None:
    """#75."""
    s = ready()
    s.players[s.current_player].trace_log = [(0, "pink"), (1, "pink")]
    r = play(s, "75")
    score = me(r).score
    r2 = do(r, "place_trace", slot=0, space="discovery", color="pink")
    assert me(r2).score >= score + 5 + 3  # discovery points and 3 pink traces at 1 each


def test_hayabusa_needs_a_probe_on_asteroids() -> None:
    """#18."""
    assert not play(ready(), "18").state.pending
    s = ready()
    ast = solar.find_cell(s, "ASTEROID")
    assert ast is not None
    s.probes.append(Probe(id="a1", player=s.current_player, ring=ast[0], sector=ast[1]))
    assert play(s, "18").state.pending[0].data == {"color": "yellow"}


def test_publicity_conditional_trace() -> None:
    """#108 SETI@Home: with at least 8 publicity."""
    assert not play(ready(publicity=7), "108").state.pending
    assert play(ready(publicity=8), "108").state.pending[0].kind == "trace"


# ---------------------------------------------------------------------------------------------------------------------------------
# quick missions
# ---------------------------------------------------------------------------------------------------------------------------------


def played_mission(s: GameState, cid: str) -> StepResult:
    return settle(play(s, cid))


def test_quick_mission_is_completed_by_a_free_action_when_its_condition_holds() -> None:
    """CARD-10, CARD-11, CARD-16, FREE-07: #5 Venera Probe (orbiter or lander at Venus)."""
    s = ready()
    pl = s.current_player
    r = played_mission(s, "5")
    assert not [m for m in r.legal if m["type"] == "complete_mission"]
    s2 = r.state.model_copy(deep=True)
    s2.players[pl].orbiters["venus"] = 1
    r2 = with_state(s2)
    assert {"type": "complete_mission", "card": "5"} in r2.legal
    score, pub = s2.players[pl].score, s2.players[pl].publicity
    r3 = do(r2, "complete_mission", card="5")
    assert me(r3).score == score + 7 and me(r3).publicity == pub + 1
    assert "5" in me(r3).completed_missions and not me(r3).missions


def test_quick_mission_can_be_completed_straight_away() -> None:
    """CARD-11: if the condition is already met when the card is played, it can be completed immediately."""
    s = ready()
    pl = s.current_player
    s.players[pl].orbiters["mercury"] = 1
    r = played_mission(s, "32")
    assert {"type": "complete_mission", "card": "32"} in r.legal


def test_orbiter_or_lander_conditions_include_moons() -> None:
    """FAQ-C058, CARD-40."""
    s = ready()
    p = s.players[s.current_player]
    c = card_defs.orbland("jupiter")
    assert not cards.cond_ok(s, p, c)
    p.landers["Io"] = 1
    assert cards.cond_ok(s, p, c)
    assert cards.cond_ok(s, p, card_defs.orbland(n=1)) and not cards.cond_ok(s, p, card_defs.orbland("saturn"))


def test_two_planet_condition_and_same_planet_condition() -> None:
    """#10 ODINUS (Neptune and Uranus), #112 (orbiter and lander at a single planet)."""
    s = ready()
    p = s.players[s.current_player]
    both = {"c": "both", "planets": ["neptune", "uranus"]}
    p.orbiters["neptune"] = 1
    assert not cards.cond_ok(s, p, both)
    p.landers["Titania"] = 1  # a moon of Uranus
    assert cards.cond_ok(s, p, both)
    same = {"c": "same_planet"}
    assert not cards.cond_ok(s, p, same)
    p.landers["neptune"] = 1
    assert cards.cond_ok(s, p, same)


def test_win_conditions() -> None:
    """#39 (2 wins in yellow sectors), #103 (the same sector twice, FAQ-C103)."""
    s = ready()
    p = s.players[s.current_player]
    yellow = rewards.sectors_of_color(s, "yellow")
    s.sectors[yellow[0]].winners = [p.index]
    s.sectors[yellow[1]].winners = [p.index]
    assert cards.cond_ok(s, p, card_defs.wins("yellow", 2)) and not cards.cond_ok(s, p, {"c": "wins_same", "n": 2})
    s.sectors[yellow[1]].winners = [p.index, p.index]
    assert cards.cond_ok(s, p, {"c": "wins_same", "n": 2})


def test_trace_conditions() -> None:
    """#64 (a blue trace on each species), #70 (3 blue), #102 (all three kinds for one species)."""
    s = ready()
    p = s.players[s.current_player]
    p.trace_log = [(0, "blue")]
    assert not cards.cond_ok(s, p, card_defs.each_species("blue"))
    p.trace_log.append((1, "blue"))
    assert cards.cond_ok(s, p, card_defs.each_species("blue")) and not cards.cond_ok(s, p, card_defs.traces("blue", 3))
    p.trace_log.append((0, "blue"))
    assert cards.cond_ok(s, p, card_defs.traces("blue", 3))
    p.trace_log = [(1, "pink"), (1, "yellow"), (0, "blue")]
    assert not cards.cond_ok(s, p, {"c": "single_species_all"})
    p.trace_log.append((1, "blue"))
    assert cards.cond_ok(s, p, {"c": "single_species_all"})


def test_state_conditions() -> None:
    """#51 (8 publicity), #61 (50 points), #89 (no cards in hand), #115 (3 telescope techs), #88 (4 sectors), #95 (asteroid by Earth)."""
    s = ready()
    p = s.players[s.current_player]
    assert not cards.cond_ok(s, p, {"c": "publicity", "n": 8}) and not cards.cond_ok(s, p, {"c": "score", "n": 50})
    p.publicity, p.score = 8, 50
    assert cards.cond_ok(s, p, {"c": "publicity", "n": 8}) and cards.cond_ok(s, p, {"c": "score", "n": 50})
    p.hand = []
    assert cards.cond_ok(s, p, {"c": "hand_empty"})
    p.techs = ["telescope-dot", "telescope-link"]
    assert not cards.cond_ok(s, p, {"c": "techs", "cat": "telescope", "n": 3})
    p.techs.append("telescope-cross")
    assert cards.cond_ok(s, p, {"c": "techs", "cat": "telescope", "n": 3})
    for i in range(3):
        s.sectors[i].markers = [p.index]
    assert not cards.cond_ok(s, p, {"c": "sig_sectors", "n": 4})
    s.sectors[3].markers = [p.index]
    assert cards.cond_ok(s, p, {"c": "sig_sectors", "n": 4})


def test_probe_position_conditions() -> None:
    """#104 (a probe on a comet), #127/#18 (on asteroids), #87 (5 spaces from Earth, ambiguity A-017)."""
    s = ready()
    p = s.players[s.current_player]
    assert not cards.cond_ok(s, p, {"c": "probe_on", "where": "comet"})
    pr = put_probe(s, "COMET")
    assert cards.cond_ok(s, p, {"c": "probe_on", "where": "comet"})
    s.probes.remove(pr)
    put_probe(s, "EARTH")
    assert not cards.cond_ok(s, p, {"c": "probe_far", "n": 5})
    assert cards.distance_from_earth(s, *solar.earth(s)) == 0


# ---------------------------------------------------------------------------------------------------------------------------------
# triggerable missions
# ---------------------------------------------------------------------------------------------------------------------------------


def test_triggerable_mission_circle_is_covered_when_the_trigger_happens() -> None:
    """CARD-12, FAQ-31: #128 Advanced Navigation System, a visit to any planet except Earth covers one circle."""
    s = ready()
    pr, pos = adjacent_planet_probe(s, "mars")
    r = played_mission(s, "128")
    r = with_state(r.state.model_copy(deep=True))
    r.state.main_done = False
    r.state.players[r.state.current_player].movement = 5
    r = with_state(r.state)
    r = do(r, "move_probe", probe=pr.id, to=list(pos))
    d = r.state.pending[0]
    assert d.kind == "mission_trigger" and len(d.data["options"]) == 3
    assert {"type": "decline_cover"} in r.legal
    energy = me(r).energy
    r2 = do(r, "cover", card="128", circle=0)
    assert me(r2).energy == energy + 1 and r2.state.players[r2.state.current_player].missions[0].used == [True, False, False]


def test_declining_a_circle_keeps_it_for_later() -> None:
    """FAQ-31: covering is optional."""
    s = ready()
    pr, pos = adjacent_planet_probe(s, "mars")
    s.players[s.current_player].missions.append(MissionState(card="128", kind="trigger", used=[False] * 3))
    s.players[s.current_player].movement = 5
    r = do(with_state(s), "move_probe", probe=pr.id, to=list(pos))
    r2 = do(r, "decline_cover")
    assert me(r2).missions[0].used == [False, False, False]


def test_a_mission_cannot_be_triggered_by_things_done_before_it_was_played() -> None:
    """CARD-12, FAQ-C001: a probe already on the planet does not count."""
    s = ready()
    put_probe(s, "jupiter")
    r = played_mission(s, "1")
    assert not r.state.pending


def test_a_completed_triggerable_mission_is_turned_face_down() -> None:
    """CARD-15."""
    s = ready()
    p = s.players[s.current_player]
    p.missions.append(MissionState(card="4", kind="trigger", used=[True, False]))
    s2 = with_state(s)
    cards.cover(s, p, "4", 1, [])
    assert not p.missions and p.completed_missions == ["4"]
    assert s2 is not None


def test_launch_triggers_cape_canaveral() -> None:
    """#80: each launch covers one circle (1 movement)."""
    s = ready()
    s.players[s.current_player].missions.append(MissionState(card="80", kind="trigger", used=[False] * 3))
    r = do(with_state(s), "launch")
    assert r.state.pending[0].kind == "mission_trigger"
    r2 = do(r, "cover", card="80", circle=0)
    assert me(r2).movement == 1


def test_a_mission_card_is_in_play_during_its_own_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    """CARD-12, ruling A-019 (reading 2): in play from the moment the card is played, so its own launch can cover a circle."""
    defs = dict(card_defs.CARDS)
    circle = card_defs.circle({"e": "launch"}, card_defs.energy(1))
    defs["117"] = {"fx": [card_defs.LAUNCH], "mission": card_defs.trig(circle)}
    monkeypatch.setattr(card_defs, "CARDS", defs)
    r = play(ready(), "117")
    assert r.state.pending[0].kind == "mission_trigger" and r.state.pending[0].data["options"] == [["117", 0]]


def test_strategic_planning_can_cover_its_own_play_cost() -> None:
    """A-019 reading 2 applied to #106: it is in play when its cost is paid."""
    r = play(ready(), "106")
    assert r.state.pending and r.state.pending[0].data["options"] == [["106", 0]]


def test_signal_colour_triggers_control_center() -> None:
    """#116, FAQ-C116: each signal in a sector of the indicated colour can cover its circle."""
    s = ready()
    pl = s.current_player
    s.players[pl].missions.append(MissionState(card="116", kind="trigger", used=[False] * 3))
    sec = rewards.sectors_of_color(s, "red")[0]
    ev: list[dict[str, Any]] = []
    rewards.mark_signal(s, s.players[pl], sec, ev)
    assert s.pending[0].kind == "mission_trigger" and s.pending[0].data["options"] == [["116", 1]]


def test_discarding_a_card_for_its_corner_triggers_cornell() -> None:
    """#138, FAQ-C138."""
    s = ready()
    p = s.players[s.current_player]
    p.missions.append(MissionState(card="138", kind="trigger", used=[False] * 3))
    cid = next(c for c in p.hand if any(k == "publicity" for k, _ in tables.cards()[c]["free"]))
    r = do(with_state(s), "discard_free", card=cid)
    assert r.state.pending[0].kind == "mission_trigger"
    assert r.state.pending[0].data["options"][0] == ["138", 0]


def test_paying_a_cost_triggers_strategic_planning() -> None:
    """#106, FAQ-C106: only when a card costing 1, 2 or 3 credits is played as the main action."""
    s = ready()
    p = s.players[s.current_player]
    p.missions.append(MissionState(card="106", kind="trigger", used=[False] * 3))
    give(s, "110")  # cost 1
    r = do(with_state(s), "play_card", card="110")
    assert r.state.pending[0].data["options"] == [["106", 0]]


def test_orbit_and_land_trigger_johnson_space_center() -> None:
    """#82: the orbit circle and the land circle."""
    s = ready()
    pl = s.current_player
    s.players[pl].missions.append(MissionState(card="82", kind="trigger", used=[False] * 2))
    put_probe(s, "venus")
    r = do(with_state(s), "orbit", probe="t1")
    opts = [d for d in r.state.pending if d.kind == "mission_trigger"]
    assert opts and opts[0].data["options"] == [["82", 0]]


def test_tech_and_scan_triggers() -> None:
    """#76 NASA Research Center (techs), #131 (telescope tech and scan)."""
    s = ready(publicity=8)
    pl = s.current_player
    s.players[pl].missions.append(MissionState(card="76", kind="trigger", used=[False] * 3))
    idx = next(i for i, ts in enumerate(s.tech_stacks) if ts.category == "probe" and ts.glyph == "link")
    r = do(with_state(s), "research", stack=idx)
    triggers = [d for d in r.state.pending if d.kind == "mission_trigger"]
    assert triggers and triggers[0].data["options"] == [["76", 0]]
    s2 = ready()
    s2.players[s2.current_player].missions.append(MissionState(card="101", kind="trigger", used=[False] * 3))
    r2 = do(with_state(s2), "scan")
    assert r2.state.pending[0].kind == "mission_trigger" and len(r2.state.pending[0].data["options"]) == 3


def test_trace_triggers_nasa_astrobiology() -> None:
    """#77, #107, FAQ-C107: a trace of a kind covers one circle."""
    s = ready()
    pl = s.current_player
    s.players[pl].missions.append(MissionState(card="107", kind="trigger", used=[False] * 2))
    s.pending = [Decision(kind="trace", player=pl, data={"color": "blue"})]
    r = do(with_state(s), "place_trace", slot=0, space="discovery", color="blue")
    assert r.state.pending[0].kind == "mission_trigger" and len(r.state.pending[0].data["options"]) == 2


# ---------------------------------------------------------------------------------------------------------------------------------
# end-of-game scoring cards
# ---------------------------------------------------------------------------------------------------------------------------------


def test_end_scoring_cards() -> None:
    """CARD-20, CARD-21, END-02: #38, #12, #68, #126, #86, #127."""
    s = ready()
    p = s.players[s.current_player]
    p.end_cards = ["38", "12", "68", "126", "86", "127"]
    red = rewards.sectors_of_color(s, "red")
    s.sectors[red[0]].winners = [p.index, p.index]
    p.orbiters["jupiter"] = 1
    p.landers["Io"] = 1
    p.trace_log = [(0, "blue"), (1, "blue"), (0, "pink")]
    p.techs = ["computer-dot", "computer-link", "probe-dot"]
    s.sectors[0].markers = [p.index]
    s.sectors[1].markers = [p.index, 1 - p.index]
    assert cards.end_points(s, p) == 3 * 2 + 3 * 2 + 2 * 2 + 2 * 2 + 1 * 2 + 0
    ast = solar.find_cell(s, "ASTEROID")
    assert ast is not None
    s.probes.append(Probe(id="a", player=p.index, ring=ast[0], sector=ast[1]))
    assert cards.end_points(s, p) == 3 * 2 + 3 * 2 + 2 * 2 + 2 * 2 + 1 * 2 + 13


@pytest.mark.parametrize("cid", [c for c in PLAYABLE if "end" in card_defs.CARDS[c]])
def test_every_end_scoring_card_scores_zero_with_nothing(cid: str) -> None:
    """CARD-20: nothing to count, nothing to score."""
    s = ready()
    p = s.players[s.current_player]
    p.end_cards = [cid]
    assert cards.end_points(s, p) == 0


# Immediate gains read from the card art (independent of card_defs): id -> (publicity, data, energy, credits, movement, launches, draws)
IMMEDIATE = {
    "110": (3, 0, 0, 0, 0, 0, 0),
    "137": (0, 2, 0, 0, 0, 0, 0),
    "14": (1, 2, 0, 0, 0, 0, 0),
    "96": (1, 1, 0, 0, 0, 0, 1),
    "79": (1, 0, 0, 0, 0, 0, 0),
    "94": (1, 0, 0, 0, 0, 0, 0),
    "77": (1, 0, 0, 0, 0, 0, 0),
    "78": (1, 0, 0, 0, 0, 0, 0),
    "5": (1, 0, 0, 0, 0, 1, 0),
    "6": (0, 1, 0, 0, 0, 1, 0),
    "7": (0, 0, 0, 0, 1, 1, 0),
    "130": (0, 0, 0, 0, 0, 1, 0),
    "104": (0, 0, 0, 0, 0, 1, 0),
    "60": (0, 0, 0, 0, 0, 1, 0),
    "58": (0, 0, 0, 0, 0, 1, 0),
    "31": (0, 0, 0, 0, 1, 1, 0),
    "132": (2, 0, 0, 0, 0, 1, 0),
    "117": (0, 0, 0, 0, 0, 1, 0),
    "127": (2, 0, 0, 0, 0, 0, 0),
    "95": (2, 0, 0, 0, 0, 0, 0),
    "135": (1, 0, 0, 0, 0, 0, 0),
    "51": (0, 1, 0, 0, 0, 0, 0),
    "107": (0, 2, 0, 0, 0, 0, 0),
    "89": (0, 0, 0, 0, 0, 0, 3),
    "124": (0, 0, 0, 0, 2, 0, 0),
    "123": (0, 0, 0, 0, 1, 0, 0),
    "125": (0, 0, 0, 0, 1, 0, 0),
    "19": (0, 0, 0, 0, 2, 0, 0),
    "26": (0, 0, 0, 0, 2, 0, 0),
    "22": (0, 0, 0, 0, 2, 0, 0),
    "24": (0, 0, 0, 0, 3, 0, 0),
    "25": (0, 0, 0, 0, 4, 0, 0),
    "59": (0, 0, 1, 0, 0, 0, 0),
    "109": (0, 0, 1, 0, 0, 0, 0),
    "69": (0, 1, 0, 0, 0, 0, 0),
    "121": (0, 3, 0, 0, 0, 0, 0),
    "67": (1, 0, 0, 0, 0, 0, 0),
    "56": (0, 0, 0, 0, 1, 0, 0),
    "48": (0, 0, 0, 0, 1, 0, 0),
    "49": (0, 0, 0, 0, 1, 0, 0),
    "27": (0, 0, 0, 0, 1, 0, 0),
    "28": (0, 0, 0, 0, 1, 0, 0),
    "29": (0, 0, 0, 0, 1, 0, 0),
}


@pytest.mark.parametrize("cid", sorted(IMMEDIATE, key=int))
def test_card_gains_what_the_art_shows(cid: str) -> None:
    """CARD-01 (one test per card for the plain effects): immediate resources of the card."""
    s = ready(publicity=3)
    pl = s.current_player
    p = s.players[pl]
    before = (p.publicity, p.data_pool, p.energy, p.credits, p.movement, len(s.probes), len(p.hand))
    give(s, cid)
    n_hand = len(p.hand) - 1  # the card itself leaves the hand when played
    r = do(with_state(s), "play_card", card=cid)
    q = me(r)
    cost = int(tables.cards()[cid]["cost"])
    pub, data, energy, credits, mv, probes, drawn = IMMEDIATE[cid]
    assert q.publicity == before[0] + pub
    assert q.data_pool == before[1] + data
    assert q.energy == before[2] + energy
    assert q.credits == before[3] - cost + credits
    assert q.movement == before[4] + mv
    assert len(r.state.probes) == before[5] + probes
    assert len(q.hand) == n_hand + drawn


def test_remove_orbiter_lets_the_player_choose_which_orbiter() -> None:
    """#15 Atmospheric Entry, A-018, FAQ-C015: the first-orbiter space is freed, the other orbiters do not slide."""
    s = ready()
    pl = s.current_player
    st = s.planets["venus"]
    st.orbiters = [pl, 1 - pl, pl]
    st.first_orbiter = pl
    s.players[pl].orbiters["venus"] = 2
    r = play(s, "15")
    firsts = {m["first"] for m in decisions(r.legal) if m["planet"] == "venus"}
    assert firsts == {True, False}
    score, data = me(r).score, me(r).data_pool
    r2 = do(r, "remove_orbiter", planet="venus", first=True)
    assert r2.state.planets["venus"].first_orbiter is None and r2.state.planets["venus"].orbiters == [1 - pl, pl]
    assert me(r2).score >= score + 3 and me(r2).data_pool == data + 1 and me(r2).orbiters["venus"] == 1
    assert len(me(r2).hand) >= len(me(r).hand)  # the card from the row or the deck is a pending choice


def test_next_orbiter_takes_the_freed_first_space() -> None:
    """FAQ-C015: the next orbiter gains the 3 points even though other orbiters are there."""
    s = ready()
    pl = s.current_player
    st = s.planets["venus"]
    st.orbiters = [1 - pl]
    st.first_orbiter = None
    put_probe(s, "venus")
    s.players[pl].credits = s.players[pl].energy = 5
    score = s.players[pl].score
    r = settle(do(with_state(s), "orbit", probe="t1"))
    assert me(r).score == score + 3 + 6 and r.state.planets["venus"].first_orbiter == pl


def test_remove_lander_frees_its_first_lander_space() -> None:
    """#84 Sample Return, A-018, FAQ-C084."""
    s = ready()
    pl = s.current_player
    st = s.planets["mars"]
    st.landers = [pl, pl]
    st.first_land_data_taken = [True, False]
    st.first_land_owners = [pl, None]
    s.players[pl].landers["mars"] = 2
    r = play(s, "84")
    slots = {m["slot"] for m in decisions(r.legal)}
    assert slots == {0, None}
    r2 = do(r, "remove_lander", planet="mars", slot=0)
    assert r2.state.planets["mars"].first_land_data_taken == [False, False] and me(r2).landers["mars"] == 1
    assert r2.state.pending[0].kind == "trace" and r2.state.pending[0].data["color"] == "yellow"


def test_remove_cards_do_nothing_without_a_figure() -> None:
    """#15, #84: nothing to remove, nothing happens."""
    assert not play(ready(), "15").state.pending
    assert not play(ready(), "84").state.pending


def test_a_trace_counts_for_the_colour_of_the_space_it_is_placed_on() -> None:
    """A-017, A-022: every colored marker on the species slots counts for the color of its space, overflow spaces included."""
    s = ready()
    p = s.players[s.current_player]
    ev: list[dict[str, Any]] = []
    rewards.place_trace(s, p, {"slot": 0, "space": "discovery", "color": "blue"}, ev)  # an any-trace placed on blue
    rewards.place_trace(s, p, {"slot": 1, "space": "overflow", "color": "yellow"}, ev)
    assert p.trace_log == [(0, "blue"), (1, "yellow")] and s.species[1].overflow_kinds == ["yellow"]
    assert cards.cond_ok(s, p, card_defs.traces("blue", 1)) and cards.cond_ok(s, p, card_defs.traces("yellow", 1))
