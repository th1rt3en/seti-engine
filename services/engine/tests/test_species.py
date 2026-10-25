"""Alien species: discovery, boards, alien cards, Anomalies and the Centaurian messages (ALIEN-*, LIFE-04, FAQ-40, FAQ-41)."""

from typing import Any

from test_engine import begin, decisions, do, with_state

from seti_engine import effects, rewards, solar, species, tables, trail
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import Decision, GameState, SpeciesSlot


def game(first: str = "anomalies", second: str = "centaurians") -> GameState:
    s = begin(3).state.model_copy(deep=True)
    s.species = [SpeciesSlot(species=n, board=species.new_board(n)) for n in (first, second)]
    return s


def discover(s: GameState, slot: int, owners: tuple[str, str, str] = ("p0", "p0", "p1")) -> StepResult:
    """Fill the three discovery spaces and end the turn so the species is revealed."""
    s.species[slot].discovery_spaces = list(owners)
    s.species[slot].complete = True
    s.main_done = True
    r = do(with_state(s), "end_turn")
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    return r


def trace_decision(s: GameState, color: str) -> None:
    s.pending = [Decision(kind="trace", player=s.current_player, data={"color": color})]


def test_species_is_revealed_after_the_turn_and_cards_go_to_the_markers() -> None:
    """ALIEN-01, ALIEN-06, FAQ-40: one card per player marker; nonplayer markers get none."""
    s = game()
    hands = [len(p.hand) for p in s.players]
    s.species[0].discovery_spaces = ["p0", "n", "p1"]
    s.species[0].complete = True
    assert not s.species[0].discovered
    s.main_done = True
    r = do(with_state(s), "end_turn")
    sl = r.state.species[0]
    assert sl.discovered and len(sl.deck) == 10 - 2 - 1 and sl.face_up is not None
    assert [len(p.hand) - h for p, h in zip(r.state.players, hands, strict=True)] == [1, 1, 0]
    assert any(e["type"] == "discovered" for e in r.events)


def test_a_player_with_two_markers_gets_two_cards() -> None:
    s = game()
    pl = s.current_player
    hand = len(s.players[pl].hand)
    r = discover(s, 0, (f"p{pl}", f"p{pl}", "n"))
    assert len(r.state.players[pl].hand) == hand + 2


def test_deck_of_the_species_is_its_own_cards() -> None:
    """ALIEN-04: only that species' cards."""
    r = discover(game(), 1)
    sl = r.state.species[1]
    assert {tables.cards()[c]["species"] for c in [*sl.deck, sl.face_up or ""] if c} == {"centaurians"}


def test_discovered_board_offers_spaces_of_the_matching_color() -> None:
    """LIFE-04, FAQ-41: any empty space of the color on a discovered board, plus the other species' discovery space and overflow."""
    s = discover(game(), 0).state.model_copy(deep=True)
    trace_decision(s, "yellow")
    moves = decisions(legal_moves(s))
    board = [m for m in moves if m["space"] == "board"]
    assert (
        {m["index"] for m in board} == {0, 1, 2, 3, 4} and {m["color"] for m in board} == {"yellow"} and {m["slot"] for m in board} == {0}
    )
    assert any(m["space"] == "discovery" and m["slot"] == 1 for m in moves)
    assert [m["color"] for m in moves if m["space"] == "overflow"] == ["yellow", "yellow"]  # one yellow overflow space per species


def mark(s: GameState, slot: int, color: str, k: int) -> list[dict[str, Any]]:
    p = s.players[s.current_player]
    ev: list[dict[str, Any]] = []
    rewards.place_trace(s, p, {"slot": slot, "space": "board", "color": color, "index": k}, ev)
    return ev


def test_marking_a_board_space_gives_its_reward_and_blocks_it() -> None:
    """LIFE-04, ALIEN-DATA-10: Anomalies pink space 2 gives 3 points."""
    s = discover(game(), 0).state.model_copy(deep=True)
    p = s.players[s.current_player]
    score = p.score
    mark(s, 0, "pink", 1)
    assert p.score == score + 3 and s.species[0].board["pink"][1] == [p.index] and p.trace_log[-1] == (0, "pink")
    trace_decision(s, "pink")
    assert 1 not in {m["index"] for m in decisions(legal_moves(s)) if m["space"] == "board"}


