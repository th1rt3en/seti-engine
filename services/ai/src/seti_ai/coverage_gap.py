"""How much does the candidate set of the search miss? (docs/AI-MCTS.md, the coverage question)

The tree search of a turn chooses among the bundles that its root has: one greedy bundle, a few sampled ones and the neighbours of the best two (about 30
in all). If the best turn is not among them, no amount of simulations finds it. This tool measures that, on positions from games of the heuristic bot:

1. the SMALL set is made as the search makes it (`--branch`, `--keep`, `--neighbours`), in one world (the hidden cards drawn once);
2. the BIG set is made in the same world with a far larger effort: many sampled bundles (two temperatures), then several rounds of every neighbour of the
   best ones (a free action added, taken out or moved), so a bundle that needs a long chain of free actions in a specific order has a chance to be built;
3. both are scored by the same brain (points gained in the bundle + the value after it), so the gap is `best of big - best of small`, in points, relative to
   that brain. A gap that only comes from the noise of the value head (the maximum of many noisy numbers is high) is not a real one: with `--truth K` the
   best bundle of each set is played on by the heuristic bot (both seats) to the end of the game K times with the same seeds, and the real difference in
   final score is reported too.

    python -m seti_ai.coverage_gap --model models_beta/v002/model.pt --positions 24 --truth 3
    python -m seti_ai.coverage_gap --brain heuristic --positions 24

It writes nothing but its report (printed, and `--out` as JSON). It trains nothing.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from seti_engine import engine
from seti_engine.models import GameState, Options
from seti_engine.projection import to_act

from . import bots, views
from .bundle_search import BundleSearch, Candidate, History, SearchConfig, _points, answer, determinize, drive, play_bundle_g
from .bundles import bundle_key
from .knowledge import Knowledge


@dataclass
class Position:
    state: GameState
    seat: int
    history: History
    knowledge: Knowledge
    turn: int  # which turn start of the game this is (1 is the first)


def positions_from_games(games: int, seed: int, per_game: int, skip: int) -> list[Position]:
    """Turn starts of the games of the heuristic bot against itself: `per_game` of them in each game, spread over the game, none of the first `skip`."""
    out: list[Position] = []
    for g in range(games):
        sd = seed * 1000 + g
        rng = random.Random(sd)
        players = [bots.heuristic(), bots.heuristic()]
        r = engine.start(Options(players=2, seed=sd))
        history: History = []
        know = Knowledge()
        for p in players:
            p.history = history  # type: ignore[attr-defined]
            p.knowledge = know  # type: ignore[attr-defined]
        starts: list[Position] = []
        last: dict[int, Any] = {}
        steps = 0
        while r.legal and steps < 3000:
            seat = to_act(r.state)
            assert seat is not None
            view = views.project(r.state, seat, previews=False)
            key = bundle_key(r.state, seat)
            if last.get(seat) != key and "main" in view.classes:
                last[seat] = key
                starts.append(Position(r.state, seat, list(history), _copy_know(know), len(starts) + 1))
            i = players[seat].act(r.state, view, rng)
            move = dict(view.legal[i])
            r = engine.apply(r.state, view.legal[i])
            know.update(seat, move, r.events)
            for e in r.events:
                if e.get("type") == "take_display_card" and e.get("player") == seat:
                    move["display_card"] = e["card"]
            history.append((seat, move))
            steps += 1
        usable = starts[skip:]
        if usable:
            step = max(1, len(usable) // per_game)
            out += usable[::step][:per_game]
    return out


def _copy_know(k: Knowledge) -> Knowledge:
    import copy

    return copy.deepcopy(k)


class Maker:
    """Makes and scores bundles in one world, many at a time (the network is called for batches)."""

    def __init__(self, brain: Any, cfg: SearchConfig) -> None:
        self.brain = brain
        self.cfg = cfg
        self.irreversible = getattr(brain, "irreversible", None)

    def run(
        self, world: GameState, pos: Position, jobs: list[dict[str, Any]], rng: random.Random
    ) -> list[tuple[Candidate, GameState] | None]:
        """Each job is `{plan, greedy, temperature, origin}`; the bundle is played on the world and valued. None: a plan that does not fit."""
        procs = [
            play_bundle_g(
                world,
                pos.seat,
                pos.history,
                pos.knowledge,
                random.Random(rng.getrandbits(62)),
                plan=j.get("plan"),
                greedy=j.get("greedy", False),
                temperature=j.get("temperature", 1.0),
                max_micro=self.cfg.max_micro,
                irreversible=self.irreversible,
            )
            for j in jobs
        ]
        rolls = drive(procs, self.brain) if procs else []
        keep = [(j, r) for j, r in zip(jobs, rolls, strict=True) if r.moves and (j.get("plan") is None or r.followed)]
        asks = [("value", r.end, pos.seat, r.history, r.knowledge) for _, r in keep if r.end.phase != "finished"]
        vals = iter(answer(self.brain, asks) if asks else [])
        out: list[tuple[Candidate, GameState] | None] = []
        for j, r in keep:
            v = 0.0 if r.end.phase == "finished" else float(next(vals))
            out.append((Candidate(r.moves, _points(r.end, world, pos.seat), v, j.get("origin", "")), r.end))
        return out


def small_set(maker: Maker, world: GameState, pos: Position, a: argparse.Namespace, rng: random.Random) -> dict[str, tuple[Candidate, GameState]]:
    """The root of the search as the tree search makes it: a greedy bundle, `branch - 1` sampled ones, the neighbours of the best `keep`."""
    found: dict[str, tuple[Candidate, GameState]] = {}

    def add(items: list[tuple[Candidate, GameState] | None]) -> None:
        for it in items:
            if it is not None and (it[0].key not in found or found[it[0].key][0].score < it[0].score):
                found[it[0].key] = it

    add(maker.run(world, pos, [{"greedy": True, "origin": "greedy"}] + [{"temperature": 1.0, "origin": "sample"}] * (a.branch - 1), rng))
    edit = BundleSearch(maker.brain, maker.cfg)._edits
    for base in sorted(found.values(), key=lambda t: -t[0].score)[: a.keep]:
        edits = edit(world, pos.seat, base[0].moves)
        rng.shuffle(edits)
        add(maker.run(world, pos, [{"plan": m, "greedy": True, "origin": o} for o, m in edits[: a.neighbours]], rng))
    return found


def big_set(
    maker: Maker, world: GameState, pos: Position, a: argparse.Namespace, rng: random.Random, start: dict[str, tuple[Candidate, GameState]]
) -> dict[str, tuple[Candidate, GameState]]:
    """A far larger set in the same world: the small set, many more samples, then rounds of all the neighbours of the best ones."""
    found = dict(start)

    def add(items: list[tuple[Candidate, GameState] | None]) -> int:
        new = 0
        for it in items:
            if it is None:
                continue
            if it[0].key not in found:
                new += 1
            if it[0].key not in found or found[it[0].key][0].score < it[0].score:
                found[it[0].key] = it
        return new

    half = a.samples // 2
    add(maker.run(world, pos, [{"temperature": 1.0, "origin": "sample"}] * half + [{"temperature": 2.0, "origin": "hot"}] * (a.samples - half), rng))
    edit = BundleSearch(maker.brain, maker.cfg)._edits
    tried: set[str] = set()
    for _ in range(a.rounds):
        bases = [t for t in sorted(found.values(), key=lambda t: -t[0].score) if t[0].key not in tried][: a.beam]
        if not bases:
            break
        jobs: list[dict[str, Any]] = []
        for base in bases:
            tried.add(base[0].key)
            edits = edit(world, pos.seat, base[0].moves)
            rng.shuffle(edits)
            jobs += [{"plan": m, "greedy": True, "origin": o} for o, m in edits[: a.edit_cap]]
        if add(maker.run(world, pos, jobs, rng)) == 0:
            break
    return found


def rollout(state: GameState, seat: int, seed: int) -> float | None:
    """Play on from `state` with the heuristic bot in every seat; the final total of `seat` minus the best of the others (None: not finished)."""
    rng = random.Random(seed)
    players = [bots.heuristic() for _ in state.players]
    history: History = []
    know = Knowledge()
    for p in players:
        p.history = history  # type: ignore[attr-defined]
        p.knowledge = know  # type: ignore[attr-defined]
    r_state = state
    steps = 0
    while r_state.phase != "finished" and steps < 3000:
        who = to_act(r_state)
        if who is None:
            break
        view = views.project(r_state, who, previews=False)
        i = players[who].act(r_state, view, rng)
        move = dict(view.legal[i])
        res = engine.apply(r_state, view.legal[i])
        know.update(who, move, res.events)
        history.append((who, move))
        r_state = res.state
        steps += 1
    if r_state.phase != "finished":
        return None
    rows = {row["player"]: row["total"] for row in r_state.final_scores}
    mine = float(rows.get(seat, r_state.players[seat].score))
    others = [float(rows.get(p.index, p.score)) for p in r_state.players if p.index != seat]
    return mine - max(others)


def load_brain(a: argparse.Namespace) -> Any:
    if a.brain == "heuristic":
        from .brains import HeuristicBrain

        return HeuristicBrain()
    from .agent import LocalNet, net_from
    from .brains import NetBrain

    net = net_from(a.model)
    net.eval()
    views.set_irreversible(net.cfg.irreversible)
    return NetBrain(LocalNet(net))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brain", choices=["net", "heuristic"], default="net")
    ap.add_argument("--model", default="models_beta/v002/model.pt")
    ap.add_argument("--games", type=int, default=6, help="games of the heuristic bot that the positions are taken from")
    ap.add_argument("--per-game", type=int, default=4)
    ap.add_argument("--positions", type=int, default=24, help="at most this many positions")
    ap.add_argument("--skip", type=int, default=2, help="turn starts at the beginning of a game that are not used")
    ap.add_argument("--branch", type=int, default=6)
    ap.add_argument("--keep", type=int, default=2)
    ap.add_argument("--neighbours", type=int, default=12)
    ap.add_argument("--samples", type=int, default=240, help="sampled bundles of the big set")
    ap.add_argument("--rounds", type=int, default=4, help="rounds of neighbours of the big set")
    ap.add_argument("--beam", type=int, default=10, help="bundles that get all their neighbours in a round")
    ap.add_argument("--edit-cap", type=int, default=80, help="at most this many neighbours of one bundle in a round")
    ap.add_argument("--truth", type=int, default=0, help="rollouts with the heuristic bot of the best bundle of each set (0: none)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    brain = load_brain(a)
    cfg = SearchConfig(max_micro=80)
    maker = Maker(brain, cfg)
    t0 = time.time()
    pos_list = positions_from_games(a.games, a.seed, a.per_game, a.skip)[: a.positions]
    print(f"{len(pos_list)} positions from {a.games} games of the heuristic bot ({time.time() - t0:.0f}s); brain: {a.brain}", flush=True)
    rows: list[dict[str, Any]] = []
    for n, pos in enumerate(pos_list, start=1):
        rng = random.Random(a.seed * 10_000 + n)
        world = determinize(pos.state, pos.seat, pos.knowledge, rng)
        t1 = time.time()
        small = small_set(maker, world, pos, a, rng)
        big = big_set(maker, world, pos, a, rng, small)
        if not small or not big:
            continue
        sb = max(small.values(), key=lambda t: t[0].score)
        bb = max(big.values(), key=lambda t: t[0].score)
        ranked = sorted(big.values(), key=lambda t: -t[0].score)
        rank_of_small = 1 + sum(1 for t in ranked if t[0].score > sb[0].score + 1e-9)
        row: dict[str, Any] = {
            "turn": pos.turn,
            "small_n": len(small),
            "big_n": len(big),
            "small_best": round(sb[0].score, 2),
            "big_best": round(bb[0].score, 2),
            "gap": round(bb[0].score - sb[0].score, 2),
            "big_best_in_small": bb[0].key in small,
            "big_best_len": len(bb[0].moves),
            "small_best_len": len(sb[0].moves),
            "big_best_origin": bb[0].origin,
            "rank_of_small_best_in_big": rank_of_small,
        }
        if a.truth > 0 and bb[0].key != sb[0].key:
            diffs = []
            for k in range(a.truth):
                seed = a.seed * 777 + n * 31 + k
                x, y = rollout(bb[1], pos.seat, seed), rollout(sb[1], pos.seat, seed)
                if x is not None and y is not None:
                    diffs.append(x - y)
            if diffs:
                row["truth_big_minus_small"] = round(statistics.fmean(diffs), 2)
        rows.append(row)
        print(
            f"  {n}/{len(pos_list)} turn {pos.turn}: small {row['small_n']} bundles best {row['small_best']}, "
            f"big {row['big_n']} bundles best {row['big_best']} "
            f"(gap {row['gap']}, in small: {row['big_best_in_small']}, length {row['small_best_len']} -> {row['big_best_len']}"
            f"{', truth ' + str(row['truth_big_minus_small']) if 'truth_big_minus_small' in row else ''}) ({time.time() - t1:.0f}s)",
            flush=True,
        )
    if not rows:
        print("no positions")
        return
    gaps = np.array([r["gap"] for r in rows])
    print("\nsummary", flush=True)
    print(
        f"  positions {len(rows)}; bundles in the small set {np.mean([r['small_n'] for r in rows]):.0f}, "
        f"in the big set {np.mean([r['big_n'] for r in rows]):.0f}"
    )
    print(f"  gap (big best - small best), points on the brain's scale: mean {gaps.mean():.2f}, median {np.median(gaps):.2f}, max {gaps.max():.2f}")
    for t in (0.5, 1, 3, 5):
        print(f"  positions where the gap is more than {t}: {np.mean(gaps > t):.0%}")
    print(f"  the best bundle of the big set is in the small set: {np.mean([r['big_best_in_small'] for r in rows]):.0%}")
    print(
        f"  length of the best bundle: small {np.mean([r['small_best_len'] for r in rows]):.1f}, "
        f"big {np.mean([r['big_best_len'] for r in rows]):.1f} moves; "
        f"the longest big best: {max(r['big_best_len'] for r in rows)}"
    )
    print(f"  rank of the small best in the big set: median {np.median([r['rank_of_small_best_in_big'] for r in rows]):.0f}")
    real = [r["truth_big_minus_small"] for r in rows if "truth_big_minus_small" in r]
    if real:
        print(
            f"  real outcome (heuristic bot plays on, {a.truth} rollouts, same seeds), big best minus small best, final score difference: "
            f"mean {np.mean(real):.2f} over {len(real)} positions"
        )
    if a.out:
        Path(a.out).write_text(json.dumps({"args": vars(a), "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
