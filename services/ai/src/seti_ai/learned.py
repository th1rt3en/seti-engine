"""Heuristic bot version 4: a one-step lookahead bot whose value function is learned from the final scores of its own games instead of being written by hand.

    .venv/Scripts/python.exe -m seti_ai.learned --iterations 12 --games 200 --out tuned

The value of a position for a seat is a linear function of counts taken from the position (score, resources, structures, techs ...), one set of weights for each
round of the game, fitted by ridge regression to the seat's final score (the mean over the positions of the games played). The bot plays one step ahead with it
(it tries every legal move and takes the one whose position has the highest value), like the earlier heuristic bots. Each iteration plays games with the
current bot (a few random moves for variety), fits the next value function to what those games scored, and the bot that uses it plays the next games
(policy iteration: the value of the positions under the bot's own play, then the bot that picks the best of them). No neural network and no search.
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
from numpy.typing import NDArray
from seti_engine import engine
from seti_engine.models import GameState
from seti_engine.projection import View

from . import arena, bots
from .bots import TURN_ENDERS, LookaheadBot, _options, _sectors_led

OPTIONS = [{}, {"expansion": True, "organizations": True}]
ORGS = [
    "orbital_dynamics", "fenwick_research_center", "stratus_core", "deep_sky_survey", "turing_systems", "cosmos_strategy_group", "futurespan_institute",
    "helion_assembly", "xenolab", "mission_relay", "dlr",
]  # fmt: skip  # noqa: E501
CATS = ("probe", "telescope", "computer")
BASE = [
    "score", "credits", "energy", "data", "publicity", "movement", "hand", "tucked", "computer", "probes", "launched", "techs", "orbiters", "landers", "missions",  # noqa: E501
    "completed", "end_cards", "traces", "wins", "markers", "led", "tokens", "passed", "main_done", *CATS, "credits2", "energy2", "data2", "hand2", "score_x_hand",  # noqa: E501
]  # fmt: skip
N_ROUNDS = 5
DIM = len(BASE) * N_ROUNDS + len(ORGS) + 2  # the hand-set value of heuristic v3 and the constant are the last two


def features(state: GameState, seat: int) -> NDArray[np.float64]:
    """The numbers that describe a position for a seat; the base ones are repeated for each round (only the block of the current round is filled)."""
    p = state.players[seat]
    markers = sum(sec.markers.count(seat) for sec in state.sectors)
    in_play = sum(1 for pr in state.probes if pr.player == seat and not pr.capsule)
    cats = [sum(1 for t in p.techs if t.startswith(c + "-")) for c in CATS]
    v = [
        p.score, p.credits, p.energy, p.data_pool, p.publicity, p.movement, len(p.hand), len(p.tucked), sum(p.computer), in_play, p.probes_launched,
        len(p.techs), sum(p.orbiters.values()), sum(p.landers.values()), len(p.missions), len(p.completed_missions), len(p.end_cards), len(p.trace_log),
        p.sector_wins, markers, _sectors_led(state, seat), p.signal_tokens, float(p.passed), float(state.main_done and state.current_player == seat),
        *cats, p.credits**2 / 10, p.energy**2 / 10, p.data_pool**2 / 10, len(p.hand) ** 2 / 10, p.score * len(p.hand) / 50,
    ]  # fmt: skip
    out = np.zeros(DIM)
    r = max(1, min(state.round, N_ROUNDS)) - 1
    out[r * len(BASE) : (r + 1) * len(BASE)] = v
    if p.organization in ORGS:
        out[N_ROUNDS * len(BASE) + ORGS.index(p.organization)] = 1.0
    out[-2] = bots._board_value(state, p, bots.HEURISTIC)  # the starting point: heuristic v3's own value; the other columns learn what it misses
    out[-1] = 1.0
    return out


class LearnedBot(LookaheadBot):
    """A one-step lookahead bot with a learned value function (`w`: the weights of `features`)."""

    def __init__(self, w: NDArray[np.float64], name: str = "learned", noise: float = 0.05) -> None:
        super().__init__(name, bots.HEURISTIC, noise=noise)
        self.w = w

    def _value(self, state: GameState, p: Any) -> float:
        return float(features(state, p.index) @ self.w)

    def _gain(self, state: GameState, seat: int, m: dict[str, Any], base: float, nxt: GameState, rng: random.Random) -> float:
        gain = float(features(nxt, seat) @ self.w) - base
        if m["type"] in TURN_ENDERS:
            gain -= 0.05  # only a tie-break: the value function knows what a turn is worth
        return gain

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        base = float(features(state, seat) @ self.w)
        best, best_value = 0, -1e9
        for i in _options(view):
            m = view.legal[i]
            try:
                nxt = engine.apply(state, m).state
            except Exception:
                continue
            value = self._gain(state, seat, m, base, nxt, rng) + self.noise * rng.random()
            if value > best_value:
                best, best_value = i, value
        return best


class Recorder:
    """Plays like `bot` (with a random move now and then, `eps`) and keeps the features of each position it decides in."""

    def __init__(self, bot: Any, eps: float, seat_rows: dict[int, list[NDArray[np.float64]]]) -> None:
        self.bot, self.eps, self.rows, self.name = bot, eps, seat_rows, bot.name
        self.history: Any = None
        self.knowledge: Any = None

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        self.rows.setdefault(seat, []).append(features(state, seat))
        if rng.random() < self.eps:
            return rng.choice(_options(view))
        return int(self.bot.act(state, view, rng))


def _make(kind: str, w: list[float] | None) -> Any:
    return bots.heuristic() if kind == "v3" else LearnedBot(np.array(w))


def _collect(job: tuple[str, list[float] | None, int, int, float]) -> tuple[NDArray[np.float64], NDArray[np.float64], list[int]]:
    kind, w, seed, opt, eps = job
    rows: dict[int, list[NDArray[np.float64]]] = {}
    players = [Recorder(_make(kind, w), eps, rows), Recorder(_make(kind, w), eps, rows)]
    res = arena.play_game(players, seed, random.Random(seed), OPTIONS[opt])
    xs, ys = [], []
    for seat, r in rows.items():
        xs += r
        ys += [res.scores[seat]] * len(r)
    return np.array(xs), np.array(ys, dtype=float), res.scores


def _eval(job: tuple[str, list[float] | None, int, int, int]) -> float:
    kind, w, seed, opt, seat = job
    a, b = _make(kind, w), bots.heuristic()
    res = arena.play_game([a, b] if seat == 0 else [b, a], seed, random.Random(seed), OPTIONS[opt])
    return float(res.scores[seat])


def fit(x: NDArray[np.float64], y: NDArray[np.float64], ridge: float = 3.0) -> NDArray[np.float64]:
    """Ridge regression of the final score on the features (standardised, so that one ridge fits all the columns)."""
    mu = x.mean(0)
    sd = x.std(0)
    sd[sd < 1e-9] = 1.0
    z = (x - mu) / sd
    z[:, -1] = 1.0
    n = len(y)
    pen = np.full(z.shape[1], ridge / n)
    pen[-2:] = 0.0  # the value of v3 and the constant are not pulled toward zero
    a = z.T @ z / n + np.diag(pen)
    b = z.T @ y / n
    coef = np.linalg.solve(a, b)
    w = coef / sd
    w[-1] = float(coef[-1] - np.sum(coef[:-1] * mu[:-1] / sd[:-1]))
    return w


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iterations", type=int, default=12)
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--eval-games", type=int, default=40)
    ap.add_argument("--eps", type=float, default=0.05)
    ap.add_argument("--keep", type=int, default=2, help="the games of this many iterations are used for the fit")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--out", default="tuned")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []
    w: list[float] | None = None
    kind = "v3"
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for it in range(0, a.iterations + 1):
            t0 = time.time()
            jobs = [(kind, w, 3_000_000 + it * 10_000 + k, k % 2, a.eps) for k in range(a.games)]
            res = pool.map(_collect, jobs, chunksize=1)
            data.append((np.concatenate([r[0] for r in res]), np.concatenate([r[1] for r in res])))
            data = data[-a.keep :]
            scores = [s for r in res for s in r[2]]
            x = np.concatenate([d[0] for d in data])
            y = np.concatenate([d[1] for d in data])
            wn = fit(x, y)
            kind, w = "learned", wn.tolist()
            fitted = float(np.sqrt(np.mean((x @ wn - y) ** 2)))
            ev = pool.map(_eval, [("learned", w, 800_000 + k // 2, (k // 2) % 2, k % 2) for k in range(a.eval_games * 2)], chunksize=1)
            base_ev = ev
            print(
                f"iteration {it}: games scored {np.mean(scores):.1f} on average ({len(y)} positions, fit error {fitted:.1f}); the new bot scores "
                f"{np.mean(base_ev):.1f} against heuristic v3 ({time.time() - t0:.0f}s)",
                flush=True,
            )
            (out / "learned.json").write_text(json.dumps({"w": w, "iteration": it, "eval": float(np.mean(base_ev))}), encoding="utf-8")


if __name__ == "__main__":
    main()
