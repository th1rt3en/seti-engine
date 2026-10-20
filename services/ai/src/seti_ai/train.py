"""Training on this machine: learn from the bots' games, then improve by playing against itself (PPO), with the aim of raising the agent's own score.

    .venv/Scripts/python.exe -m seti_ai.train bc  --games 400 --epochs 6 --preset base        # copy the heuristic bot (a warm start)
    .venv/Scripts/python.exe -m seti_ai.train ppo --start models/bc --iters 300                # self-play: the part that makes it better
    .venv/Scripts/python.exe -m seti_ai.train eval --model models/v001 --eval-games 40        # play the bots again

The game is 2 players, base game (`--players 2`); more players and the expansion come later. The reward of a decision is the change in the seat's
board score until its next decision, and the last one gets what the end of the game adds (the end-of-game cards, the gold tiles ...), so the sum is
the seat's own final score. A game that is not finished within the step limit ends with a penalty, so that stalling does not pay.
The games are played by worker processes on the CPU cores; the network runs on the GPU in a server process that answers all of them (server.py), and the
update runs on the GPU in this process. Nothing here is a rule: the engine plays every game and lists every legal move.
"""

from __future__ import annotations

import argparse
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from . import arena, bots, features, registry
from .agent import PRESETS, VALUE_SCALE, NNAgent, PolicyNet, Step, collate, net_from, new_net, save_net
from .server import Client, start_server

GAMMA = 1.0
LAMBDA = 0.95
UNFINISHED_PENALTY = 1.0  # in units of 20 points
_STATE: dict[str, Any] = {}


@dataclass
class Traj:
    steps: list[Step]
    rewards: np.ndarray
    final: int


def rewards_of(steps: list[Step], final: int, finished: bool = True) -> np.ndarray:
    """A decision earns the score that its seat gets before its next decision; the last one earns the rest up to the final score
    (or, in a game that did not finish, a penalty)."""
    out = np.zeros(len(steps), dtype=np.float32)
    for i, s in enumerate(steps):
        nxt = steps[i + 1].board_score if i + 1 < len(steps) else final
        out[i] = (nxt - s.board_score) / VALUE_SCALE
    if not finished and len(out) > 0:
        out[-1] -= UNFINISHED_PENALTY
    return out


def init_worker(req_q: Any, resp_qs: list[Any], counter: Any) -> None:
    with counter.get_lock():
        wid = counter.value
        counter.value += 1
    torch.set_num_threads(1)
    _STATE["client"] = Client(wid, req_q, resp_qs[wid])


class _Recorder:
    """Wraps a bot so that its decisions are kept in the same form as the agent's (for learning to copy it)."""

    def __init__(self, bot: Any, helper: NNAgent) -> None:
        self.bot, self.helper, self.name = bot, helper, bot.name

    def act(self, state: Any, view: Any, rng: random.Random) -> int:
        a: int = self.bot.act(state, view, rng)
        keep = [i for i, m in enumerate(view.legal) if m["type"] != "undo"] or list(range(len(view.legal)))
        tokens = features.encode_view(view)
        toks, nums = features.encode_moves(view, keep)
        self.helper.steps.append(Step(tokens, toks, nums, keep.index(a) if a in keep else 0, 0.0, 0.0, state.players[view.viewer].score, view.viewer))
        return a


def _by_seat(steps: list[Step]) -> dict[int, list[Step]]:
    out: dict[int, list[Step]] = {}
    for s in steps:
        out.setdefault(s.seat, []).append(s)
    return out


def play_job(job: dict[str, Any]) -> dict[str, Any]:
    """One game in a worker: self-play, or against a bot (`opp`), or a copy of two bots (`bc`); returns the trajectories and the scores."""
    seed = job["seed"]
    rng = random.Random(seed)
    kind = job["kind"]
    if kind == "bc":
        helper = NNAgent(None, record=True)
        a, b = bots.BOTS[job["bot_a"]](), bots.BOTS[job["bot_b"]]()
        res = arena.play_game([_Recorder(a, helper), _Recorder(b, helper)], seed, rng)
        agent_seats = [0, 1]
    else:
        agent = NNAgent(_STATE["client"], explore=job.get("explore", True), record=job.get("record", True), temperature=job.get("temperature", 1.0))
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
            trajs.append({"steps": steps, "rewards": rewards_of(steps, res.scores[seat], res.finished), "final": res.scores[seat]})
    return {"trajs": trajs, "scores": res.scores, "finished": res.finished, "kind": kind, "opp": job.get("opp"), "seat": job.get("seat"), "steps": res.steps}


