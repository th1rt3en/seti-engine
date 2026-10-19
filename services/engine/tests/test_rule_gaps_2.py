"""More tests that name rules without a test (docs/spec/untested-rules.md): scan, sectors, traces, milestones."""

from test_cards import ready
from test_engine import begin, do, with_state
from test_scan_orbit_land import complete, settle
from test_species import discover, game

from seti_engine import effects, rewards, solar, tables
from seti_engine.engine import apply, legal_moves
from seti_engine.models import GameState


def test_a_card_discarded_for_a_signal_sends_it_to_a_sector_of_its_color() -> None:  # SECTOR-21, SECTOR-22, CARD-42, CARD-47
    s = ready()
    for want in ("yellow", "red", "blue", "black"):
        s2 = s.model_copy(deep=True)
        card = next(c for c, v in tables.cards().items() if v["deck"] == "base" and v["sector"] == want and c in s2.deck)
        s2.deck.remove(card)
        s2.card_row[0] = card
        r = do(with_state(s2), "scan")
        r = do(r, "scan_earth", sector=solar.earth(r.state)[1])
        r = do(r, "scan_discard", source="row:0")
        moves = [m for m in r.legal if m["type"] == "mark_signal"]
        assert moves and {r.state.sectors[m["sector"]].color for m in moves} == {want}
        assert set(rewards.sectors_of_color(r.state, want)) == {m["sector"] for m in moves}  # both sectors of that color


def test_the_scan_action_itself_gives_no_trace_and_marks_signals_by_the_sector_rules() -> None:  # SCAN-06, SCAN-07
    s = ready()
    p = s.players[s.current_player]
    traces = len(p.trace_log)
    earth = solar.earth(s)[1]
    markers = len(s.sectors[earth].markers)
    remaining = s.sectors[earth].data_remaining
    r = do(with_state(s), "scan")
    r = do(r, "scan_earth", sector=earth)
    q = r.state.players[s.current_player]
    assert len(q.trace_log) == traces and not any(d.kind == "trace" for d in r.state.pending)  # no trace from the action
    assert len(r.state.sectors[earth].markers) == markers + 1 and r.state.sectors[earth].data_remaining == remaining - 1  # SECTOR-01


def test_the_winner_of_a_sector_can_gain_a_life_trace() -> None:  # SECTOR-16
    s = begin(2).state.model_copy(deep=True)
    star = "Proxima Centauri"  # first and later win: 1 pink trace
    index = next(i for i, sec in enumerate(s.sectors) if sec.star == star)
    r = complete(s, index, [0, 0, 0])
    assert any(kind == "pink" for _, kind in r.state.players[0].trace_log)  # the winner marked the pink trace of the reward


def test_every_win_of_a_sector_counts_even_in_the_same_sector() -> None:  # SECTOR-20, CARD-44
    s = begin(2).state.model_copy(deep=True)
    r = complete(s, 1, [0, 0, 0])
    s2 = settle(r).state.model_copy(deep=True)
    s2.phase, s2.stage, s2.pending = "play", None, []
    s2.players[0].passed = False
    r2 = settle(complete(s2, 1, [0, 0, 0]))
    assert r2.state.players[0].sector_wins == 2 and r2.state.sectors[1].winners == [0, 0]


def test_overflow_and_discovery_traces_count_as_traces_marked_for_an_alien_species() -> None:  # LIFE-02
    s = game()
    p = s.players[s.current_player]
    rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": "pink"}, [])
    rewards.place_trace(s, p, {"slot": 0, "space": "discovery", "color": "yellow"}, [])
    assert [(slot, kind) for slot, kind in p.trace_log] == [(0, "pink"), (0, "yellow")]


def test_nonplayer_markers_only_fill_discovery_spaces_never_a_species_board() -> None:  # LIFE-05, ALIEN-02
    s = begin(2).state.model_copy(deep=True)
    s.species[0].discovered = False
    before = [(sl.board, list(sl.overflow)) for sl in s.species]
    pl = s.current_player
    s.players[pl].score = 19
    effects.gain_score(s, s.players[pl], 2)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert "n" in r.state.species[0].discovery_spaces
    assert [(sl.board, list(sl.overflow)) for sl in r.state.species] == before


def test_after_discovery_a_trace_can_go_on_a_space_of_its_color_on_the_species_board() -> None:  # ALIEN-03, LIFE-04
    from seti_engine import species

    st = discover(game(), 0).state
    p = st.players[st.current_player]
    board = species.board_moves(st, p, 0, ("pink",))
    assert board and all(m["space"] == "board" and m["color"] == "pink" and m["slot"] == 0 for m in board)
    assert {m["color"] for m in species.board_moves(st, p, 0, ("pink", "yellow", "blue"))} == {"pink", "yellow", "blue"}


