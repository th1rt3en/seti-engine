"""The random state is written as a string in JSON (JavaScript would round a number of 64 bits), and a game that the Worker played before
that is replayed with the rounding it suffered (A-004, CLAUDE.md rule 4: the same seed and actions always give the same state)."""

import json
import random

from seti_engine import replay as rp
from seti_engine.engine import apply, legal_moves, start
from seti_engine.models import GameState, Options


def test_the_random_state_is_a_string_in_json_and_a_number_is_still_read() -> None:
    state = start(Options(players=2, seed=7)).state
    assert state.rng_state > 2**53  # a number of this size does not survive JavaScript
    written = json.loads(state.model_dump_json())
    assert written["rng_state"] == str(state.rng_state)
    assert GameState.model_validate_json(state.model_dump_json()).rng_state == state.rng_state
    old = json.loads(state.model_dump_json())
    old["rng_state"] = state.rng_state  # a game stored before: a number
    assert GameState.model_validate(old).rng_state == state.rng_state
    assert isinstance(state.model_dump()["rng_state"], int)  # in the engine it stays a number


def played_through_javascript(seed: int, moves: int) -> tuple[dict, bool]:
    """A game as the Worker played it before: the state was rounded like a JavaScript number between two moves."""
    rng = random.Random(seed)
    r = start(Options(players=2, seed=seed))
    actions = []
    for n in range(moves):
        if not r.legal:
            break
        move = rng.choice(legal_moves(r.state))
        state = r.state.model_copy()
        state.rng_state = rp.js_number(state.rng_state)
        r = apply(state, move)
        actions.append({"seq": n, "seat": 0, "action": move, "at": n, "events": r.events})
    return {"format": rp.FORMAT, "header": {"id": "g", "options": {"players": 2, "seed": seed}}, "actions": actions}, True


def test_a_game_played_with_a_rounded_state_replays_with_the_double_encoding() -> None:
    file, _ = played_through_javascript(seed=3, moves=400)
    for n, entry, result in rp.steps(file, rng_encoding="double"):
        if entry is not None:
            assert entry["events"] == result.events, f"the events of action {n - 1} differ"


def test_the_header_can_say_that_the_state_was_rounded() -> None:
    file, _ = played_through_javascript(seed=3, moves=60)
    file["header"]["rngEncoding"] = "double"
    assert sum(1 for _ in rp.steps(file)) == 61


def test_js_number_is_the_nearest_double_written_with_its_shortest_digits() -> None:
    assert rp.js_number(5) == 5
    assert rp.js_number(2**53 + 1) == 2**53  # the odd number above 2**53 is not a double
    assert rp.js_number(12345678901234567890) == 12345678901234567000  # JSON.stringify(12345678901234567890) in JavaScript


def test_the_replay_view_endpoint_gives_a_step_and_the_one_before() -> None:
    from fastapi.testclient import TestClient

    from seti_engine.service import app

    file, _ = played_through_javascript(seed=3, moves=80)
    actions = [e["action"] for e in file["actions"]]
    client = TestClient(app)
    body = {"options": file["header"]["options"], "actions": actions, "step": 40, "viewer": None, "rng_encoding": "double"}
    res = client.post("/replay/view", json=body)
    assert res.status_code == 200
    got = res.json()
    assert got["step"] == 40 and got["previous"] is not None
    # the same state as the step-by-step replay (the round count and the scores are enough to see that it is the 40th)
    states = [r.state for _, _, r in rp.steps(file, rng_encoding="double")]
    assert got["view"]["state"]["round"] == states[40].round
    assert [p["score"] for p in got["view"]["state"]["players"]] == [p.score for p in states[40].players]
    assert [p["score"] for p in got["previous"]["state"]["players"]] == [p.score for p in states[39].players]
    start = client.post("/replay/view", json={**body, "step": 0}).json()
    assert start["previous"] is None
    far = client.post("/replay/view", json={**body, "step": 9999}).json()
    assert far["step"] == 80  # a step past the end is the last one