def test_top_capsule_can_be_marked_again_and_later_markers_are_higher() -> None:
    """ALIEN-ANO-05: the top space is always available."""
    s = discover(game(), 0).state.model_copy(deep=True)
    first = s.current_player
    mark(s, 0, "blue", 0)
    s.current_player = (first + 1) % 3
    mark(s, 0, "blue", 0)
    assert s.species[0].board["blue"][0] == [first, s.current_player]
    assert species.anomaly_reward(s, s.species[0], "blue") == s.current_player


def test_alien_card_reward_lets_the_player_draw_from_the_deck_or_the_face_up_card() -> None:
    """ALIEN-05, ALIEN-DATA-12: Anomalies pink space 4: 2 points and an alien card."""
    s = discover(game(), 0).state.model_copy(deep=True)
    pl = s.current_player
    face_up, hand = s.species[0].face_up, len(s.players[pl].hand)
    mark(s, 0, "pink", 3)
    assert s.pending[0].kind == "take_alien_card" and {m["source"] for m in decisions(legal_moves(s))} == {"deck", "face_up"}
    r = do(with_state(s), "take_alien", source="face_up")
    assert face_up in r.state.players[pl].hand and len(r.state.players[pl].hand) == hand + 1
    assert r.state.species[0].face_up is not None and r.state.species[0].face_up != face_up
    assert {"type": "take_alien_display_card", "player": pl, "card": face_up, "slot": 0} in r.events
    deck_pick = do(with_state(s), "take_alien", source="deck")
    assert not any(e["type"] == "take_alien_display_card" for e in deck_pick.events)  # the top of the deck is not shown


def test_alien_card_icon_does_nothing_when_the_species_has_no_cards_left() -> None:
    """ALIEN-05 ('Oumuamua sheet): with no cards to draw the symbol has no effect."""
    s = discover(game(), 0).state.model_copy(deep=True)
    s.species[0].deck, s.species[0].face_up = [], None
    mark(s, 0, "pink", 3)
    assert not s.pending


def test_trace_on_a_board_counts_for_missions() -> None:
    """A-017: markers on the species board count by their space's color."""
    s = discover(game(), 0).state.model_copy(deep=True)
    p = s.players[s.current_player]
    mark(s, 0, "yellow", 1)
    mark(s, 0, "yellow", 2)
    assert sum(1 for _, k in p.trace_log if k == "yellow") == 2


# --- Anomalies -------------------------------------------------------------------------------------------------------------------


def sandbox_free_reward(token: dict[str, Any]) -> list[dict[str, Any]]:
    faces = next(x for x in tables.alien_boards()["anomalies"]["tokens"] if x["column"] == token["color"])["sides"]
    return list(faces[token["side"]])


def test_anomalies_are_placed_in_earths_sector_and_three_sectors_either_side() -> None:
    """ALIEN-ANO-01: the placement is logged with each token's sector, color, face and reward."""
    r = discover(game(), 0)
    s = r.state
    e = solar.earth(s)[1]
    toks = s.species[0].extra["tokens"]
    assert sorted(t["sector"] for t in toks) == sorted([e, (e + 3) % 8, (e - 3) % 8])
    assert sorted(t["color"] for t in toks) == ["blue", "pink", "yellow"]
    placed = [x for x in r.events if x["type"] == "anomalies_placed"]
    assert len(placed) == 1 and placed[0]["earth_sector"] == e
    assert [(t["sector"], t["color"], t["side"]) for t in placed[0]["tokens"]] == [(t["sector"], t["color"], t["side"]) for t in toks]
    assert all(t["reward"] for t in placed[0]["tokens"])
    assert all(t["reward"] == sandbox_free_reward(t) for t in toks)  # the state carries what each token pays, for the page


