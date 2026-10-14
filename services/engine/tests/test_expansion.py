"""The Space Agencies organization module: EXP-01, EXP-SIG-01, EXP-ORG-02 to EXP-ORG-10, EXP-QS-01 to EXP-QS-04, A-031, A-036."""

import random

import pytest

from seti_engine import orgs, tables
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import GameState, Options
from seti_engine.projection import project

OPTS = {"expansion": True, "organizations": True}


def new(players: int = 2, seed: int = 1, **extra: object) -> GameState:
    return start(Options(players=players, seed=seed, **OPTS, **extra)).state  # type: ignore[arg-type]


def act(s: GameState, **a: object) -> GameState:
    return apply(s, dict(a)).state


def pick(s: GameState, kind: str, **match: object) -> GameState:
    """Play the first legal move of the given type that has the given fields."""
    for m in legal_moves(s):
        if m["type"] == kind and all(m.get(k) == v for k, v in match.items()):
            return act(s, **m)
    raise AssertionError(f"no legal {kind} {match}: {legal_moves(s)}")


def setup_with(org_choice: str | None = None, seed: int = 1, players: int = 2) -> GameState:
    """Everyone picks `org_choice` where offered (else the first move), then the first quick start cards, and tucks the first cards."""
    s = new(players, seed)
    while s.phase == "setup":
        m = legal_moves(s)
        want = next((x for x in m if x["type"] == "choose_org" and x["org"] == org_choice), m[0])
        s = act(s, **want)
    return s


def test_the_options_need_the_expansion() -> None:  # EXP-01
    with pytest.raises(ValueError):
        Options(players=2, organizations=True)
    with pytest.raises(ValueError):
        Options(players=3, expansion=True, neutral_quick_start=True)
    with pytest.raises(ValueError):
        Options(players=2, expansion=True, beginner_organizations=True)


def test_the_expansion_alone_changes_nothing_else() -> None:  # EXP-01, EXP-03
    base = start(Options(players=2, seed=4)).state
    with_exp = start(Options(players=2, seed=4, expansion=True)).state
    assert base.players[0].hand == with_exp.players[0].hand
    assert base.round == with_exp.round == 1


def test_setup_deals_two_organizations_and_three_quick_start_cards() -> None:  # EXP-ORG-03, EXP-ORG-04
    s = new(3)
    assert s.round == 2 and s.end_of_round_stacks[0] == []  # EXP-ORG-02
    for p in s.players:
        assert (len(p.offered_orgs), len(p.offered_quick), len(p.hand)) == (2, 3, 4)
        assert (p.credits, p.energy, p.publicity) == (0, 0, 0)
    seen = [o for p in s.players for o in p.offered_orgs]
    assert len(seen) == len(set(seen))
    assert s.pending[0].kind == "choose_org" and s.pending[0].player == s.start_player


def test_a_player_only_sees_their_own_offers() -> None:  # CLAUDE.md rule 6
    s = new(2)
    other = 1 - s.start_player
    seen = project(s, s.start_player).state
    assert seen.players[s.start_player].offered_orgs
    assert set(seen.players[other].offered_orgs) == {"?"} and set(seen.players[other].offered_quick) == {"?"}


def test_choosing_resolves_starting_resources_and_tucks() -> None:  # EXP-ORG-04, EXP-ORG-06, EXP-ORG-07
    s = setup_with()
    assert s.phase == "play"
    for p in s.players:
        org = tables.organizations()[p.organization or ""]
        assert len(p.quick_start) == 2 and len(p.tucked) >= min(org["tuck_income_cards"], 1) - 1
        assert not p.offered_orgs and not p.offered_quick


def test_beginner_organizations() -> None:  # EXP-ORG-05
    s = new(4, beginner_organizations=True)
    got = sorted(p.offered_orgs[0] for p in s.players)
    assert got == sorted(orgs.BEGINNER_ORGS)
    assert all(len(p.offered_quick) == 2 for p in s.players)


def test_orbital_dynamics_launches_two_probes_and_holds_three() -> None:  # EXP-ORG-13, LAUNCH-02
    for seed in range(60):
        s = new(2, seed, beginner_organizations=True)
        if any("orbital_dynamics" in p.offered_orgs for p in s.players):
            break
    while s.phase == "setup":
        m = legal_moves(s)
        s = act(s, **m[0])
    p = next(p for p in s.players if p.organization == "orbital_dynamics")
    assert sum(1 for pr in s.probes if pr.player == p.index) == 2


def test_quick_start_marks_give_no_benefit() -> None:  # EXP-QS-01
    s = new(2)
    p = s.players[0]
    before = (p.score, p.data_pool, p.publicity)
    sector = next(i for i, x in enumerate(s.sectors) if x.star == "Barnard's Star")
    orgs.place_marks(s, p, "SR.3")
    assert s.sectors[sector].markers == [0, 0]
    assert (p.score, p.data_pool, p.publicity) == before
    assert s.completed == []


def test_quick_start_lower_half() -> None:  # EXP-QS-02
    s = new(2)
    p = s.players[0]
    score, data = p.score, p.data_pool
    orgs.lower(s, p, "SR.3")
    assert (p.score - score, p.data_pool - data) == (2, 2)


def test_neutral_quick_start_cards() -> None:  # EXP-QS-03, EXP-QS-04
    s = new(2, neutral_quick_start=True)
    assert len(s.neutral_quick) == 4
    assert all(q not in p.offered_quick for q in s.neutral_quick for p in s.players)
    assert all(p.score <= 2 for p in s.players)  # no benefit for the neutral pieces


def test_income_replaces_the_income_card_and_resets_the_ability() -> None:  # EXP-ORG-08, EXP-ORG-10, A-031
    s = setup_with()
    p = s.players[0]
    inc = tables.organizations()[p.organization or ""]["income"]
    p.org_used = True
    c = p.credits
    orgs.gain_income(s, p)
    assert p.credits - c == inc["credit"] + sum(1 for t in p.tucked if tables.cards()[t]["income"] == "credit")
    assert not p.org_used


def test_signal_tokens_are_a_resource() -> None:  # EXP-SIG-01
    s = new(2)
    from seti_engine import rewards

    rewards.grant(s, s.players[0], [{"t": "signal_token", "n": 2}], [])
    assert s.players[0].signal_tokens == 2


@pytest.mark.parametrize("seed", range(6))
def test_random_games_with_organizations_finish(seed: int) -> None:  # EXP-ORG-02, fuzz
    rng = random.Random(seed)
    players = 2 + seed % 3
    s = new(players, seed, neutral_quick_start=players == 2 and seed % 2 == 0)
    for _ in range(6000):
        if s.phase == "finished":
            break
        m = [x for x in legal_moves(s) if x["type"] != "undo"]
        s = act(s, **rng.choice(m))
    assert s.phase == "finished" and s.round == 5


def test_a_neutral_marker_never_wins_and_may_stay() -> None:  # EXP-QS-04, SECTOR-12, SECTOR-13
    s = new(2, neutral_quick_start=True)
    sec = s.sectors[0]
    sec.markers = [orgs.rewards.NEUTRAL, orgs.rewards.NEUTRAL, 0, 1, 1][: sec.capacity]
    before = [p.publicity for p in s.players]
    orgs.rewards.resolve_sector(s, 0, [])
    assert sec.winners and sec.winners[0] in (0, 1)
    assert s.players[0].publicity > before[0] and s.players[1].publicity > before[1]  # SECTOR-12; the neutral color gets none
    assert sec.markers in ([], [orgs.rewards.NEUTRAL], [0], [1])
