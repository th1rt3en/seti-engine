"""Alien cards ET.1 to ET.40 (ALIEN-MASC-*, ALIEN-ANO-*, ALIEN-OUM-*, ALIEN-CEN-*, FAQ-C201, FAQ-C215, FAQ-C220, FAQ-C221, FAQ-C231)."""

import pytest
from test_cards import give, me, put_probe, settle
from test_engine import decisions, do, total_cards, with_state
from test_species import discover, game

from seti_engine import card_defs, cards, effects, solar, species, tables
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import GameState, Probe

ALIEN = [f"ET.{i}" for i in range(1, 41)]
SPECIES_OF = {c: tables.cards()[c]["species"] for c in ALIEN}


def world(name: str) -> GameState:
    """A game where `name` is discovered (and the other slot is Anomalies, or Centaurians for Anomalies)."""
    other = "centaurians" if name == "anomalies" else "anomalies"
    s = discover(game(name, other), 0).state.model_copy(deep=True)
    s.main_done = False
    p = s.players[s.current_player]
    p.credits = p.energy = 9
    p.publicity = 5
    for q in s.players:
        q.messages = []  # the Centaurian message tiles are not what these tests are about
    return s


def play(s: GameState, cid: str) -> StepResult:
    give(s, cid)
    return do(with_state(s), "play_card", card=cid)


def first_pending(r: StepResult) -> str:
    return r.state.pending[0].kind if r.state.pending else ""


# ---------------------------------------------------------------------------------------------------------------------------------
# all alien cards
# ---------------------------------------------------------------------------------------------------------------------------------


def test_every_alien_card_has_a_definition() -> None:
    assert set(ALIEN) <= set(card_defs.CARDS) and all(cards.playable(c) for c in ALIEN)


@pytest.mark.parametrize("cid", ALIEN)
def test_alien_card_plays_to_the_right_place(cid: str) -> None:
    """PLAY-02, CARD-30, ALIEN-CEN-02: the card ends where it belongs and nothing gets stuck."""
    s = world(SPECIES_OF[cid])
    pl = s.current_player
    put_probe(s, "EARTH", "e1")
    put_probe(s, "jupiter", "j1")
    r = play(s, cid)
    for _ in range(40):
        if not r.state.pending:
            break
        r = apply(r.state, r.legal[0])
    st = r.state
    assert not st.pending and not st.queue and st.playing is None and total_cards(st) == 138
    p = st.players[pl]
    d = card_defs.CARDS[cid]
    if "green" in d:
        assert cid in [m.card for m in p.message_cards]
    elif "mission" in d:
        assert cid in [m.card for m in p.missions] + p.completed_missions
    elif "end" in d:
        assert cid in p.end_cards
    else:
        assert cid in st.discard or cid in p.hand  # ET.15 may keep other cards; this one goes to the discard pile


def test_centaurian_cards_cost_energy() -> None:
    """ALIEN-CEN-02."""
    s = world("centaurians")
    p = s.players[s.current_player]
    p.credits, p.energy = 9, 0
    give(s, "ET.31")
    assert {"type": "play_card", "card": "ET.31"} not in legal_moves(s)
    p.energy = 1
    r = do(with_state(s), "play_card", card="ET.31")
    assert me(r).energy == 0 and me(r).credits == 9


# ---------------------------------------------------------------------------------------------------------------------------------
# Mascamites
# ---------------------------------------------------------------------------------------------------------------------------------


