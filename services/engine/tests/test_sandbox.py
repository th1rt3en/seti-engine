"""The solo sandbox (D33): a practice game for one player, without the rival, with free cards, resources and disc rotation."""

import random

import pytest
from test_engine import with_state

from seti_engine import sandbox, solar
from seti_engine.engine import IllegalAction, StepResult, apply, legal_moves, start
from seti_engine.models import GameState, Options, Probe, SpeciesSlot


def begin_sandbox(seed: int = 3, promo: bool = False) -> StepResult:
    r = start(Options(players=1, sandbox=True, seed=seed, promo_cards=promo))
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    return r


def sandbox_marker(r: StepResult) -> dict:
    return next(m for m in r.legal if m["type"] == "sandbox")


def reveal(s: GameState, species: str) -> None:
    from seti_engine import species as sp

    s.species = [SpeciesSlot(species=species, board=sp.new_board(species)), s.species[1]]
    sp._discover(s, 0, [])


def test_the_sandbox_is_a_game_for_one_player_without_a_rival() -> None:
    """SANDBOX-01."""
    r = begin_sandbox()
    assert r.state.rival is None and len(r.state.players) == 1 and r.state.options.sandbox
    assert sandbox_marker(r)["discs"] == [1, 2, 3]
    with pytest.raises(ValueError):
        Options(players=2, sandbox=True)


def test_sandbox_actions_are_refused_in_a_normal_game() -> None:
    """SANDBOX-01."""
    r = start(Options(players=1, seed=3))
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    assert not any(m["type"] == "sandbox" for m in r.legal)
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "sandbox_resource", "resource": "credit", "n": 3})


def test_any_base_card_can_be_added_to_the_hand_and_leaves_the_deck() -> None:
    """SANDBOX-02."""
    r = begin_sandbox()
    cid = r.state.deck[0]
    other = next(c for c in sandbox_marker(r)["cards"] if c not in r.state.players[0].hand and c != cid and not c.startswith("ET."))
    before = len(r.state.players[0].hand)
    r2 = apply(r.state, {"type": "sandbox_add_card", "card": cid})
    assert r2.state.players[0].hand.count(cid) == 1 and cid not in r2.state.deck and len(r2.state.players[0].hand) == before + 1
    r3 = apply(r2.state, {"type": "sandbox_add_card", "card": other})
    assert other in r3.state.players[0].hand and sum(1 for c in (*r3.state.deck, *r3.state.discard, *r3.state.card_row) if c == other) == 0
    assert len(r3.state.card_row) == 3  # a card taken from the display is replaced


def test_alien_cards_need_their_species_to_be_face_up() -> None:
    """SANDBOX-02."""
    r = begin_sandbox()
    assert not any(c.startswith("ET.") for c in sandbox_marker(r)["cards"])
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "sandbox_add_card", "card": "ET.31"})
    s = r.state.model_copy(deep=True)
    reveal(s, "centaurians")
    s.pending = []
    s.stage = None
    r2 = with_state(s)
    assert "ET.31" in sandbox_marker(r2)["cards"] and "ET.1" not in sandbox_marker(r2)["cards"]
    r3 = apply(r2.state, {"type": "sandbox_add_card", "card": "ET.31"})
    assert "ET.31" in r3.state.players[0].hand and "ET.31" not in r3.state.species[0].deck


def test_exertian_cards_go_to_the_exertian_hand_not_the_hand() -> None:
    """SANDBOX-02, ALIEN-EXE-02."""
    r = begin_sandbox()
    s = r.state.model_copy(deep=True)
    reveal(s, "exertians")
    s.pending = []
    s.stage = None
    r2 = apply(with_state(s).state, {"type": "sandbox_add_card", "card": "ET.41"})
    assert "ET.41" in r2.state.players[0].exertian_hand and "ET.41" not in r2.state.players[0].hand


def test_resources_can_be_added_and_removed_within_their_limits() -> None:
    """SANDBOX-03."""
    r = begin_sandbox()
    p = r.state.players[0]
    credits, energy = p.credits, p.energy
    r = apply(r.state, {"type": "sandbox_resource", "resource": "credit", "n": 7})
    r = apply(r.state, {"type": "sandbox_resource", "resource": "energy", "n": 5})
    r = apply(r.state, {"type": "sandbox_resource", "resource": "data", "n": 20})
    r = apply(r.state, {"type": "sandbox_resource", "resource": "publicity", "n": 50})
    q = r.state.players[0]
    assert q.credits == credits + 7 and q.energy == energy + 5 and q.data_pool == 6 and q.publicity == 10
    r = apply(r.state, {"type": "sandbox_resource", "resource": "credit", "n": -50})
    assert r.state.players[0].credits == 0
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "sandbox_resource", "resource": "credit", "n": 0})
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "sandbox_resource", "resource": "gold", "n": 1})


def test_exofossils_exist_only_when_oumuamua_is_face_up() -> None:
    """SANDBOX-03."""
    r = begin_sandbox()
    assert "exofossil" not in sandbox_marker(r)["resources"]
    with pytest.raises(IllegalAction):
        apply(r.state, {"type": "sandbox_resource", "resource": "exofossil", "n": 2})
    s = r.state.model_copy(deep=True)
    reveal(s, "oumuamua")
    s.pending = []
    s.stage = None
    r2 = with_state(s)
    assert "exofossil" in sandbox_marker(r2)["resources"]
    r3 = apply(r2.state, {"type": "sandbox_resource", "resource": "exofossil", "n": 4})
    assert r3.state.players[0].exofossils == 4


