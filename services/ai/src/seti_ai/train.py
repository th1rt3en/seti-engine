"""Training on this machine: learn from the bots' games, then improve by playing against itself (PPO), with the aim of raising the agent's own score.

    .venv/Scripts/python.exe -m seti_ai.train bc  --games 300 --epochs 6              # copy the heuristic bot (a warm start)
    .venv/Scripts/python.exe -m seti_ai.train ppo --start models/bc --iters 200        # self-play: the part that makes it better
    .venv/Scripts/python.exe -m seti_ai.train eval --model models/v001 --games 40      # play the bots again

The game is 2 players, base game (`--players 2`); more players and the expansion come later. The reward of a decision is the change in the seat's
board score until its next decision, and the last one gets what the end of the game adds (the end-of-game cards, the gold tiles ...), so the sum is
the seat's own final score. Nothing here is a rule: the engine plays every game and lists every legal move.
The workers play on the CPU cores with a copy of the network; the update runs on the GPU. Models are saved as versions (registry.py).
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from . import arena, bots, registry
from .agent import VALUE_SCALE, NNAgent, PolicyNet, Step, new_net

GAMMA = 1.0
LAMBDA = 0.95
_NET: dict[str, Any] = {"tag": None, "net": None}


@dataclass
class Traj:
    """The decisions of one seat in one game, with what PPO needs: the returns and the advantages."""

    steps: list[Step]
    rewards: np.ndarray
    final: int


def rewards_of(steps: list[Step], final: int) -> np.ndarray:
    """A decision earns the score that its seat gets before its next decision; the last one earns the rest up to the final score."""
    out = np.zeros(len(steps), dtype=np.float32)
    for i, s in enumerate(steps):
        nxt = steps[i + 1].board_score if i + 1 < len(steps) else final
        out[i] = (nxt - s.board_score) / VALUE_SCALE
    return out


def _load(path: str, tag: int) -> PolicyNet:
    if _NET["tag"] != (path, tag):
        torch.set_num_threads(1)
        net = new_net()
        net.load_state_dict(torch.load(path, map_location="cpu"))
        net.eval()
        _NET.update(tag=(path, tag), net=net)
    return _NET["net"]  # type: ignore[no-any-return]


class _Recorder:
    """Wraps a bot so that its decisions are kept in the same form as the agent's (for learning to copy it)."""

    def __init__(self, bot: Any, helper: NNAgent) -> None:
        self.bot, self.helper, self.name = bot, helper, bot.name

    def act(self, state: Any, view: Any, rng: random.Random) -> int:
        from . import features

        a: int = self.bot.act(state, view, rng)
        obs = features.encode_view(view)
        toks, nums = features.encode_moves(view)
        self.helper.steps.append(Step(obs, toks, nums, a, 0.0, 0.0, state.players[view.viewer].score, view.viewer))
        return a


def _by_seat(steps: list[Step]) -> dict[int, list[Step]]:
    out: dict[int, list[Step]] = {}
    for s in steps:
        out.setdefault(s.seat, []).append(s)
    return out


def play_job(job: dict[str, Any]) -> dict[str, Any]:
    """One game in a worker: self-play, or against a bot (`opp`), or a bot copy (`bc`); returns the trajectories and the scores."""
    seed = job["seed"]
    rng = random.Random(seed)
    kind = job["kind"]
    if kind == "bc":
        helper = NNAgent(new_net(), record=True)
        a, b = bots.BOTS[job["bot_a"]](), bots.BOTS[job["bot_b"]]()
        res = arena.play_game([_Recorder(a, helper), _Recorder(b, helper)], seed, rng)
        agent_seats = [0, 1]
    else:
        net = _load(job["weights"], job["tag"])
        agent = NNAgent(net, explore=job.get("explore", True), record=job.get("record", True), temperature=job.get("temperature", 1.0))
        if kind == "self":
            res = arena.play_game([agent, agent], seed, rng)
            agent_seats = [0, 1]
        else:
            seat = job["seat"]
            opp = bots.BOTS[job["opp"]]()
            res = arena.play_game([agent, opp] if seat == 0 else [opp, agent], seed, rng)
            agent_seats = [seat]
        helper = agent
    trajs: list[dict[str, Any]] = []
    for seat, steps in _by_seat(helper.steps).items():
        if seat in agent_seats and steps:
            trajs.append({"steps": steps, "rewards": rewards_of(steps, res.scores[seat]), "final": res.scores[seat]})
    return {"trajs": trajs, "scores": res.scores, "finished": res.finished, "kind": kind, "opp": job.get("opp"), "seat": job.get("seat")}


