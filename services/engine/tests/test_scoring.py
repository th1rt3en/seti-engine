"""Final scoring: gold tiles, end cards, Exertian danger and the winner (END-01 to END-17, MILE-02, MILE-03, FAQ-34, FAQ-C113)."""

from test_cards import ready

from seti_engine import card_defs, cards, scoring
from seti_engine.engine import start
from seti_engine.models import GameState, GoldTile, Options


def tile(s: GameState, name: str, side: str, markers: list[int]) -> GoldTile:
    g = next(x for x in s.gold_tiles if x.tile == name)
    g.side, g.markers = side, markers
    return g


def test_tile_values_follow_the_order_the_markers_were_placed() -> None:
    """MILE-03: the first chooser gets the top value, the second the next, later choosers the last."""
    s = ready(players=3)
    g = tile(s, "Tech", "A", [2, 0, 1])
    assert scoring.tile_values(g) == [11, 8, 5]
    for pl in range(3):
        s.players[pl].techs = ["probe-dot", "telescope-dot", "computer-dot"]
    assert [scoring.gold_points(s, s.players[pl]) for pl in range(3)] == [8, 5, 11]
    s.players[0].techs = []
    assert scoring.gold_points(s, s.players[0]) == 0


def test_tech_tiles() -> None:
    """END-10, END-11."""
    s = ready()
    p = s.players[0]
    p.techs = ["probe-dot", "probe-link", "telescope-dot", "computer-dot", "computer-link"]
    assert scoring.sets_for(s, p, tile(s, "Tech", "A", [0])) == 1  # the scarcest type has 1
    assert scoring.sets_for(s, p, tile(s, "Tech", "B", [0])) == 2  # five techs make 2 pairs


def test_mission_tiles_count_completed_missions_and_end_cards() -> None:
    """END-12, END-13, FAQ-34."""
    s = ready()
    p = s.players[0]
    p.completed_missions = ["1", "2", "3"]
    p.end_cards = ["38"]
    p.missions = []  # missions not yet completed do not count
    assert scoring.sets_for(s, p, tile(s, "Mission", "A", [0])) == 3
    assert scoring.sets_for(s, p, tile(s, "Mission", "B", [0])) == 2  # 4 in all make 2 pairs


def test_income_tiles_ignore_publicity_and_data_incomes() -> None:
    """END-14, END-15, FAQ-C231."""
    s = ready()
    p = s.players[0]
    by = {}
    from seti_engine import tables

    for c, v in tables.cards().items():
        if v["deck"] == "base":
            by.setdefault(v["income"], []).append(c)
    p.tucked = [*by["credit"][:3], *by["energy"][:2], *by["card"][:1], "ET.31"]  # ET.31's income is publicity
    assert scoring.sets_for(s, p, tile(s, "Income", "A", [0])) == 1
    assert scoring.sets_for(s, p, tile(s, "Income", "B", [0])) == 3


def test_other_tiles() -> None:
    """END-16, END-17, A-022: overflow markers count by the color of their space."""
    s = ready()
    p = s.players[0]
    p.trace_log = [(0, "pink"), (0, "pink"), (1, "yellow"), (1, "blue"), (0, "blue")]
    a = tile(s, "Other", "A", [0])
    assert scoring.sets_for(s, p, a) == 1  # pink, yellow, blue; the second pink and blue have no yellow to go with
    p.trace_log += [(0, "yellow")]  # a marker on a yellow overflow space completes a second set
    assert scoring.sets_for(s, p, a) == 2
    b = tile(s, "Other", "B", [0])
    s.sectors[0].winners = [0, 0, 0]
    p.orbiters, p.landers = {"venus": 1}, {"mars": 1, "Io": 1}
    assert scoring.sets_for(s, p, b) == 3  # 3 wins and 3 orbiters or landers


def test_a_player_without_a_marker_scores_nothing_for_a_tile() -> None:
    """MILE-02, MILE-03."""
    s = ready()
    p = s.players[0]
    p.completed_missions = ["1"]
    tile(s, "Mission", "A", [1])
    assert scoring.gold_points(s, p) == 0


def test_solvay_conference_scores_the_best_unmarked_tile_at_its_lowest_value() -> None:
    """#113, FAQ-C113."""
    s = ready()
    p = s.players[0]
    p.completed_missions = ["1", "2"]
    p.techs = ["probe-dot", "telescope-dot", "computer-dot"]
    for g in s.gold_tiles:
        g.markers = []
    tile(s, "Mission", "A", [0])  # marked: not available to the card
    tile(s, "Tech", "A", [])
    p.end_cards = ["113"]
    assert cards.end_points(s, p) == 5  # Tech A: one set at the third value (5)
    tile(s, "Tech", "A", [0])
    tile(s, "Income", "A", [])
    p.tucked = []
    tile(s, "Other", "B", [])
    assert cards.end_points(s, p) == 0


def test_final_scores_add_up_and_the_danger_loss_comes_last() -> None:
    """END-01 to END-03, ALIEN-EXE-07."""
    s = ready()
    p0, p1 = s.players[0], s.players[1]
    p0.score, p1.score = 100, 50
    p0.end_cards = ["38"]
    s.sectors[[i for i, x in enumerate(s.sectors) if x.color == "red"][0]].winners = [0, 0]  # #38: 3 per red win
    tile(s, "Mission", "A", [0])
    p0.completed_missions = ["1", "2"]  # first marker: 4 each
    rows = scoring.final_scores(s)
    assert rows[0]["total"] == 100 + 6 + 8 and rows[1]["total"] == 50
    assert scoring.winners(rows) == [0]
    rows[1]["total"] = rows[0]["total"]
    assert scoring.winners(rows) == [0, 1]  # equal scores tie


def test_a_finished_game_has_its_final_scores() -> None:
    """END-01."""
    from test_engine import play_towards_progress

    r = play_towards_progress(2, 3)
    st = r.state
    assert st.phase == "finished" and len(st.final_scores) == 2 and st.winners
    for row, p in zip(st.final_scores, st.players, strict=True):
        assert row["total"] == p.score + row["cards"] + row["gold"] + row["exertian"] - row["loss"]
    assert start(Options(players=2, seed=1)).state.final_scores == [] and card_defs.CARDS["113"]["end"]["what"] == "solvay"


def test_the_end_of_the_game_logs_each_end_card_and_each_gold_tile() -> None:  # END-02, END-10 to END-17, the log
    s = ready(players=2)
    tile(s, "Tech", "A", [1, 0])
    s.players[0].techs = ["probe-dot", "telescope-dot", "computer-dot"]
    s.players[0].end_cards = ["12"]  # an end-of-game scoring card
    events = scoring.endgame_events(s)
    gold = [e for e in events if e["type"] == "endgame_gold" and e["player"] == 0]
    assert len(gold) == 1 and gold[0]["tile"] == "Tech" and gold[0]["sets"] == 1
    assert gold[0]["points"] == gold[0]["per"] * gold[0]["sets"] == scoring.gold_points(s, s.players[0])
    card = next(e for e in events if e["type"] == "endgame_card")
    assert card["card"] == "12" and card["points"] == cards.end_card_points(s, s.players[0], "12")
