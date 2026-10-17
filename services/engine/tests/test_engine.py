"""Turn and round flow, passing, income, launching, movement and the free actions (TURN, PASS, ROUND, INCOME, LAUNCH, MOVE, FREE rules)."""

import random

import pytest

from seti_engine import effects, solar, tables
from seti_engine.engine import IllegalAction, StepResult, apply, legal_moves, start
from seti_engine.models import GameState, Options, Probe


def begin(players: int = 3, seed: int = 4) -> StepResult:
    r = start(Options(players=players, seed=seed))
    while r.state.pending:  # each player tucks their first card (SETUP-36)
        r = apply(r.state, r.legal[0])
    return r


def total_cards(s: GameState) -> int:
    """Main-deck cards (alien cards are counted separately: they live in their own decks and hands)."""
    piles = [s.deck, s.discard, s.card_row, s.aside, *s.end_of_round_stacks]
    for p in s.players:
        piles += [p.hand, p.tucked, p.missions and [m.card for m in p.missions] or [], p.completed_missions, p.end_cards, p.kept_cards]
    n = sum(1 for pile in piles for c in pile if not c.startswith("ET."))
    if (
        s.playing
        and not s.playing.startswith("ET.")
        and s.playing not in [c for p in s.players for c in p.tucked + [m.card for m in p.missions]]
    ):
        n += 1
    return n


def do(r: StepResult, kind: str, **kw: object) -> StepResult:
    return apply(r.state, {"type": kind, **kw})


def decisions(moves: list[dict[str, object]]) -> list[dict[str, object]]:
    """The moves that answer the pending decision, without the free actions that may interrupt it (FREE-00) and the undo (UNDO-01)."""
    from seti_engine.engine import FREE_TYPES

    return [m for m in moves if m["type"] not in FREE_TYPES and m["type"] != "undo"]


def with_state(s: GameState) -> StepResult:
    return StepResult(state=s, events=[], legal=legal_moves(s))


def test_setup_tuck_gives_the_income_resource_and_starts_play() -> None:
    r = start(Options(players=2, seed=1))
    p0 = r.state.pending[0].player
    card = r.legal[0]["card"]
    before = r.state.players[p0]
    income = tables.cards()[card]["income"]
    r2 = apply(r.state, r.legal[0])
    p = r2.state.players[p0]
    assert card in p.tucked and card not in p.hand
    if income == "credit":
        assert p.credits == before.credits + 1
    elif income == "energy":
        assert p.energy == before.energy + 1
    else:
        assert len(p.hand) == len(before.hand)  # tucked one, drew one
    assert r2.state.phase == "setup"
    r3 = apply(r2.state, r2.legal[0])
    assert r3.state.phase == "play" and total_cards(r3.state) == 138


def test_illegal_action_is_rejected() -> None:
    r = begin()
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "launch", "extra": 1})
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "end_turn"})  # the main action comes first


def test_launch_costs_two_credits_and_uses_the_main_action() -> None:
    r = begin()
    pl = r.state.current_player
    r2 = do(r, "launch")
    p = r2.state.players[pl]
    assert p.credits == r.state.players[pl].credits - 2
    probe = r2.state.probes[0]
    assert (probe.ring, probe.sector) == solar.earth(r2.state)  # LAUNCH-01
    assert {"type": "launch"} not in r2.legal and {"type": "pass"} not in r2.legal and {"type": "end_turn"} in r2.legal
    r3 = do(r2, "end_turn")
    assert r3.state.current_player != pl


def test_probe_limit_is_one_by_default_and_two_with_the_tech() -> None:
    """LAUNCH-02, LAUNCH-03."""
    r = begin(2)
    pl = r.state.current_player
    r = do(do(r, "launch"), "end_turn")
    r = do(r, "pass")  # the other player passes
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    assert r.state.current_player == pl and {"type": "launch"} not in r.legal
    s = r.state.model_copy(deep=True)
    s.players[pl].techs.append("probe-dot")
    assert {"type": "launch"} in legal_moves(s)


