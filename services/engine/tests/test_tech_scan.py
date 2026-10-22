"""Scan steps, telescope techs, research, computer techs and analyze (SCAN, TECH, TECHACT, ANALYZE rules)."""

from test_cards import put_probe
from test_engine import begin, decisions, do, with_state

from seti_engine import rewards, solar, tables
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import ComputerTech


def test_scan_marks_earth_sector_then_a_row_card_sector() -> None:
    """SCAN-01 to SCAN-03, SCAN-05, SECTOR-01."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].credits, s.players[pl].energy = 3, 4
    earth_sector = solar.earth(s)[1]
    r2 = do(with_state(s), "scan")
    p = r2.state.players[pl]
    assert p.credits == 2 and p.energy == 2
    # in any order (rulebook p.12; owner ruling, 2026-10-22, SCAN-01): both steps are offered, and the scan cannot be finished before them
    assert {m["type"] for m in decisions(r2.legal)} == {"scan_earth", "scan_discard"}
    r3 = do(r2, "scan_earth", sector=earth_sector)
    assert r3.state.sectors[earth_sector].markers == [pl]
    assert {m["type"] for m in decisions(r3.legal)} == {"scan_discard"}  # the row step is left, and it is not optional
    cid = r3.state.card_row[0]
    color = tables.cards()[cid]["sector"]
    r4 = do(r3, "scan_discard", source="row:0")
    assert cid in r4.state.discard and len(r4.state.card_row) == 2  # refilled only after the scan
    assert {m["sector"] for m in decisions(r4.legal)} == set(rewards.sectors_of_color(r4.state, color))
    r5 = apply(r4.state, r4.legal[0])
    assert [m["type"] for m in decisions(r5.legal)] == ["scan_done"]
    r6 = do(r5, "scan_done")
    assert len(r6.state.card_row) == 3 and r6.state.scan_steps == []
    assert sum(len(sec.markers) for sec in r6.state.sectors) == 2


def after_basic_steps(r: StepResult) -> StepResult:
    """Do step 1 (Earth) and step 2 (a card of the row), and answer the signal choices, so that the telescope steps are next."""
    r = do(r, "scan_earth", sector=next(m["sector"] for m in r.legal if m["type"] == "scan_earth"))
    r = do(r, "scan_discard", source="row:0")
    while r.state.pending and r.state.pending[0].kind == "signal":
        r = apply(r.state, r.legal[0])
    return r


def scan_ready(*techs: str) -> StepResult:
    r = begin(2)
    s = r.state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.credits, p.energy, p.publicity = 3, 6, 5
    p.techs += techs
    return do(with_state(s), "scan")


def test_telescope_dot_marks_a_sector_next_to_earth() -> None:
    """TECH-TT01."""
    r = scan_ready("telescope-dot")
    e = solar.earth(r.state)[1]
    assert {m["sector"] for m in r.legal if m["type"] == "scan_earth"} == {e, (e - 1) % 8, (e + 1) % 8}


def test_telescope_branch_discards_a_hand_card_for_an_extra_signal() -> None:
    """TECH-TT02."""
    r = after_basic_steps(scan_ready("telescope-branch"))
    hand = r.state.players[r.state.current_player].hand
    assert {m["card"] for m in r.legal if m["type"] == "scan_hand_discard"} == set(hand)
    r2 = do(r, "scan_hand_discard", card=hand[0])
    assert r2.state.pending[0].kind == "signal" and hand[0] in r2.state.discard


def test_telescope_link_pays_publicity_for_a_mercury_signal() -> None:
    """TECH-TT03."""
    r = after_basic_steps(scan_ready("telescope-link"))
    pl = r.state.current_player
    r2 = do(r, "scan_mercury")
    assert r2.state.players[pl].publicity == 4
    assert sum(len(sec.markers) for sec in r2.state.sectors) == 3  # Earth, the card of the row, Mercury
    assert not [m for m in r2.legal if m["type"] == "scan_mercury"]  # once per scan


def test_telescope_cross_launches_for_one_energy_or_moves() -> None:
    """TECH-TT04, FAQ-22."""
    r = after_basic_steps(scan_ready("telescope-cross"))
    pl = r.state.current_player
    r2 = do(r, "scan_probe", mode="launch")
    p = r2.state.players[pl]
    assert p.energy == 6 - 2 - 1 and p.credits == 2 and len(r2.state.probes) == 1
    r3 = do(r, "scan_probe", mode="move")
    assert r3.state.players[pl].movement == 1 and r3.state.players[pl].energy == 6 - 2  # the movement costs no energy
    s = r.state.model_copy(deep=True)
    s.players[pl].energy = 0  # no energy: only the free movement is left
    assert {m["mode"] for m in decisions(with_state(s).legal) if m["type"] == "scan_probe"} == {"move"}


def test_the_steps_of_a_scan_come_in_any_order_and_the_techs_can_be_left_undone() -> None:  # SCAN-01 (owner ruling, 2026-10-22), SCAN-04
    r = scan_ready("telescope-link", "telescope-branch", "telescope-cross")
    assert {m["type"] for m in decisions(r.legal)} == {
        "scan_earth",
        "scan_discard",
        "scan_mercury",
        "scan_hand_discard",
        "scan_probe",
    }, "every step is offered from the start, and there is no move to skip one"
    r = after_basic_steps(r)
    assert {m["type"] for m in decisions(r.legal)} == {"scan_mercury", "scan_hand_discard", "scan_probe", "scan_done"}
    assert [m["type"] for m in decisions(do(r, "scan_done").legal)] != ["scan_done"]  # the scan ends with the techs left undone


def test_a_tech_step_can_be_done_before_earth_and_the_card_of_the_row() -> None:  # SCAN-01 (owner ruling, 2026-10-22), TECH-TT04, FAQ-22
    r = scan_ready("telescope-cross")
    pl = r.state.current_player
    energy = r.state.players[pl].energy
    # spend 1 energy to launch a probe, or gain 1 movement, before the signal in Earth's sector
    launched = do(r, "scan_probe", mode="launch")
    assert launched.state.players[pl].energy == energy - 1 and len(launched.state.probes) == 1
    assert {m["type"] for m in decisions(launched.legal)} == {"scan_earth", "scan_discard"}, "the tech step is done"
    moved = do(r, "scan_probe", mode="move")
    assert moved.state.players[pl].movement == 1
    # the scan goes on and can be finished once Earth's sector and the card of the row are done
    r = do(moved, "scan_earth", sector=next(m["sector"] for m in moved.legal if m["type"] == "scan_earth"))
    assert "scan_done" not in {m["type"] for m in decisions(r.legal)}
    r = do(r, "scan_discard", source="row:0")
    while r.state.pending and r.state.pending[0].kind == "signal":
        r = apply(r.state, r.legal[0])
    assert [m["type"] for m in decisions(r.legal)] == ["scan_done"]  # the tech step was done already


def test_a_card_of_the_hand_can_be_discarded_for_a_signal_before_earth() -> None:  # SCAN-01 (owner ruling, 2026-10-22), TECH-TT02
    r = scan_ready("telescope-branch")
    pl = r.state.current_player
    hand = r.state.players[pl].hand
    card = next(c for c in hand if tables.cards()[c].get("sector"))
    first = do(r, "scan_hand_discard", card=card)
    assert card not in first.state.players[pl].hand and card in first.state.discard
    r = first
    while r.state.pending and r.state.pending[0].kind == "signal":
        r = apply(r.state, next(m for m in r.legal if m["type"] == "mark_signal"))
    assert {m["type"] for m in decisions(r.legal)} == {"scan_earth", "scan_discard"}


def test_the_card_of_the_row_can_be_discarded_before_the_sector_of_earth() -> None:  # SCAN-01 (owner ruling, 2026-10-22), SCAN-03
    r = scan_ready()
    r = do(r, "scan_discard", source="row:0")
    while r.state.pending and r.state.pending[0].kind == "signal":
        r = apply(r.state, next(m for m in r.legal if m["type"] == "mark_signal"))
    assert {m["type"] for m in decisions(r.legal)} == {"scan_earth"}
    r = do(r, "scan_earth", sector=r.legal[0]["sector"])
    assert [m["type"] for m in decisions(r.legal)] == ["scan_done"]


def test_a_step_that_cannot_be_paid_is_not_offered_and_does_not_hold_the_scan() -> None:  # SCAN-04
    r = scan_ready("telescope-link", "telescope-cross")
    s = r.state.model_copy(deep=True)
    s.players[s.current_player].publicity = 0  # no Mercury signal
    r = with_state(s)
    assert "scan_mercury" not in {m["type"] for m in decisions(r.legal)}
    r = after_basic_steps(r)
    assert {m["type"] for m in decisions(r.legal)} == {"scan_probe", "scan_done"}


def test_a_step_that_could_not_be_paid_can_be_done_once_the_signals_gave_the_publicity() -> None:  # SCAN-04: the step is kept, not dropped
    r = scan_ready("telescope-link")
    s = r.state.model_copy(deep=True)
    s.players[s.current_player].publicity = 0
    r = with_state(s)
    assert "scan_mercury" not in {m["type"] for m in decisions(r.legal)}
    s2 = r.state.model_copy(deep=True)
    s2.players[s2.current_player].publicity = 1  # as if a reward gave it
    assert "scan_mercury" in {m["type"] for m in decisions(with_state(s2).legal)}


def test_a_skip_in_the_log_of_a_game_played_from_left_to_right_still_replays() -> None:  # SCAN-01: the move of the old rule
    r = after_basic_steps(scan_ready("telescope-link", "telescope-cross"))
    r = apply(r.state, {"type": "scan_skip"})  # the old move: the current optional step (Mercury) is not done
    assert {m["type"] for m in decisions(r.legal)} == {"scan_probe", "scan_done"}


def test_research_rotates_then_takes_the_top_tile() -> None:
    """TECHACT-01 to TECHACT-04, TECHACT-07, ROTATE-01, TECH-PT01, BOARD-52, FAQ-03, FAQ-05."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].publicity = 8
    r = with_state(s)
    assert len([m for m in r.legal if m["type"] == "research"]) == 12
    idx = next(i for i, st in enumerate(s.tech_stacks) if st.category == "probe" and st.glyph == "dot")
    top = s.tech_stacks[idx].tiles[0]
    score = s.players[pl].score
    r2 = do(r, "research", stack=idx)
    p = r2.state.players[pl]
    assert "probe-dot" in p.techs and r2.state.rotations == 1
    assert r2.state.tech_stacks[idx].two_point_tile is False and top not in r2.state.tech_stacks[idx].tiles
    assert p.score >= score + 2  # TECHACT-03: the first taker scores 2
    assert len(r2.state.probes) == 1  # TECH-PT01: the free launch
    assert not [m for m in r2.legal if m["type"] == "research"]  # main action used
    s3 = r2.state.model_copy(deep=True)
    s3.pending, s3.main_done = [], False
    s3.players[pl].publicity = 8
    assert len([m for m in legal_moves(s3) if m["type"] == "research"]) == 11  # TECHACT-07: not the same tech twice


