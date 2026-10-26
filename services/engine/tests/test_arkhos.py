"""Arkhos (Space Agencies): EXP-ARK-01 to EXP-ARK-07."""

from seti_engine import arkhos, rewards, species, tables
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import Decision, GameState, Options
from seti_engine.projection import project


def game(players: int = 2, seed: int = 1) -> GameState:
    s = start(Options(players=players, seed=seed, expansion=True)).state.model_copy(deep=True)
    s.phase = "play"
    s.pending = []
    s.species[0].species = "arkhos"
    s.species[0].board = species.new_board("arkhos")
    return s


def discovered(markers: tuple[str | None, str | None, str | None] = ("p0", None, None)) -> GameState:
    s = game()
    s.species[0].discovery_spaces = list(markers)
    species._discover(s, 0, [])
    return s


def test_discovery_prepares_the_exploration_deck_and_deals_security_cards() -> None:  # EXP-ARK-01, EXP-ARK-03
    s = discovered(("p0", "p1", "p1"))
    extra = s.species[0].extra
    assert len(extra["explore_aside"]) == 4
    assert len(set(extra["explore_deck"]) | set(extra["explore_aside"]) | set(extra["explore_discard"])) == 9
    assert len(extra["explore_discard"]) == 3  # one minor reward for each of the three markers (EXP-ARK-01)
    for p in s.players:
        assert sorted(p.security) == ["blue", "pink", "yellow"]
        for color, cid in p.security.items():
            assert next(x for x in tables.arkhos()["security"] if x["id"] == cid)["trace"] == color


def test_an_exploration_card_gives_its_minor_or_major_reward() -> None:  # EXP-ARK-02, EXP-ARK-04
    s = discovered()
    p = s.players[0]
    s.species[0].extra["explore_deck"] = ["ET 40", "ET 36"]
    score = p.score
    arkhos.explore(s, p, "minor", [])
    assert p.score - score == 4  # ET 40: 4 VP
    pub = p.publicity
    arkhos.explore(s, p, "major", [])
    assert p.publicity - pub == 3 and any(
        d.kind == "trace" and d.data["color"] == "blue" for d in s.pending
    )  # ET 36: 3 publicity, blue trace


def test_an_empty_exploration_deck_is_rebuilt_from_the_discards_and_the_aside_cards() -> None:  # EXP-ARK-04
    s = discovered()
    extra = s.species[0].extra
    extra["explore_discard"] = [c for c in (x["id"] for x in tables.arkhos()["exploration"]) if c not in extra["explore_aside"]]
    extra["explore_deck"] = []
    arkhos.explore(s, s.players[0], "minor", [])
    assert (
        len(extra["explore_deck"]) == 4 and len(extra["explore_aside"]) == 4 and len(extra["explore_discard"]) == 1
    )  # 5 drawn, 1 revealed


def test_only_level_zero_is_open_until_a_security_card_is_breached() -> None:  # EXP-ARK-05, EXP-ARK-06
    s = discovered()
    p = s.players[0]
    levels = {m["index"] for m in rewards.trace_moves(s, _trace(p, "pink")) if m["space"] == "board"}
    assert levels == {0}
    p.security.pop("pink")  # one breached
    levels = {m["index"] for m in rewards.trace_moves(s, _trace(p, "pink")) if m["space"] == "board"}
    assert levels == {0, 1}
    p.security.clear()  # all breached: every space is open
    assert arkhos.access(p) == 3


def _trace(p, color):  # type: ignore[no-untyped-def]
    from seti_engine.models import Decision

    return Decision(kind="trace", player=p.index, data={"color": color, "slots": [0]})


def test_marking_an_overflow_space_lets_the_player_breach_that_color() -> None:  # EXP-ARK-06, EXP-ARK-07
    s = discovered()
    p = s.players[0]
    card = p.security["yellow"]
    rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": "yellow"}, [])
    d = s.pending[-1]
    assert d.kind == "breach" and d.data["color"] == "yellow"
    s.phase, s.current_player = "play", 0
    r = apply(s, {"type": "breach"})
    assert card in r.state.players[0].hand and "yellow" not in r.state.players[0].security
    breach_event = next(e for e in r.events if e["type"] == "breach")
    assert breach_event["color"] == "yellow" and "card" not in breach_event  # the log names the color, not the card (rule 6)
    declined = apply(s, {"type": "skip_breach"}).state
    assert "yellow" in declined.players[0].security and card not in declined.players[0].hand


