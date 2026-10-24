"""CARD-12, CARD-15: a mission circle that was covered (or whose mission is complete) is not offered again by a second decision."""

from test_engine import begin, with_state

from seti_engine import card_defs
from seti_engine.engine import apply, legal_moves
from seti_engine.models import Decision, MissionState, Options


def test_a_circle_covered_by_one_decision_is_not_offered_by_the_next() -> None:
    """CARD-14: one circle at a time; the effect must trigger again to cover another."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    cid = next(c for c, d in card_defs.CARDS.items() if d.get("mission", {}).get("kind") == "trigger" and len(d["mission"]["circles"]) == 2)
    s.players[pl].missions = [MissionState(card=cid, kind="trigger", used=[True, False])]
    both = Decision(kind="mission_trigger", player=pl, data={"options": [[cid, 1]]})
    s.pending = [both, both.model_copy(deep=True)]
    first = with_state(s)
    assert {"type": "cover", "card": cid, "circle": 1} in first.legal
    done = apply(first.state, {"type": "cover", "card": cid, "circle": 1})  # the last circle: the mission is complete and leaves the player
    assert cid in done.state.players[pl].completed_missions
    assert not any(m["type"] == "cover" for m in legal_moves(done.state))  # nothing to cover: only declining is left
    assert {"type": "decline_cover"} in legal_moves(done.state)


def test_a_species_with_its_three_spaces_full_is_revealed_when_the_turn_is_over_even_if_the_flag_was_lost() -> None:
    """ALIEN-01: two neutral markers and the rival's marker (a solo game) fill the spaces; the species turns face up when the turn ends."""
    from seti_engine.engine import start

    r = start(Options(players=1, difficulty=3, seed=11))
    while r.state.phase == "setup" or r.state.pending:
        r = apply(r.state, r.legal[0])
    s = r.state.model_copy(deep=True)
    s.species[1].discovery_spaces = ["p1", "n", "n"]
    s.species[1].complete = False  # the flag is not what decides
    assert not s.species[1].discovered
    done = apply(s, {"type": "end_turn"} if {"type": "end_turn"} in legal_moves(s) else {"type": "pass"})
    state = done.state
    while state.pending and not state.species[1].discovered:
        state = apply(state, legal_moves(state)[0]).state
    assert state.species[1].discovered


def test_the_card_taken_for_a_covered_circle_is_credited_to_the_circle_not_to_the_card_that_was_played() -> None:
    """CARD-12 (the log): a circle's reward that waits for a choice is named after the mission, also while another card is being played."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].missions = [MissionState(card="76", kind="trigger", used=[False, False, False])]
    s.playing = next(c for c in s.players[pl].hand if c != "76")
    s.pending = [Decision(kind="mission_trigger", player=pl, data={"options": [["76", 2]]}, source={"kind": "card", "card": s.playing})]
    covered = apply(with_state(s).state, {"type": "cover", "card": "76", "circle": 2})
    assert covered.state.pending[0].kind == "take_card" and covered.state.pending[0].source == {"kind": "mission", "card": "76"}
    taken = apply(covered.state, {"type": "take_card", "source": "deck"})
    sources = [e["source"] for e in taken.events if isinstance(e.get("source"), dict)]
    assert {"kind": "mission", "card": "76"} in sources
    assert not any(x.get("kind") == "card" for x in sources)
