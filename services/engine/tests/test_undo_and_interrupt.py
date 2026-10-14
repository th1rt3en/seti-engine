"""Taking moves back (UNDO-01), free actions during a main action (FREE-00), the card row during a scan (A-026, SCAN-03) and
sectors resolved right after the main action (SECTOR-10, TURN-05, A-005)."""

from test_engine import begin, decisions

from seti_engine import move_notes, solar
from seti_engine.engine import FREE_TYPES, apply, legal_moves
from seti_engine.models import GameState


def ready() -> tuple[GameState, int]:
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].credits, s.players[pl].energy, s.players[pl].publicity = 5, 5, 6
    return s, pl


def test_several_moves_can_be_taken_back_one_after_the_other() -> None:
    """UNDO-01: every move that shows nothing hidden can be taken back, back to the first one."""
    s, pl = ready()
    r1 = apply(s, {"type": "move_energy"})
    r2 = apply(r1.state, {"type": "exchange", "give": "credit", "get": "energy"})
    r3 = apply(r2.state, {"type": "launch"})  # a main action, shows nothing
    assert {"type": "undo"} in r3.legal
    b2 = apply(r3.state, {"type": "undo"})
    assert b2.state.model_dump(exclude={"undo", "undo_log"}) == r2.state.model_dump(exclude={"undo", "undo_log"})
    b1 = apply(b2.state, {"type": "undo"})
    assert b1.state.model_dump(exclude={"undo", "undo_log"}) == r1.state.model_dump(exclude={"undo", "undo_log"})
    b0 = apply(b1.state, {"type": "undo"})
    assert b0.state.model_dump(exclude={"undo", "undo_log"}) == s.model_dump(exclude={"undo", "undo_log"})
    assert b0.state.undo is None and {"type": "undo"} not in b0.legal


def test_a_move_that_shows_something_hidden_cannot_be_taken_back_and_ends_the_chance() -> None:
    """UNDO-01: a card from the deck, or a card from the row (its replacement comes from the deck), is a reveal."""
    s, pl = ready()
    r1 = apply(s, {"type": "move_energy"})
    assert {"type": "undo"} in r1.legal
    r2 = apply(r1.state, {"type": "buy_card", "source": "row:0"})
    assert {"type": "undo"} not in r2.legal and r2.state.undo is None and r2.state.undo_log == []
    r3 = apply(r2.state, {"type": "move_energy"})  # the chance starts again from here
    assert {"type": "undo"} in r3.legal
    back = apply(r3.state, {"type": "undo"})
    assert back.state.model_dump(exclude={"undo", "undo_log"}) == r2.state.model_dump(exclude={"undo", "undo_log"})


def test_the_page_is_told_which_moves_cannot_be_taken_back() -> None:
    """UNDO-01: the notes mark the moves that show something hidden, so the page can ask for a confirmation."""
    s, pl = ready()
    legal = legal_moves(s)
    notes = move_notes.notes(s, legal)
    flagged = {m["type"] + str(m.get("source", "")) for m, n in zip(legal, notes, strict=True) if n and n.get("irreversible")}
    assert {"buy_carddeck", "buy_cardrow:0", "pass"} <= flagged
    assert not any(n and n.get("irreversible") for m, n in zip(legal, notes, strict=True) if m["type"] in ("move_energy", "launch", "scan"))


def test_finishing_a_scan_refills_the_row_and_cannot_be_taken_back() -> None:
    """SCAN-03, A-026: the row is refilled after the whole scan, from the deck."""
    s, pl = ready()
    r = apply(s, {"type": "scan"})
    r = apply(r.state, {"type": "scan_earth", "sector": solar.earth(r.state)[1]})
    r = apply(r.state, {"type": "scan_discard", "source": "row:0"})
    assert len(r.state.card_row) == 2
    assert {"type": "undo"} in r.legal  # nothing hidden so far
    while r.state.pending and not [m for m in r.legal if m["type"] == "scan_done"]:
        r = apply(r.state, decisions(r.legal)[0])
    done = {"type": "scan_done"}
    assert move_notes.notes(r.state, [done])[0] == {"irreversible": True}
    r = apply(r.state, done)
    assert len(r.state.card_row) == 3 and {"type": "undo"} not in r.legal


def test_a_free_action_can_interrupt_the_main_action_and_the_row_gap_of_a_scan_stays() -> None:
    """FREE-00, A-026: buying a display card with publicity during a scan replaces only the card bought; the scan's gap waits."""
    s, pl = ready()
    r = apply(s, {"type": "scan"})
    r = apply(r.state, {"type": "scan_earth", "sector": solar.earth(r.state)[1]})
    r = apply(r.state, {"type": "scan_discard", "source": "row:0"})
    while r.state.pending[0].kind == "signal":
        r = apply(r.state, r.legal[0])
    assert r.state.pending[0].kind == "scan_step" and len(r.state.card_row) == 2
    free = [m for m in r.legal if m["type"] in FREE_TYPES]
    assert {"type": "buy_card", "source": "row:0"} in free  # during the main action
    bought = r.state.card_row[0]
    r2 = apply(r.state, {"type": "buy_card", "source": "row:0"})
    assert bought in r2.state.players[pl].hand
    assert len(r2.state.card_row) == 2  # one replaced at once, the scan's gap is still open
    assert r2.state.pending[0].kind == "scan_step" and r2.state.stashed == []  # back to the scan
    r3 = apply(r2.state, {"type": "scan_done"})
    assert len(r3.state.card_row) == 3


def test_a_free_action_cannot_interrupt_another_free_action() -> None:
    """FREE-00: the decisions of a free action are answered first, and no other free action is offered meanwhile."""
    s, pl = ready()
    s.players[pl].data_pool = 3
    s.players[pl].computer = [True, True, True, False, False, False]  # the next space lets the player tuck a card (BOARD-71)
    r = apply(s, {"type": "scan"})  # a main action with decisions pending
    assert r.state.pending[0].kind == "scan_step"
    r2 = apply(r.state, {"type": "place_data"})  # a free action in the middle of it
    assert r2.state.pending[0].kind == "income_tuck" and r2.state.free_active and r2.state.stashed
    assert not [m for m in r2.legal if m["type"] in FREE_TYPES]
    r3 = apply(r2.state, {"type": "skip_tuck"})
    assert r3.state.pending[0].kind == "scan_step" and not r3.state.free_active and not r3.state.stashed
    assert [m for m in r3.legal if m["type"] in FREE_TYPES]


def test_sectors_are_resolved_right_after_the_main_action_not_at_the_end_of_the_turn() -> None:
    """SECTOR-10, TURN-05, A-005: the free actions that follow cannot change who wins the sector."""
    s, pl = ready()
    sector = solar.earth(s)[1]
    sec = s.sectors[sector]
    sec.markers = [1 - pl] * (sec.capacity - 1)  # one signal short of completing the sector of Earth, then the scan marks it
    sec.data_remaining = 1
    r = apply(s, {"type": "scan"})
    r = apply(r.state, {"type": "scan_earth", "sector": sector})
    while r.state.pending:
        if any(m["type"] == "scan_done" for m in r.legal):
            r = apply(r.state, {"type": "scan_done"})
        else:
            r = apply(r.state, decisions(r.legal)[0])
    assert r.state.main_done and r.state.stage is None
    assert r.state.completed == [] and r.state.sectors[sector].winners  # resolved already, the turn is not over
    assert {"type": "end_turn"} in r.legal and [m for m in r.legal if m["type"] in FREE_TYPES]
    assert r.state.current_player == pl