def test_rotation_into_an_anomaly_pays_the_highest_marker_of_its_column() -> None:
    """ALIEN-ANO-02 to ALIEN-ANO-04."""
    s = discover(game(), 0).state.model_copy(deep=True)
    sl = s.species[0]
    e = solar.earth(s)[1]
    sl.extra["tokens"] = [{"sector": e, "color": "yellow", "side": 1}, {"sector": (e + 4) % 8, "color": "pink", "side": 0}]
    sl.board["yellow"][3] = [2]
    sl.board["yellow"][1] = [0]  # higher than space 4 (the top is space 1)
    ev: list[dict[str, Any]] = []
    pub = s.players[0].publicity
    species.after_rotation(s, ev)
    assert [x["player"] for x in ev if x["type"] == "anomaly"] == [0]
    logged = next(x for x in ev if x["type"] == "anomaly")  # the log says which token, where, and what it paid
    assert (logged["sector"], logged["color"], logged["side"], logged["reward"]) == (e, "yellow", 1, [{"n": 2, "t": "publicity"}])
    assert s.players[0].publicity == pub + 2  # the yellow token's other face: 2 publicity
    gain = next(g for g in trail.events_of(s) if g["type"] == "gains")  # the gain has its own source, so its own line in the log
    assert gain["source"] == {"kind": "anomaly", "color": "yellow", "sector": e} and gain["changes"] == {"publicity": 2}


def test_anomaly_with_an_empty_column_pays_nobody() -> None:
    """ALIEN-ANO-03."""
    s = discover(game(), 0).state.model_copy(deep=True)
    e = solar.earth(s)[1]
    s.species[0].extra["tokens"] = [{"sector": e, "color": "blue", "side": 0}]
    ev: list[dict[str, Any]] = []
    species.after_rotation(s, ev)
    assert [x["player"] for x in ev if x["type"] == "anomaly"] == [None]


def test_a_research_rotation_checks_the_anomalies() -> None:
    """ALIEN-ANO-02: every rotation checks them, including the one of a tech research."""
    s = discover(game(), 0).state.model_copy(deep=True)
    s.main_done = False
    s.players[s.current_player].publicity = 6
    r = do(with_state(s), "research", stack=0)
    assert any(e["type"] == "rotate" for e in r.events)


def test_a_card_that_rotates_the_solar_system_checks_the_anomalies() -> None:
    """ALIEN-ANO-02: the rotation of a card (Planetary Geologic Mapping) sets off the anomaly that Earth reaches, like any rotation."""
    from seti_engine import cards  # noqa: PLC0415

    s = discover(game(), 0).state.model_copy(deep=True)
    ahead = s.model_copy(deep=True)
    solar.rotate(ahead)
    reached = solar.earth(ahead)[1]  # where Earth is after the rotation
    s.species[0].extra["tokens"] = [{"sector": reached, "color": "pink", "side": 0}]
    s.species[0].board["pink"][0] = [0]
    ev: list[dict[str, Any]] = []
    cards.run_step(s, s.players[0], {"t": "rotate"}, ev)
    assert [x["player"] for x in ev if x["type"] == "anomaly"] == [0]


# --- Centaurians -----------------------------------------------------------------------------------------------------------------


def test_each_player_gets_a_message_milestone_fifteen_points_ahead() -> None:
    """ALIEN-CEN-01."""
    s = game("centaurians", "anomalies")
    before = [p.score for p in s.players]
    r = discover(s, 0)
    assert [p.messages for p in r.state.players] == [[b + 15] for b in before]
    placed = next(e for e in r.events if e["type"] == "messages_placed")
    assert placed["targets"] == [{"player": i, "target": b + 15} for i, b in enumerate(before)]


def test_reaching_a_message_lets_the_player_cover_a_reward() -> None:
    """ALIEN-CEN-04, MILE-01: resolved at the end of the turn; the tile covers the reward for other players."""
    s = discover(game("centaurians", "anomalies"), 0).state.model_copy(deep=True)
    s.main_done = False
    pl = s.current_player
    s.players[pl].messages = [s.players[pl].score + 15]
    effects.gain_score(s, s.players[pl], 20)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.pending[0].kind == "message_reward" and {m["hex"] for m in r.legal} == {0, 1, 2, 3}
    pub = r.state.players[pl].publicity
    assert all(m["reward"] for m in r.legal)  # the prompt shows what each reward is
    assert any(e["type"] == "message_reached" and e["player"] == pl for e in r.events)
    r2 = apply(r.state, next(m for m in r.legal if m["hex"] == 2))
    assert any(e["type"] == "message_reward" and e["hex"] == 2 and e["player"] == pl for e in r2.events)
    assert r2.state.players[pl].publicity == pub + 3 and r2.state.species[0].extra["covered"][2] == pl
    assert r2.state.players[pl].messages == []
    s3 = r2.state.model_copy(deep=True)
    other = (pl + 1) % 3
    s3.players[other].messages = [s3.players[other].score + 1]
    effects.gain_score(s3, s3.players[other], 5)
    s3.current_player = other
    s3.main_done = True
    r3 = do(with_state(s3), "end_turn")
    assert 2 not in {m["hex"] for m in r3.legal}