def gae(values: np.ndarray, rewards: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    adv = np.zeros_like(rewards)
    last = 0.0
    for t in reversed(range(len(rewards))):
        nxt = values[t + 1] if t + 1 < len(values) else 0.0
        delta = rewards[t] + GAMMA * nxt - values[t]
        last = delta + GAMMA * LAMBDA * last
        adv[t] = last
    return adv, adv + values


def run_games(pool: Any, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(pool.imap_unordered(play_job, jobs, chunksize=1))


def _batch(chunk: list[Step], device: torch.device) -> Any:
    return collate([(s.tokens, s.toks, s.nums) for s in chunk], device)


def bc_train(net: PolicyNet, trajs: list[dict[str, Any]], epochs: int, device: torch.device, lr: float = 3e-4, batch: int = 64) -> None:
    """Learn to pick the move that the bot picked (cross-entropy over the legal moves) and the return of the position."""
    steps: list[Step] = []
    targets: list[float] = []
    for t in trajs:
        steps += t["steps"]
        targets += list(np.cumsum(t["rewards"][::-1])[::-1])
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=0.01)
    net.train()
    idx = np.arange(len(steps))
    for ep in range(epochs):
        np.random.shuffle(idx)
        tot, acc, cnt = 0.0, 0.0, 0
        for b in range(0, len(idx), batch):
            sel = idx[b : b + batch]
            chunk = [steps[i] for i in sel]
            bt = _batch(chunk, device)
            act = torch.tensor([s.action for s in chunk], device=device)
            target = torch.tensor([targets[i] for i in sel], dtype=torch.float32, device=device)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                logits, value = net(bt)
            loss = nn.functional.cross_entropy(logits, act) + 0.5 * nn.functional.mse_loss(value, target)
            opt.zero_grad()
            loss.backward()  # type: ignore[no-untyped-call]
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tot += float(loss.detach()) * len(sel)
            acc += float((logits.argmax(dim=1) == act).float().sum())
            cnt += len(sel)
        print(f"  bc epoch {ep + 1}/{epochs}: loss {tot / cnt:.3f}, picks the bot's move {acc / cnt:.1%} ({cnt} decisions)", flush=True)


def ppo_update(net: PolicyNet, opt: torch.optim.Optimizer, trajs: list[dict[str, Any]], device: torch.device, epochs: int = 2, batch: int = 64) -> dict[str, float]:
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
    ret_np = np.asarray(ret_all, dtype=np.float32)
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
            bt = _batch(chunk, device)
            act = torch.tensor([s.action for s in chunk], device=device)
            adv_t = torch.from_numpy(adv_np[sel]).to(device)
            ret_t = torch.from_numpy(ret_np[sel]).to(device)
            old = torch.from_numpy(old_logp[sel]).to(device)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                logits, value = net(bt)
            logp_all = torch.log_softmax(logits, dim=1)
            logp = logp_all.gather(1, act.unsqueeze(1)).squeeze(1)
            ratio = torch.exp(logp - old)
            surr = torch.min(ratio * adv_t, torch.clamp(ratio, 0.8, 1.2) * adv_t)
            entropy = -(torch.softmax(logits, dim=1) * logp_all.masked_fill(~bt.move_mask, 0.0)).sum(dim=1).mean()
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


def evaluate(pool: Any, games: int, opponents: tuple[str, ...] = ("random", "greedy", "heuristic"), first_seed: int = 50_000) -> dict[str, Any]:
    """The agent (taking the best move) against each bot, the same seeds, the seats swapped: its mean score, the bot's, its win rate."""
    out: dict[str, Any] = {}
    for opp in opponents:
        jobs = [{"kind": "bot", "opp": opp, "seat": k % 2, "seed": first_seed + k // 2, "explore": False, "record": False} for k in range(games)]
        results = run_games(pool, jobs)
        mine, theirs, wins = [], [], 0.0
        for r in results:
            seat = r["seat"]
            a, b = r["scores"][seat], r["scores"][1 - seat]
            mine.append(a)
            theirs.append(b)
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
        out[opp] = {"games": games, "agent_score": round(float(np.mean(mine)), 1), "bot_score": round(float(np.mean(theirs)), 1), "win_rate": round(wins / games, 3)}
        print(f"  vs {opp}: agent {out[opp]['agent_score']} against {out[opp]['bot_score']} (wins {out[opp]['win_rate']:.0%}, {games} games)", flush=True)
    return out


def load_into_server(req_q: Any, ctl_q: Any, path: str) -> None:
    req_q.put(("load", path))
    ctl_q.get()  # "loaded"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["bc", "ppo", "eval"])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--games", type=int, default=96, help="games per iteration (ppo) or for the copy (bc)")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--preset", default="base", choices=list(PRESETS))
    ap.add_argument("--start", default=None, help="a model folder to start from")
    ap.add_argument("--model", default=None, help="a model folder (eval)")
    ap.add_argument("--models", default="models")
    ap.add_argument("--eval-every", type=int, default=10)
    ap.add_argument("--eval-games", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    root = Path(a.models)
    root.mkdir(parents=True, exist_ok=True)
    server, req_q, resp_qs, ctl_q, ctx = start_server(a.workers, device.type)
    counter = ctx.Value("i", 0)
    try:
        with ctx.Pool(a.workers, initializer=init_worker, initargs=(req_q, resp_qs, counter)) as pool:
            if a.cmd == "bc":
                net = new_net(a.preset).to(device)
                print(f"network {a.preset}: {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M parameters", flush=True)
                pairs = [("heuristic", "heuristic"), ("heuristic", "greedy"), ("greedy", "heuristic"), ("heuristic", "random")]
                jobs = [{"kind": "bc", "seed": a.seed * 100_000 + k, "bot_a": pairs[k % 4][0], "bot_b": pairs[k % 4][1]} for k in range(a.games)]
                t0 = time.time()
                results = run_games(pool, jobs)
                trajs = [t for r in results for t in r["trajs"]]
                print(f"{a.games} bot games in {time.time() - t0:.0f}s, {sum(len(t['steps']) for t in trajs)} decisions", flush=True)
                bc_train(net, trajs, a.epochs, device)
                out = root / f"bc-{a.preset}"
                out.mkdir(parents=True, exist_ok=True)
                save_net(net, str(out / "model.pt"))
                print("saved", out)
            elif a.cmd == "eval":
                assert a.model
                load_into_server(req_q, ctl_q, str(Path(a.model) / "model.pt"))
                print(evaluate(pool, a.eval_games))
            else:
                net = net_from(str(Path(a.start) / "model.pt"), device) if a.start else new_net(a.preset).to(device)
                opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
                weights = str(root / "_current.pt")
                parent = Path(a.start).name if a.start else None
                best = -1e9
                for it in range(1, a.iters + 1):
                    t0 = time.time()
                    save_net(net, weights)
                    load_into_server(req_q, ctl_q, weights)
                    jobs = []
                    for k in range(a.games):
                        seed = a.seed * 1_000_000 + it * 1000 + k
                        r = k % 4
                        if r < 2:
                            jobs.append({"kind": "self", "seed": seed})
                        else:
                            jobs.append({"kind": "bot", "opp": "heuristic" if r == 2 else "greedy", "seat": k % 2, "seed": seed})
                    results = run_games(pool, jobs)
                    trajs = [t for res in results for t in res["trajs"]]
                    finals = [t["final"] for t in trajs]
                    unfinished = sum(1 for res in results if not res["finished"])
                    t1 = time.time()
                    stats = ppo_update(net, opt, trajs, device)
                    print(
                        f"iter {it}: {len(results)} games ({unfinished} not finished), {sum(len(t['steps']) for t in trajs)} decisions, own score {np.mean(finals):.1f}, "
                        f"policy {stats['policy']:.3f} value {stats['value']:.3f} entropy {stats['entropy']:.2f} clipped {stats['clip']:.2f}, "
                        f"play {t1 - t0:.0f}s update {time.time() - t1:.0f}s",
                        flush=True,
                    )
                    if it % a.eval_every == 0 or it == a.iters:
                        save_net(net, weights)
                        load_into_server(req_q, ctl_q, weights)
                        ev = evaluate(pool, a.eval_games)
                        key = ev["heuristic"]["agent_score"]
                        if key > best:
                            best = key
                            v = registry.save_version(root, net, parent, {"iterations": it, "games_per_iteration": a.games, "lr": a.lr, "players": 2, "network": f"transformer {net.cfg.layers} layers, {net.cfg.d_model} wide, {sum(p.numel() for p in net.parameters()) / 1e6:.0f}M parameters", "features": "v2"}, ev)
                            print(f"  saved as {v}", flush=True)
    finally:
        req_q.put(("stop",))
        server.join(timeout=10)


if __name__ == "__main__":
    main()
