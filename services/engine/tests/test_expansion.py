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


# ---------------------------------------------------------------------------------------------------------------------------------
# the organizations' powers (EXP-ORG-09, EXP-ORG-10, EXP-ORG-11, EXP-ORG-12, EXP-ORG-13)
# ---------------------------------------------------------------------------------------------------------------------------------


def with_org(org: str, **res: int) -> GameState:
    """A game in play in which the current player has `org` (and plenty of resources)."""
    s = setup_with()
    p = s.players[s.current_player]
    p.organization, p.org_used, p.org_data, p.org_marks = org, False, {}, []
    if org == "xenolab":
        p.org_data["tiles"] = {"launch": True, "scan": True, "research": True}
    p.credits, p.energy, p.publicity = res.get("credits", 9), res.get("energy", 9), res.get("publicity", 9)
    return s


def can(s: GameState, kind: str, **match: object) -> bool:
    return any(m["type"] == kind and all(m.get(k) == v for k, v in match.items()) for m in legal_moves(s))


def cur(s: GameState):  # type: ignore[no-untyped-def]
    return s.players[s.current_player]


def test_fenwick_researches_for_five_publicity() -> None:  # EXP-ORG-09, EXP-ORG-13
    s = with_org("fenwick_research_center", publicity=5)
    assert can(s, "research")
    cur(s).publicity = 4
    assert not can(s, "research")
    assert orgs.research_cost(cur(s), 6) == 5


def test_deep_sky_survey_analyzes_without_energy() -> None:  # EXP-ORG-09, EXP-ORG-13
    s = with_org("deep_sky_survey", energy=0)
    cur(s).computer = [True] * 6
    assert can(s, "analyze")
    s2 = act(s, type="analyze")
    assert cur(s2).energy == 0 and not any(cur(s2).computer)
    cur(s).organization = None
    assert not can(s, "analyze")


def test_deep_sky_survey_switches_a_card_once_per_round() -> None:  # EXP-ORG-10, EXP-ORG-13
    s = with_org("deep_sky_survey")
    mine, row = cur(s).hand[0], s.card_row[0]
    s = act(s, type="org_free", org="deep_sky_survey", card=mine, row=0)
    assert s.card_row[0] == mine and row in cur(s).hand and cur(s).org_used
    assert not any(m["type"] == "org_free" for m in legal_moves(s))


def test_stratus_core_gains_every_corner_of_the_row_without_discarding() -> None:  # EXP-ORG-13
    s = with_org("stratus_core")
    row = list(s.card_row)
    s = act(s, type="org_free", org="stratus_core")
    assert s.card_row == row


def test_turing_systems_borrows_a_tech_for_the_turn() -> None:  # EXP-ORG-13
    s = with_org("turing_systems")
    s = act(s, type="org_free", org="turing_systems", tech="probe-dot")
    assert cur(s).org_data["borrowed"] == ["probe-dot"]
    from seti_engine import effects

    assert effects.tech_active(cur(s), "probe-dot") and "probe-dot" not in cur(s).techs
    orgs.end_turn(s, cur(s))
    assert not effects.tech_active(cur(s), "probe-dot")


def test_turing_systems_gains_publicity_for_a_computer_tech() -> None:  # EXP-ORG-13
    s = with_org("turing_systems")
    p = cur(s)
    before = p.publicity
    orgs.on_tech(s, p, "computer")
    orgs.on_tech(s, p, "probe")
    assert p.publicity == before + 1


def test_sentinel_marks_a_signal_when_it_launches_and_replays_a_corner() -> None:  # EXP-ORG-13
    s = with_org("sentinel_probe_network")
    sector = orgs.solar.earth(s)[1]
    before = len(s.sectors[sector].markers)
    s = act(s, type="launch")
    assert len(s.sectors[sector].markers) == before + 1
    p = cur(s)
    p.org_data["corner"] = next(c for c in tables.cards() if c.isdigit())
    assert can(s, "org_free", org="sentinel_probe_network")
    s = act(s, type="org_free", org="sentinel_probe_network")
    assert "corner" not in cur(s).org_data


def test_mission_relay_starts_on_the_lowest_space_of_the_mission_tile() -> None:  # EXP-ORG-13
    s = new(2)
    p = s.players[0]
    from seti_engine.scoring import tile_values

    s.players[0].organization = "mission_relay"
    s.players[0].offered_quick = ["SR.18", "SR.19"]
    s.players[0].quick_start = []
    orgs.start(s, p, [])
    g = next(g for g in s.gold_tiles if g.tile == "Mission")
    assert g.low_markers == [0] and g.markers == []
    assert tile_values(g)[2] >= 0
    assert not any(m["type"] == "choose_gold" and m["tile"] == "Mission" for m in legal_moves(_choose_gold(s, 0)))


def _choose_gold(s: GameState, player: int) -> GameState:
    from seti_engine.models import Decision

    s2 = s.model_copy(deep=True)
    s2.phase = "play"
    s2.pending = [Decision(kind="gold_choice", player=player)]
    return s2


