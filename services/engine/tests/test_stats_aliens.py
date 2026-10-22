"""The statistics of the alien species (stats.py): what each species gave and did."""

from collections import Counter
from typing import Any

from seti_engine import amoeba, cards, scoring, species, stats
from seti_engine.engine import apply, start
from seti_engine.models import GameState, Options


def state(players: int = 2, **kw: Any) -> GameState:
    s = start(Options(players=players, seed=1, **kw)).state.model_copy(deep=True)
    s.phase = "play"
    s.pending = []
    return s


def gains(source: dict[str, Any], **changes: int) -> dict[str, Any]:
    return {"type": "gains", "player": 0, "source": source, "changes": changes}


def test_every_source_of_the_species_names_its_species_and_the_part_of_the_rules() -> None:
    assert stats.alien_source({"kind": "explore", "card": "x", "level": "major"}) == ("arkhos", "major")
    assert stats.alien_source({"kind": "glyph", "glyph": "g", "what": "icon"}) == ("glyphids", "translation")
    assert stats.alien_source({"kind": "glyph", "glyph": "g", "what": "decipher"}) == ("glyphids", "translation")
    assert stats.alien_source({"kind": "anomaly", "color": "red", "sector": 1}) == ("anomalies", "token")
    assert stats.alien_source({"kind": "alien", "species": "amoeba", "what": "group"}) == ("amoeba", "group")
    assert stats.alien_source({"kind": "card", "card": "1"}) is None
    assert stats.alien_source({"kind": "trace", "color": "red", "slot": 0}) is None  # a trace is no effect of the species


def test_the_resources_of_an_effect_are_counted_by_species_and_by_part_of_the_rules() -> None:
    c: Counter[str] = Counter()
    stats.gain_counts(c, gains({"kind": "alien", "species": "mascamites", "what": "sample"}, credit=2, publicity=1, vp=3))
    stats.gain_counts(c, gains({"kind": "explore", "card": "x", "level": "minor"}, data=1, card=1))
    stats.gain_counts(c, gains({"kind": "explore", "card": "y", "level": "minor"}, data=1))
    stats.gain_counts(c, gains({"kind": "card", "card": "5"}, credit=4))  # no species
    assert c["alien.mascamites.sample.credit"] == 2 and c["alien.mascamites.sample.vp"] == 3 and c["alien.mascamites.sample.publicity"] == 1
    assert c["alien.arkhos.minor.data"] == 2 and c["alien.arkhos.minor.card"] == 1
    assert c["publicity.alien.mascamites"] == 1
    assert not [k for k in c if k.startswith("alien.") and "credit" in k and k != "alien.mascamites.sample.credit"]
    assert c["gain.card.credit"] == 4  # the sources that were counted before are still counted


def test_a_loss_is_not_a_gain_of_the_species() -> None:
    c: Counter[str] = Counter()
    stats.gain_counts(c, gains({"kind": "alien", "species": "amoeba", "what": "single"}, data=-1, vp=2))
    assert c["alien.amoeba.single.vp"] == 2 and "alien.amoeba.single.data" not in c


def test_deliveries_anomaly_wins_and_the_tile_of_oumuamua_are_counted() -> None:
    c: Counter[str] = Counter()
    s = state()
    for e in (
        {"type": "sample_delivered", "player": 0},
        {"type": "anomaly", "player": 0},
        {"type": "anomaly", "player": 0},
        {"type": "signal_tile", "player": 0},
        {"type": "tile_resolved", "player": 0},
    ):
        stats.alien_events(c, e, s, s)
    assert (c["mascamites.delivered"], c["anomalies.won"], c["oumuamua.signals"], c["oumuamua.wins"]) == (1, 2, 1, 1)


def test_the_rewards_of_the_centaurian_board_count_the_order_in_which_they_are_taken() -> None:
    s = state()
    s.species[0].species = "centaurians"
    s.species[0].discovered = True
    s.species[0].extra["covered"] = [None, 1, None, 0]  # two taken already
    c: Counter[str] = Counter()
    stats.alien_events(c, {"type": "message_reward", "player": 0, "hex": 2, "reward": []}, s, s)
    assert c["centaurians.pick.2"] == 1 and c["centaurians.order.2"] == 3  # the third taken
    stats.alien_events(c, {"type": "message_card_placed", "player": 0}, s, s)
    stats.alien_events(c, {"type": "message_resolved", "player": 0}, s, s)
    assert c["centaurians.cards.played"] == 1 and c["centaurians.cards.completed"] == 1


