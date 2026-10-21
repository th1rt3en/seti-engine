"""Rebuild a game from its archive (docs/PLAN.md decision D25).

The Worker writes every game to Google Cloud Storage as a `replay.json` (format "seti-game-log/1"): a header with the options and the
seed, then the actions in order, each with the events the engine reported, then the result. This module turns that file back into the
sequence of states and events. It is pure (no I/O): `tools/engine/replay_log.py` reads the file or the bucket's objects.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from . import engine
from .models import Options

FORMAT = "seti-game-log/1"


class ReplayMismatch(Exception):
    """The engine does not reproduce what the archive recorded (the rules changed since the game, or the archive is damaged)."""


def js_number(x: int) -> int:
    """What a whole number becomes after JavaScript has read it from JSON and written it again: the nearest double, written with its
    shortest digits. The Worker did this to the random state of every game that was played before the state was written as a string
    (`models.RngState`)."""
    return int(Decimal(repr(float(x))))


def steps(replay: dict[str, Any], rng_encoding: str | None = None) -> Iterator[tuple[int, dict[str, Any] | None, engine.StepResult]]:
    """Yield (step, entry, result) for every step: step 0 is the start (entry None); step n follows the n-th archived action.
    `rng_encoding` (or the header's `rngEncoding`) is "exact" (the default: the random state was kept whole) or "double": the game was
    played through the Worker before the state was written as a string, which rounded the random state after every move, so the replay
    does the same."""
    if replay.get("format") != FORMAT:
        raise ValueError(f"unknown archive format {replay.get('format')!r}")
    encoding = rng_encoding or replay["header"].get("rngEncoding") or "exact"
    options = Options.model_validate(replay["header"]["options"])
    result = engine.start(options)
    yield 0, None, result
    for n, entry in enumerate(replay["actions"], start=1):
        if entry["seq"] != n - 1:
            raise ReplayMismatch(f"action {n - 1} is missing or out of order (found seq {entry['seq']})")
        state = result.state
        if encoding == "double":
            state = state.model_copy()
            state.rng_state = js_number(state.rng_state)
        result = engine.apply(state, entry["action"])
        yield n, entry, result


def verify(replay: dict[str, Any]) -> engine.StepResult:
    """Replay the whole game and check it against the archive: the events of every action and the end of the game."""
    last: engine.StepResult | None = None
    for n, entry, result in steps(replay):
        if entry is not None and entry.get("events") is not None and entry["events"] != result.events:
            raise ReplayMismatch(f"the events of action {n - 1} differ from the archive")
        last = result
    assert last is not None
    recorded = replay.get("result")
    if recorded is not None and recorded["result"]["reason"] == "completed" and last.state.phase != "finished":
        raise ReplayMismatch("the archive says the game was completed, the replay is not finished")
    return last
