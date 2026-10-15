"""The solo rival with the species of the expansion (EXP-SOLO-07, EXP-ARK-08, EXP-GLY-08, EXP-AMO-06, A-033)."""

from typing import Any

from seti_engine import amoeba, glyphids, rival, scoring, species
from seti_engine.engine import start
from seti_engine.models import GameState, Options, SpeciesSlot


def solo_with(*names: str, seed: int = 3, difficulty: int = 3) -> GameState:
    """A solo expansion game whose species are `names` (discovered)."""
    s = start(Options(players=1, seed=seed, difficulty=difficulty, expansion=True)).state
    s.pending = []
    events: list[dict[str, Any]] = []
    s.species = [SpeciesSlot(species=n, board=species.new_board(n)) for n in names]
    for i, sl in enumerate(s.species):
        sl.discovered = True
        sl.discovery_spaces = [None, None, None]
        if sl.species == "glyphids":
            glyphids.setup(s, sl, events)
        elif sl.species == "amoeba":
            amoeba.setup(s, sl, events)
        elif sl.species == "arkhos":
            from seti_engine import arkhos

            arkhos.discover(s, sl, [], events)
        assert i >= 0
    return s


def test_exp_solo_07_the_species_of_the_expansion_are_in_a_solo_pool() -> None:
    seen: set[str] = set()
    for seed in range(40):
        seen |= {sl.species for sl in start(Options(players=1, seed=seed, expansion=True)).state.species}
    assert {"arkhos", "glyphids", "amoeba"} <= seen
    base: set[str] = set()
    for seed in range(40):
        base |= {sl.species for sl in start(Options(players=1, seed=seed)).state.species}
    assert not base & {"arkhos", "glyphids", "amoeba"}


def test_exp_solo_07_each_species_has_a_rival_card() -> None:
    assert rival.SPECIES_CARD["glyphids"] == "SE.2" and rival.SPECIES_CARD["arkhos"] == "SE.3" and rival.SPECIES_CARD["amoeba"] == "SE.4"


def test_exp_ark_08_the_rival_has_security_cards_and_an_advance_instead_of_a_breach() -> None:
    s = solo_with("arkhos", "amoeba")
    r = s.players[1]
    assert set(r.security) == {"pink", "yellow", "blue"}
    before = s.rival.progress  # type: ignore[union-attr]
    from seti_engine import arkhos

    arkhos.on_overflow(s, r, 0, "pink")
    assert "pink" in r.security and not s.pending  # no breach, no decision
    assert s.rival.progress == (before + 1) % len(rival.TRACK)  # type: ignore[union-attr]


def test_exp_ark_08_its_arkhos_card_breaches_at_random_and_explores_twice() -> None:
    s = solo_with("arkhos", "amoeba")
    r = s.players[1]
    score = r.score
    ev: list[dict[str, Any]] = []
    assert rival._text(s, {"kind": "text", "effect": "arkhos_breach"}, ev)
    assert len(r.security) == 2 and r.score >= score + 3  # the overflow space gives 3 VP
    assert len([e for e in ev if e.get("type") == "explore"]) == 2
    assert len(s.species[0].overflow) == 1


def test_exp_ark_08_the_rival_ignores_arkhos_spaces_it_cannot_reach() -> None:
    s = solo_with("arkhos", "amoeba")
    p = s.players[1]
    moves = species.board_moves(s, p, 0, ("pink",))
    assert {m["index"] for m in moves} == {0}  # level 0 only, with all 3 security cards in front


def test_exp_gly_08_a_new_glyph_is_placed_at_once_and_a_repeat_is_kept() -> None:
    s = solo_with("glyphids", "amoeba")
    p = s.players[1]
    ev: list[dict[str, Any]] = []
    extra = s.species[0].extra
    extra["tokens"]["planet:mars"] = "red"
    glyphids.take(s, p, "planet:mars", ev)
    assert "red" in glyphids.deciphered(s) and "red" not in p.glyphs
    extra["tokens"]["planet:venus"] = "red"
    glyphids.take(s, p, "planet:venus", ev)
    assert p.glyphs == ["red"]  # the type is already on the board: the token is kept


def test_exp_gly_08_the_rival_scores_3_points_for_each_token() -> None:
    s = solo_with("glyphids", "amoeba")
    p = s.players[1]
    p.glyphs = ["red", "red", "blue"]
    rows = scoring.final_scores(s)
    assert rows[1]["glyphs"] == 9


def test_exp_gly_08_a_signal_token_reward_is_an_advance() -> None:
    s = solo_with("glyphids", "amoeba")
    before = s.rival.progress  # type: ignore[union-attr]
    rival.grant(s, [{"t": "signal_token", "n": 1}], [])
    assert s.rival.progress == (before + 1) % len(rival.TRACK)  # type: ignore[union-attr]


def test_exp_gly_08_the_glyphids_card_goes_for_planets_that_carry_a_glyph() -> None:
    s = solo_with("glyphids", "amoeba")
    extra = s.species[0].extra
    extra["tokens"] = {k: v for k, v in extra["tokens"].items() if not k.startswith("planet:")}
    card = rival.tables.rival_cards()["SE.2"]["actions"][0]
    assert rival._probe(s, card, []) is False  # no planet carries a token: the probe action is skipped


def test_exp_amo_06_the_rival_ignores_amoeba_spaces_with_fewer_than_two_organelle_bonuses() -> None:
    s = solo_with("amoeba", "glyphids")
    extra = s.species[0].extra
    for color in ("pink", "yellow", "blue"):
        assert rival._rival_wants(s, 0, color, 0) == (len(amoeba.in_section(extra, color)) >= 2)


def test_a_033_the_amoeba_card_needs_a_full_section() -> None:
    s = solo_with("amoeba", "glyphids")
    extra = s.species[0].extra
    extra["organelles"] = {"Y1": 0, "Y2": 1, "IY": 2, "P1": 3, "B1": 4}
    before = dict(extra["organelles"])
    assert rival._text(s, {"kind": "text", "effect": "amoeba_section"}, [])
    assert extra["organelles"] != before  # the yellow section (3 organelles) mutated
    assert rival._text(s, {"kind": "text", "effect": "amoeba_section"}, []) is False
