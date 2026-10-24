"""D25, UNDO-01: the archive of a game has no `undo` and none of the moves taken back, and what is left replays to the same game."""

import random
from typing import Any

import pytest

from seti_engine.engine import apply, start
from seti_engine.models import GameState, Options


def without_undone(log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The same as `withoutUndone` of apps/worker/src/core/archive.ts."""
    kept: list[dict[str, Any]] = []
    for a in log:
        if a["type"] == "undo":
            kept.pop()
        else:
            kept.append(a)
    return kept


def comparable(s: GameState) -> dict[str, Any]:
    d = s.model_dump()
    d["undo"], d["undo_log"] = None, []  # what can still be taken back is not part of the game
    return d


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_a_log_without_the_undone_moves_replays_to_the_same_game(seed: int) -> None:
    rnd = random.Random(seed)
    options = Options(players=2, seed=seed)
    r = start(options)
    log: list[dict[str, Any]] = []
    undone = 0
    for _ in range(250):
        if not r.legal:
            break
        undos = [m for m in r.legal if m["type"] == "undo"]
        move = undos[0] if undos and rnd.random() < 0.3 else rnd.choice([m for m in r.legal if m["type"] != "undo"] or r.legal)
        r = apply(r.state, move)
        log.append(move)
        undone += move["type"] == "undo"
    assert undone > 0, "the test must take some moves back"
    replayed = start(options)
    kept = without_undone(log)
    for a in kept:
        replayed = apply(replayed.state, a)
    assert len(kept) == len(log) - 2 * undone
    assert comparable(replayed.state) == comparable(r.state)
