"""The promo cards SE EN 01 (Pluto) and SE EN 02 (Gateway to Mars): PROMO-01 to PROMO-03, A-001, FAQ-C300."""

from test_cards import give, put_probe, ready, settle
from test_engine import decisions, do, with_state

from seti_engine import card_defs
from seti_engine.engine import OUTERMOST_RING, StepResult, apply, legal_moves, start
from seti_engine.models import GameState, Options

PLUTO = "SE_EN_01"
GATEWAY = "SE_EN_02"


def play(s: GameState, cid: str) -> StepResult:
    give(s, cid)
    return do(with_state(s), "play_card", card=cid)


def outer_probe(s: GameState, pid: str = "o1", pl: int | None = None) -> None:
    from seti_engine.models import Probe

    pl = s.current_player if pl is None else pl
    s.probes.append(Probe(id=pid, player=pl, ring=OUTERMOST_RING, sector=2))


def with_pluto(credits: int = 9, energy: int = 9) -> tuple[GameState, int]:
    """A game in which the current player has played SE EN 01 and has a probe on the outermost ring."""
    s = ready(credits=credits, energy=energy)
    pl = s.current_player
    r = settle(play(s, PLUTO))
    s = r.state.model_copy(deep=True)
    s.main_done = False
    s.players[pl].credits, s.players[pl].energy = credits, energy
    outer_probe(s)
    return s, pl


def test_the_option_puts_both_promo_cards_in_the_deck() -> None:
    """PROMO-01, A-001: off, the deck holds the 138 base cards; on, the two promo cards too, drawn and played like any other."""
    off = start(Options(players=2, seed=1)).state
    on = start(Options(players=2, seed=1, promo_cards=True)).state

    def cards_of(s: GameState) -> list[str]:
        piles = (s.deck, s.card_row, *[p.hand for p in s.players], *s.end_of_round_stacks)
        return [c for pile in piles for c in pile if not c.startswith("ET.")]

    assert len(cards_of(off)) == 138 and len(cards_of(on)) == 140
    assert not {PLUTO, GATEWAY} & set(cards_of(off)) and {PLUTO, GATEWAY} <= set(cards_of(on))


def test_playing_not_a_planet_since_2006_keeps_the_card_and_makes_pluto_a_planet() -> None:
    """PROMO-02: SE EN 01 stays in front of its player; Pluto has one orbiter space and one lander space."""
    s = ready()
    pl = s.current_player
    r = settle(play(s, PLUTO))
    assert PLUTO in r.state.players[pl].kept_cards and PLUTO not in r.state.discard
    assert r.state.pluto_owner == pl and "pluto" in r.state.planets


def test_only_the_owner_can_orbit_or_land_at_pluto_with_a_probe_on_the_outermost_ring() -> None:
    """PROMO-02, FAQ-C300."""
    s, pl = with_pluto()
    other = 1 - pl
    outer_probe(s, "x1", other)
    moves = legal_moves(s)
    assert {"type": "orbit", "probe": "o1", "at": "pluto"} in moves and {"type": "land", "probe": "o1", "at": "pluto"} in moves
    assert not any(m.get("at") == "pluto" and m["probe"] == "x1" for m in moves)
    inner = put_probe(s, "mars", "i1")
    assert inner.ring != OUTERMOST_RING
    assert not any(m.get("at") == "pluto" and m["probe"] == "i1" for m in legal_moves(s))
    s.current_player = other
    s.players[other].credits, s.players[other].energy = 9, 9
    assert not any(m.get("at") == "pluto" for m in legal_moves(s))  # the card is not theirs


def test_orbiting_pluto_costs_one_credit_and_one_energy_and_gives_11_points_3_publicity_and_a_trace() -> None:
    """PROMO-02 (A-001): the probe leaves the board; one orbiter at most."""
    s, pl = with_pluto()
    p = s.players[pl]
    score, publicity = p.score, p.publicity
    r = do(with_state(s), "orbit", probe="o1", at="pluto")
    q = r.state.players[pl]
    assert q.credits == 8 and q.energy == 8 and q.score == score + 11 and q.publicity == publicity + 3
    assert q.orbiters == {"pluto": 1} and r.state.planets["pluto"].orbiters == [pl]
    assert not any(pr.id == "o1" for pr in r.state.probes)
    assert r.state.pending and r.state.pending[0].kind == "trace" and r.state.pending[0].data["color"] == "any"
    r2 = settle(r)
    assert not any(m.get("at") == "pluto" and m["type"] == "orbit" for m in legal_moves(r2.state))  # the orbiter space is taken