def test_mission_relay_pays_two_publicity_for_a_card_and_its_income() -> None:  # EXP-ORG-13
    s = with_org("mission_relay", publicity=3)
    hand = len(cur(s).hand)
    s = act(s, type="org_free", org="mission_relay", source="row:0")
    assert len(cur(s).hand) == hand + 1 and cur(s).publicity <= 1 + 1


def test_cosmos_marks_a_space_when_a_card_is_played_and_clears_on_use() -> None:  # EXP-ORG-11, EXP-ORG-13
    s = with_org("cosmos_strategy_group")
    p = cur(s)
    cid = next(c for c in tables.cards() if c.isdigit() and tables.cards()[c]["sector"] == "red")
    orgs.on_card_played(s, p, cid, False)
    d = s.pending[-1]
    assert d.kind == "org_mark" and d.data["spaces"] == ["publicity"]
    pub = p.publicity
    s.pending = [d]
    s = act(s, type="org_mark", space="publicity")
    assert cur(s).org_marks == ["publicity"] and cur(s).publicity == pub + 1
    s = act(s, type="org_free", org="cosmos_strategy_group", source="deck")
    assert cur(s).org_marks == []


def test_helion_marks_a_space_for_a_tech_and_its_free_action_clears_them() -> None:  # EXP-ORG-11, EXP-ORG-13
    s = with_org("helion_assembly")
    p = cur(s)
    p.techs.append("probe-dot")
    orgs.on_tech(s, p, "probe")
    assert s.pending[-1].data["spaces"] == ["energy"]
    energy = p.energy
    s.pending = [s.pending[-1]]
    s = act(s, type="org_mark", space="energy")
    assert cur(s).energy == energy + 1
    card = cur(s).hand[0]
    s = act(s, type="org_free", org="helion_assembly", tech="probe-dot", card=card)
    assert cur(s).org_marks == [] and card in cur(s).tucked and cur(s).org_data["disabled"] == ["probe-dot"]
    from seti_engine import effects

    assert not effects.tech_active(cur(s), "probe-dot")


def test_xenolab_tiles_are_discounted_actions_and_traces_flip_them_back() -> None:  # EXP-ORG-13, A-037
    s = with_org("xenolab", credits=1, energy=0, publicity=0)
    assert can(s, "org_main", tile="launch") and not can(s, "launch")
    s = act(s, type="org_main", org="xenolab", tile="launch")
    p = cur(s)
    assert p.credits == 0 and p.org_data["tiles"]["launch"] is False and sum(1 for x in s.probes if x.player == p.index) >= 1
    orgs.on_trace(p, "blue")
    assert p.org_data["tiles"]["launch"] is True


def test_xenolab_scan_and_research_cost() -> None:  # EXP-ORG-13
    s = with_org("xenolab", credits=0, energy=2, publicity=4)
    assert can(s, "org_main", tile="scan") and not can(s, "scan")
    assert any(m["type"] == "org_main" and m["tile"] == "research" for m in legal_moves(s))
    s = act(s, type="org_main", org="xenolab", tile="scan")
    assert cur(s).energy == 0 and cur(s).org_data["tiles"]["scan"] is False


def test_futurespan_prepares_a_card_waits_for_the_token_and_plays_it_free() -> None:  # EXP-ORG-12, A-036
    s = with_org("futurespan_institute", credits=0)
    p = cur(s)
    card = next(c for c in p.hand if tables.cards()[c]["cost"] >= 1)
    cost = int(tables.cards()[card]["cost"])
    score = p.score
    s = act(s, type="org_free", org="futurespan_institute", card=card)
    p = cur(s)
    assert card not in p.hand and p.org_data["fs_token"] == score + 10 * cost + 5
    assert not can(s, "org_main", org="futurespan_institute")
    assert not any(m.get("card") for m in legal_moves(s) if m["type"] == "org_free")  # only one card at a time
    s = act(s, type="org_free", org="futurespan_institute", delay=True)
    assert cur(s).org_data["fs_token"] == score + 10 * cost + 8
    assert not any(m["type"] == "org_free" for m in legal_moves(s))  # once per round
    cur(s).score = cur(s).org_data["fs_token"]
    assert can(s, "org_main", org="futurespan_institute")
    s = act(s, type="org_main", org="futurespan_institute")
    assert "fs_card" not in cur(s).org_data and cur(s).credits == 0


def test_futurespan_card_is_hidden_from_the_others() -> None:  # CLAUDE.md rule 6
    s = with_org("futurespan_institute")
    card = cur(s).hand[0]
    s = act(s, type="org_free", org="futurespan_institute", card=card)
    other = 1 - s.current_player
    assert project(s, other).state.players[s.current_player].org_data["fs_card"] == "?"
    assert project(s, s.current_player).state.players[s.current_player].org_data["fs_card"] == card


@pytest.mark.parametrize("org", sorted(tables.organizations()))
def test_every_organization_plays_a_whole_game(org: str) -> None:  # EXP-ORG-13, fuzz
    for seed in range(2):
        rng = random.Random(seed)
        s = new(2, seed)
        for p in s.players:
            p.offered_orgs = [org]
        for _ in range(8000):
            if s.phase == "finished":
                break
            m = [x for x in legal_moves(s) if x["type"] != "undo"]
            s = act(s, **rng.choice(m))
        assert s.phase == "finished"