def test_land_and_collect_a_sample() -> None:
    """ET.4 Martian Quarantine Lab, ALIEN-MASC-02: land without paying, then pick a sample on that planet."""
    s = world("mascamites")
    pl = s.current_player
    put_probe(s, "jupiter", "j1")
    energy = s.players[pl].energy
    r = play(s, "ET.4")
    assert first_pending(r) == "land_free"
    r = do(r, "land_free", probe="j1")
    assert me(r).energy == energy and first_pending(r) in ("land_data_slot", "mascamite_sample", "trace", "")
    r = settle_until(r, "mascamite_sample")
    tokens = species.samples_on(r.state, "jupiter")
    assert len(tokens) == 3 and {m["sample"] for m in decisions(r.legal)} == set(tokens)
    r = do(r, "pick_sample", planet="jupiter", sample=tokens[0])
    caps = [pr for pr in r.state.probes if pr.capsule]
    assert len(caps) == 1 and caps[0].sample == tokens[0] and len(species.samples_on(r.state, "jupiter")) == 2


def settle_until(r: StepResult, kind: str) -> StepResult:
    for _ in range(30):
        if first_pending(r) == kind:
            return r
        assert r.state.pending, f"never reached {kind}"
        r = apply(r.state, r.legal[0])
    raise AssertionError(kind)


def test_collecting_on_a_planet_without_samples_does_nothing_extra() -> None:
    """ALIEN-MASC-02: a card can land on a planet without samples; no capsule appears."""
    s = world("mascamites")
    put_probe(s, "mars", "m1")
    r = settle(play(s, "ET.4"))
    assert not [pr for pr in r.state.probes if pr.capsule] and r.state.players[s.current_player].landers == {"mars": 1}


def test_orbit_or_land_card() -> None:
    """ET.3 Mass Sample Collection: an orbit or land action without paying its cost."""
    s = world("mascamites")
    put_probe(s, "saturn", "s1")
    r = play(s, "ET.3")
    kinds = {m["type"] for m in decisions(r.legal)}
    assert kinds == {"orbit_free", "land_free"}
    credits = me(r).credits
    r = do(r, "orbit_free", probe="s1")
    assert me(r).credits == credits and r.state.planets["saturn"].orbiters == [r.state.current_player]
    r = settle_until(r, "mascamite_sample")
    assert {m["planet"] for m in decisions(r.legal)} == {"saturn"}


def test_peek_at_samples_gives_the_reward_and_puts_the_sample_back() -> None:
    """ET.5 Ecosystem Study, FAQ-C201: needs a probe on Jupiter's or Saturn's space."""
    s = world("mascamites")
    assert not play(s, "ET.5").state.pending  # no probe there
    s = world("mascamites")
    put_probe(s, "saturn", "s1")
    r = play(s, "ET.5")
    tokens = species.samples_on(r.state, "saturn")
    assert first_pending(r) == "mascamite_sample" and {m["sample"] for m in decisions(r.legal)} == set(tokens)
    r2 = do(r, "pick_sample", planet="saturn", sample=tokens[0])
    assert species.samples_on(r2.state, "saturn") == tokens and not [pr for pr in r2.state.probes if pr.capsule]


def deliver_world(cid: str, dest: str) -> StepResult:
    s = world("mascamites")
    pl = s.current_player
    s.players[pl].missions = []
    s = settle(play(s, cid)).state.model_copy(deep=True)
    s.main_done = False
    pos = solar.earth(s) if dest == "earth" else solar.find_cell(s, "PLANET:MARS")
    assert pos is not None
    s.probes.append(Probe(id="cap", player=pl, ring=pos[0], sector=pos[1], capsule=True, sample=3))  # a sample worth 2 data
    return with_state(s)


def test_delivering_a_sample_completes_the_mission() -> None:
    """ET.1 First Contact, ALIEN-MASC-04: the token's reward and the card's reward; the card is a completed mission."""
    r = deliver_world("ET.1", "earth")
    assert {"type": "deliver_sample", "card": "ET.1", "capsule": "cap"} in r.legal
    data = me(r).data_pool
    r2 = do(r, "deliver_sample", card="ET.1", capsule="cap")
    assert me(r2).data_pool == data + 2 + 2 and "ET.1" in me(r2).completed_missions
    # the whole delivery, the card's own reward too, is told as the sample of the Mascamites (the statistics count it as an alien effect)
    gains = [g for g in r2.events if g["type"] == "gains" and g["player"] == me(r2).index]
    assert gains and all(g["source"].get("kind") == "alien" and g["source"].get("species") == "mascamites" for g in gains)
    assert not [pr for pr in r2.state.probes if pr.capsule] and r2.state.species[0].extra["sample_spaces"][-1]["token"] == 3


