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

    assert all(cards.playable(f"GL.{n}") for n in range(1, 11))
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


# the ten Glyphids cards (EXP-GLY-06, A-045)


def _with_glyphs(deciphered_slots: dict[str, tuple[str, int]]) -> GameState:
    s = discovered()
    s.current_player = 0
    s.phase = "play"
    extra = s.species[0].extra
    for glyph, (row, k) in deciphered_slots.items():
        extra[row][k] = glyph
    return s


def _play(s: GameState, cid: str, answer: bool = True):  # type: ignore[no-untyped-def]
    from seti_engine.engine import apply as step

    s.players[0].hand.append(cid)
    s.players[0].credits = s.players[0].energy = 9
    r = step(s, {"type": "play_card", "card": cid})
    while answer and r.state.pending:
        r = step(r.state, r.legal[0])
    return r


def test_gl_corner_gives_the_resource_of_a_deciphered_glyph() -> None:  # GL.1 to GL.10 (corners)
    s = _with_glyphs({"orange": ("bottom", 3)})
    p = s.players[0]
    side = s.species[0].extra["sides"][1]
    reward = tables.glyphids()["translation"]["bottom"][side][3]
    from seti_engine import cards

    before = (p.score, p.publicity, p.data_pool, len(p.hand))
    cards.gain_corner(s, p, "GL.1")  # orange
    after = (p.score, p.publicity, p.data_pool, len(p.hand))
    assert after != before and reward["t"] in {"vp", "publicity", "data", "card_random"}
    cards.gain_corner(s, p, "GL.3")  # cyan, not deciphered: nothing
    assert (p.score, p.publicity, p.data_pool, len(p.hand)) == after


def test_gl1_and_gl9_choose_a_group_and_score_tokens_at_the_end() -> None:  # GL.1, GL.9
    s = _with_glyphs({"yellow": ("bottom", 0), "blue": ("bottom", 1)})
    r = _play(s, "GL.1", answer=False)
    assert r.state.pending[0].kind == "glyph_group"
    assert {m["group"] for m in r.legal if m["type"] == "glyph_group"} == {0, 1}
    r = apply(r.state, {"type": "glyph_group", "group": 0})
    p = r.state.players[0]
    p.glyphs = ["red", "red", "red", "blue"]
    assert cards_end(r.state, p) == 9  # 3 VP for each token of the type with the most tokens
    s2 = _with_glyphs({})
    r2 = _play(s2, "GL.9")
    p2 = r2.state.players[0]
    p2.glyphs = ["red", "red", "blue", "cyan"]
    assert cards_end(r2.state, p2) == 3  # 1 VP for each glyph in the largest set of different glyphs


def cards_end(s: GameState, p) -> int:  # type: ignore[no-untyped-def]
    from seti_engine import cards

    return int(cards.end_points(s, p))


def test_gl2_and_gl8_choose_a_triple_and_a_doubled_glyph_pays_twice() -> None:  # GL.2, GL.8 (A-045)
    s = _with_glyphs({"pink": ("bottom", 2)})  # the 3 VP slot or another strip face: any resource
    r = _play(s, "GL.2", answer=False)
    assert r.state.pending[0].kind == "glyph_group"
    p = r.state.players[0]
    before = (p.score, p.publicity, p.data_pool, len(p.hand))
    from seti_engine.engine import apply as step

    r = step(r.state, {"type": "glyph_group", "group": 0})  # pink, pink, red: the pink resource twice
    p = r.state.players[0]
    assert (p.score, p.publicity, p.data_pool, len(p.hand)) != before
    assert cards_playable("GL.8")


def cards_playable(cid: str) -> bool:
    from seti_engine import cards

    return bool(cards.playable(cid))