def test_a_disc_can_be_turned_either_way_without_changing_the_turn_of_the_game() -> None:
    """SANDBOX-04."""
    r = begin_sandbox()
    s = r.state
    angles, rotations = list(s.disc_angles), s.rotations
    r2 = apply(s, {"type": "sandbox_rotate", "disc": 2, "step": 1})
    assert r2.state.disc_angles == [angles[0], (angles[1] + 1) % 8, angles[2]] and r2.state.rotations == rotations
    r3 = apply(r2.state, {"type": "sandbox_rotate", "disc": 2, "step": -1})
    assert r3.state.disc_angles == angles
    with pytest.raises(IllegalAction):
        apply(r3.state, {"type": "sandbox_rotate", "disc": 4, "step": 1})


def test_a_probe_rides_along_with_its_disc_and_a_pushed_probe_gains_nothing() -> None:
    """SANDBOX-04."""
    r = begin_sandbox()
    s = r.state.model_copy(deep=True)
    pos = solar.find_cell(s, "PLANET:MARS")
    assert pos is not None
    disc = solar.visible(s, *pos)[0]
    s.probes.append(Probe(id="p1", player=0, ring=pos[0], sector=pos[1]))
    publicity = s.players[0].publicity
    r2 = apply(with_state(s).state, {"type": "sandbox_rotate", "disc": disc, "step": 1}) if disc <= 3 else None
    if r2 is not None:
        moved = next(pr for pr in r2.state.probes if pr.id == "p1")
        assert moved.sector == (pos[1] + 1) % 8 and solar.visible(r2.state, moved.ring, moved.sector)[1] == "PLANET:MARS"
        assert r2.state.players[0].publicity == publicity


def test_sandbox_changes_can_be_taken_back() -> None:
    """SANDBOX-05, UNDO-01."""
    r = begin_sandbox()
    credits = r.state.players[0].credits
    r2 = apply(r.state, {"type": "sandbox_resource", "resource": "credit", "n": 5})
    assert {"type": "undo"} in r2.legal
    r3 = apply(r2.state, {"type": "undo"})
    assert r3.state.players[0].credits == credits


def test_the_sandbox_keeps_working_through_a_whole_game_of_random_moves() -> None:
    """SANDBOX-01 to SANDBOX-05: a one-player game without a rival plays to the end with things added all the time."""
    rnd = random.Random(5)
    r = begin_sandbox(seed=7)
    steps = 0
    while r.legal and steps < 20000:
        if steps % 7 == 0:  # now and then something is added
            action = rnd.choice(
                [
                    {"type": "sandbox_resource", "resource": rnd.choice(["credit", "energy", "data"]), "n": rnd.randint(1, 5)},
                    {"type": "sandbox_rotate", "disc": rnd.randint(1, 3), "step": rnd.choice([1, -1])},
                    {"type": "sandbox_add_card", "card": rnd.choice(sandbox.addable_cards(r.state))},
                ]
            )
            if not r.state.pending:
                r = apply(r.state, action)
        r = apply(r.state, rnd.choice([m for m in r.legal if m["type"] != "sandbox"]))
        steps += 1
        assert len(legal_moves(r.state)) == len(r.legal)
    assert r.state.phase == "finished"


def test_the_sandbox_can_choose_the_face_down_species() -> None:
    """SANDBOX-06: a chosen species keeps its slot; a slot left to chance takes another species."""
    both = start(Options(players=1, sandbox=True, seed=3, sandbox_species=["exertians", "mascamites"])).state
    assert [sl.species for sl in both.species] == ["exertians", "mascamites"]
    one = start(Options(players=1, sandbox=True, seed=3, sandbox_species=[None, "oumuamua"])).state
    assert one.species[1].species == "oumuamua" and one.species[0].species != "oumuamua"
    again = start(Options(players=1, sandbox=True, seed=3, sandbox_species=[None, "oumuamua"])).state
    assert [sl.species for sl in again.species] == [sl.species for sl in one.species]  # the same seed gives the same game
    assert not any(sl.discovered for sl in both.species)  # they are still face down: discovering them is part of play
    plain = start(Options(players=1, sandbox=True, seed=3)).state
    assert [sl.species for sl in plain.species] == [sl.species for sl in start(Options(players=1, sandbox=True, seed=3)).state.species]


def test_the_species_choice_is_refused_outside_the_sandbox_and_when_it_makes_no_sense() -> None:
    """SANDBOX-06."""
    with pytest.raises(ValueError):
        Options(players=1, sandbox_species=["exertians", None])
    with pytest.raises(ValueError):
        Options(players=1, sandbox=True, sandbox_species=["exertians", "exertians"])
    with pytest.raises(ValueError):
        Options(players=1, sandbox=True, sandbox_species=["glyphids", None])
    with pytest.raises(ValueError):
        Options(players=1, sandbox=True, sandbox_species=["exertians"])


def test_sandbox_06_the_species_of_the_expansion_can_be_chosen_with_the_expansion() -> None:
    s = start(Options(players=1, sandbox=True, expansion=True, seed=3, sandbox_species=["arkhos", "amoeba"])).state
    assert [sl.species for sl in s.species] == ["arkhos", "amoeba"]
    mixed = start(Options(players=1, sandbox=True, expansion=True, seed=3, sandbox_species=["glyphids", None])).state
    assert mixed.species[0].species == "glyphids" and mixed.species[1].species != "glyphids"
    with pytest.raises(ValueError):  # not without the expansion
        Options(players=1, sandbox=True, sandbox_species=["arkhos", None])