def test_a_capsule_must_be_at_the_destination() -> None:
    """ET.4: Mars, not Earth."""
    r = deliver_world("ET.4", "earth")
    assert not [m for m in r.legal if m["type"] == "deliver_sample"]
    r = deliver_world("ET.4", "mars")
    assert [m for m in r.legal if m["type"] == "deliver_sample"]


def test_the_breeding_sample_resolves_the_token_twice() -> None:
    """ET.7."""
    r = deliver_world("ET.7", "earth")
    data = me(r).data_pool
    r2 = do(r, "deliver_sample", card="ET.7", capsule="cap")
    assert me(r2).data_pool == data + 4


def test_species_trace_mission_lets_the_player_look_at_samples() -> None:
    """ET.10 Computer Simulations: 2 blue traces for this species."""
    s = world("mascamites")
    pl = s.current_player
    r = settle(play(s, "ET.10"))
    s2 = r.state.model_copy(deep=True)
    s2.players[pl].trace_log = [(0, "blue")]
    assert {"type": "complete_mission", "card": "ET.10"} not in legal_moves(s2)
    s2.players[pl].trace_log.append((0, "blue"))
    r2 = do(with_state(s2), "complete_mission", card="ET.10")
    assert first_pending(r2) == "mascamite_planet" and {m["planet"] for m in decisions(r2.legal)} == {"jupiter", "saturn"}  # ALIEN-MASC-07
    assert {m["type"] for m in decisions(r2.legal)} == {"pick_planet"}


def test_alien_masc_07_the_player_chooses_the_planet_before_looking_at_any_sample() -> None:
    """ALIEN-MASC-07 (ET.8 to ET.10: "Choose Jupiter or Saturn. Look at all its samples, pick one, ..."): the choice comes first, and
    only the samples of the chosen planet are shown (owner, 2026-10-28)."""
    s = world("mascamites")
    pl = s.current_player
    r = settle(play(s, "ET.8"))
    s2 = r.state.model_copy(deep=True)
    s2.players[pl].trace_log = [(0, "yellow"), (0, "yellow")]
    r2 = do(with_state(s2), "complete_mission", card="ET.8")
    assert first_pending(r2) == "mascamite_planet"
    slot = next(sl for sl in r2.state.species if sl.species == "mascamites")
    assert not slot.extra.get("seen", {}).get(str(pl)), "nothing has been looked at before the planet is chosen"
    r3 = do(r2, "pick_planet", planet="saturn")
    assert first_pending(r3) == "mascamite_sample"
    assert {m["planet"] for m in decisions(r3.legal)} == {"saturn"} and {m["type"] for m in decisions(r3.legal)} == {"pick_sample"}
    slot3 = next(sl for sl in r3.state.species if sl.species == "mascamites")
    seen = set(slot3.extra["seen"][str(pl)])
    assert seen == set(species.samples_on(r3.state, "saturn")), "only the tokens of the chosen planet were seen"
    token = species.samples_on(r3.state, "saturn")[0]
    r4 = do(r3, "pick_sample", planet="saturn", sample=token)
    assert not r4.state.pending and species.samples_on(r4.state, "saturn") == species.samples_on(r3.state, "saturn")  # put back


# ---------------------------------------------------------------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------------------------------------------------------------