def test_centaurian_spaces_cost_data_from_the_pool() -> None:
    """ALIEN-CEN-05: the top space costs 1 data each time, the second space 3 data."""
    s = discover(game("centaurians", "anomalies"), 0).state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.data_pool = 0
    trace_decision(s, "pink")
    assert not {m["index"] for m in decisions(legal_moves(s)) if m["space"] == "board"} & {0, 1}
    p.data_pool = 3
    assert {0, 1} <= {m["index"] for m in decisions(legal_moves(s)) if m["space"] == "board"}
    mark(s, 0, "pink", 1)
    assert p.data_pool == 0 and p.score >= 15


# --- 'Oumuamua -------------------------------------------------------------------------------------------------------------------


def oum_game() -> GameState:
    return discover(game("oumuamua", "anomalies"), 0).state.model_copy(deep=True)


def test_oumuamua_tile_is_placed_as_a_planet_with_three_data() -> None:
    """ALIEN-OUM-01, ALIEN-OUM-05."""
    s = oum_game()
    assert s.oumuamua_placed and "oumuamua" in s.planets
    assert s.species[0].extra["tile"] == {"data": 3, "markers": []} and s.species[0].extra["supply"] == 17
    pos = solar.find_cell(s, "PLANET:OUMUAMUA")
    assert pos is not None and species.oumuamua_sector(s) == pos[1]


def test_a_probe_on_the_oumuamua_space_gains_its_player_publicity_when_it_arrives() -> None:
    """ALIEN-OUM-01."""
    s = game("oumuamua", "anomalies")
    ring, sector = 3, (3 + s.disc_angles[2]) % 8
    from seti_engine.models import Probe

    s.probes.append(Probe(id="x", player=1, ring=ring, sector=sector))
    pub = s.players[1].publicity
    r = discover(s, 0)
    assert r.state.players[1].publicity == min(10, pub + 1)


def test_signal_in_oumuamuas_sector_can_go_on_the_tile() -> None:
    """ALIEN-OUM-03: a choice between the sector and the tile; the first marker scores 1 point."""
    s = oum_game()
    p = s.players[s.current_player]
    sec = species.oumuamua_sector(s)
    assert sec is not None
    ev: list[dict[str, Any]] = []
    rewards.mark_signal(s, p, sec, ev)
    assert s.pending[0].kind == "oumuamua_signal" and not s.sectors[sec].markers
    score, data = p.score, p.data_pool
    r = do(with_state(s), "signal_where", where="tile")
    q = r.state.players[r.state.current_player]
    assert r.state.species[0].extra["tile"]["markers"] == [q.index] and q.score == score + 1 and q.data_pool == data + 1
    s2 = oum_game()
    rewards.mark_signal(s2, s2.players[s2.current_player], sec, ev)
    r2 = do(with_state(s2), "signal_where", where="sector")
    assert r2.state.sectors[sec].markers == [r2.state.current_player]


def _scan_with_a_discarded_card(s: GameState) -> tuple[StepResult, int]:
    """A scan in which a display card of the color of 'Oumuamua's sector is discarded for a signal: the game at the choice of the sector."""
    sec = species.oumuamua_sector(s)
    assert sec is not None
    color = s.sectors[sec].color
    cid = next(c for c, v in tables.cards().items() if v.get("sector") == color and v["deck"] == "base")
    p = s.players[s.current_player]
    s.card_row[0] = cid
    p.credits, p.energy, p.hand = 5, 5, []
    s.main_done, s.pending, s.stage = False, [], None
    r = do(with_state(s), "scan")
    r = do(r, "scan_discard", source="row:0")
    assert r.state.pending[0].kind == "signal"
    return r, sec