def _two_species(s: GameState) -> GameState:
    s.species[0].discovery_spaces = [None, None, None]
    s.species[1].discovery_spaces = [None, None, None]
    return s


def test_neutral_milestones_have_no_effect_when_the_markers_are_used_up_or_all_discovery_spaces_are_full() -> None:  # MILE-06
    s = _two_species(begin(2).state.model_copy(deep=True))
    s.neutral_markers = {"20": 0, "30": 0}
    s.species[0].discovered = s.species[1].discovered = False
    pl = s.current_player
    s.players[pl].score = 19
    effects.gain_score(s, s.players[pl], 2)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.species[0].discovery_spaces == [None, None, None] and r.state.neutral_markers == {"20": 0, "30": 0}
    full = _two_species(begin(2).state.model_copy(deep=True))
    for sl in full.species:
        sl.discovery_spaces = ["p0", "p0", "p1"]  # all six discovery spaces are full
    pl = full.current_player
    full.players[pl].score = 19
    before = dict(full.neutral_markers)
    effects.gain_score(full, full.players[pl], 2)
    full.main_done = True
    r2 = do(with_state(full), "end_turn")
    assert r2.state.neutral_markers == before


def test_milestones_resolve_from_the_player_whose_turn_ended_clockwise_and_the_neutral_one_last() -> None:  # MILE-10
    s = begin(3).state.model_copy(deep=True)
    s.current_player = 1
    s.crossed = [(0, 20), (0, 25), (2, 25), (1, 25)]  # a neutral milestone is listed first but is resolved last
    s.main_done = True
    s.species[0].discovery_spaces = [None, None, None]
    s.species[0].discovered = False
    order: list[int] = []
    r = do(with_state(s), "end_turn")
    while r.state.pending and r.state.pending[0].kind == "gold_choice":
        order.append(r.state.pending[0].player)
        r = apply(r.state, next(m for m in r.legal if m["type"] == "choose_gold"))
    assert order == [1, 2, 0]
    assert r.state.species[0].discovery_spaces[0] == "n"  # then the neutral marker


def test_a_species_discovered_by_milestones_is_revealed_after_the_milestones() -> None:  # MILE-11, TURN-04
    s = game()
    s.species[0].discovery_spaces = ["p1", "p1", None]
    s.crossed = [(0, 25), (0, 20)]
    s.current_player = 0
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.pending and r.state.pending[0].kind == "gold_choice"
    assert not r.state.species[0].discovered  # not yet: the milestone choices come first
    r = apply(r.state, next(m for m in r.legal if m["type"] == "choose_gold"))
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    assert r.state.species[0].discovered
    assert legal_moves(r.state) is not None


def test_playing_a_card_uses_only_one_benefit() -> None:  # CARD-03
    s = ready()
    from test_cards import me, play

    card = "124"
    r = play(s, card)
    assert card not in me(r).hand and card not in me(r).tucked  # played for its effect: it is not also tucked for income
    assert card in r.state.discard


def test_a_random_draw_leaves_the_card_row_alone_and_a_taken_row_card_is_replaced() -> None:  # CARD-31, RES-05, RES-04
    s = ready()
    row = list(s.card_row)
    p = s.players[s.current_player]
    hand = len(p.hand)
    effects.draw_random_card(s, p)  # "draw a random card from the top of the deck": never from the row
    assert len(p.hand) == hand + 1 and s.card_row == row
    taken = effects.take_from_row_or_deck(s, p, "row:1")
    assert (
        taken == row[1] and len(s.card_row) == 3 and s.card_row[:2] == [row[0], row[2]]
    )  # the others close up, a new card joins at the end


def test_a_signal_of_a_color_is_offered_only_in_sectors_of_that_color() -> None:  # CARD-43, SECTOR-21
    from seti_engine.models import Decision

    s = ready()
    s.pending = [Decision(kind="signal", player=s.current_player, data={"color": "red"})]
    moves = [m for m in legal_moves(s) if m["type"] == "mark_signal"]
    assert moves and {s.sectors[m["sector"]].color for m in moves} == {"red"}


def test_a_trace_of_a_kind_counts_the_markers_by_the_color_of_their_space() -> None:  # CARD-46
    s = game()
    p = s.players[s.current_player]
    for color in ("pink", "pink", "blue"):
        rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": color}, [])
    assert sum(1 for _, kind in p.trace_log if kind == "pink") == 2 and sum(1 for _, kind in p.trace_log if kind == "blue") == 1