def test_next_anomaly_is_the_nearest_one_in_the_direction_of_rotation() -> None:
    """FAQ-54, FAQ-C220."""
    from seti_engine import alien_steps

    s = world("anomalies")
    e = solar.earth(s)[1]
    s.species[0].extra["tokens"] = [
        {"sector": (e + 5) % 8, "color": "pink", "side": 0},
        {"sector": (e + 2) % 8, "color": "blue", "side": 0},
        {"sector": e, "color": "yellow", "side": 0},
    ]
    assert alien_steps.next_anomaly(s)["color"] == "blue"  # type: ignore[index]
    s.species[0].extra["tokens"] = [t for t in s.species[0].extra["tokens"] if t["color"] != "blue"]
    assert alien_steps.next_anomaly(s)["color"] == "pink"
    s.species[0].extra["tokens"] = [{"sector": e, "color": "yellow", "side": 0}]
    assert alien_steps.next_anomaly(s)["color"] == "yellow"  # only Earth's own sector: it is the next one eight rotations on


def test_signs_of_life_gives_movement_with_an_anomaly_in_earths_sector() -> None:
    """ET.11."""
    s = world("anomalies")
    e = solar.earth(s)[1]
    s.species[0].extra["tokens"] = [{"sector": (e + 1) % 8, "color": "pink", "side": 0}]
    assert me(play(s, "ET.11")).movement == 0
    s = world("anomalies")
    s.species[0].extra["tokens"] = [{"sector": solar.earth(s)[1], "color": "pink", "side": 0}]
    r = play(s, "ET.11")
    assert me(r).movement == 1 and len(r.state.probes) == 1


def test_close_up_view_moves_five_but_gives_no_publicity_for_moving() -> None:
    """ET.12."""
    s = world("anomalies")
    pos = solar.find_cell(s, "PLANET:MARS")
    assert pos is not None
    nb = next(n for n in solar.adjacent(*pos) if not solar.visible(s, *n)[1].startswith("PLANET"))
    s.probes.append(Probe(id="f", player=s.current_player, ring=nb[0], sector=nb[1]))
    r = play(s, "ET.12")
    assert me(r).movement == 5
    pub = me(r).publicity
    r = do(r, "move_probe", probe="f", to=list(pos))
    assert me(r).publicity == pub


def test_listening_carefully_marks_a_signal_where_the_next_anomaly_is() -> None:
    """ET.14."""
    from seti_engine import alien_steps

    s = world("anomalies")
    tok = alien_steps.next_anomaly(s)
    assert tok is not None
    r = play(s, "ET.14")
    r = do(r, "scan_earth", sector=solar.earth(r.state)[1])
    r = do(r, "scan_discard", source="row:0")
    r = apply(r.state, r.legal[0])
    r = do(r, "scan_done")
    assert r.state.sectors[tok["sector"]].markers.count(r.state.current_player) >= 1


def test_part_of_everyday_life_draws_three_and_places_them() -> None:
    """ET.15, FAQ-C215: one for its corner, another for its income resource, the third kept."""
    s = world("anomalies")
    deck_top = list(s.deck[-3:])
    hand = len(s.players[s.current_player].hand)
    r = play(s, "ET.15")
    assert first_pending(r) == "pol_corner" and set(r.state.aside) == set(deck_top)
    pick1 = r.legal[0]["card"]
    r = do(r, "pol_pick", card=pick1)
    assert {"type": "pol_discard", "player": r.state.current_player, "card": pick1, "for": "corner"} in r.events  # the log names the card
    assert first_pending(r) == "pol_income"
    pick2 = next(m["card"] for m in r.legal if m["card"] != pick1)
    r = do(r, "pol_pick", card=pick2)
    assert {"type": "pol_discard", "player": r.state.current_player, "card": pick2, "for": "income"} in r.events
    keep = [c for c in deck_top if c not in (pick1, pick2)]
    assert not r.state.pending and all(c in me(r).hand for c in keep) and len(me(r).hand) == hand + 1
    assert pick1 in r.state.discard and pick2 in r.state.discard