def test_discarding_a_display_card_offers_the_tile_of_oumuamua_with_the_sectors() -> None:
    """ALIEN-OUM-03: the tile is one of the choices of the signal, with the sector: nothing is asked after the choice."""
    r, sec = _scan_with_a_discarded_card(oum_game())
    here = [m for m in r.legal if m["type"] == "mark_signal" and m["sector"] == sec]
    assert {m["where"] for m in here} == {"sector", "tile"}  # both, as moves
    me = r.state.current_player
    data = r.state.players[me].data_pool
    r = apply(r.state, {"type": "mark_signal", "sector": sec, "where": "tile"})
    assert r.state.species[0].extra["tile"]["markers"] == [me] and not r.state.sectors[sec].markers  # on the tile, not in the sector
    assert r.state.players[me].data_pool == data + 1  # and the data of the tile is gained
    assert r.state.pending[0].kind == "scan_step"  # no second question: the scan goes on
    r2, sec = _scan_with_a_discarded_card(oum_game())
    r2 = apply(r2.state, {"type": "mark_signal", "sector": sec, "where": "sector"})
    assert r2.state.sectors[sec].markers == [r2.state.current_player] and r2.state.pending[0].kind == "scan_step"


def test_a_game_played_with_the_old_question_still_replays() -> None:
    """The log of a game before 2026-10-25 has `mark_signal` without `where` and then `signal_where`: both are still accepted."""
    r, sec = _scan_with_a_discarded_card(oum_game())
    r = apply(r.state, {"type": "mark_signal", "sector": sec})  # not offered any more, accepted
    assert r.state.pending[0].kind == "oumuamua_signal"  # the old question follows at once
    r = apply(r.state, {"type": "signal_where", "where": "tile"})
    assert r.state.species[0].extra["tile"]["markers"] == [r.state.current_player]


def test_tile_completion_gives_exofossils_and_refills() -> None:
    """ALIEN-OUM-04: the third marker scores 2 points; every contributor gains 1 exofossil; the tile is refilled with no markers."""
    s = oum_game()
    a, b = s.current_player, (s.current_player + 1) % 3
    ev: list[dict[str, Any]] = []
    species.mark_tile(s, s.players[a], ev)
    species.mark_tile(s, s.players[b], ev)
    score = s.players[a].score
    species.mark_tile(s, s.players[a], ev)
    assert s.players[a].score == score + 2 and s.completed == [-1]
    s.main_done = True
    r = do(with_state(s), "end_turn")
    st = r.state
    assert st.players[a].exofossils == 1 and st.players[b].exofossils == 1 and st.species[0].extra["supply"] == 15
    assert st.species[0].extra["tile"] == {"data": 3, "markers": []} and st.completed == []


def test_exofossil_supply_is_limited_to_seventeen() -> None:
    s = oum_game()
    p = s.players[s.current_player]
    species.gain_exofossil(s, p, 20)
    assert p.exofossils == 17 and s.species[0].extra["supply"] == 0
    species.gain_exofossil(s, s.players[(s.current_player + 1) % 3], 1)
    assert s.players[(s.current_player + 1) % 3].exofossils == 0


def test_oumuamua_board_spaces_cost_exofossils() -> None:
    """ALIEN-OUM-02: the top space costs 1 each time; the bottom space 4; paid tokens return to the supply."""
    s = oum_game()
    p = s.players[s.current_player]
    p.exofossils = 0
    trace_decision(s, "pink")
    assert not {m["index"] for m in decisions(legal_moves(s)) if m["space"] == "board"} & {0, 4}
    s.species[0].extra["supply"] = 10
    p.exofossils = 4
    assert {0, 4} <= {m["index"] for m in decisions(legal_moves(s)) if m["space"] == "board"}
    mark(s, 0, "pink", 4)
    assert p.exofossils == 0 and s.species[0].extra["supply"] == 14 and p.score >= 25


def test_orbiting_oumuamua_gives_its_rewards() -> None:
    """ALIEN-OUM-05: 10 points, an exofossil, a signal in its sector or on the tile; the first orbiter also draws an alien card."""
    from seti_engine.models import Probe

    s = oum_game()
    pl = s.current_player
    pos = solar.find_cell(s, "PLANET:OUMUAMUA")
    assert pos is not None
    s.probes.append(Probe(id="o1", player=pl, ring=pos[0], sector=pos[1]))
    s.players[pl].credits = s.players[pl].energy = 5
    s.main_done = False
    score = s.players[pl].score
    r = do(with_state(s), "orbit", probe="o1")
    kinds = [d.kind for d in r.state.pending]
    assert "take_alien_card" in kinds and "oumuamua_signal" in kinds
    assert r.state.players[pl].exofossils == 1 and r.state.players[pl].score >= score + 10
    assert r.state.planets["oumuamua"].first_orbiter == pl