def test_move_probe_costs_energy_and_visiting_a_planet_gives_publicity() -> None:
    """FREE-01, MOVE-01, MOVE-05: 1 energy per movement; entering a planet or comet space gives 1 publicity (not Earth)."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    ring, sector = solar.find_cell(s, "PLANET:MERCURY")
    nb = solar.adjacent(ring, sector)[0]
    assert solar.visible(s, *nb)[1] != "ASTEROID"
    s.probes.append(Probe(id="x", player=pl, ring=nb[0], sector=nb[1]))
    s.players[pl].energy = 3
    r = do(with_state(s), "move_energy")
    assert r.state.players[pl].movement == 1 and r.state.players[pl].energy == 2
    pub = r.state.players[pl].publicity
    r = do(r, "move_probe", probe="x", to=[ring, sector])
    assert r.state.players[pl].movement == 0
    assert r.state.players[pl].publicity == min(10, pub + 1)


def test_leaving_asteroids_costs_one_more_unless_the_tech() -> None:
    """MOVE-02, TECH-PT03."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    ring, sector = next((ri, se) for ri in range(1, 5) for se in range(8) if solar.visible(s, ri, se)[1] == "ASTEROID")
    s.probes.append(Probe(id="x", player=pl, ring=ring, sector=sector))
    s.players[pl].movement = 1
    assert not [m for m in legal_moves(s) if m["type"] == "move_probe"]
    s.players[pl].movement = 2
    assert [m for m in legal_moves(s) if m["type"] == "move_probe"]
    s.players[pl].movement = 1
    s.players[pl].techs.append("probe-link")
    assert [m for m in legal_moves(s) if m["type"] == "move_probe"]


def test_buy_a_card_for_three_publicity() -> None:
    """FREE-06 and the owner note of 2026-10-13 (available at any publicity of 3 or more)."""
    r = begin(2)
    pl = r.state.current_player
    hand = len(r.state.players[pl].hand)
    r2 = do(r, "buy_card", source="row:0")
    p = r2.state.players[pl]
    assert p.publicity == r.state.players[pl].publicity - 3 and len(p.hand) == hand + 1
    assert len(r2.state.card_row) == 3  # replaced at once (RES-04)
    assert total_cards(r2.state) == 138


def test_resource_exchange() -> None:
    """RES-06 / FREE-05: two of one resource for one of another."""
    r = begin(2)
    pl = r.state.current_player
    r2 = do(r, "exchange", give="credit", get="energy")
    assert (r2.state.players[pl].credits, r2.state.players[pl].energy) == (r.state.players[pl].credits - 2, r.state.players[pl].energy + 1)


def test_place_data_and_the_computer_spaces() -> None:
    """FREE-03, FREE-04: space 2 gives 1 publicity, space 4 lets the player tuck a card; data goes left to right."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].data_pool = 4
    s.players[pl].publicity = 4
    r = do(with_state(s), "place_data")
    assert r.state.players[pl].computer[:2] == [True, False] and r.state.players[pl].publicity == 4
    r = do(r, "place_data")
    assert r.state.players[pl].publicity == 5
    r = do(do(r, "place_data"), "place_data")
    assert r.state.pending and r.state.pending[0].kind == "income_tuck"  # FAQ-04: resolve it before any other free action
    assert all(m["type"] in ("tuck", "skip_tuck") for m in decisions(r.legal))
    hand = len(r.state.players[pl].hand)
    r = apply(r.state, {"type": "skip_tuck"})
    assert len(r.state.players[pl].hand) == hand


def test_discard_a_card_for_its_corner() -> None:
    """FREE-02."""
    r = begin(2)
    pl = r.state.current_player
    card = next(c for c in r.state.players[pl].hand if tables.cards()[c]["free"])
    (kind, n), *_ = tables.cards()[card]["free"]
    r2 = do(r, "discard_free", card=card)
    assert card in r2.state.discard and card not in r2.state.players[pl].hand
    p0, p1 = r.state.players[pl], r2.state.players[pl]
    gained = {
        "move": p1.movement - p0.movement,
        "publicity": p1.publicity - p0.publicity,
        "data": p1.data_pool - p0.data_pool,
        "score": p1.score - p0.score,
    }[kind]
    assert gained == (min(n, 10 - p0.publicity) if kind == "publicity" else n)


def test_passing_first_rotates_and_takes_a_round_card() -> None:
    """PASS-01 to PASS-04."""
    r = begin(3)
    pl = r.state.current_player
    hand = len(r.state.players[pl].hand)
    r2 = do(r, "pass")
    if r2.state.pending[0].kind == "discard_to_four":  # hand size is irrelevant here: discard first if needed
        while r2.state.pending[0].kind == "discard_to_four":
            r2 = apply(r2.state, r2.legal[0])
    assert r2.state.rotations == 1  # the first to pass rotates (PASS-03)
    assert r2.state.pending[0].kind == "take_round_card"
    assert len(r2.legal) == 4 and all(m["type"] == "take_round_card" for m in r2.legal)  # n + 1 cards to choose from
    chosen = r2.legal[0]["card"]
    r3 = apply(r2.state, r2.legal[0])
    assert chosen in r3.state.players[pl].hand and len(r3.state.players[pl].hand) == min(hand, 4) + 1
    assert r3.state.current_player != pl and r3.state.players[pl].passed
    r4 = do(r3, "pass")  # the second player to pass does not rotate again
    while r4.state.pending and r4.state.pending[0].kind == "discard_to_four":
        r4 = apply(r4.state, r4.legal[0])
    assert r4.state.rotations == 1 and len(r4.legal) == 3


def test_discard_down_to_four_when_passing() -> None:
    """PASS-02."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    while len(s.players[pl].hand) < 7:
        s.players[pl].hand.append(s.deck.pop())
    r = do(with_state(s), "pass")
    assert r.state.pending[0].kind == "discard_to_four"
    r = apply(r.state, r.legal[0])
    r = apply(r.state, r.legal[0])
    r = apply(r.state, r.legal[0])
    assert len(r.state.players[pl].hand) == 4 and r.state.pending[0].kind == "take_round_card"