def test_flooding_the_media_space_takes_the_whole_row() -> None:
    """ET.16."""
    s = world("anomalies")
    row = list(s.card_row)
    r = play(s, "ET.16")
    assert all(c in me(r).hand for c in row) and len(r.state.card_row) == 3 and not set(row) & set(r.state.card_row)


def test_are_we_being_observed_pays_the_next_anomalys_reward() -> None:
    """ET.17."""
    s = world("anomalies")
    e = solar.earth(s)[1]
    s.species[0].extra["tokens"] = [{"sector": (e + 1) % 8, "color": "yellow", "side": 1}]  # 2 publicity
    pub = s.players[s.current_player].publicity
    r = play(s, "ET.17")
    assert me(r).publicity == pub + 2


def test_amazing_uncertainty_scores_for_signals_in_anomaly_sectors() -> None:
    """ET.20, FAQ-C220: including the signal just marked."""
    s = world("anomalies")
    pl = s.current_player
    e = solar.earth(s)[1]
    sec = (e + 2) % 8
    s.species[0].extra["tokens"] = [{"sector": sec, "color": "pink", "side": 0}]
    s.sectors[sec].markers = [pl]
    score = s.players[pl].score
    r = play(s, "ET.20")
    r = do(r, "mark_signal", sector=sec)
    assert me(r).score >= score + 2  # two of the player's signals in the anomaly sector (plus any second-position points)


# ---------------------------------------------------------------------------------------------------------------------------------
# 'Oumuamua
# ---------------------------------------------------------------------------------------------------------------------------------


def test_exofossil_cards() -> None:
    """ET.26 Race Against Time and ET.29 Comparative Analysis give an exofossil."""
    s = world("oumuamua")
    assert me(play(s, "ET.26")).exofossils == 1
    assert me(play(world("oumuamua"), "ET.29")).exofossils == 1


def test_visitor_in_the_sky_scores_per_signal_on_the_tile() -> None:
    """ET.21, FAQ-C221: 2 points for each signal marked on the tile during the scan."""
    s = world("oumuamua")
    r = play(s, "ET.21")
    st = r.state.model_copy(deep=True)
    p = st.players[st.current_player]
    score = p.score
    species.mark_tile(st, p, [])
    assert p.score == score + 1 + 2  # 1 point for the first marker on the tile, 2 per tile signal of this scan


def test_altered_trajectory_gives_an_exofossil_for_a_tile_signal() -> None:
    """ET.22."""
    s = world("oumuamua")
    r = play(s, "ET.22")
    ex = me(r).exofossils
    st = r.state.model_copy(deep=True)
    species.mark_tile(st, st.players[st.current_player], [])
    r2 = do(with_state(st), "scan_earth", sector=solar.earth(st)[1])
    r2 = do(r2, "scan_discard", source="row:0")
    r2 = apply(r2.state, r2.legal[0])
    r2 = do(r2, "scan_done")
    assert me(r2).exofossils == ex + 1


def test_exofossil_discovery_pays_exofossils_for_points() -> None:
    """ET.23: with at least 3 exofossils, spend 2 for 11 points."""
    s = world("oumuamua")
    pl = s.current_player
    r = settle_oum(play(s, "ET.23"))
    s2 = r.state.model_copy(deep=True)
    s2.players[pl].exofossils = 2
    assert {"type": "complete_mission", "card": "ET.23"} not in legal_moves(s2)
    s2.players[pl].exofossils = 3
    supply = s2.species[0].extra["supply"]
    score = s2.players[pl].score
    r2 = do(with_state(s2), "complete_mission", card="ET.23")
    assert me(r2).exofossils == 1 and me(r2).score == score + 11 and r2.state.species[0].extra["supply"] == supply + 2


def settle_oum(r: StepResult) -> StepResult:
    while r.state.pending:
        move = next((m for m in r.legal if m.get("where") == "sector"), r.legal[0])
        r = apply(r.state, move)
    return r


