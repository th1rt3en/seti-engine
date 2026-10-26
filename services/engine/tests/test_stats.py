"""The statistics of a game (stats.py): derived from the replay, not a rule."""

import random
from collections import Counter
from typing import Any

from fastapi.testclient import TestClient
from test_engine import PROGRESS_TYPES

from seti_engine import stats
from seti_engine.engine import apply, start
from seti_engine.models import Options
from seti_engine.service import app

client = TestClient(app)
SPECIES = {"arkhos", "glyphids", "anomalies", "mascamites", "centaurians", "amoeba", "exertians", "oumuamua"}


def play(seed: int, players: int, **kw: Any) -> tuple[Options, list[dict[str, Any]]]:
    rnd = random.Random(seed)
    options = Options(players=players, seed=seed, **kw)
    r = start(options)
    actions: list[dict[str, Any]] = []
    for _ in range(20000):
        if not r.legal:
            break
        pref = [m for m in r.legal if m["type"] in PROGRESS_TYPES]
        m = rnd.choice(pref or r.legal)
        actions.append(dict(m))
        r = apply(r.state, m)
    assert r.state.phase == "finished"
    return options, actions


def file_of(options: Options, actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "format": "seti-game-log/1",
        "header": {"options": options.model_dump()},
        "actions": [{"seq": i, "action": a} for i, a in enumerate(actions)],
    }


def test_a_game_gives_the_same_statistics_every_time() -> None:
    options, actions = play(5, 3)
    assert stats.game_stats(file_of(options, actions)) == stats.game_stats(file_of(options, actions))


def test_every_player_has_counters_that_agree_with_each_other() -> None:
    options, actions = play(5, 3)
    s = stats.game_stats(file_of(options, actions))
    assert [p["seat"] for p in s["players"]] == [0, 1, 2] and s["rounds"] == 5 and len(s["species"]) == 2
    for p in s["players"]:
        c = p["counters"]
        assert sum(v for k, v in c.items() if k.startswith("action.")) > 0
        assert sum(v for k, v in c.items() if k.startswith("tucked.")) >= 1  # the card tucked at the setup
        assert all(f"incomerate.r{r}.credit" in c for r in range(1, 6))  # the income of each round (INCOME-01), also the last one
        assert c["incomerate.r1.credit"] >= 2 and c["incomerate.r5.credit"] >= c["incomerate.r1.credit"]


def test_probes_orbits_and_landings_that_did_not_come_from_their_main_action_are_counted_apart() -> None:
    """Every launch, orbit and landing is either the main action of that name or something else (a card, a reward, an organization tile)."""
    seen_other = {"probes.launched.other": 0, "orbits.other": 0, "lands.other": 0}
    for seed in (5, 7, 9, 11):
        options, actions = play(seed, 2, expansion=bool(seed % 2), organizations=bool(seed % 2))
        for p in stats.game_stats(file_of(options, actions))["players"]:
            c = p["counters"]
            assert c.get("probes.launched", 0) == c.get("action.launch", 0) + c.get("probes.launched.other", 0)
            assert c.get("orbiters", 0) == c.get("action.orbit", 0) + c.get("orbits.other", 0)
            assert c.get("landers", 0) == c.get("action.land", 0) + c.get("lands.other", 0)
            for k in seen_other:
                seen_other[k] += c.get(k, 0)
    assert seen_other["probes.launched.other"] > 0, "the random games launch probes by cards or rewards too"


def test_every_row_carries_the_version_of_the_statistics() -> None:
    options, actions = play(5, 2)
    for p in stats.game_stats(file_of(options, actions))["players"]:
        assert p["counters"]["stats.version"] == stats.VERSION


def test_the_organizations_offered_and_picked_are_counted() -> None:
    options, actions = play(6, 2, expansion=True, organizations=True)
    s = stats.game_stats(file_of(options, actions))
    for p in s["players"]:
        assert p["org"] in p["org_offered"] and len(p["org_offered"]) == 2


def test_the_solo_rival_is_no_player() -> None:
    options, actions = play(7, 1)
    assert len(stats.game_stats(file_of(options, actions))["players"]) == 1


def test_the_service_makes_the_same_statistics_from_the_options_and_the_actions() -> None:
    options, actions = play(5, 2)
    reply = client.post("/stats", json={"options": options.model_dump(), "actions": actions})
    assert reply.status_code in (200, 401)
    if reply.status_code == 200:
        assert reply.json() == stats.game_stats(file_of(options, actions))


