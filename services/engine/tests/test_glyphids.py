"""Glyphids (Space Agencies): EXP-GLY-01 to EXP-GLY-07."""

import random

from seti_engine import glyphids, rewards, species, tables
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import GameState, Options


def game(seed: int = 1, players: int = 2) -> GameState:
    s = start(Options(players=players, seed=seed, expansion=True)).state.model_copy(deep=True)
    s.phase = "play"
    s.pending = []
    s.species[0].species = "glyphids"
    s.species[0].board = species.new_board("glyphids")
    return s


def discovered(markers: tuple[str | None, str | None, str | None] = ("p0", "p1", None)) -> GameState:
    s = game()
    s.species[0].discovery_spaces = list(markers)
    species._discover(s, 0, [])
    return s


def test_discovery_places_the_glyph_tokens() -> None:  # EXP-GLY-01, EXP-GLY-03
    s = discovered()
    extra = s.species[0].extra
    places = extra["tokens"]
    assert sum(1 for k in places if k.startswith("board:")) == 6
    assert sum(1 for k in places if k.startswith("planet:")) == 7 and sum(1 for k in places if k.startswith("sector:")) == 8
    assert sum(1 for k in places if k.startswith("tech:")) == 12
    assert len(places) + len(extra["supply"]) == 35  # 7 kinds of 5 (A-043)
    assert [len(p.hand) for p in s.players] == [6, 6] and s.species[0].face_up is not None  # a card for each marker, 5 + 1


def test_orbiting_or_landing_takes_the_token_of_the_planet() -> None:  # EXP-GLY-04
    s = discovered()
    p = s.players[0]
    glyphids.take(s, p, "planet:mars", [])
    assert len(p.glyphs) == 1 and "planet:mars" not in s.species[0].extra["tokens"]
    glyphids.take(s, s.players[1], "planet:mars", [])
    assert s.players[1].glyphs == []  # nobody can gain a token from that place any more


def test_winning_a_sector_and_developing_a_tech_take_their_tokens() -> None:  # EXP-GLY-04
    s = discovered()
    tokens = s.species[0].extra["tokens"]
    s.sectors[0].markers = [0, 0]
    s.sectors[0].capacity = 2
    rewards.resolve_sector(s, 0, [])
    assert "sector:0" not in tokens and len(s.players[0].glyphs) >= 1
    from seti_engine import techs

    techs.take_tech(s, s.players[1], 0, [])
    assert "tech:0" not in tokens and len(s.players[1].glyphs) == 1


def test_the_upper_wells_are_replenished_and_the_lower_ones_are_not() -> None:  # EXP-GLY-04
    s = discovered()
    extra = s.species[0].extra
    supply = len(extra["supply"])
    glyphids.on_board_space(s, s.players[0], "pink", 0, [])
    assert "board:pink:0" in extra["tokens"] and len(extra["supply"]) == supply - 1
    glyphids.on_board_space(s, s.players[0], "pink", 3, [])
    assert "board:pink:3" not in extra["tokens"]
    glyphids.on_board_space(s, s.players[0], "pink", 3, [])  # the lower well is empty now: no token
    assert len(s.players[0].glyphs) == 2


def test_deciphering_places_a_token_gains_its_resource_and_locks_the_type() -> None:  # EXP-GLY-05
    s = discovered()
    p = s.players[0]
    p.glyphs = ["red", "red", "blue"]
    moves = glyphids.decipher_moves(s, p)
    assert all(m["row"] == "bottom" for m in moves)  # the top row needs both slots beneath
    extra = s.species[0].extra
    side = extra["sides"][1]
    reward = tables.glyphids()["translation"]["bottom"][side][0]
    s.current_player = 0
    before = (p.credits, p.energy, p.publicity, p.data_pool, p.score, len(p.hand))
    r = apply(s, {"type": "decipher", "glyph": "red", "row": "bottom", "index": 0})
    q = r.state.players[0]
    assert q.glyphs == ["red", "blue"] and r.state.species[0].extra["bottom"][0] == "red"
    assert (q.credits, q.energy, q.publicity, q.data_pool, q.score, len(q.hand)) != before or reward["t"] == "card_random"
    assert not any(m["glyph"] == "red" for m in glyphids.decipher_moves(r.state, q))  # a type is deciphered once


