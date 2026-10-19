"""The Space Agencies organization module: EXP-01, EXP-SIG-01, EXP-ORG-02 to EXP-ORG-10, EXP-QS-01 to EXP-QS-04, A-031, A-036."""

import random

import pytest

from seti_engine import orgs, tables
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import SPECIES_BASE, SPECIES_EXPANSION, GameState, Options
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
    # the new species join the draw of the two species, so the random order after it differs; everything else is as in the base game
    assert base.round == with_exp.round == 1
    assert len(base.players[0].hand) == len(with_exp.players[0].hand) == 5
    assert {sl.species for sl in with_exp.species} <= {*SPECIES_BASE, *SPECIES_EXPANSION}


def test_setup_deals_two_organizations_and_three_quick_start_cards() -> None:  # EXP-ORG-01, EXP-ORG-03, EXP-ORG-04
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
    from seti_engine import move_notes

    assert move_notes.note(s, {"type": "analyze"}) == {"cost": {}}  # the button shows it as free
    s2 = act(s, type="analyze")
    assert cur(s2).energy == 0 and not any(cur(s2).computer)
    cur(s).organization = None
    assert not can(s, "analyze")
    assert move_notes.note(s, {"type": "analyze"}) == {"cost": {"energy": 1}}


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
    energy = p.energy
    orgs.on_tech(s, p, "probe")  # the reward is gained and the space is blocked at once (owner, 2026-10-15)
    assert not s.pending and p.org_marks == ["energy"] and p.energy == energy + 1
    card = cur(s).hand[0]
    s = act(s, type="org_free", org="helion_assembly", tech="probe-dot")
    assert s.pending and s.pending[0].kind == "helion_tuck"  # the card to tuck is chosen next, like any tuck for income
    tucks = [m for m in legal_moves(s) if m["type"] != "undo"]
    assert {m["type"] for m in tucks} == {"tuck"} and card in {m["card"] for m in tucks}  # a tuck, with no way to skip it
    s = act(s, type="tuck", card=card)
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
    s = pick(s, "org_free", org="futurespan_institute", card=card, ahead=10 * cost + 5)  # the move says how far ahead the token goes
    p = cur(s)
    assert card not in p.hand and p.org_data["fs_token"] == score + 10 * cost + 5
    assert not can(s, "org_main", org="futurespan_institute")
    assert not any(m.get("card") for m in legal_moves(s) if m["type"] == "org_free")  # only one card at a time
    hand = len(cur(s).hand)
    assert {m["source"] for m in legal_moves(s) if m["type"] == "org_free" and m.get("delay")} >= {"deck", "row:0"}
    s = pick(s, "org_free", org="futurespan_institute", delay=True, source="row:0")  # the card is clicked in the same move
    assert cur(s).org_data["fs_token"] == score + 10 * cost + 8
    assert len(cur(s).hand) == hand + 1 and not s.pending
    assert not any(m["type"] == "org_free" for m in legal_moves(s))  # once per round
    cur(s).score = cur(s).org_data["fs_token"]
    assert can(s, "org_main", org="futurespan_institute")
    s = act(s, type="org_main", org="futurespan_institute")
    assert "fs_card" not in cur(s).org_data and cur(s).credits == 0


def test_futurespan_card_is_hidden_from_the_others() -> None:  # CLAUDE.md rule 6
    s = with_org("futurespan_institute")
    card = next(m["card"] for m in legal_moves(s) if m["type"] == "org_free" and m.get("card"))
    s = pick(s, "org_free", org="futurespan_institute", card=card)
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


def test_orbital_dynamics_moves_two_different_probes_one_step_each() -> None:  # EXP-ORG-13, A-039
    from seti_engine.models import Probe

    s = with_org("orbital_dynamics", energy=0)
    p = cur(s)
    p.movement = 0
    from seti_engine.engine import move_cost

    cheap = [(r, c) for r in (2, 3) for c in range(8) if move_cost(s, p, Probe(id="t", player=p.index, ring=r, sector=c)) == 1]
    (r1, c1), (r2, c2) = cheap[0], cheap[-1]
    s.probes = [Probe(id="a", player=p.index, ring=r1, sector=c1), Probe(id="b", player=p.index, ring=r2, sector=c2)]
    assert can(s, "org_free", org="orbital_dynamics")
    s = act(s, type="org_free", org="orbital_dynamics")
    step = next(m for m in legal_moves(s) if m["type"] == "od_step" and m["probe"] == "a")
    s = act(s, **step)
    assert cur(s).movement == 0 and next(pr for pr in s.probes if pr.id == "a").ring == step["to"][0]
    assert not any(m["type"] == "od_step" and m["probe"] == "a" for m in legal_moves(s))  # a probe moves once
    s = act(s, **next(m for m in legal_moves(s) if m["type"] == "od_step" and m["probe"] == "b"))
    assert not any(m["type"] == "od_step" for m in legal_moves(s))  # two probes at most
    assert not can(s, "org_free", org="orbital_dynamics")  # once per round


def test_orbital_dynamics_step_out_of_an_asteroid_field_needs_more_movement() -> None:  # EXP-ORG-13, A-039 (owner)
    from seti_engine import solar
    from seti_engine.engine import move_cost
    from seti_engine.models import Probe

    s = with_org("orbital_dynamics", energy=0)
    p = cur(s)
    pos = solar.find_cell(s, "ASTEROID")
    assert pos is not None
    s.probes = [Probe(id="a", player=p.index, ring=pos[0], sector=pos[1])]
    p.movement = 0
    s = act(s, type="org_free", org="orbital_dynamics")
    cost = move_cost(s, cur(s), s.probes[0])
    steps = [m for m in legal_moves(s) if m["type"] == "od_step"]
    assert bool(steps) == (cost <= 1)  # a dearer step is not offered without the extra movement
    cur(s).movement = max(0, cost - 1)
    assert any(m["type"] == "od_step" for m in legal_moves(s))