def test_research_needs_six_publicity() -> None:
    """TECHACT-01."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    s.players[s.current_player].publicity = 5
    assert not [m for m in legal_moves(s) if m["type"] == "research"]


def test_second_taker_does_not_score_the_two_point_tile() -> None:
    """TECHACT-03."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    s.tech_stacks[0].two_point_tile = False
    pl = s.current_player
    s.players[pl].publicity = 6
    s.tech_stacks[0].tiles = ["publicity", "energy", "card", "vp3"]
    score = s.players[pl].score
    r2 = do(with_state(s), "research", stack=0)
    assert r2.state.players[pl].score == score


def test_computer_tech_goes_in_a_slot_and_lower_space_pays() -> None:
    """TECHACT-05, TECH-20, TECH-21, TECH-23, BOARD-72, FAQ-20: any slot, also one that holds data (the tech goes under the token)."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    p = s.players[pl]
    p.publicity = 6
    p.computer = [True, False, False, False, False, False]  # data already sits on space 1
    idx = next(i for i, st in enumerate(s.tech_stacks) if st.category == "computer" and st.glyph == "dot")  # CT#01: lower = 1 credit
    r2 = do(with_state(s), "research", stack=idx)
    d = r2.state.pending[-1]
    assert d.kind == "computer_slot" and d.data["slots"] == [0, 2, 4, 5]
    while r2.state.pending[0].kind != "computer_slot":
        r2 = apply(r2.state, r2.legal[0])
    score = r2.state.players[pl].score
    r3 = do(r2, "place_computer_tech", slot=0)
    assert r3.state.players[pl].score == score  # TECH-23: covering data scores nothing
    s4 = r3.state.model_copy(deep=True)
    s4.pending, s4.main_done = [], False
    s4.players[pl].data_pool = 2
    assert [m for m in legal_moves(s4) if m["type"] == "place_lower"] == [{"type": "place_lower", "slot": 0}]
    credits = s4.players[pl].credits
    r5 = do(with_state(s4), "place_lower", slot=0)
    assert r5.state.players[pl].credits == credits + 1 and r5.state.players[pl].data_pool == 1
    assert not [m for m in r5.legal if m["type"] == "place_lower"]


def test_lower_space_needs_the_upper_filled() -> None:
    """TECH-21."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.computer_techs[2] = ComputerTech(tech="computer-dot")
    p.data_pool = 1
    assert not [m for m in legal_moves(s) if m["type"] == "place_lower"]


