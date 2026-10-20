"""The opponent pool of the training: who the agent plays against, and how often.

An entry is one of
- `self`: the network that is being trained plays both seats;
- `bot`: a bot of `bots.BOTS` (random, greedy, the heuristic bots, later version 4 and 5);
- `snapshot`: a frozen network, for example a past version of the model, or a model that scores about 100 points (v008).
  `memory` says whether it was trained with the
  memory of the moves (a snapshot of an older network was not, and is played without it).

The pool is a file (`models/pool.json`) that the owner can read and change; the share of the games that each entry gets is its `weight`. The games of
a round are given to the entries by a rule that depends only on the round and the position of the game, so a resumed run plays the same games. Past
versions of the model are added to the pool as the training saves them (`remember`), and only the last few are kept, so that the agent keeps meeting
its old selves (against forgetting and cycling).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_ENTRIES: list[dict[str, Any]] = [
    {"name": "self", "kind": "self", "weight": 4},
    {"name": "heuristic_v3", "kind": "bot", "bot": "heuristic", "weight": 2},
    {"name": "greedy", "kind": "bot", "bot": "greedy", "weight": 1},
]
KEEP_PAST = 6  # past versions of the model kept in the pool


def load(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data["entries"])
    return [dict(e) for e in DEFAULT_ENTRIES]


def save(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"entries": entries}, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def share(entries: list[dict[str, Any]], games: int) -> list[dict[str, Any]]:
    """The entry for each of `games` games: in proportion to the weights, in a fixed order (so that the same round always has the same opponents)."""
    total = sum(float(e["weight"]) for e in entries)
    assert total > 0, "the pool has no weight"
    out: list[dict[str, Any]] = []
    owed = [0.0] * len(entries)
    for _ in range(games):
        for i, e in enumerate(entries):
            owed[i] += float(e["weight"]) / total
        k = max(range(len(entries)), key=lambda i: owed[i])
        owed[k] -= 1.0
        out.append(entries[k])
    return out


def remember(entries: list[dict[str, Any]], version: str, path: str, weight: float = 1.0, memory: bool = True) -> list[dict[str, Any]]:
    """Add a saved version of the model to the pool as a snapshot; only the last `KEEP_PAST` of those that were added this way are kept."""
    out = [e for e in entries if e.get("name") != f"past:{version}"]
    out.append({"name": f"past:{version}", "kind": "snapshot", "path": path, "weight": weight, "memory": memory, "past": True})
    past = [e for e in out if e.get("past")]
    for old in past[:-KEEP_PAST]:
        out.remove(old)
    return out
