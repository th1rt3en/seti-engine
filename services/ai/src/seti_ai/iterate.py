"""The training of version 3 and after (docs/AI-TURN-BUNDLES.md section 13): the model improves from its own search and from the games of people.

python -m seti_ai.iterate run --owner-approved --start models_alpha/v002 --models models_v3 --people archive --iterations 10     # go on: add --resume
python -m seti_ai.iterate pause --models models_v3                                                                          # stop at the end of the iteration

One iteration (nothing in it is imitation of a person):
1. **self-play**: the model plays whole turns found by its own bundle search (`selfplay.py`), against itself and, for a share of the games, against the
   heuristic bot, and the games are cut into examples: the policy toward the bundles that the search chose, the value of every position from the points
   that the seats really gained;
2. **the games of people**: the search runs from the start of turns of people, with the turn that the person played offered as one more candidate
   (`expert.py`); the policy learns from the best bundle found, the person's or another, and the value of every position of the games comes from the points
   that the seats really gained (`dataset.py`);
3. the examples of the last `--buffer` iterations are kept (they are written to the models folder, so a resumed run has them), mixed with the games of people
   by `--people-share`, and the network is trained on them for `--epochs` epochs (`bundle_train.train_epoch`);
4. the network is measured (against the bots, and head to head against the champion with the search, `gate.py`); a candidate that passes the gate is saved
   as a new version for testing: the owner approves a version by hand before anyone can play it. The network goes on training whether or not it was saved.

Everything that is needed to go on is saved at the end of each iteration (`checkpoint.py`): a pause finishes the games in progress, saves nothing of a half
iteration and exits. Training is only ever started by the owner's go: `run` refuses to start without `--owner-approved`.
"""

from __future__ import annotations

import argparse
import json
import pickle
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch

from . import arena, bundle_train, checkpoint, dataset, expert, gate, registry, selfplay
from .agent import PRESETS, LocalNet, PolicyNet, net_from, new_net
from .bundle_data import Examples
from .bundle_search import Brain, BundleBot, BundleSearch, SearchConfig

BrainFactory = Callable[[PolicyNet], Brain]


def net_brain(net: PolicyNet) -> Brain:
    return selfplay.make_brain(LocalNet(net))


@dataclass
class Settings:
    models: Path
    people: Path | None = None
    iterations: int = 10
    selfplay_games: int = 20
    bot_share: float = 0.25  # about this share of the self-play games is against the heuristic bot (0: the model against itself only)
    human_positions: int = 200  # turn starts of people searched in each iteration
    epochs: int = 2
    batch: int = 64
    lr: float = 1e-4
    buffer: int = 4  # iterations of examples that are kept
    people_share: float = 0.3
    people_solo: bool = False
    expert_weight: float = 1.0
    gate_games: int = 4  # games with the search against the champion (0: no gate, nothing is saved)
    eval_games: int = 6  # games against each bot, the network alone
    seed: int = 1
    log_every: float = 60.0
    search: SearchConfig = field(default_factory=SearchConfig)
    explore_temperature: float = 3.0
    explore_rounds: int = 2