def gae(values: np.ndarray, rewards: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    adv = np.zeros_like(rewards)
    last = 0.0
    for t in reversed(range(len(rewards))):
        nxt = values[t + 1] if t + 1 < len(values) else 0.0
        delta = rewards[t] + GAMMA * nxt - values[t]
        last = delta + GAMMA * LAMBDA * last
        adv[t] = last
    return adv, adv + values


def collate(steps: list[Step], device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    mmax = max(s.toks.shape[0] for s in steps)
    n = len(steps)
    toks = np.zeros((n, mmax, steps[0].toks.shape[1]), dtype=np.int64)
    nums = np.zeros((n, mmax, steps[0].nums.shape[1]), dtype=np.float32)
    mask = np.zeros((n, mmax), dtype=bool)
    for i, s in enumerate(steps):
        m = s.toks.shape[0]
        toks[i, :m] = s.toks
        nums[i, :m] = s.nums
        mask[i, :m] = True
    obs = np.stack([s.obs for s in steps])
    return (
        torch.from_numpy(obs).to(device),
        torch.from_numpy(toks).to(device),
        torch.from_numpy(nums).to(device),
        torch.from_numpy(mask).to(device),
    )


def run_games(pool: Any, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(pool.imap_unordered(play_job, jobs, chunksize=1))


def bc_train(net: PolicyNet, trajs: list[dict[str, Any]], epochs: int, device: torch.device, lr: float = 1e-3, batch: int = 256) -> None:
    """Learn to pick the move that the bot picked (cross-entropy over the legal moves) and the return of the position."""
    steps: list[Step] = []
    targets: list[float] = []
    for t in trajs:
        steps += t["steps"]
        r = t["rewards"]
        ret = np.cumsum(r[::-1])[::-1]
        targets += list(ret)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    net.train()
    idx = np.arange(len(steps))
    for ep in range(epochs):
        np.random.shuffle(idx)
        tot, acc, cnt = 0.0, 0.0, 0
        for b in range(0, len(idx), batch):
            sel = idx[b : b + batch]
            chunk = [steps[i] for i in sel]
            obs, toks, nums, mask = collate(chunk, device)
            act = torch.tensor([s.action for s in chunk], device=device)
            target = torch.tensor([targets[i] for i in sel], dtype=torch.float32, device=device)
            logits, value = net(obs, toks, nums, mask)
            loss = nn.functional.cross_entropy(logits, act) + 0.5 * nn.functional.mse_loss(value, target)
            opt.zero_grad()
            loss.backward()  # type: ignore[no-untyped-call]
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tot += float(loss.detach()) * len(sel)
            acc += float((logits.argmax(dim=1) == act).float().sum())
            cnt += len(sel)
        print(f"  bc epoch {ep + 1}/{epochs}: loss {tot / cnt:.3f}, picks the bot's move {acc / cnt:.1%} ({cnt} decisions)", flush=True)


def ppo_update(
    net: PolicyNet, opt: torch.optim.Optimizer, trajs: list[dict[str, Any]], device: torch.device, epochs: int = 3, batch: int = 512
) -> dict[str, float]:
    steps: list[Step] = []
    adv_all: list[float] = []
    ret_all: list[float] = []
    for t in trajs:
        values = np.array([s.value for s in t["steps"]], dtype=np.float32)
        adv, ret = gae(values, t["rewards"])
        steps += t["steps"]
        adv_all += list(adv)
        ret_all += list(ret)
    adv_np = np.asarray(adv_all, dtype=np.float32)
    adv_np = (adv_np - adv_np.mean()) / (adv_np.std() + 1e-6)
    old_logp = np.array([s.logp for s in steps], dtype=np.float32)
    net.train()
    stats = {"policy": 0.0, "value": 0.0, "entropy": 0.0, "clip": 0.0}
    n_batches = 0
    idx = np.arange(len(steps))
    for _ in range(epochs):
        np.random.shuffle(idx)
        for b in range(0, len(idx), batch):
            sel = idx[b : b + batch]
            chunk = [steps[i] for i in sel]
            obs, toks, nums, mask = collate(chunk, device)
            act = torch.tensor([s.action for s in chunk], device=device)
            adv_t = torch.from_numpy(adv_np[sel]).to(device)
            ret_t = torch.from_numpy(np.asarray(ret_all, dtype=np.float32)[sel]).to(device)
            old = torch.from_numpy(old_logp[sel]).to(device)
            logits, value = net(obs, toks, nums, mask)
            logp_all = torch.log_softmax(logits, dim=1)
            logp = logp_all.gather(1, act.unsqueeze(1)).squeeze(1)
            ratio = torch.exp(logp - old)
            surr = torch.min(ratio * adv_t, torch.clamp(ratio, 0.8, 1.2) * adv_t)
            entropy = -(torch.softmax(logits, dim=1) * logp_all.masked_fill(~mask, 0.0)).sum(dim=1).mean()
            loss = -surr.mean() + 0.5 * nn.functional.mse_loss(value, ret_t) - 0.01 * entropy
            opt.zero_grad()
            loss.backward()  # type: ignore[no-untyped-call]
            nn.utils.clip_grad_norm_(net.parameters(), 0.5)
            opt.step()
            stats["policy"] += float((-surr.mean()).detach())
            stats["value"] += float(nn.functional.mse_loss(value, ret_t).detach())
            stats["entropy"] += float(entropy.detach())
            stats["clip"] += float(((ratio - 1).abs() > 0.2).float().mean())
            n_batches += 1
    return {k: v / max(n_batches, 1) for k, v in stats.items()}


def save_weights(net: PolicyNet, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    torch.save({k: v.detach().cpu() for k, v in net.state_dict().items()}, tmp)
    os.replace(tmp, path)


def evaluate(
    pool: Any, weights: str, tag: int, games: int, opponents: tuple[str, ...] = ("random", "greedy", "heuristic"), first_seed: int = 50_000
) -> dict[str, Any]:
    """The agent (taking the best move) against each bot, the same seeds, the seats swapped: its mean score, the bot's, its win rate."""
    out: dict[str, Any] = {}
    for opp in opponents:
        jobs = [
            {"kind": "bot", "opp": opp, "seat": k % 2, "seed": first_seed + k // 2, "weights": weights, "tag": tag, "explore": False, "record": False}
            for k in range(games)
        ]
        results = run_games(pool, jobs)
        mine, theirs, wins = [], [], 0.0
        for r in results:
            seat = r["seat"]
            a, b = r["scores"][seat], r["scores"][1 - seat]
            mine.append(a)
            theirs.append(b)
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
        out[opp] = {
            "games": games,
            "agent_score": round(float(np.mean(mine)), 1),
            "bot_score": round(float(np.mean(theirs)), 1),
            "win_rate": round(wins / games, 3),
        }
        print(f"  vs {opp}: agent {out[opp]['agent_score']} against {out[opp]['bot_score']} (wins {out[opp]['win_rate']:.0%}, {games} games)", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["bc", "ppo", "eval"])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--games", type=int, default=96, help="games per iteration (ppo), games for the copy (bc), games per bot (eval)")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--start", default=None, help="a model folder to start from")
    ap.add_argument("--model", default=None, help="a model folder (eval)")
    ap.add_argument("--models", default="models")
    ap.add_argument("--eval-every", type=int, default=10)
    ap.add_argument("--eval-games", type=int, default=20)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ctx = mp.get_context("spawn")
    root = Path(a.models)
    with ctx.Pool(a.workers) as pool:
        if a.cmd == "bc":
            net = new_net().to(device)
            pairs = [("heuristic", "heuristic"), ("heuristic", "greedy"), ("greedy", "heuristic"), ("heuristic", "random")]
            jobs = [{"kind": "bc", "seed": a.seed * 100_000 + k, "bot_a": pairs[k % 4][0], "bot_b": pairs[k % 4][1]} for k in range(a.games)]
            t0 = time.time()
            results = run_games(pool, jobs)
            trajs = [t for r in results for t in r["trajs"]]
            print(f"{a.games} bot games in {time.time() - t0:.0f}s, {sum(len(t['steps']) for t in trajs)} decisions", flush=True)
            bc_train(net, trajs, a.epochs, device)
            out = root / "bc"
            save_weights(net, out / "model.pt")
            print("saved", out)
        elif a.cmd == "eval":
            assert a.model
            path = str(Path(a.model) / "model.pt")
            print(evaluate(pool, path, int(time.time()), a.eval_games))
        else:
            net = new_net().to(device)
            if a.start:
                net.load_state_dict(torch.load(Path(a.start) / "model.pt", map_location=device))
            opt = torch.optim.Adam(net.parameters(), lr=a.lr)
            weights = str(root / "_current.pt")
            parent = Path(a.start).name if a.start else None
            best = -1e9
            for it in range(1, a.iters + 1):
                t0 = time.time()
                save_weights(net, Path(weights))
                jobs = []
                for k in range(a.games):
                    seed = a.seed * 1_000_000 + it * 1000 + k
                    r = k % 4
                    if r < 2:
                        jobs.append({"kind": "self", "seed": seed, "weights": weights, "tag": it})
                    else:
                        jobs.append({"kind": "bot", "opp": "heuristic" if r == 2 else "greedy", "seat": k % 2, "seed": seed, "weights": weights, "tag": it})
                results = run_games(pool, jobs)
                trajs = [t for res in results for t in res["trajs"]]
                finals = [t["final"] for t in trajs]
                t1 = time.time()
                stats = ppo_update(net, opt, trajs, device)
                print(
                    f"iter {it}: {len(results)} games, {sum(len(t['steps']) for t in trajs)} decisions, own score {np.mean(finals):.1f}, "
                    f"policy {stats['policy']:.3f} value {stats['value']:.3f} entropy {stats['entropy']:.2f} clipped {stats['clip']:.2f}, "
                    f"play {t1 - t0:.0f}s update {time.time() - t1:.0f}s",
                    flush=True,
                )
                if it % a.eval_every == 0 or it == a.iters:
                    save_weights(net, Path(weights))
                    ev = evaluate(pool, weights, 100_000 + it, a.eval_games)
                    key = ev["heuristic"]["agent_score"]
                    if key > best:
                        best = key
                        v = registry.save_version(
                            root, net, parent, {"iterations": it, "games_per_iteration": a.games, "lr": a.lr, "players": 2}, ev, start=a.start
                        )
                        print(f"  saved as {v}", flush=True)


if __name__ == "__main__":
    main()