# --- Exertians -------------------------------------------------------------------------------------------------------------------


def exert_game(owners: tuple[str, str, str] = ("p0", "p0", "p1")) -> StepResult:
    s = game("exertians", "anomalies")
    s.species[0].discovery_spaces = list(owners)
    s.species[0].complete = True
    s.main_done = True
    return do(with_state(s), "end_turn")


def test_exertian_cards_are_dealt_three_each_plus_one_per_marker() -> None:
    """ALIEN-EXE-01, ALIEN-EXE-05, ALIEN-EXE-02, CARD-32: not in hand, the rest of the deck leaves the game."""
    s = game("exertians", "anomalies")
    hands = [len(p.hand) for p in s.players]
    r = exert_game()
    st = r.state
    assert [len(p.exertian_hand) for p in st.players] == [5, 4, 3]
    assert [len(p.hand) for p in st.players] == hands and st.species[0].deck == [] and st.species[0].face_up is None
    assert all(c.startswith("ET.4") or c.startswith("ET.5") for p in st.players for c in p.exertian_hand)
    assert len({c for p in st.players for c in p.exertian_hand}) == 12


def test_each_marker_gives_an_immediate_chance_to_play_a_card_face_down() -> None:
    """ALIEN-EXE-01: one play per marker, optional."""
    r = exert_game()
    kinds = [(d.player, d.kind) for d in r.state.pending]
    assert kinds == [(0, "exertian_play"), (0, "exertian_play"), (1, "exertian_play")]
    card = r.state.players[0].exertian_hand[0]
    r2 = do(r, "play_exertian", card=card)
    assert r2.state.players[0].exertian_played == [card] and card not in r2.state.players[0].exertian_hand
    assert {"type": "skip_exertian"} in r2.legal
    r3 = do(r2, "skip_exertian")
    assert len(r3.state.pending) == 1


def test_exertian_milestones_are_twenty_and_forty_ahead_of_the_leader() -> None:
    """ALIEN-EXE-03."""
    r = exert_game(("n", "n", "n"))
    lead = max(p.score for p in r.state.players)
    assert [m["at"] for m in r.state.species[0].extra["milestones"]] == [lead + 20, lead + 40]
    assert [m["cost"] for m in r.state.species[0].extra["milestones"]] == [0, 1]
    logged = next(e for e in r.events if e["type"] == "exertian_milestones")  # the log says where they are and what they cost
    assert logged["milestones"] == [{"at": lead + 20, "cost": 0}, {"at": lead + 40, "cost": 1}]


def test_crossing_an_exertian_milestone_lets_even_a_player_without_traces_play_a_card() -> None:
    """ALIEN-EXE-03, ALIEN-EXE-04: the second milestone costs 1 credit and cannot be paid for later."""
    st = exert_game(("n", "n", "n")).state.model_copy(deep=True)
    pl = st.current_player
    p = st.players[pl]
    ms = st.species[0].extra["milestones"]
    p.score = ms[0]["at"] - 1
    effects.gain_score(st, p, 1)
    st.main_done = True
    r = do(with_state(st), "end_turn")
    assert r.state.pending[0].kind == "exertian_play" and r.state.pending[0].data["cost"] == 0
    r = do(r, "skip_exertian")
    st2 = r.state.model_copy(deep=True)
    p2 = st2.players[pl]
    p2.score, p2.credits = ms[1]["at"] - 1, 0
    st2.pending, st2.main_done, st2.stage = [], False, None
    effects.gain_score(st2, p2, 1)
    st2.main_done = True
    r2 = do(with_state(st2), "end_turn")
    assert not [d for d in r2.state.pending if d.kind == "exertian_play"]  # no credit: the chance is gone
    assert pl in r2.state.species[0].extra["milestones"][1]["done"]


def test_danger_comes_from_cards_and_board_markers() -> None:
    """ALIEN-EXE-06: 1 per marker on the top tier, 2 on the middle, 3 on the bottom."""
    st = exert_game(("n", "n", "n")).state.model_copy(deep=True)
    p = st.players[0]
    p.exertian_played = ["ET.53", "ET.52"]  # danger 9 and 0
    assert species.danger(st, p) == 9
    st.species[0].board["pink"][0].append(0)
    st.species[0].board["blue"][2].append(0)
    st.species[0].board["yellow"][4].append(0)
    assert species.danger(st, p) == 9 + 1 + 2 + 3


