"""The games of people, from the archive, as training examples (docs/AI-TURN-BUNDLES.md section 11).

Every game that was started is archived (decision D25): a `replay.json` per game, or the folder of a game (`header.json`, `actions/*.json`,
`result.json`). Download the bucket first, for example `gcloud storage rsync -r gs://BUCKET/seti-engine/games ./archive`; this module reads files from
a folder, it never talks to the bucket.

What counts:
- the game was played to its end (a game that was resigned or timed out has no final scores to learn the value from);
- when a seat was the model's (`bot` in the header), the host agreed that the game is collected (`consent`); a game with a model and no consent is
  never used;
- a game that the model lost counts with more weight for the moves of the people, a game that the model won or tied is skipped (`game_weights`); a
  game without the model counts once (people against each other are good examples too).
A game that the engine cannot replay any more (the rules changed since it was played) is skipped and counted, not guessed at.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seti_engine.models import Options

from .bundle_data import Examples, examples_from_log, game_weights


@dataclass
class ArchivedGame:
    id: str
    options: Options
    actions: list[dict[str, Any]]
    rng_encoding: str
    model_seats: set[int]
    scores: list[int]  # the final total of each seat
    consent: bool
    completed: bool
    models: dict[int, str] = field(default_factory=dict)


def load_file(path: Path) -> dict[str, Any]:
    """A replay file, or a folder of a game, as the replay-file dictionary."""
    if path.is_file():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    actions = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((path / "actions").glob("*.json"))]
    result = path / "result.json"
    return {
        "header": json.loads((path / "header.json").read_text(encoding="utf-8")),
        "actions": actions,
        "result": json.loads(result.read_text(encoding="utf-8")) if result.exists() else None,
    }


def game_paths(root: Path) -> Iterator[Path]:
    """Every game under a folder: a `replay.json`, or a folder that has a `header.json` and no `replay.json`."""
    seen: set[Path] = set()
    for p in sorted(root.rglob("replay.json")):
        seen.add(p.parent)
        yield p
    for p in sorted(root.rglob("header.json")):
        if p.parent not in seen:
            yield p.parent


def parse(file: dict[str, Any]) -> ArchivedGame:
    header = file["header"]
    result = file.get("result")
    ranking = result["result"]["ranking"] if result else []
    scores = [0] * int(header["options"].get("players", len(header["seats"])))
    for r in ranking:
        if 0 <= r["seat"] < len(scores):
            scores[r["seat"]] = int(r["score"])
    seats = header.get("seats", [])
    return ArchivedGame(
        id=str(header.get("id", "")),
        options=Options(**header["options"]),
        actions=[e["action"] for e in file["actions"]],
        rng_encoding=header.get("rngEncoding", "double"),
        model_seats={s["seat"] for s in seats if s.get("bot")},
        scores=scores,
        consent=bool(header.get("consent")),
        completed=bool(result and result.get("status") == "finished" and result["result"].get("reason") == "completed"),
        models={s["seat"]: s["bot"]["model"] for s in seats if s.get("bot")},
    )


@dataclass
class Stats:
    games: int = 0
    used: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, why: str) -> None:
        self.skipped[why] = self.skipped.get(why, 0) + 1

    def __str__(self) -> str:
        why = ", ".join(f"{n} {k}" for k, n in sorted(self.skipped.items()))
        return f"{self.games} games, {self.used} used" + (f" (skipped: {why})" if why else "")


def examples_of(game: ArchivedGame, lost_weight: float = 3.0, memory: bool = True) -> Examples | str:
    """The examples of one game, or the reason it is not used."""
    if not game.completed:
        return "not played to the end"
    if game.model_seats and not game.consent:
        return "an AI without the host's agreement"
    policy, value = game_weights(game.scores, game.model_seats, lost_weight)
    if not any(policy.values()) and not any(value.values()):
        return "the model won or tied"
    try:
        return examples_from_log(
            game.options,
            game.actions,
            game.rng_encoding,
            policy_weight=lambda s: policy.get(s, 0.0),
            value_weight=lambda s: value.get(s, 0.0),
            memory=memory,
        )
    except Exception:  # the rules changed since the game was played, or the log is damaged: skipped, not guessed at
        return "cannot be replayed"


def load_examples(root: Path, lost_weight: float = 3.0, memory: bool = True) -> tuple[Examples, Stats]:
    """All the usable games under `root`, and what became of the others."""
    out, stats = Examples(), Stats()
    for path in game_paths(root):
        stats.games += 1
        try:
            game = parse(load_file(path))
        except Exception:
            stats.skip("unreadable")
            continue
        got = examples_of(game, lost_weight, memory)
        if isinstance(got, str):
            stats.skip(got)
            continue
        out.extend(got)
        out.finished = True
        stats.used += 1
    return out, stats


def mix(bots_data: Examples, people: Examples, share: float, max_repeat: int = 20, seed: int = 0) -> Examples:
    """The data of an epoch: the games of bots, and the games of people making about `share` of the choices and of the value positions.

    There are few games of people, so they are repeated (each at most `max_repeat` times) until they make the share; with less than that they simply
    make a smaller share. `share` 0 gives the games of bots alone."""
    if not 0.0 <= share < 1.0:
        raise ValueError("the share of the games of people is between 0 and 1 (1 excluded)")
    rng = random.Random(seed)

    def pick(a: list[Any], b: list[Any]) -> list[Any]:
        if share == 0.0 or not b:
            return list(a)
        want = int(len(a) * share / (1.0 - share))
        n = min(want, len(b) * max_repeat)
        rep = [b[i % len(b)] for i in range(n)]
        rng.shuffle(rep)
        return [*a, *rep]

    out = Examples()
    out.policy = pick(bots_data.policy, people.policy)
    out.value = pick(bots_data.value, people.value)
    out.bundles = bots_data.bundles + people.bundles
    out.finished = bots_data.finished or people.finished
    return out