def test_analyze_clears_the_computer_and_marks_a_blue_trace() -> None:
    """ANALYZE-01 to ANALYZE-03, TECH-22, BOARD-73, FAQ-17: all six top spaces are needed; the computer is cleared, the data pool is not."""
    r = begin(2)
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    p = s.players[pl]
    p.energy = 2
    p.data_pool = 3
    p.computer = [True] * 5 + [False]
    assert not [m for m in legal_moves(s) if m["type"] == "analyze"]  # the top row must be full
    p.computer = [True] * 6
    p.computer_techs[0] = ComputerTech(tech="computer-dot", lower_filled=True)
    r2 = do(with_state(s), "analyze")
    q = r2.state.players[pl]
    assert q.energy == 1 and q.computer == [False] * 6 and q.data_pool == 3 and not q.computer_techs[0].lower_filled
    assert r2.state.pending[0].data == {"color": "blue"}
    r3 = do(r2, "place_trace", slot=0, space="discovery", color="blue")
    assert r3.state.species[0].discovery_spaces[2] == f"p{pl}"


def test_a_probe_can_be_moved_in_the_middle_of_a_scan() -> None:  # FREE-00, FREE-01: movement from a mission
    from seti_engine.projection import project

    r = scan_ready()
    s = r.state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].movement = 1
    put_probe(s, "EARTH")
    assert s.pending[0].kind == "scan_step"
    v = project(s, pl)
    assert v.reach and v.reach[0].cells  # the page offers the probes and the spaces they can reach, not one button for each space