def test_landing_on_pluto_costs_three_energy_or_two_with_an_orbiter_and_gives_11_points_4_data_and_a_yellow_trace() -> None:
    """PROMO-02, LAND-02 (FAQ-C300)."""
    s, pl = with_pluto()
    outer_probe(s, "o2")
    p = s.players[pl]
    score, data = p.score, p.data_pool
    r = do(with_state(s), "land", probe="o1", at="pluto")
    q = r.state.players[pl]
    assert q.energy == 6 and q.score == score + 11 and q.landers == {"pluto": 1}
    assert q.data_pool == data + 4
    assert r.state.pending[0].kind == "trace" and r.state.pending[0].data["color"] == "yellow"
    # with an orbiter at Pluto the landing costs 2
    s2, pl2 = with_pluto()
    outer_probe(s2, "o2")
    r2 = settle(do(with_state(s2), "orbit", probe="o1", at="pluto"))
    s3 = r2.state.model_copy(deep=True)
    s3.main_done = False
    s3.players[pl2].energy = 5
    r3 = do(with_state(s3), "land", probe="o2", at="pluto")
    assert r3.state.players[pl2].energy == 3
    assert not any(m.get("at") == "pluto" and m["type"] == "land" for m in settle(r3).legal)  # one lander at most


def test_pluto_counts_as_a_planet_for_other_effects() -> None:
    """PROMO-02, FAQ-C300: its orbiter counts for the missions that need an orbiter, and for the gold tile (orbiters plus landers)."""
    from seti_engine import cards

    s, pl = with_pluto()
    assert not cards.cond_ok(s, s.players[pl], card_defs.orbland(orbiters_only=True))
    r = settle(do(with_state(s), "orbit", probe="o1", at="pluto"))
    assert cards.cond_ok(r.state, r.state.players[pl], card_defs.orbland(orbiters_only=True))
    assert sum(r.state.players[pl].orbiters.values()) + sum(r.state.players[pl].landers.values()) == 1


def test_gateway_to_mars_is_a_mission_with_two_circles() -> None:
    """PROMO-03: 2 publicity, then 5 points, for an orbit or a landing at Mars (or its moons) or for playing a card that names Mars."""
    d = card_defs.CARDS[GATEWAY]
    assert d["mission"]["kind"] == "trigger" and len(d["mission"]["circles"]) == 2
    assert d["mission"]["circles"][0]["r"] == [{"t": "publicity", "n": 2}] and d["mission"]["circles"][1]["r"] == [{"t": "vp", "n": 5}]


def mars_game() -> tuple[GameState, int]:
    s = ready(credits=9, energy=9)
    pl = s.current_player
    r = settle(play(s, GATEWAY))
    s = r.state.model_copy(deep=True)
    s.main_done = False
    s.players[pl].credits, s.players[pl].energy = 9, 9
    return s, pl


def test_orbiting_mars_covers_a_circle_of_gateway_to_mars() -> None:
    """PROMO-03."""
    s, pl = mars_game()
    put_probe(s, "mars", "m1")
    s.players[pl].publicity = 3
    r = do(with_state(s), "orbit", probe="m1")
    r = settle_until_trigger(r)
    assert r.state.pending[0].kind == "mission_trigger"
    r2 = apply(r.state, {"type": "cover", "card": GATEWAY, "circle": 0})
    assert (
        r2.state.players[pl].publicity == 3 + 2 + 0 or r2.state.players[pl].publicity >= 5
    )  # 2 publicity (the orbit itself may give more)
    assert r2.state.players[pl].missions[0].used == [True, False]


def settle_until_trigger(r: StepResult) -> StepResult:
    for _ in range(40):
        if r.state.pending and r.state.pending[0].kind == "mission_trigger":
            return r
        if not r.state.pending:
            return r
        r = apply(r.state, decisions(r.legal)[0])
    return r


def test_landing_at_mars_and_playing_a_card_that_names_mars_trigger_it_too() -> None:
    """PROMO-03: #13 Perseverance Rover names Mars in its flavor text; a card that does not, does not."""
    assert {"13", "14", "22", "34", "76", "84", "85", "119", "ET.4", "SA.31"} == card_defs.MARS_FLAVOR  # A-027, confirmed
    s, pl = mars_game()
    r = settle_until_trigger(play(s, "22"))  # Mars Flyby
    assert r.state.pending and r.state.pending[0].kind == "mission_trigger"
    s2, pl2 = mars_game()
    r2 = settle_until_trigger(play(s2, "39"))  # 61 Virginis Observation: not about Mars
    assert not (
        r2.state.pending
        and r2.state.pending[0].kind == "mission_trigger"
        and any(o[0] == GATEWAY for o in r2.state.pending[0].data["options"])
    )
    s3, pl3 = mars_game()
    put_probe(s3, "mars", "m1")
    r3 = settle_until_trigger(do(with_state(s3), "land", probe="m1"))
    assert r3.state.pending and any(o[0] == GATEWAY for o in r3.state.pending[0].data["options"])


def test_orbiting_another_planet_does_not_trigger_gateway_to_mars() -> None:
    s, pl = mars_game()
    put_probe(s, "venus", "v1")
    r = settle_until_trigger(do(with_state(s), "orbit", probe="v1"))
    assert not (r.state.pending and r.state.pending[0].kind == "mission_trigger")
