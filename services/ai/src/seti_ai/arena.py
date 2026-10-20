"""Games between players, offline: the engine plays them, the players choose among the legal moves.

A player is any object with `act(state, view, rng) -> index` (the bots) or a learning agent (agent.py). `play_game` runs one game to its end and gives
each seat's final total, which is the number the agent learns to raise. A cap on the steps keeps a stuck game from running for ever.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import Any

from seti_engine import engine
from seti_engine.models import GameState, Options
from seti_engine.projection import View, project, to_act

MAX_STEPS = 3000  # a game that is not over after this many decisions is stopped (the learner is penalised)


@dataclass
class GameResult:
    seed: int
    scores: list[int]  # the final total of each seat
    winner: int | None  # None for a tie
    steps: int
    finished: bool
    state: GameState | None = field(default=None, repr=False)


def final_totals(state: GameState) -> list[int]:
    rows = {r["player"]: r["total"] for r in state.final_scores}
    return [int(rows.get(p.index, p.score)) for p in state.players]


def play_game(players: list[Any], seed: int, rng: random.Random | None = None, options: dict[str, Any] | None = None) -> GameResult:
    """`players[seat]` plays that seat. The seat that is to act is asked with its own view of the game."""
    rng = rng or random.Random(seed)
    opts = Options(players=len(players), seed=seed, **(options or {}))
    r = engine.start(opts)
    steps = 0
    history: list[tuple[int, dict[str, Any]]] = []  # the actions of both seats so far: the memory of the agent
    for p in players:
        p.history = history
    while r.legal and steps < MAX_STEPS:
        seat = to_act(r.state)
        assert seat is not None
        view: View = project(r.state, seat, previews=False)
        i = players[seat].act(r.state, view, rng)
        history.append((seat, dict(view.legal[i])))
        r = engine.apply(r.state, view.legal[i])
        steps += 1
    done = r.state.phase == "finished"
    scores = final_totals(r.state) if done else [p.score for p in r.state.players]
    top = max(scores)
    winners = [i for i, s in enumerate(scores) if s == top]
    return GameResult(seed, scores, winners[0] if len(winners) == 1 else None, steps, done)


def match(a: Any, b: Any, games: int, first_seed: int = 10_000, options: dict[str, Any] | None = None) -> dict[str, float]:
    """`a` against `b` over the same seeds with the seats swapped: the mean score of each, the win rate of `a` (a tie is half), the steps."""
    sa: list[int] = []
    sb: list[int] = []
    wins = 0.0
    steps = 0
    for k in range(games):
        seed = first_seed + k // 2
        swap = k % 2 == 1
        res = play_game([b, a] if swap else [a, b], seed, random.Random(seed * 7 + k), options)
        mine, theirs = (res.scores[1], res.scores[0]) if swap else (res.scores[0], res.scores[1])
        sa.append(mine)
        sb.append(theirs)
        wins += 1.0 if mine > theirs else 0.5 if mine == theirs else 0.0
        steps += res.steps
    return {
        "games": games,
        "a_score": statistics.fmean(sa),
        "b_score": statistics.fmean(sb),
        "a_win_rate": wins / games,
        "steps": steps / games,
    }