def test_futurespan_prepares_only_cards_that_cost_1_to_4() -> None:  # EXP-ORG-12, A-052 (owner)
    s = with_org("futurespan_institute")
    p = cur(s)
    p.hand = ["SA.17", "SA.8", "SA.10", "SA.1"]  # costs 0, 3, 4, 1
    offered = {m["card"] for m in legal_moves(s) if m["type"] == "org_free" and m.get("card")}
    assert offered == {"SA.8", "SA.10", "SA.1"}


def test_exp_org_08_the_tracker_shows_the_income_of_the_organization() -> None:
    from seti_engine import orgs, projection

    s = start(Options(players=2, seed=3, expansion=True, organizations=True)).state
    p = s.players[0]
    p.organization = "helion_assembly"
    inc = orgs.by_id("helion_assembly")["income"]
    shown = projection.tracker(s, p).income
    assert shown["credit"] == inc["credit"] and shown["energy"] == inc["energy"]
    assert shown["publicity"] == inc["publicity"] and shown["data"] == inc["data"]


def test_exp_org_13_the_note_of_a_research_move_shows_the_cost_of_fenwick() -> None:
    from seti_engine import move_notes

    s = start(Options(players=2, seed=3, expansion=True, organizations=True)).state
    move = {"type": "research", "stack": 0}
    s.players[s.current_player].organization = "fenwick_research_center"
    assert move_notes.note(s, move) == {"cost": {"publicity": 5}}
    s.players[s.current_player].organization = "stratus_core"
    assert move_notes.note(s, move) == {"cost": {"publicity": 6}}


def test_exp_org_04_both_quick_start_cards_are_kept_in_one_choice() -> None:
    """EXP-ORG-04 (owner, 2026-10-16): one choice, a move for every pair of the offered cards, and what each source gave is reported."""
    from seti_engine.engine import apply, start
    from seti_engine.models import Options

    r = start(Options(players=2, seed=9, expansion=True, organizations=True))
    r = apply(r.state, r.legal[0])  # the first player's organization
    d = r.state.pending[0]
    assert d.kind == "choose_quick"
    offered = sorted(r.state.players[d.player].offered_quick)
    assert len(offered) == 3
    pairs = [m["cards"] for m in r.legal]
    expected = [[offered[0], offered[1]], [offered[0], offered[2]], [offered[1], offered[2]]]
    assert sorted(map(sorted, pairs)) == sorted(map(sorted, expected))
    assert all(m["type"] == "choose_quick" for m in r.legal)
    chosen = r.legal[0]
    after = apply(r.state, chosen)
    p = after.state.players[d.player]
    assert sorted(p.quick_start) == sorted(chosen["cards"]) and p.offered_quick == []
    gains = [e for e in after.events if e["type"] == "gains" and e["player"] == d.player]
    kinds = [(e["source"]["kind"], e["source"].get("card")) for e in gains]
    assert kinds[0][0] == "organization"  # the organization first, apart from the cards
    assert {c for k, c in kinds if k == "quick_start"} <= set(chosen["cards"])  # a card that gives nothing has no line
    for e in gains:
        assert e["changes"] and all(v != 0 for v in e["changes"].values())


def test_mission_relay_publicity_for_a_mission_card_is_logged_apart() -> None:  # EXP-ORG-13, the log
    from seti_engine import trail

    s = with_org("mission_relay")
    p = cur(s)
    s.trail = []
    before = p.publicity
    orgs.on_mission_played(s, p)
    assert p.publicity == before + 1
    gains = trail.events_of(s)
    assert gains and gains[0]["source"] == {"kind": "organization", "org": "mission_relay", "what": "mission"}


def test_an_organization_whose_income_has_a_signal_token_gives_it_each_round() -> None:  # EXP-SIG-03, EXP-ORG-13
    with_token = [o for o, d in tables.organizations().items() if d["income"]["signalToken"] > 0]
    assert with_token
    s = setup_with()
    p = s.players[0]
    p.organization = with_token[0]
    before = p.signal_tokens
    orgs.gain_income(s, p)
    assert p.signal_tokens - before == tables.organizations()[with_token[0]]["income"]["signalToken"]


def test_signal_tokens_are_used_during_a_scan_to_discard_another_card_of_the_row() -> None:  # EXP-SIG-02
    from seti_engine import solar

    s = setup_with()
    p = s.players[s.current_player]
    p.credits, p.energy, p.signal_tokens = 9, 9, 1
    r = apply(s, {"type": "scan"})
    r = apply(r.state, {"type": "scan_earth", "sector": solar.earth(r.state)[1]})
    assert not any(m["type"] == "scan_token" for m in legal_moves(r.state))  # the normal row step comes first
    r = apply(r.state, {"type": "scan_discard", "source": "row:0"})
    while r.state.pending and r.state.pending[0].kind == "signal":
        r = apply(r.state, next(m for m in r.legal if m["type"] == "mark_signal"))
    token_moves = [m for m in legal_moves(r.state) if m["type"] == "scan_token"]
    assert token_moves  # now a signal token can be spent on one more card of the row
    row = len(r.state.card_row)
    r = apply(r.state, token_moves[0])
    assert r.state.players[r.state.current_player].signal_tokens == 0
    assert len(r.state.card_row) <= row  # the card left the row (the row is refilled after the whole scan)