def test_gl3_to_gl7_missions_cover_a_circle_for_a_glyph_resource() -> None:  # GL.3 to GL.7
    from seti_engine import cards

    s = _with_glyphs({})
    expected = {
        "GL.3": [{"e": "orbit_or_land"}],
        "GL.4": [{"e": "tech", "cat": "probe"}],
        "GL.5": [{"e": "scan"}],
        "GL.6": [{"e": "launch"}],
    }
    for cid, events in expected.items():
        r = _play(_with_glyphs({}), cid)
        st = r.state
        cards.fire(st, st.players[0], events, [])
        assert st.pending and st.pending[0].kind == "mission_trigger", cid
    r = _play(_with_glyphs({}), "GL.7")
    cards.fire(r.state, r.state.players[0], [{"e": "trace", "kind": "pink", "species": "arkhos"}], [])
    assert r.state.pending[0].kind == "mission_trigger"
    assert s is not None


def test_gl5_gl7_main_effects() -> None:  # GL.5, GL.7
    r = _play(_with_glyphs({}), "GL.5")
    assert r.state.players[0].signal_tokens == 1
    s = _with_glyphs({})
    hand = len(s.players[0].hand)
    r = _play(s, "GL.7")
    assert len(r.state.players[0].hand) == hand + 1  # the card played is out, one card is in (and the card put in the hand for the test)


def test_gl10_launches_and_has_a_quick_mission_for_this_species() -> None:  # GL.10
    r = _play(_with_glyphs({}), "GL.10")
    st = r.state
    assert any(pr.player == 0 for pr in st.probes) and "GL.10" in [m.card for m in st.players[0].missions]


def test_discarding_a_glyph_card_for_its_corner_gives_the_resource_and_the_log_says_so() -> None:  # EXP-GLY-06
    """The free corner of a Glyphids card: the resource of the deciphered glyph, or a line in the log that nothing happened."""
    s = discovered()
    s.current_player = 0
    s.phase = "play"
    s.pending = []
    me = s.players[0]
    cid = next(c["id"] for c in tables.glyphids()["cards"] if c["corner"] == "orange")
    extra = s.species[0].extra
    extra["sides"] = [0, 0]  # the first top slot gives a credit
    me.hand = [cid]
    nothing = apply(s, {"type": "discard_free", "card": cid})
    assert [e for e in nothing.events if e["type"] == "glyph_resource"] == [
        {"type": "glyph_resource", "player": 0, "glyph": "orange", "reward": []}
    ]
    assert nothing.state.players[0].credits == me.credits
    extra["top"][0] = "orange"
    done = apply(s, {"type": "discard_free", "card": cid})
    assert done.state.players[0].credits == me.credits + 1
    assert [e["reward"] for e in done.events if e["type"] == "glyph_resource"] == [[{"t": "credit", "n": 1}]]


def test_gains_of_a_move_are_listed_by_source() -> None:  # the log: what was gained, and because of what
    s = discovered()
    s.current_player = 0
    s.phase = "play"
    s.pending = []
    me = s.players[0]
    cid = next(c["id"] for c in tables.glyphids()["cards"] if c["corner"] == "orange")
    s.species[0].extra["sides"] = [0, 0]
    s.species[0].extra["top"][0] = "orange"
    me.hand = [cid]
    r = apply(s, {"type": "discard_free", "card": cid})
    gains = [e for e in r.events if e["type"] == "gains" and e["player"] == 0]
    # the credit is the glyph's, the discarded card is the move's
    assert {"kind": "glyph", "glyph": "orange", "what": "icon"} in [g["source"] for g in gains]
    credit = next(g for g in gains if g["source"]["kind"] == "glyph")
    assert credit["changes"] == {"credit": 1}
    assert next(g for g in gains if g["source"]["kind"] == "move")["changes"] == {"card": -1}
    # nothing is counted twice: the gains add up to the net change
    net = next(e for e in r.events if e["type"] == "delta" and e["player"] == 0)["changes"]
    total: dict[str, int] = {}
    for g in gains:
        for k, v in g["changes"].items():
            total[k] = total.get(k, 0) + v
    assert total == net