def test_the_cards_played_are_counted_by_round_and_the_final_score_by_part() -> None:
    options, actions = play(5, 3)
    s = stats.game_stats(file_of(options, actions))
    assert s["version"] == stats.VERSION
    for p in s["players"]:
        c = p["counters"]
        by_round = {k: v for k, v in c.items() if k.startswith("card.")}
        assert sum(by_round.values()) == c.get("cards.played", 0)  # every card played is in exactly one round
        assert all(int(k.rsplit(".r", 1)[1]) in range(1, 6) for k in by_round)
        assert c.get("final.board", 0) > 0  # the page adds the parts up: board + cards + gold + Exertian + glyphs - loss is the final score


def test_what_each_resource_was_spent_on_is_counted() -> None:
    options, actions = play(5, 3)
    s = stats.game_stats(file_of(options, actions))
    assert s["version"] == stats.VERSION
    keys = {k for p in s["players"] for k in p["counters"] if k.startswith("spend.")}
    assert {"spend.scan.credit", "spend.play_card.credit", "spend.computer_empty.data", "spend.trade.card"} <= keys
    assert not [k for k in keys if k.endswith(".vp")]  # points are not spent


def test_the_exofossils_left_at_the_end_and_the_glyph_tokens_are_counted() -> None:
    from seti_engine import trail

    s = start(Options(players=2, seed=1, expansion=True)).state.model_copy(deep=True)
    p = s.players[0]
    p.glyphs = ["red"]
    with trail.scope(s, {"kind": "planet", "planet": "mars", "what": "orbit"}):
        p.glyphs.append("blue")  # a token that an orbit gave
    with trail.cost(s, "decipher"):
        p.glyphs.remove("red")  # a token placed on the translation board
    c: Counter[str] = Counter()
    for e in trail.events_of(s):
        stats.gain_counts(c, e)
    assert c["gain.planet.token"] == 1 and c["spend.decipher.token"] == 1


def test_the_exofossils_and_the_costs_of_effects_are_counted() -> None:
    from collections import Counter

    from seti_engine import trail

    s = start(Options(players=2, seed=1)).state.model_copy(deep=True)
    p = s.players[0]
    p.exofossils = 3
    with trail.cost(s, "optional"):  # an optional effect that asks an exofossil
        p.exofossils -= 1
    with trail.scope(s, {"kind": "alien", "species": "oumuamua", "what": "tile"}):
        p.exofossils += 2
    c: Counter[str] = Counter()
    for e in trail.events_of(s):
        stats.gain_counts(c, e)
    assert c["spend.optional.exofossil"] == 1
    assert c["gain.alien.exofossil"] == 2 and c["alien.oumuamua.tile.exofossil"] == 2


def test_the_publicity_that_the_aliens_gave_is_counted_by_species() -> None:
    """The per-species counters add up to the per-source ones (explore, glyph, anomaly and the alien scope) and name a real species."""
    for seed in range(3, 25):
        for kw in ({}, {"expansion": True, "organizations": True}):
            options, actions = play(seed, 2, **kw)
            for p in stats.game_stats(file_of(options, actions))["players"]:
                c = p["counters"]
                by_species = {k: v for k, v in c.items() if k.startswith("publicity.alien.")}
                by_source = sum(v for k, v in c.items() if k in [f"gain.{s}.publicity" for s in ("explore", "glyph", "anomaly", "alien")])
                assert sum(by_species.values()) == by_source
                assert all(k.split(".")[-1] in SPECIES for k in by_species)


def test_the_techs_are_counted_by_where_they_came_from() -> None:
    options, actions = play(5, 3)
    s = stats.game_stats(file_of(options, actions))
    origins = Counter[str]()
    for p in s["players"]:
        for k, v in p["counters"].items():
            if k.startswith("techorigin."):
                origins[k] += v
    assert origins["techorigin.research"] > 0
    assert sum(origins.values()) >= sum(v for p in s["players"] for k, v in p["counters"].items() if k.startswith("techcat."))


def test_the_cards_held_discarded_for_a_corner_and_scored_at_the_end_are_counted() -> None:
    options, actions = play(5, 3)
    s = stats.game_stats(file_of(options, actions))
    total: Counter[str] = Counter()
    for p in s["players"]:
        for k, v in p["counters"].items():
            total[k.split(".")[0]] += v
    assert total["cardheld"] > 0 and total["cardheld"] >= total["card"]  # a card that is played was in a hand
    assert total["cardcorner"] == sum(1 for a in actions if a["type"] == "discard_free")
    assert total["cardend"] == sum(p["counters"].get("endcards.points", 0) for p in s["players"])