def test_explorations_breaches_and_glyph_tokens_are_counted_by_where_they_came_from() -> None:
    s = state(expansion=True)
    c: Counter[str] = Counter()
    for e in (
        {"type": "explore", "player": 0, "card": "x", "level": "minor"},
        {"type": "explore", "player": 0, "card": "y", "level": "major"},
        {"type": "explore", "player": 0, "card": "z", "level": "major"},
        {"type": "breach", "player": 0, "color": "pink"},
        {"type": "glyph", "player": 0, "glyph": "a", "where": "board:pink:0"},  # an upper well
        {"type": "glyph", "player": 0, "glyph": "a", "where": "board:blue:3"},  # a lower well
        {"type": "glyph", "player": 0, "glyph": "b", "where": "planet:mars"},
        {"type": "glyph", "player": 0, "glyph": "b", "where": "sector:3"},
        {"type": "glyph", "player": 0, "glyph": "c", "where": "tech:1"},
        {"type": "decipher", "player": 0, "glyph": "a", "row": "top", "index": 0},
    ):
        stats.alien_events(c, e, s, s)
    assert (c["arkhos.explore.minor"], c["arkhos.explore.major"], c["arkhos.breach"]) == (1, 2, 1)
    assert c["glyphids.token.board_top"] == 1 and c["glyphids.token.board_low"] == 1
    assert (c["glyphids.token.planet"], c["glyphids.token.sector"], c["glyphids.token.tech"], c["glyphids.placed"]) == (1, 1, 1, 1)


def test_organelles_are_counted_by_color_for_a_single_trigger_and_a_group() -> None:
    s = state(expansion=True)
    c: Counter[str] = Counter()
    stats.alien_events(c, {"type": "organelle", "player": 0, "space": "P2"}, s, s)
    stats.alien_events(c, {"type": "organelles", "player": 0, "color": "yellow", "spaces": ["Y1", "Y2"]}, s, s)
    stats.alien_events(c, {"type": "organelles", "player": 0, "color": "yellow", "spaces": ["Y1"]}, s, s)
    assert c[f"amoeba.single.{amoeba.color_of('P2')}"] == 1
    assert c["amoeba.group.yellow"] == 2 and c["amoeba.group.yellow.tokens"] == 3


def test_a_picked_organelle_flows_from_the_engine_into_the_counters() -> None:  # EXP-AMO-04
    s = state(expansion=True)
    s.species[0].species = "amoeba"
    s.species[0].board = species.new_board("amoeba")
    s.species[0].discovery_spaces = ["p0", None, None]
    species._discover(s, 0, [])
    s.current_player = 0
    s.species[0].extra["organelles"] = {"Y1": 3, "Y2": 1, "P1": 4, "P2": 2, "IB": 0}  # P2: 1 publicity
    cards.run_step(s, s.players[0], {"t": "organelle", "color": amoeba.color_of("P2")}, [])
    r = apply(s, {"type": "pick_organelle", "space": "P2"})
    c: Counter[str] = Counter()
    for e in r.events:
        if e["type"] == "gains":
            stats.gain_counts(c, e)
        else:
            stats.alien_events(c, e, s, r.state)
    assert c["alien.amoeba.single.publicity"] == 1 and c[f"amoeba.single.{amoeba.color_of('P2')}"] == 1


def test_the_exofossils_the_danger_and_the_leftover_tokens_are_taken_from_the_end_state() -> None:  # ALIEN-EXE-06, ALIEN-EXE-07, EXP-GLY-07
    s = state(expansion=True)
    s.species[0].species, s.species[0].discovered = "exertians", True
    s.species[1].species, s.species[1].discovered = "glyphids", True
    s.species[1].extra = {"tokens": {}, "supply": [], "top": [None] * 3, "bottom": [None] * 4, "sides": [0, 0]}
    s.species[0].board = species.new_board("exertians")
    s.species[0].board["pink"][4].append(0)  # one marker of danger 3 on the board
    p = s.players[0]
    p.exertian_played = ["ET.41", "ET.43"]  # danger 6 and 3
    p.glyphs = ["a", "a", "b"]
    p.score = 50
    p.orbiters = {"oumuamua": 2}
    p.landers = {"oumuamua": 1}
    s.final_scores = scoring.final_scores(s)
    c: Counter[str] = Counter()
    stats.alien_end(c, s, p)
    assert c["exertians.danger.cards"] == 9 and c["exertians.danger.board"] == 3 and c["exertians.danger"] == 12
    assert c["exertians.played"] == 2
    assert c["exertians.loss"] == s.final_scores[0]["loss"] > 0  # the most dangerous player loses a tenth
    assert c["glyphids.leftover"] == 3 and c["glyphids.leftover.vp"] == s.final_scores[0]["glyphs"] > 0
    assert (c["oumuamua.orbiters"], c["oumuamua.landers"]) == (2, 1)
    assert c["alien.exertians.games"] == 1 and c["alien.glyphids.games"] == 1 and "alien.amoeba.games" not in c
