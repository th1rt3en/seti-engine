"""The tracker of a view (INCOME-01, INCOME-03, ROUND-02, CARD-16, CARD-20) and the turn counter."""

from test_engine import begin

from seti_engine import projection, tables
from seti_engine.engine import apply


def test_income_is_the_income_card_plus_each_tucked_card() -> None:
    """INCOME-01, INCOME-03, ROUND-02: 3 credits, 2 energy and 1 card, plus what each tucked card gives."""
    s = begin(2).state.model_copy(deep=True)
    p = s.players[0]
    kinds = [tables.cards()[c]["income"] for c in p.tucked]
    t = projection.tracker(s, p)
    for k in ("credit", "energy", "card"):
        assert t.tucked[k] == kinds.count(k)
        assert t.income[k] == projection.INCOME_BASE[k] + kinds.count(k)
    assert t.score == p.score and t.missions_done == 0 and t.end_cards == 0


def test_the_tracker_counts_missions_and_end_cards_and_is_public() -> None:
    s = begin(3).state.model_copy(deep=True)
    s.players[1].completed_missions = ["1", "2", "3"]
    s.players[1].end_cards = ["95"]
    view = projection.project(s, viewer=0)  # another player's hand is hidden, their tracker is not
    assert len(view.trackers) == 3
    assert view.trackers[1].missions_done == 3 and view.trackers[1].end_cards == 1


def test_the_solo_rival_has_no_income() -> None:
    """A-025."""
    from seti_engine.engine import start
    from seti_engine.models import Options

    r = start(Options(players=1, seed=3, difficulty=2))
    s = r.state
    assert s.rival is not None
    rival_tracker = projection.tracker(s, s.players[s.rival.index])
    assert rival_tracker.income == {"credit": 0, "energy": 0, "card": 0}


def test_the_turn_counter_counts_turns_in_the_round_and_starts_again() -> None:
    r = begin(2)
    assert r.state.turn == 1 and r.state.round == 1
    first = r.state.current_player
    r = apply(r.state, {"type": "launch"})
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    r = apply(r.state, {"type": "end_turn"})
    assert r.state.current_player != first and r.state.turn == 2
    # both players pass: the round ends, and the counter starts again
    s = r.state
    while s.round == 1 and s.phase == "play":
        r = apply(s, {"type": "pass"})
        while r.state.pending:
            r = apply(r.state, r.legal[0])
        s = r.state
    assert s.round == 2 and s.turn == 1


def test_exertian_danger_is_public_for_the_board_and_private_for_the_cards() -> None:
    """ALIEN-EXE-06: the board danger and the number of cards played show to everyone; the danger of the played cards only to its owner."""
    from seti_engine import species
    from seti_engine.models import SpeciesSlot

    s = begin(3).state.model_copy(deep=True)
    s.species = [SpeciesSlot(species="exertians", board=species.new_board("exertians"), discovered=True), s.species[1]]
    s.players[1].exertian_played = ["ET.41", "ET.43"]  # danger 6 and 3
    s.species[0].board["pink"][4].append(1)  # a marker on the bottom tier: 3
    mine = projection.project(s, viewer=1).trackers[1]
    other = projection.project(s, viewer=0).trackers[1]
    assert (mine.danger_board, mine.exertian_played, mine.danger_cards) == (3, 2, 9)
    assert (other.danger_board, other.exertian_played, other.danger_cards) == (3, 2, None)
    assert species.danger(s, s.players[1]) == 12