@dataclass
class Buffer:
    """The examples of the last iterations, kept in files so that a resumed run has them."""

    root: Path
    keep: int

    def path(self, it: int) -> Path:
        return self.root / "buffer" / f"iteration_{it:04d}.pkl"

    def add(self, it: int, ex: Examples) -> None:
        self.path(it).parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path(it).with_suffix(".tmp")
        with tmp.open("wb") as f:
            pickle.dump(ex, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(self.path(it))
        for old in sorted(self.path(it).parent.glob("iteration_*.pkl"))[: -self.keep]:
            old.unlink()

    def load(self) -> Examples:
        out = Examples()
        for p in sorted((self.root / "buffer").glob("iteration_*.pkl")):
            with p.open("rb") as f:
                out.extend(pickle.load(f))
        return out


def self_play_data(
    net: PolicyNet, it: int, s: Settings, brain: BrainFactory, stop: Callable[[], bool] = lambda: False
) -> tuple[Examples, dict[str, Any]] | None:
    """The games of one iteration: the examples, and how the games went. None if a pause was asked for in the middle (the games are thrown away)."""
    out = Examples()
    scores: list[float] = []
    vs_bot: list[tuple[int, int]] = []
    steps = searches = 0
    started = time.time()
    every = round(1 / s.bot_share) if s.bot_share > 0 else 0
    for k in range(s.selfplay_games):
        if stop():
            return None
        cfg = selfplay.SelfPlayConfig(s.search, s.explore_temperature, s.explore_rounds, "heuristic" if every and k % every == 0 else "")
        g = selfplay.play(brain(net), s.seed * 1_000_003 + it * 1_000 + k, cfg, kind=k % 2)
        out.extend(g.examples)
        steps += g.steps
        searches += g.searches
        scores += [float(g.scores[i]) for i in g.model_seats]
        if cfg.bot:
            seat = g.model_seats[0]
            vs_bot.append((g.scores[seat], g.scores[1 - seat]))
        done = time.time() - started
        print(
            f"    self-play game {k + 1}/{s.selfplay_games}{' against the heuristic bot' if cfg.bot else ''}: "
            f"{g.scores} in {g.steps} steps, {g.searches} searches; {len(out.policy)} choices, {len(out.value)} positions so far "
            f"({done:.0f}s, about {done / (k + 1) * (s.selfplay_games - k - 1):.0f}s left)",
            flush=True,
        )
    out.finished = True
    return out, {
        "games": s.selfplay_games,
        "mean_score": round(float(np.mean(scores)), 1) if scores else 0.0,
        "against_heuristic": {
            "games": len(vs_bot),
            "model": round(float(np.mean([a for a, _ in vs_bot])), 1) if vs_bot else 0.0,
            "bot": round(float(np.mean([b for _, b in vs_bot])), 1) if vs_bot else 0.0,
        },
        "steps": steps,
        "searches": searches,
        "seconds": round(time.time() - started),
    }


def human_data(
    net: PolicyNet, it: int, s: Settings, brain: BrainFactory, stop: Callable[[], bool] = lambda: False
) -> tuple[Examples, expert.ExpertStats] | None:
    """The policy examples from searching at the starts of turns of people with the person's turn offered (the value of the games is `human_values`)."""
    if s.people is None or s.human_positions <= 0:
        return Examples(), expert.ExpertStats()
    found, stats = expert.sample_positions(s.people, s.human_positions, s.seed * 7919 + it, solo=s.people_solo)
    print(f"    positions of people: {len(found)} turn starts from {stats}", flush=True)
    search = BundleSearch(brain(net), s.search)
    ex, st = expert.search_positions([p for p in found if not stop()], search, random.Random(s.seed * 31 + it), s.expert_weight)
    if stop():
        return None
    print(f"    search at the positions of people: {st}", flush=True)
    return ex, st


def human_values(s: Settings) -> Examples:
    """The value of every position of the games of people (no policy imitation): the same in every iteration."""
    if s.people is None:
        return Examples()
    ex, stats = dataset.load_examples(s.people, imitate=0.0, solo=s.people_solo)
    print(f"games of people: {stats}; {len(ex.value)} positions after a bundle", flush=True)
    return ex


def head_to_head(net: PolicyNet, champion: PolicyNet, games: int, cfg: SearchConfig, brain: BrainFactory) -> dict[str, Any]:
    """The candidate against the champion, both with the bundle search, the same seeds and the seats swapped."""
    mine: list[int] = []
    theirs: list[int] = []
    wins = 0.0
    for k in range(games):
        seed, seat = 70_000 + k // 2, k % 2
        a, b = BundleBot(brain(net), SearchConfig(**vars(cfg))), BundleBot(brain(champion), SearchConfig(**vars(cfg)))
        res = arena.play_game([a, b] if seat == 0 else [b, a], seed, random.Random(seed))
        x, y = res.scores[seat], res.scores[1 - seat]
        mine.append(x)
        theirs.append(y)
        wins += 1.0 if x > y else 0.5 if x == y else 0.0
        print(f"    against the champion, game {k + 1}/{games}: {x} against {y}", flush=True)
    return {
        "games": games,
        "agent_score": round(float(np.mean(mine)), 1) if mine else 0.0,
        "bot_score": round(float(np.mean(theirs)), 1) if theirs else 0.0,
        "win_rate": wins / games if games else 0.0,
    }


def champion_of(start: Path) -> dict[str, Any]:
    """The version that the run starts from, with its mean score against heuristic v3 from its manifest (the yardstick of the gate)."""
    folder = start if start.is_dir() else start.parent
    manifest = folder / "manifest.json"
    bench = 0.0
    version = folder.name
    if manifest.exists():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        bench = float(m.get("evaluation", {}).get("heuristic", {}).get("agent_score", 0.0))
        version = str(m.get("version", version))
    return {"version": version, "path": str(start if start.is_file() else start / "model.pt"), "bench": bench}


def train_on(net: PolicyNet, opt: torch.optim.Optimizer, data: Examples, s: Settings, device: torch.device, rng: np.random.Generator) -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    for e in range(1, s.epochs + 1):
        t = time.time()
        st = bundle_train.train_epoch(net, opt, data, device, rng, s.batch, s.log_every)
        print(
            f"  epoch {e}/{s.epochs}: policy loss {st['policy_loss']:.3f}, picks the searched move {st['accuracy']:.1%}, "
            f"value error {st['value_rmse_points']:.1f} points ({time.time() - t:.0f}s, {st['seconds_per_batch']:.2f}s a batch)",
            flush=True,
        )
        out.append(st)
    return out


def iteration(
    net: PolicyNet,
    opt: torch.optim.Optimizer,
    it: int,
    s: Settings,
    device: torch.device,
    values: Examples,
    buf: Buffer,
    champion: dict[str, Any],
    brain: BrainFactory,
    stop: Callable[[], bool] = lambda: False,
) -> dict[str, Any] | None:
    """One iteration; its record (also written to metrics.jsonl), or None when a pause cut it short (nothing was saved)."""
    t0 = time.time()
    print(f"iteration {it}", flush=True)
    sp = self_play_data(net, it, s, brain, stop)
    if sp is None:
        return None
    hd = human_data(net, it, s, brain, stop)
    if hd is None:
        return None
    fresh = Examples()
    fresh.extend(sp[0])
    fresh.extend(hd[0])
    buf.add(it, fresh)
    pool = buf.load()
    data = dataset.mix(pool, values, s.people_share, seed=s.seed + it)
    print(
        f"  training data: {len(data.policy)} choices, {len(data.value)} positions after a bundle (the last {s.buffer} iterations and the games of people)",
        flush=True,
    )
    epochs = train_on(net, opt, data, s, device, np.random.default_rng(s.seed * 17 + it))
    record: dict[str, Any] = {
        "kind": "iterate",
        "iteration": it,
        "self_play": sp[1],
        "expert": {k: v for k, v in vars(hd[1]).items()},
        "data": {"choices": len(data.policy), "positions": len(data.value)},
        "epochs": epochs,
    }
    net.eval()
    record["against_bots"] = bundle_train.evaluate_vs_bots(net, s.eval_games, device) if s.eval_games > 0 else {}
    bench = float(record["against_bots"].get("heuristic", {}).get("agent_score", 0.0))
    if s.gate_games > 0:
        champ_net = net_from(champion["path"], device)
        h2h = head_to_head(net, champ_net, s.gate_games, s.search, brain)
        decision = gate.decide(champion, h2h, bench)
        record["gate"] = {"h2h": h2h, "promote": decision.promote, "reason": decision.reason, "champion": champion["version"]}
        print(f"  gate: {decision.reason} -> {'saved as a new version' if decision.promote else 'not saved'}", flush=True)
        if decision.promote:
            version = registry.save_version(
                s.models,
                net,
                champion["version"],
                {"iterations": it, "method": "self-play with the bundle search and the games of people (iterate.py)", "players": 2, "iteration": it},
                {**record["against_bots"], "head_to_head": h2h},
            )
            record["saved"] = version
            champion.update({"version": version, "path": str(s.models / version / "model.pt"), "bench": bench})
    record["seconds"] = round(time.time() - t0)
    gate.log_metrics(s.models, record)
    return record


def run(s: Settings, start: Path, resume: bool, brain: BrainFactory = net_brain, device: torch.device | None = None, preset: str = "") -> None:
    root = s.models
    root.mkdir(parents=True, exist_ok=True)
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint.clear_pause(root)
    checkpoint.install_signal_handler()
    champion = champion_of(start)
    first = 1
    if resume and checkpoint.exists(root):
        net, opt_state, meta, rng_state = checkpoint.load(root, device)
        opt = torch.optim.AdamW(net.parameters(), lr=s.lr, weight_decay=0.01)
        opt.load_state_dict(opt_state)
        checkpoint.restore_rng(rng_state)
        first = int(meta["iteration"]) + 1
        champion = meta.get("champion") or champion
        print(f"resuming after iteration {meta['iteration']} (the champion is {champion['version']})", flush=True)
    else:
        net = new_net(preset).to(device) if preset else net_from(str(start if start.is_file() else start / "model.pt"), device)
        opt = torch.optim.AdamW(net.parameters(), lr=s.lr, weight_decay=0.01)
        print(f"starting from {champion['version']}: {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M parameters, on {device}", flush=True)
    values = human_values(s)
    buf = Buffer(root, s.buffer)
    for it in range(first, s.iterations + 1):
        rec = iteration(net, opt, it, s, device, values, buf, champion, brain, lambda: checkpoint.pause_requested(root))
        if rec is None:
            print("paused in the middle of an iteration: nothing of it was saved (run again with --resume)", flush=True)
            checkpoint.clear_pause(root)
            return
        checkpoint.save(root, net, opt, {"iteration": it, "best": 0.0, "champion": champion, "parent": champion["version"], "args": {"seed": s.seed}})
        if checkpoint.pause_requested(root) and it < s.iterations:
            print("paused: the checkpoint is saved (run again with --resume)", flush=True)
            checkpoint.clear_pause(root)
            return


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "pause"])
    ap.add_argument("--owner-approved", action="store_true", help="the owner has said go for this run (training never starts without it)")
    ap.add_argument("--models", default="models_v3")
    ap.add_argument("--start", default="models_alpha/v002", help="the version to start from (its folder, or a model.pt)")
    ap.add_argument("--preset", default="", choices=["", *PRESETS], help="start from a new network of this size instead of --start")
    ap.add_argument("--people", default="", help="the downloaded archive of games")
    ap.add_argument("--people-share", type=float, default=0.3)
    ap.add_argument("--people-solo", action="store_true")
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--selfplay-games", type=int, default=20)
    ap.add_argument("--bot-share", type=float, default=0.25)
    ap.add_argument("--human-positions", type=int, default=200)
    ap.add_argument("--expert-weight", type=float, default=1.0)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--buffer", type=int, default=4)
    ap.add_argument("--gate-games", type=int, default=4)
    ap.add_argument("--eval-games", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--log-every", type=float, default=60.0)
    ap.add_argument("--explore-temperature", type=float, default=3.0)
    ap.add_argument("--explore-rounds", type=int, default=2)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if a.cmd == "pause":
        checkpoint.request_pause(Path(a.models))
        print("pause requested: the run stops at the end of the iteration that it is in")
        return
    if not a.owner_approved:
        raise SystemExit("training starts only with the owner's go: add --owner-approved when they have said it (docs/AI-DECISIONS.md)")
    s = Settings(
        models=Path(a.models),
        people=Path(a.people) if a.people else None,
        iterations=a.iterations,
        selfplay_games=a.selfplay_games,
        bot_share=a.bot_share,
        human_positions=a.human_positions,
        epochs=a.epochs,
        batch=a.batch,
        lr=a.lr,
        buffer=a.buffer,
        people_share=a.people_share,
        people_solo=a.people_solo,
        expert_weight=a.expert_weight,
        gate_games=a.gate_games,
        eval_games=a.eval_games,
        seed=a.seed,
        log_every=a.log_every,
        explore_temperature=a.explore_temperature,
        explore_rounds=a.explore_rounds,
    )
    run(s, Path(a.start), a.resume, preset=a.preset)


if __name__ == "__main__":
    main()
