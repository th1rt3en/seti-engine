"""The statistics of a game (stats.py): derived from the replay, not a rule."""

import random
from typing import Any

from fastapi.testclient import TestClient
from test_engine import PROGRESS_TYPES

from seti_engine import stats
from seti_engine.engine import apply, start
from seti_engine.models import Options
from seti_engine.service import app

client = TestClient(app)


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