def test_two_overflow_marks_of_one_color_breach_the_card_once() -> None:  # EXP-ARK-06 (a crash found by the training on a real game)
    s = discovered()
    p = s.players[0]
    card = p.security["yellow"]
    rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": "yellow"}, [])
    rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": "yellow"}, [])
    assert [d.kind for d in s.pending].count("breach") == 2
    s.phase, s.current_player = "play", 0
    r = apply(s, {"type": "breach"})
    assert card in r.state.players[0].hand
    assert not [d for d in r.state.pending if d.kind == "breach"]  # the second one is void: no card is left to breach
    # a decision that was left over (a game saved by the earlier engine) can only be declined, and declining does not fail
    stale = r.state.model_copy(deep=True)
    stale.pending = [Decision(kind="breach", player=0, data={"color": "yellow"})]
    types = {m["type"] for m in legal_moves(stale)}
    assert "skip_breach" in types and "breach" not in types
    arkhos.breach(stale, stale.players[0], stale.pending.pop(0), {"type": "breach"}, [])  # answered anyway: no error
    assert not stale.players[0].security.get("yellow")


def test_a_security_card_gives_a_minor_reward_when_discarded_and_a_major_one_when_played() -> None:  # EXP-ARK-07
    s = discovered()
    s.current_player = 0
    p = s.players[0]
    cid = p.security.pop("pink")
    p.hand.append(cid)
    p.credits = 5
    assert {"type": "discard_free", "card": cid} in legal_moves(s)
    assert {"type": "play_card", "card": cid} in legal_moves(s)
    s.species[0].extra["explore_deck"] = ["ET 36", "ET 39"]
    r = apply(s, {"type": "discard_free", "card": cid})
    assert r.state.players[0].publicity == p.publicity + 2  # ET 36 minor: 2 publicity
    s2 = s.model_copy(deep=True)
    r = apply(s2, {"type": "play_card", "card": cid})
    assert r.state.players[0].credits == 3 and r.state.players[0].publicity == p.publicity + 3  # 2 credits, ET 36 major: 3 publicity


def test_the_security_cards_and_the_deck_are_hidden() -> None:  # CLAUDE.md rule 6
    s = discovered()
    seen = project(s, 1).state
    assert set(seen.players[0].security.values()) == {"?"}
    assert set(seen.species[0].extra["explore_deck"]) <= {"?"} and set(seen.species[0].extra["explore_aside"]) == {"?"}
    mine = project(s, 0).state
    assert "?" not in mine.players[0].security.values()


def test_random_games_with_arkhos_finish() -> None:  # EXP-ARK-01 to EXP-ARK-07, fuzz
    import random

    for seed in range(4):
        rng = random.Random(seed)
        s = start(Options(players=2 + seed % 3, seed=seed, expansion=True)).state
        s.species[0].species = "arkhos"
        s.species[0].board = species.new_board("arkhos")
        s.species[0].discovery_spaces = ["p0", "p1", "p0"]  # found after the first turn, so that the whole game is played with Arkhos
        s.species[0].complete = True
        for _ in range(9000):
            if s.phase == "finished":
                break
            moves = [m for m in legal_moves(s) if m["type"] != "undo"]
            s = apply(s, rng.choice(moves)).state
        assert s.phase == "finished"
        assert s.species[0].discovered


def test_the_gains_of_an_exploration_card_are_logged_under_that_card() -> None:  # EXP-ARK-02, the log
    from seti_engine import trail

    s = discovered()
    p = s.players[0]
    s.species[0].extra["explore_deck"] = ["ET 40"]
    s.trail = []
    arkhos.explore(s, p, "minor", [])
    gains = trail.events_of(s)
    assert gains and gains[0]["source"] == {"kind": "explore", "card": "ET 40", "level": "minor"}


def test_an_exploration_reveals_the_next_card_so_it_cannot_be_taken_back() -> None:  # EXP-ARK-02, EXP-ARK-04, UNDO-01
    from seti_engine.engine import _reveals

    s = discovered()
    before = s.model_copy(deep=True)
    arkhos.explore(s, s.players[0], "minor", [])
    assert _reveals(before, s)  # the deck of the exploration cards changed: the move showed something that was hidden