def test_the_player_with_the_most_danger_loses_a_tenth_of_their_points() -> None:
    """ALIEN-EXE-07: rounded down; ties all lose."""
    st = exert_game(("n", "n", "n")).state.model_copy(deep=True)
    st.players[0].exertian_played = ["ET.53"]  # 9
    st.players[1].exertian_played = ["ET.51"]  # 8
    assert species.exertian_losses(st, [168, 100, 90]) == [16, 0, 0]
    st.players[1].exertian_played = ["ET.53"]
    assert species.exertian_losses(st, [168, 105, 90]) == [16, 10, 0]
    st.players[2].exertian_played = []
    assert species.exertian_losses(st, [5, 100, 90]) == [0, 10, 0]


def test_exertian_card_points_need_their_condition() -> None:
    """ALIEN-EXE-06: ET.44 (2 red wins, 12 points), ET.49 (4 landers, 16), ET.52 (6 Exertian traces, 7)."""
    from seti_engine import cards

    st = exert_game(("n", "n", "n")).state.model_copy(deep=True)
    p = st.players[0]
    p.exertian_played = ["ET.44", "ET.49", "ET.52"]
    assert cards.exertian_points(st, p) == 0
    red = rewards.sectors_of_color(st, "red")
    st.sectors[red[0]].winners = [0, 0]
    p.landers = {"mars": 2, "Io": 2}
    st.species[0].overflow = [0] * 6
    assert cards.exertian_points(st, p) == 12 + 16 + 7


def test_exertian_cards_stay_out_of_the_hand_limit() -> None:
    """ALIEN-EXE-02: they are not counted for the hand limit and cannot be discarded."""
    st = exert_game(("n", "n", "n")).state.model_copy(deep=True)
    p = st.players[st.current_player]
    assert len(p.hand) <= 5 and len(p.exertian_hand) == 3
    assert not [m for m in legal_moves(with_state(st).state) if m.get("card") in p.exertian_hand]


# --- Mascamites ------------------------------------------------------------------------------------------------------------------


def masc_game() -> GameState:
    return discover(game("mascamites", "anomalies"), 0).state.model_copy(deep=True)


def test_mascamite_samples_are_dealt_to_jupiter_and_saturn() -> None:
    """ALIEN-MASC-01: three on each, the seventh face up on its blue space."""
    s = masc_game()
    ex = s.species[0].extra
    assert len(ex["samples"]["jupiter"]) == 3 and len(ex["samples"]["saturn"]) == 3
    assert ex["sample_spaces"] == [
        {"token": ex["sample_spaces"][0]["token"], "marker": None, "reward": species.sample_faces()[ex["sample_spaces"][0]["token"]]}
    ]
    all_tokens = [*ex["samples"]["jupiter"], *ex["samples"]["saturn"], ex["sample_spaces"][0]["token"]]
    assert sorted(all_tokens) == list(range(7))


def put_probe_at(s: GameState, planet: str) -> str:
    from seti_engine.models import Probe

    pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
    assert pos is not None
    s.probes.append(Probe(id="m1", player=s.current_player, ring=pos[0], sector=pos[1]))
    return "m1"


def test_collecting_a_sample_makes_a_capsule_where_the_probe_is() -> None:
    """ALIEN-MASC-02: choose one of the samples on the planet; the others stay."""
    s = masc_game()
    pid = put_probe_at(s, "jupiter")
    options = species.collect_sample_options(s, pid)
    assert len(options) == 3
    ev: list[dict[str, Any]] = []
    species.collect_sample(s, s.players[s.current_player], "jupiter", options[1], ev)
    caps = [pr for pr in s.probes if pr.capsule]
    probe = next(pr for pr in s.probes if pr.id == pid)
    assert len(caps) == 1 and caps[0].sample == options[1] and (caps[0].ring, caps[0].sector) == (probe.ring, probe.sector)
    assert s.species[0].extra["samples"]["jupiter"] == [options[0], options[2]]
    assert species.collect_sample_options(s, pid) == [options[0], options[2]]


def test_no_samples_away_from_jupiter_and_saturn() -> None:
    s = masc_game()
    assert species.collect_sample_options(s, put_probe_at(s, "mars")) == []