def test_probe_customisation_trades_exofossils_for_movement() -> None:
    """ET.25: any number of times, 2 movement for each exofossil."""
    s = world("oumuamua")
    s.players[s.current_player].exofossils = 2
    r = play(s, "ET.25")
    assert first_pending(r) == "optional"
    r = do(r, "opt_yes")
    r = do(r, "opt_yes")
    assert me(r).movement == 4 and me(r).exofossils == 0 and not r.state.pending


def test_exofossil_samples_can_turn_an_exofossil_into_data() -> None:
    """ET.28."""
    s = world("oumuamua")
    s.players[s.current_player].exofossils = 1
    r = play(s, "ET.28")
    r = settle_until(r, "optional")
    data = me(r).data_pool
    r = do(r, "opt_yes")
    assert me(r).data_pool == data + 1 and me(r).exofossils == 0


def test_comparative_analysis_covers_a_circle_for_any_trace() -> None:
    """ET.29, FAQ-C107: any trace, whatever its kind, even on an overflow space."""
    s = world("oumuamua")
    r = settle(play(s, "ET.29"))
    st = r.state.model_copy(deep=True)
    st.main_done = False
    from seti_engine.models import Decision

    st.pending = [Decision(kind="trace", player=st.current_player, data={"color": "any"})]
    r2 = do(with_state(st), "place_trace", slot=1, space="overflow", color="pink")
    assert first_pending(r2) == "mission_trigger" and len(r2.state.pending[0].data["options"]) == 3


def test_excavation_rover_scores_for_landing_on_oumuamua() -> None:
    """ET.30."""
    s = world("oumuamua")
    put_probe(s, "oumuamua", "o1")
    score = s.players[s.current_player].score
    r = settle(play(s, "ET.30"))
    assert me(r).score >= score + 3 + 9  # the card's 3 and the landing's 9


# ---------------------------------------------------------------------------------------------------------------------------------
# Centaurians
# ---------------------------------------------------------------------------------------------------------------------------------


def test_playing_a_centaurian_card_places_a_marker_fifteen_ahead() -> None:
    """ALIEN-CEN-02."""
    s = world("centaurians")
    pl = s.current_player
    score = s.players[pl].score
    data = s.players[pl].data_pool
    r = settle(play(s, "ET.35"))
    assert [(m.target, m.card) for m in me(r).message_cards] == [(score + 15, "ET.35")] and me(r).data_pool == data + 1
    assert "ET.35" not in r.state.discard


def test_placing_and_reaching_a_message_marker_are_logged() -> None:
    """ALIEN-CEN-02: the log says which card put a marker where, and when its green part resolves."""
    s = world("centaurians")
    score = s.players[s.current_player].score
    r = settle(play(s, "ET.35"))
    assert {"type": "message_card_placed", "player": r.state.current_player, "card": "ET.35", "target": score + 15} in r.events
    r2 = reach(r)
    assert any(e["type"] == "message_resolved" and e["card"] == "ET.35" and e["target"] == score + 15 for e in r2.events)


def reach(r: StepResult, extra: int = 0) -> StepResult:
    st = r.state.model_copy(deep=True)
    p = st.players[st.current_player]
    effects.gain_score(st, p, p.message_cards[0].target - p.score + extra)
    st.main_done = True
    return do(with_state(st), "end_turn")


def test_reaching_the_marker_resolves_the_green_part() -> None:
    """ALIEN-CEN-02, ALIEN-CEN-04: ET.35 marks a yellow trace; the card is then discarded (it is not income)."""
    r = settle(play(world("centaurians"), "ET.35"))
    r2 = reach(r)
    assert first_pending(r2) == "trace" and r2.state.pending[0].data["color"] == "yellow"
    r3 = settle(r2)
    assert not me(r3).message_cards and "ET.35" in r3.state.discard


def test_the_effect_of_a_message_card_names_the_card_as_its_source() -> None:
    """ALIEN-CEN-03: the decision and the log of the green part say which card it comes from."""
    r2 = reach(settle(play(world("centaurians"), "ET.35")))
    assert r2.state.pending[0].source == {"kind": "alien", "species": "centaurians", "what": "card", "card": "ET.35"}


