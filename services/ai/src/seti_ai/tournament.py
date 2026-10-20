"""Matches between bots on all the CPU cores, to measure them and to tune the heuristic bot. No network and no learning here: bots only.

    .venv/Scripts/python.exe -m seti_ai.tournament heuristic greedy --games 60

A bot is a name of `bots.BOTS`, or a JSON object that describes a `LookaheadBot` (weights, round multipliers, tech values ...), so that variants can be tried
without writing code. The games are played on the same seeds with the seats swapped.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import random
import statistics
from typing import Any

from . import arena, bots


def make(spec: str) -> Any:
    if spec in bots.BOTS:
        return bots.BOTS[spec]()
    return bots.from_spec(json.loads(spec))


def _game(job: tuple[str, str, int, int]) -> tuple[int, int, int, bool]:
    a_spec, b_spec, seed, seat = job
    a, b = make(a_spec), make(b_spec)
    players = [a, b] if seat == 0 else [b, a]
    res = arena.play_game(players, seed, random.Random(seed * 7 + seat))
    mine, theirs = (res.scores[seat], res.scores[1 - seat])
    return mine, theirs, res.steps, res.finished


def match(pool: Any, a: str, b: str, games: int, first_seed: int = 70_000) -> dict[str, float]:
    jobs = [(a, b, first_seed + k // 2, k % 2) for k in range(games)]
    res = pool.map(_game, jobs, chunksize=1)
    wins = sum(1.0 if m > t else 0.5 if m == t else 0.0 for m, t, _, _ in res)
    return {
        "games": games,
        "a_score": round(statistics.fmean(m for m, _, _, _ in res), 1),
        "b_score": round(statistics.fmean(t for _, t, _, _ in res), 1),
        "a_win_rate": round(wins / games, 3),
        "unfinished": sum(1 for *_, f in res if not f),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--seed", type=int, default=70_000)
    a = ap.parse_args()
    with mp.get_context("spawn").Pool(a.workers) as pool:
        print(json.dumps(match(pool, a.a, a.b, a.games, a.seed)))


if __name__ == "__main__":
    main()