def test_a_capsule_moves_like_a_probe_but_does_not_count_for_the_limit_or_orbit() -> None:
    """ALIEN-MASC-03."""
    from seti_engine.models import Probe

    s = masc_game()
    s.main_done = False
    pl = s.current_player
    pos = solar.find_cell(s, "PLANET:MARS")
    assert pos is not None
    s.probes.append(Probe(id="cap", player=pl, ring=pos[0], sector=pos[1], capsule=True, sample=0))
    s.players[pl].credits = s.players[pl].energy = 5
    s.players[pl].movement = 2
    moves = legal_moves(s)
    assert any(m["type"] == "move_probe" and m["probe"] == "cap" for m in moves)
    assert not any(m["type"] in ("orbit", "land") for m in moves)
    assert {"type": "launch"} in moves  # the limit counts real probes only


def test_delivering_a_sample_pays_its_reward_and_adds_a_blue_space() -> None:
    """ALIEN-MASC-04, ALIEN-MASC-05."""
    from seti_engine.models import Probe

    s = masc_game()
    pl = s.current_player
    s.probes.append(Probe(id="cap", player=pl, ring=1, sector=0, capsule=True, sample=3))  # face 3: 2 data
    ev: list[dict[str, Any]] = []
    data = s.players[pl].data_pool
    species.deliver_sample(s, s.players[pl], "cap", ev)
    assert not [pr for pr in s.probes if pr.capsule] and s.players[pl].data_pool == data + 2
    assert [sp["token"] for sp in s.species[0].extra["sample_spaces"]][-1] == 3


def test_any_player_may_mark_a_blue_space_with_a_sample_and_gains_its_reward() -> None:
    """ALIEN-MASC-05: once, and the marker gains the sample's reward."""
    s = masc_game()
    token = s.species[0].extra["sample_spaces"][0]["token"]
    trace_decision(s, "blue")
    moves = [m for m in decisions(legal_moves(s)) if m["space"] == "sample"]
    assert moves == [{"type": "place_trace", "slot": 0, "space": "sample", "color": "blue", "index": 0}]
    p = s.players[s.current_player]
    reward = {r["t"]: r["n"] for r in species.sample_faces()[token]}
    before = (p.score, p.publicity, p.data_pool, p.energy, p.credits, len(p.hand))
    ev: list[dict[str, Any]] = []
    rewards.place_trace(s, p, moves[0], ev)
    assert s.species[0].extra["sample_spaces"][0]["marker"] == p.index
    after = (p.score, p.publicity, p.data_pool, p.energy, p.credits, len(p.hand))
    want = {"vp": 0, "publicity": 1, "data": 2, "energy": 3, "credit": 4, "card_random": 5}
    for key, idx in want.items():
        if key in reward:
            assert after[idx] - before[idx] >= min(reward[key], 1) if key != "publicity" else after[idx] >= before[idx]
    assert p.trace_log[-1] == (0, "blue")
    trace_decision(s, "blue")
    assert not [m for m in decisions(legal_moves(s)) if m["space"] == "sample"]


def test_mascamite_setup_is_logged_without_revealing_the_face_down_samples() -> None:
    """ALIEN-MASC-01."""
    r = discover(game("mascamites", "anomalies"), 0)
    placed = next(e for e in r.events if e["type"] == "samples_placed")
    assert placed["planets"] == {"jupiter": 3, "saturn": 3}
    assert placed["face_up"]["reward"] == species.sample_faces()[placed["face_up"]["token"]]


def test_a_player_sees_the_samples_they_looked_at_and_the_others_stay_face_down() -> None:
    """ALIEN-MASC-02: looking at the samples on a planet shows their faces to that player only (the projection, not a rule)."""
    from seti_engine.projection import project

    s = masc_game()
    jup = list(s.species[0].extra["samples"]["jupiter"])
    assert project(s, 0).state.species[0].extra["samples"]["jupiter"] == [-1, -1, -1]  # nobody has looked
    p = s.players[0]
    species.record_seen(s, p.index, ["jupiter"])
    assert project(s, 0).state.species[0].extra["samples"]["jupiter"] == jup  # the player who looked
    assert project(s, 1).state.species[0].extra["samples"]["jupiter"] == [-1, -1, -1]  # the other player
    assert project(s, None).state.species[0].extra["samples"]["saturn"] == [-1, -1, -1]  # a spectator; Saturn was not looked at
    assert "seen" not in project(s, 0).state.species[0].extra