def test_a_card_can_turn_into_income_when_its_marker_is_reached() -> None:
    """ET.32, FAQ-C231: the card is tucked and its income is gained at once."""
    s = world("centaurians")
    r = settle(play(s, "ET.32"))
    pl = r.state.current_player
    data = r.state.players[pl].data_pool
    r2 = reach(r)
    p = r2.state.players[pl]
    assert "ET.32" in p.tucked and not p.message_cards and "ET.32" not in r2.state.discard
    assert p.data_pool == min(6, data + 1)  # the card's data income, gained at once


def test_messages_are_resolved_in_the_order_they_were_sent() -> None:
    """ALIEN-CEN-03."""
    s = world("centaurians")
    r = settle(play(s, "ET.36"))
    st = r.state.model_copy(deep=True)
    st.main_done = False
    st.players[st.current_player].message_cards.append(
        __import__("seti_engine.models", fromlist=["MessageCard"]).MessageCard(target=999, card="ET.35")
    )
    st.players[st.current_player].energy = 5
    assert [m.card for m in st.players[st.current_player].message_cards] == ["ET.36", "ET.35"]
    r2 = reach(with_state(st))
    assert r2.state.pending[0].data["color"] == "blue"


def test_message_cards_are_not_missions() -> None:
    """ALIEN-CEN-02, FAQ-43."""
    r = settle(play(world("centaurians"), "ET.31"))
    assert not me(r).missions and not me(r).completed_missions
    r2 = settle(reach(r))  # FAQ-43: resolving the green part does not complete a mission, so the grey gold tile does not count it
    assert not me(r2).completed_missions


def test_end_scoring_counts_the_traces_for_a_species() -> None:
    """ET.5, ET.24: 1 point for each trace marked for the species (discovery, overflow and board all count)."""
    s = world("mascamites")
    p = s.players[s.current_player]
    slot = s.species[0]
    slot.discovery_spaces, slot.overflow = ["n", "n", "n"], []
    p.end_cards = ["ET.5"]
    assert cards.end_points(s, p) == 0
    slot.overflow = [p.index, p.index]
    slot.board["pink"][0].append(p.index)
    slot.discovery_spaces[0] = f"p{p.index}"
    assert cards.end_points(s, p) == 4


def test_a_collected_sample_is_hidden_from_everyone_but_its_owner() -> None:
    """ALIEN-MASC-02, ALIEN-MASC-04, ALIEN-MASC-06: the token under a capsule stays face down until it is delivered."""
    from seti_engine import projection
    from seti_engine.models import Probe

    s = world("mascamites")
    pl = s.current_player
    s.probes.append(Probe(id="capsule1", player=pl, ring=1, sector=1, capsule=True, sample=3))
    other = (pl + 1) % len(s.players)
    assert next(p for p in projection.project(s, pl).state.probes if p.id == "capsule1").sample == 3
    assert next(p for p in projection.project(s, other).state.probes if p.id == "capsule1").sample == -1
    assert next(p for p in projection.project(s, None).state.probes if p.id == "capsule1").sample == -1


def test_sample_choices_come_with_the_reward_of_each_token() -> None:
    """ALIEN-MASC-02: the player looks at the samples of the planet before choosing, so the page needs each token's face."""
    from seti_engine import move_notes
    from seti_engine.models import Decision

    s = world("mascamites")
    s.pending = [Decision(kind="mascamite_sample", player=s.current_player, data={"mode": "collect", "planets": ["jupiter"]})]
    legal = decisions(legal_moves(s))
    notes = move_notes.notes(s, legal)
    assert len(legal) == 3
    assert all(n is not None and n["rewards"] == species.sample_faces()[m["sample"]] for m, n in zip(legal, notes, strict=True))