def test_a_top_slot_needs_both_slots_beneath() -> None:  # EXP-GLY-05, A-044
    s = discovered()
    p = s.players[0]
    p.glyphs = ["red"]
    extra = s.species[0].extra
    extra["bottom"][0], extra["bottom"][1] = "blue", "cyan"
    assert any(m["row"] == "top" and m["index"] == 0 for m in glyphids.decipher_moves(s, p))
    assert not any(m["row"] == "top" and m["index"] == 1 for m in glyphids.decipher_moves(s, p))


def test_a_glyph_icon_gives_its_resource_only_once_deciphered() -> None:  # EXP-GLY-06
    s = discovered()
    p = s.players[0]
    side = s.species[0].extra["sides"][1]
    kind = tables.glyphids()["translation"]["bottom"][side][0]["t"]
    snapshot = (p.credits, p.energy, p.publicity, p.data_pool, p.score, len(p.hand), p.signal_tokens)
    glyphids.glyph_resource(s, p, "orange", [])
    assert snapshot == (p.credits, p.energy, p.publicity, p.data_pool, p.score, len(p.hand), p.signal_tokens)
    s.species[0].extra["bottom"][0] = "orange"
    glyphids.glyph_resource(s, p, "orange", [])
    assert kind in {"data", "card_random", "vp", "publicity"}
    assert snapshot != (p.credits, p.energy, p.publicity, p.data_pool, p.score, len(p.hand), p.signal_tokens) or kind == "card_random"


def test_unplaced_tokens_score_by_sets_of_different_types() -> None:  # EXP-GLY-07
    s = game()
    p = s.players[0]
    p.glyphs = []
    assert glyphids.end_points(p) == 0
    p.glyphs = ["red"]
    assert glyphids.end_points(p) == 1
    p.glyphs = ["red", "red", "blue", "cyan", "black", "pink", "orange", "yellow"]
    assert glyphids.end_points(p) == 20 + 1  # a set of 7, then a set of 1
    p.glyphs = ["red", "red", "blue", "blue", "cyan"]
    assert glyphids.end_points(p) == 5 + 3  # a set of 3, then a set of 2


def test_the_glyph_cards_with_a_defined_effect() -> None:  # EXP-GLY-06
    from seti_engine import card_defs, cards

    assert all(cards.playable(c) for c in ("GL.3", "GL.4", "GL.6", "GL.7"))
    assert not cards.playable("GL.1")  # the cards that offer a choice wait for the owner's check (A-045)
    assert card_defs.CARDS["GL.3"]["mission"]["kind"] == "trigger"


def test_the_supply_is_hidden() -> None:  # CLAUDE.md rule 6
    from seti_engine.projection import project

    s = discovered()
    assert set(project(s, 0).state.species[0].extra["supply"]) == {"?"}


def test_random_games_with_glyphids_finish() -> None:  # EXP-GLY-01 to EXP-GLY-07, fuzz
    for seed in range(4):
        rng = random.Random(seed)
        s = start(Options(players=2 + seed % 3, seed=seed, expansion=True)).state
        s.species[0].species = "glyphids"
        s.species[0].board = species.new_board("glyphids")
        s.species[0].discovery_spaces = ["p0", "p1", "p0"]
        s.species[0].complete = True
        for _ in range(9000):
            if s.phase == "finished":
                break
            s = apply(s, rng.choice([m for m in legal_moves(s) if m["type"] != "undo"])).state
        assert s.phase == "finished" and s.species[0].discovered
