"""Amoeba (Space Agencies): EXP-AMO-01 to EXP-AMO-05."""

import random

from seti_engine import amoeba, card_defs, cards, rewards, species, tables
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import GameState, Options


def game(seed: int = 1, players: int = 2) -> GameState:
    s = start(Options(players=players, seed=seed, expansion=True)).state.model_copy(deep=True)
    s.phase = "play"
    s.pending = []
    s.species[0].species = "amoeba"
    s.species[0].board = species.new_board("amoeba")
    return s


def discovered() -> GameState:
    s = game()
    s.species[0].discovery_spaces = ["p0", None, None]
    species._discover(s, 0, [])
    return s


def test_discovery_deals_the_five_organelles_on_the_marked_spaces() -> None:  # EXP-AMO-01, EXP-AMO-02
    s = discovered()
    organelles = s.species[0].extra["organelles"]
    assert sorted(organelles) == ["IB", "P1", "P2", "Y1", "Y2"]
    assert sorted(organelles.values()) == [0, 1, 2, 3, 4]
    assert len(s.players[0].hand) == 6 and s.species[0].face_up is not None  # a card for the marker, the top card face up


def test_marking_a_space_also_gains_the_organelles_of_its_section() -> None:  # EXP-AMO-03
    s = discovered()
    p = s.players[0]
    extra = s.species[0].extra
    extra["organelles"] = {"Y1": 3, "Y2": 1, "P1": 4, "P2": 2, "IB": 0}  # 2 VP, 1 data, 4 VP, 1 publicity, 1 card
    score, data = p.score, p.data_pool
    species.mark_board_space(s, p, 0, "yellow", 1, [])  # 1 VP on the space, then the yellow section: 2 VP and 1 data
    assert p.score - score == 1 + 2 and p.data_pool - data == 1


def test_the_organelles_that_gave_their_bonuses_mutate() -> None:  # EXP-AMO-05
    s = discovered()
    extra = s.species[0].extra
    extra["organelles"] = {"Y1": 3, "Y2": 1, "P1": 4, "P2": 2, "IB": 0}
    amoeba.gain_section(s, s.players[0], "yellow", [])
    # the yellow organelles move together: Y2's goes to B1, Y1's to Y2
    assert extra["organelles"] == {"B1": 1, "Y2": 3, "P1": 4, "P2": 2, "IB": 0}


def test_the_inner_organelle_moves_counter_clockwise_and_an_occupied_target_is_skipped() -> None:  # EXP-AMO-05
    s = discovered()
    extra = s.species[0].extra
    extra["organelles"] = {"IB": 0, "IY": 1, "Y1": 2}
    amoeba.mutate(extra, ["IB"])  # IB -> IY is occupied, so on to IP
    assert extra["organelles"] == {"IP": 0, "IY": 1, "Y1": 2}
    extra["organelles"] = {"B2": 0, "P1": 1, "P2": 2}
    amoeba.mutate(extra, ["B2"])  # B2 -> P1 and P2 are occupied, so on to Y1
    assert extra["organelles"] == {"Y1": 0, "P1": 1, "P2": 2}


def test_a_single_organelle_icon_gains_one_bonus_of_the_section() -> None:  # EXP-AMO-04
    s = discovered()
    p = s.players[0]
    s.current_player = 0
    s.species[0].extra["organelles"] = {"Y1": 3, "Y2": 1, "P1": 4, "P2": 2, "IB": 0}
    cards.run_step(s, p, {"t": "organelle", "color": "yellow"}, [])
    assert s.pending[0].kind == "organelle"
    moves = legal_moves(s)
    assert {m["space"] for m in moves if m["type"] == "pick_organelle"} == {"Y1", "Y2"}
    score = p.score
    r = apply(s, {"type": "pick_organelle", "space": "Y1"})
    assert r.state.players[0].score - score == 2 and "Y1" not in r.state.species[0].extra["organelles"]
    after = r.state.species[0].extra["organelles"]
    assert after["Y2"] == 1 and after["B1"] == 3 and after["P1"] == 4  # only the one moved: Y2 was occupied, so it went on to B1


def test_removing_a_marker_gains_the_organelles_of_its_section() -> None:  # EXP-AMO-04 (ET.19)
    s = discovered()
    p = s.players[0]
    s.current_player = 0
    s.species[0].board["blue"][1].append(0)
    s.species[0].extra["organelles"] = {"B1": 4, "P1": 2, "Y1": 0, "Y2": 1, "IB": 3}
    cards.run_step(s, p, {"t": "amoeba_remove"}, [])
    assert legal_moves(s)[0] == {"type": "amoeba_remove", "color": "blue", "index": 1}
    score = p.score
    r = apply(s, {"type": "amoeba_remove", "color": "blue", "index": 1})
    assert r.state.species[0].board["blue"][1] == [] and r.state.players[0].score - score == 4 + 2  # B1: 4 VP, IB: 2 VP


def test_the_amoeba_cards() -> None:  # EXP-AMO-04
    assert all(cards.playable(c) for c in ("AM.11", "AM.12", "AM.13", "AM.15", "AM.16", "AM.17", "AM.18", "AM.19"))
    assert not cards.playable("AM.14") and not cards.playable("AM.20")  # waiting for the owner's check (A-049)
    s = discovered()
    p = s.players[0]
    s.species[0].board["pink"][0].append(0)
    p.trace_log = [(0, "pink"), (0, "pink"), (0, "blue")]
    p.end_cards = ["AM.11"]
    assert cards.end_points(s, p) == 4  # 2 VP for each pink trace for this species
    assert tables.cards()["AM.11"]["species"] == "amoeba" and card_defs.CARDS["AM.17"]["mission"]["kind"] == "trigger"


def test_a_trace_for_this_species_triggers_its_mission_circles() -> None:  # EXP-AMO-04
    s = discovered()
    p = s.players[0]
    s.current_player = 0
    cards.play(s, p, p.hand[0], [])  # any card, to have the machinery in a play
    s.pending, s.queue, s.playing = [], [], None
    p.missions = []
    from seti_engine.models import MissionState

    p.missions.append(MissionState(card="AM.18", kind="trigger", used=[False, False]))
    rewards.place_trace(s, p, {"slot": 0, "space": "overflow", "color": "blue"}, [])
    assert any(d.kind == "mission_trigger" for d in s.pending)


def test_random_games_with_amoeba_finish() -> None:  # EXP-AMO-01 to EXP-AMO-05, fuzz
    for seed in range(4):
        rng = random.Random(seed)
        s = start(Options(players=2 + seed % 3, seed=seed, expansion=True)).state
        s.species[0].species = "amoeba"
        s.species[0].board = species.new_board("amoeba")
        s.species[0].discovery_spaces = ["p0", "p1", "p0"]
        s.species[0].complete = True
        for _ in range(9000):
            if s.phase == "finished":
                break
            s = apply(s, rng.choice([m for m in legal_moves(s) if m["type"] != "undo"])).state
        assert s.phase == "finished" and s.species[0].discovered
