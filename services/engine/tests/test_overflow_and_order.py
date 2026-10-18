"""Owner rulings of 2026-10-14: place pool data before data that would overflow the pool (RES-01), and choose the order in which
the sectors completed during a turn are resolved (TURN-05, SECTOR-10)."""

import pytest
from test_engine import begin, with_state

from seti_engine import effects, rewards
from seti_engine.engine import _advance, apply, legal_moves
from seti_engine.models import GameState


def in_play(pool: int) -> tuple[GameState, int]:
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].data_pool = pool
    return s, pl


def test_res01_a_gain_that_would_overflow_waits_for_the_player_to_place_data() -> None:
    """RES-01: the player may place pool data into the computer first."""
    s, pl = in_play(6)
    effects.gain_data(s, s.players[pl], 2)
    assert s.players[pl].data_pool == 6 and s.pending[0].kind == "data_overflow"
    moves = legal_moves(s)
    assert {"type": "place_data"} in moves and {"type": "data_done"} in moves
    r = apply(s, {"type": "place_data"})  # 5 in the pool: the gain of 2 still overflows by 1
    assert r.state.players[pl].computer[0] and r.state.players[pl].data_pool == 5
    assert r.state.pending[-1].kind == "data_overflow"
    r = apply(r.state, {"type": "place_data"})  # 4 in the pool: now both fit
    while r.state.pending and r.state.pending[0].kind != "data_overflow":
        r = apply(r.state, r.legal[0])  # (a computer space may ask about a tuck)
    assert r.state.players[pl].data_pool == 6 and not any(d.kind == "data_overflow" for d in r.state.pending)


def test_res01_the_player_may_decline_and_the_extra_data_is_lost() -> None:
    s, pl = in_play(5)
    effects.gain_data(s, s.players[pl], 3)
    r = apply(s, {"type": "data_done"})
    assert r.state.players[pl].data_pool == 6 and not r.state.pending


def test_res01_no_question_when_nothing_overflows_or_nothing_can_be_placed() -> None:
    s, pl = in_play(4)
    effects.gain_data(s, s.players[pl], 2)
    assert s.players[pl].data_pool == 6 and not s.pending
    full, fp = in_play(6)
    full.players[fp].computer = [True] * len(full.players[fp].computer)
    effects.gain_data(full, full.players[fp], 1)
    assert full.players[fp].data_pool == 6 and not full.pending  # no room in the computer: discarded at once


def test_res01_only_the_player_whose_turn_it_is_is_asked() -> None:
    """The ruling covers the player's own turn (FREE-03): a gain out of turn is capped at once."""
    s, pl = in_play(6)
    other = 1 - pl
    s.players[other].data_pool = 6
    effects.gain_data(s, s.players[other], 1)
    assert not s.pending and s.players[other].data_pool == 6


def test_res01_a_scan_signal_gives_the_choice() -> None:
    """RES-01 through SECTOR-01: marking a signal with a full pool asks before the data is taken."""
    s, pl = in_play(6)
    rewards.mark_signal(s, s.players[pl], 0, [])
    assert s.pending[0].kind == "data_overflow" and s.sectors[0].markers == [pl]


def test_turn05_the_player_chooses_the_order_of_completed_sectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """TURN-05, SECTOR-10: with several completed sectors the player picks the next one to resolve."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.completed, s.main_done, s.stage = [2, 5, 7], True, "turn_end"
    order: list[int] = []
    monkeypatch.setattr(rewards, "resolve_sector", lambda st, i, ev: order.append(i))
    _advance(s, [])
    assert s.pending[0].kind == "sector_order" and s.pending[0].player == pl
    assert legal_moves(s) == [{"type": "resolve_sector", "sector": i} for i in (2, 5, 7)]
    from seti_engine.move_notes import note

    picked = [note(s, m) for m in legal_moves(s)]  # the page shows each sector as a place on the board to click
    assert [n["sector"] for n in picked if n] == [2, 5, 7] and all(n and n["resolve"] for n in picked)
    r = apply(s, {"type": "resolve_sector", "sector": 7})
    assert order == [7] and r.state.pending[0].kind == "sector_order"
    assert legal_moves(r.state) == [{"type": "resolve_sector", "sector": i} for i in (2, 5)]
    r = apply(r.state, {"type": "resolve_sector", "sector": 5})
    assert order == [7, 5, 2]  # the last one is resolved without asking
    assert r.state.current_player != pl or not r.state.completed


def test_turn05_one_completed_sector_needs_no_question(monkeypatch: pytest.MonkeyPatch) -> None:
    s = begin(2).state.model_copy(deep=True)
    s.completed, s.main_done, s.stage = [4], True, "turn_end"
    seen: list[int] = []
    monkeypatch.setattr(rewards, "resolve_sector", lambda st, i, ev: seen.append(i))
    _advance(s, [])
    assert seen == [4] and not any(d.kind == "sector_order" for d in s.pending)
    _ = with_state