def run_round(r: StepResult) -> StepResult:
    """Everyone passes at once, always choosing the first option."""
    rnd = r.state.round
    while r.state.round == rnd and r.state.phase != "finished":
        if r.state.pending:
            move = r.legal[0]
        elif not r.state.main_done:
            move = {"type": "pass"}
        else:
            move = {"type": "end_turn"}
        r = apply(r.state, move)
    return r


def test_round_end_gives_income_and_moves_the_starting_player() -> None:
    """ROUND-01 to ROUND-03, INCOME-03."""
    r = begin(2)
    first = r.state.start_player
    credits = [p.credits for p in r.state.players]
    tucked = [list(p.tucked) for p in r.state.players]
    r = run_round(r)
    s = r.state
    assert s.round == 2 and s.start_player == (first + 1) % 2 and s.current_player == s.start_player
    assert not any(p.passed for p in s.players) and not s.first_pass_done
    for i, p in enumerate(s.players):
        extra = sum(1 for c in tucked[i] if tables.cards()[c]["income"] == "credit")
        assert p.credits == credits[i] + 3 + extra  # nobody spent credits in this round
    assert total_cards(s) == 138


def test_the_game_ends_after_five_rounds() -> None:
    """GAME-01, ROUND-03, PASS-05: five rounds, no income after the fifth, no end-of-round card in round 5."""
    r = begin(2)
    for expected in range(1, 6):
        assert r.state.round == expected
        r = run_round(r)
    assert r.state.phase == "finished" and len(r.state.final_scores) == len(r.state.players) and r.state.winners and r.legal == []


def test_milestone_choice_of_a_gold_tile_at_25() -> None:
    """MILE-02, MILE-03: a player cannot choose the same tile twice."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].score = 24
    effects.gain_score(s, s.players[pl], 3)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.pending[0].kind == "gold_choice" and len(r.legal) == 4
    r = apply(r.state, {"type": "choose_gold", "tile": "Mission"})
    assert r.state.gold_tiles[1].markers == [pl] and r.state.current_player != pl


def test_neutral_milestone_marker_goes_to_the_leftmost_discovery_space() -> None:
    """MILE-05, A-008, A-009, FAQ-33: one marker per crossing."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].score = 19
    effects.gain_score(s, s.players[pl], 2)
    s.main_done = True
    r = do(with_state(s), "end_turn")
    assert r.state.species[0].discovery_spaces == ["n", None, None]
    assert r.state.neutral_markers == {"20": 1, "30": 2}


# ---------------------------------------------------------------------------------------------------------------------------------
# whole-game properties
# ---------------------------------------------------------------------------------------------------------------------------------


def check_invariants(s: GameState) -> None:
    assert total_cards(s) == 138
    for p in s.players:
        assert p.credits >= 0 and p.energy >= 0 and p.movement >= 0
        assert 0 <= p.publicity <= 10 and 0 <= p.data_pool <= (999 if s.rival and p.index == s.rival.index else 6)  # SOLO-17
        assert (
            len([pr for pr in s.probes if pr.player == p.index and not pr.capsule]) <= (2 if "probe-dot" in p.techs else 1) + 2
        )  # card #9 ignores the limit (FAQ-C009)
    for pr in s.probes:
        solar.visible(s, pr.ring, pr.sector)


