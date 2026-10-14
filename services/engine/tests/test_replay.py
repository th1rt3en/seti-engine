"""The game archive (decision D25): a replay.json rebuilds the game and every event."""

import copy
import json

import pytest
from test_engine import play_randomly

from seti_engine import replay as rp
from seti_engine.engine import apply, start
from seti_engine.models import Options


def archive_of(players: int, seed: int, policy: int) -> tuple[dict[str, object], object]:
    """Play a game and write it the way the Worker does."""
    final, log = play_randomly(players, seed, policy)
    r = start(Options(players=players, seed=seed))
    actions = []
    for n, move in enumerate(log):
        r = apply(r.state, move)
        actions.append({"seq": n, "seat": 0, "action": move, "at": n, "events": r.events})
    file = {
        "format": rp.FORMAT,
        "header": {"id": "g", "options": {"players": players, "seed": seed}},
        "actions": actions,
        "result": {"status": "finished", "result": {"reason": "completed"}},
    }
    return json.loads(json.dumps(file)), final  # through JSON, as the archive stores it


@pytest.mark.parametrize("players", [1, 2, 4])
def test_the_archive_rebuilds_the_game_and_its_events(players: int) -> None:
    file, final = archive_of(players, seed=11, policy=3)
    last = rp.verify(file)  # type: ignore[arg-type]
    assert last.state == final.state  # type: ignore[attr-defined]
    assert last.state.phase == "finished"


def test_every_step_is_yielded_in_order() -> None:
    file, _ = archive_of(2, seed=5, policy=1)
    seen = [n for n, _, _ in rp.steps(file)]  # type: ignore[arg-type]
    assert seen == list(range(len(file["actions"]) + 1))  # type: ignore[arg-type]


def test_a_changed_event_or_a_missing_action_is_detected() -> None:
    file, _ = archive_of(2, seed=5, policy=1)
    bad = copy.deepcopy(file)
    bad["actions"][3]["events"] = [{"type": "nothing happened"}]  # type: ignore[index]
    with pytest.raises(rp.ReplayMismatch):
        rp.verify(bad)  # type: ignore[arg-type]
    gap = copy.deepcopy(file)
    del gap["actions"][2]  # type: ignore[attr-defined]
    with pytest.raises(rp.ReplayMismatch):
        rp.verify(gap)  # type: ignore[arg-type]


def test_an_unknown_format_is_refused() -> None:
    with pytest.raises(ValueError):
        list(rp.steps({"format": "other", "header": {}, "actions": []}))
