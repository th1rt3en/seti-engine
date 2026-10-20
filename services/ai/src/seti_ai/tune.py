"""Tuning of the heuristic bot by evolution (no neural network, no learning of the agent): the weights and the biases of the bot are changed at random, the
variants play games against the current heuristic bot, and the settings move toward those that score more.

    .venv/Scripts/python.exe -m seti_ai.tune --generations 40 --out tuned

The objective is the variant's own mean final score, over base-game and expansion games (organizations and quick start cards), on the same games for every
variant of a generation. The bot stays a one-step lookahead bot whose value function has more terms; the numbers it uses are what is tuned.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import arena, bots

TYPES = [
    "scan", "analyze", "launch", "orbit", "land", "research", "play_card", "discard_free", "tuck", "buy_card", "take_card", "place_data",
    "place_computer_tech", "complete_mission", "place_trace", "move_probe", "move_energy", "exchange", "end_turn", "pass",
]  # fmt: skip
ORGS = [
    "orbital_dynamics", "fenwick_research_center", "stratus_core", "deep_sky_survey", "turing_systems", "cosmos_strategy_group", "futurespan_institute",
    "helion_assembly", "xenolab", "mission_relay", "dlr",
]  # fmt: skip
START_BIAS = {"play_card": 1.0, "complete_mission": 1.0}


class Space:
    """The numbers that are tuned, with their starting value and the size of a step."""

    def __init__(self, start_weights: dict[str, float]) -> None:
        self.names: list[str] = []
        self.start: list[float] = []
        self.sigma: list[float] = []
        for k, v in start_weights.items():
            self.add(f"w:{k}", v, 0.25 * max(abs(v), 0.6))
        for k in ("lead", "token"):
            self.add(f"w:{k}", start_weights.get(k, 0.0), 0.5)
        for t in TYPES:
            self.add(f"b:{t}", START_BIAS.get(t, 0.0), 1.0)
        self.add("use_the_turn", 0.0, 3.0)
        for o in ORGS:
            self.add(f"o:{o}", 0.0, 1.0)
        for q in range(1, 22):
            self.add(f"q:SR.{q}", 0.0, 0.5)

    def add(self, name: str, start: float, sigma: float) -> None:
        self.names.append(name)
        self.start.append(start)
        self.sigma.append(sigma)

    def spec(self, x: np.ndarray, name: str = "tuned") -> dict[str, Any]:
        d = dict(zip(self.names, map(float, x), strict=True))
        return {
            "name": name,
            "base": "heuristic_v1",
            "weights": {k[2:]: v for k, v in d.items() if k.startswith("w:")},
            "bias": {k[2:]: v for k, v in d.items() if k.startswith("b:") and abs(v) > 1e-9},
            "use_the_turn": d["use_the_turn"],
            "org_bias": {k[2:]: v for k, v in d.items() if k.startswith("o:")},
            "quick_bias": {k[2:]: v for k, v in d.items() if k.startswith("q:")},
            "no_scan_r1": True,
            "noise": 0.05,
        }


OPTIONS = [{}, {"expansion": True, "organizations": True}]


def _game(job: tuple[str, str, int, int, int]) -> float:
    spec_json, opp, seed, seat, kind = job
    me = bots.from_spec(json.loads(spec_json)) if spec_json.startswith("{") else bots.BOTS[spec_json]()
    other = bots.BOTS[opp]()
    players = [me, other] if seat == 0 else [other, me]
    res = arena.play_game(players, seed, random.Random(seed * 3 + seat), OPTIONS[kind])
    return float(res.scores[seat]) if res.finished else float(res.scores[seat]) - 20.0


def score_of(pool: Any, spec: dict[str, Any] | str, opp: str, seeds: list[int], kinds: tuple[int, ...] = (0, 1)) -> dict[str, float]:
    """The mean own score of a bot over the games (seats swapped; base and expansion): in all, and for each kind."""
    sj = spec if isinstance(spec, str) else json.dumps(spec)
    jobs = [(sj, opp, seed, k % 2, kind) for kind in kinds for k, seed in enumerate(seeds)]
    res = pool.map(_game, jobs, chunksize=1)
    out: dict[str, float] = {"all": float(np.mean(res))}
    for i, kind in enumerate(kinds):
        part = res[i * len(seeds) : (i + 1) * len(seeds)]
        out["expansion" if kind == 1 else "base"] = float(np.mean(part))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generations", type=int, default=40)
    ap.add_argument("--population", type=int, default=16, help="variants of a generation (half of them are mirror images of the others)")
    ap.add_argument("--games", type=int, default=12, help="games of each kind (base, expansion) for each variant")
    ap.add_argument("--opponent", default="heuristic")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--lr", type=float, default=0.35)
    ap.add_argument("--out", default="tuned")
    ap.add_argument("--resume", default=None, help="a saved vector (json) to start from")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    space = Space(bots.HEURISTIC)
    sig = np.array(space.sigma)
    mu = np.array(space.start)
    if a.resume:
        mu = np.array(json.loads(Path(a.resume).read_text(encoding="utf-8"))["x"])
    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with mp.get_context("spawn").Pool(a.workers) as pool:
        base = score_of(pool, "heuristic", a.opponent, list(range(900_000, 900_000 + 30)))
        print(f"the start (heuristic bot version 3) against {a.opponent}: {base}", flush=True)
        for g in range(1, a.generations + 1):
            t0 = time.time()
            half = a.population // 2
            eps = rng.standard_normal((half, len(mu)))
            eps = np.concatenate([eps, -eps])
            seeds = [1_000_000 + g * 1000 + k for k in range(a.games)]
            fit = np.array([score_of(pool, space.spec(mu + e * sig * 0.6), a.opponent, seeds)["all"] for e in eps])
            ranks = fit.argsort().argsort() / (len(fit) - 1) - 0.5  # centred ranks: -0.5 .. 0.5
            step = (ranks[:, None] * eps).sum(axis=0) / (len(fit) * 0.6) * sig * a.lr * 2
            mu = mu + step
            if g % 4 == 0 or g == a.generations:
                check = score_of(pool, space.spec(mu), a.opponent, list(range(900_000, 900_000 + 30)))
                print(
                    f"generation {g}: the variants scored {fit.mean():.1f} on average, the best {fit.max():.1f}; "
                    f"the mean setting scores {check} ({time.time() - t0:.0f}s)",
                    flush=True,
                )
                (out / "best.json").write_text(
                    json.dumps({"x": mu.tolist(), "names": space.names, "spec": space.spec(mu), "check": check}, indent=1), encoding="utf-8"
                )
            else:
                print(f"generation {g}: the variants scored {fit.mean():.1f} on average, the best {fit.max():.1f} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