def play_randomly(players: int, seed: int, policy_seed: int) -> tuple[StepResult, list[dict[str, object]]]:
    rnd = random.Random(policy_seed)
    r = start(Options(players=players, seed=seed))
    log: list[dict[str, object]] = []
    while r.legal:
        move = rnd.choice(r.legal)
        log.append(move)
        r = apply(r.state, move)
        check_invariants(r.state)
        assert len(log) < 20000, "game did not terminate"
    return r, log


@pytest.mark.parametrize("players", [2, 3, 4])
def test_random_games_always_finish_and_keep_the_invariants(players: int) -> None:
    for seed in range(8):
        r, _ = play_randomly(players, seed, seed + 100)
        assert r.state.phase == "finished" and r.state.round == 5


def test_a_game_replays_exactly_from_its_seed_and_action_log() -> None:
    """D8: event sourcing. The same options and actions always give the same final state."""
    r1, log = play_randomly(3, 21, 7)
    r = start(Options(players=3, seed=21))
    for a in log:
        r = apply(r.state, a)
    assert r.state.model_dump() == r1.state.model_dump()


PROGRESS_TYPES = {
    "play_card", "orbit", "land", "land_free", "analyze", "place_data", "scan", "research", "complete_mission", "cover",
    "scan_earth", "scan_discard", "scan_hand_discard", "scan_mercury",
}  # fmt: skip


def play_towards_progress(players: int, seed: int) -> StepResult:
    """A random player that prefers moves that make progress, so that traces, species discoveries and missions do happen."""
    rnd = random.Random(seed)
    r = start(Options(players=players, seed=seed))
    for _ in range(20000):
        if not r.legal:
            break
        good = [m for m in r.legal if m["type"] in PROGRESS_TYPES or (m["type"] == "place_trace" and m["space"] != "overflow")]
        other = [m for m in r.legal if m["type"] != "exchange"]  # the many ways to exchange cards would crowd out the rest
        move = rnd.choice(good) if good and rnd.random() < 0.8 else rnd.choice(other or r.legal)
        r = apply(r.state, move)
        check_invariants(r.state)
    return r


@pytest.mark.parametrize("players", [2, 3, 4])
def test_progress_seeking_games_finish_and_discover_species(players: int) -> None:
    discovered = 0
    for seed in range(6):
        r = play_towards_progress(players, seed)
        assert r.state.phase == "finished"
        discovered += sum(1 for x in r.state.species if x.discovered)
    assert discovered >= 1


def test_exchange_two_cards_for_a_resource_or_a_card() -> None:
    """RES-06, FREE-05 (p.18 'discard 2 cards to get 1 credit, 1 energy, or even 1 new card'): the cards go to the discard pile."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    p = s.players[pl]
    p.hand = ["1", "2", "3"]
    base = with_state(s)
    gives = [m for m in base.legal if m["type"] == "exchange" and m["give"] == "card"]
    assert {tuple(m["cards"]) for m in gives} == {("1", "2"), ("1", "3"), ("2", "3")}  # pairs of the hand, no card twice
    assert {m["get"] for m in gives} == {"credit", "energy", "card"}
    assert {m["source"] for m in gives if m["get"] == "card"} == {"deck", *(f"row:{i}" for i in range(len(s.card_row)))}
    r = do(base, "exchange", give="card", cards=["1", "3"], get="credit")
    q = r.state.players[pl]
    assert q.hand == ["2"] and q.credits == p.credits + 1 and r.state.discard[-2:] == ["1", "3"]
    row_first = s.card_row[0]
    r = do(base, "exchange", give="card", cards=["2", "3"], get="card", source="row:0")
    q = r.state.players[pl]
    assert q.hand == ["1", row_first] and len(r.state.card_row) == len(s.card_row)  # the row is refilled (RES-04)
    r = do(base, "exchange", give="card", cards=["1", "2"], get="energy")
    assert r.state.players[pl].energy == p.energy + 1


def test_exchange_two_credits_or_energy_for_a_card() -> None:
    """RES-06: two credits or two energy also buy one card, from the card row or the top of the deck."""
    s = begin(2).state.model_copy(deep=True)
    pl = s.current_player
    s.players[pl].credits, s.players[pl].energy = 2, 0
    base = with_state(s)
    hand = len(s.players[pl].hand)
    r = do(base, "exchange", give="credit", get="card", source="deck")
    assert r.state.players[pl].credits == 0 and len(r.state.players[pl].hand) == hand + 1
    assert not any(m["type"] == "exchange" and m["give"] == "energy" for m in base.legal)
