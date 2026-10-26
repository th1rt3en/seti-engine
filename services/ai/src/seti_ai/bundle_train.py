"""Training of the network at the level of bundles (docs/AI-TURN-BUNDLES.md). The first run is the alpha: a small network that is taught what the
heuristic bots do and what a position after a turn is worth, from games of bots cut into bundles.

python -m seti_ai.bundle_train alpha --games 300 --epochs 6 --models models_alpha          # the alpha python -m seti_ai.bundle_train alpha --resume
--models models_alpha                          # go on after a pause python -m seti_ai.bundle_train pause --models models_alpha
# ask a run to stop at the end of the epoch

What it learns from (`bundle_data.py`): the choice of every micro move of a bundle (policy), and from the position after each bundle the points the
seat still gained until the end of the game (value). The games of people (and of people against the model) are made into examples by `dataset.py`: the
value of every position, and no imitation of the exact human moves. The data are made again from the same seeds when a run is resumed, so the games are
the same. Written to the log as it goes; the mean scores are shown against the 250 of an advanced player (gate.py).
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from seti_engine.models import Options
from torch import nn

from . import arena, bots, checkpoint, dataset, features, gate, registry
from .agent import PRESETS, VALUE_SCALE, LocalNet, NNAgent, PolicyNet, collate, new_net
from .bundle_data import Examples, examples_from_log

OPTIONS = [{}, {"expansion": True, "organizations": True}]  # the base game and the expansion, half of the games each
PAIRS = [("heuristic", "heuristic"), ("heuristic", "greedy"), ("greedy", "heuristic"), ("heuristic", "random")]
DUMMY_TOKS = np.zeros((1, features.MAX_TOKENS), dtype=np.int32)  # a position with nobody to act has no move to choose: a blank one that the network ignores
DUMMY_NUMS = np.zeros((1, features.MOVE_NUM), dtype=np.float32)


def bot_game_examples(job: dict[str, Any]) -> tuple[Examples, list[int]]:
    """One game of two bots (in a worker): played, cut into bundles, made into examples."""
    opts = dict(OPTIONS[job["kind"]])
    a, b = bots.BOTS[job["bot_a"]](), bots.BOTS[job["bot_b"]]()
    seed = job["seed"]
    res = arena.play_game([a, b], seed, random.Random(seed), opts)
    return examples_from_log(Options(players=2, seed=seed, **opts), res.actions), res.scores


def make_data(games: int, seed: int, workers: int) -> tuple[Examples, list[int]]:
    jobs = [{"kind": k % 2, "bot_a": PAIRS[(k // 2) % 4][0], "bot_b": PAIRS[(k // 2) % 4][1], "seed": seed * 100_000 + k} for k in range(games)]
    out = Examples()
    scores: list[int] = []
    t0 = time.time()
    with mp.get_context("spawn").Pool(workers) as pool:
        for n, (ex, sc) in enumerate(pool.imap_unordered(bot_game_examples, jobs, chunksize=1), start=1):
            out.extend(ex)
            scores += sc
            if n % 50 == 0 or n == games:
                print(
                    f"  {n}/{games} games of bots ({time.time() - t0:.0f}s): {len(out.policy)} choices, {len(out.value)} positions after a bundle", flush=True
                )
    return out, scores


def gpu_memory(device: torch.device) -> str:
    if device.type != "cuda":
        return ""
    gib = 1024**3
    return f", gpu memory {torch.cuda.memory_allocated() / gib:.1f} GiB in use, {torch.cuda.max_memory_allocated() / gib:.1f} GiB peak"


def train_epoch(
    net: PolicyNet,
    opt: torch.optim.Optimizer,
    ex: Examples,
    device: torch.device,
    rng: np.random.Generator,
    batch: int = 64,
    log_every: float = 60.0,
) -> dict[str, float]:
    """One pass over the choices (each batch comes with as many positions after a bundle, for the value). Weighted: an example of weight 3 counts three
    times. A line of progress goes to the log every `log_every` seconds: the batch, the time left, the speed, the running losses, the gradient and the
    memory; the numbers of the whole epoch come back with the result."""
    net.train()
    order = rng.permutation(len(ex.policy))
    tot = {"policy": 0.0, "acc": 0.0, "value": 0.0, "n": 0.0, "nv": 0.0, "grad": 0.0, "batches": 0.0}
    batches = -(-len(order) // batch)
    started = last = time.time()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for b in range(0, len(order), batch):
        pol = [ex.policy[i] for i in order[b : b + batch]]
        val = [ex.value[j] for j in rng.integers(0, len(ex.value), size=len(pol))] if ex.value else []
        steps = [(p.tokens, p.toks, p.nums) for p in pol] + [(v.tokens, DUMMY_TOKS, DUMMY_NUMS) for v in val]
        bt = collate(steps, device)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
            logits, value = net(bt)
        n = len(pol)
        act = torch.tensor([p.action for p in pol], device=device)
        w = torch.tensor([p.weight for p in pol], dtype=torch.float32, device=device)
        ce = nn.functional.cross_entropy(logits[:n], act, reduction="none")
        policy_loss = (ce * w).sum() / w.sum()
        loss = policy_loss
        value_loss = torch.zeros((), device=device)
        if val:
            target = torch.tensor([v.target for v in val], dtype=torch.float32, device=device)
            vw = torch.tensor([v.weight for v in val], dtype=torch.float32, device=device)
            value_loss = (((value[n:] - target) ** 2) * vw).sum() / vw.sum()
            loss = loss + 0.5 * value_loss
        opt.zero_grad()
        loss.backward()  # type: ignore[no-untyped-call]
        grad = float(nn.utils.clip_grad_norm_(net.parameters(), 1.0))
        opt.step()
        tot["grad"] += grad
        tot["batches"] += 1
        tot["policy"] += float(policy_loss.detach()) * n
        tot["acc"] += float((logits[:n].argmax(dim=1) == act).float().sum())
        tot["n"] += n
        if val:
            tot["value"] += float(value_loss.detach()) * len(val)
            tot["nv"] += len(val)
        now = time.time()
        if now - last >= log_every:
            last = now
            done = int(tot["batches"])
            speed = done / (now - started)
            mean_loss, acc = tot["policy"] / max(tot["n"], 1), tot["acc"] / max(tot["n"], 1)
            rmse = (tot["value"] / max(tot["nv"], 1)) ** 0.5 * VALUE_SCALE
            print(
                f"    batch {done}/{batches} ({done / batches:.0%}), {now - started:.0f}s so far, "
                f"about {(batches - done) / speed:.0f}s left ({speed:.2f} batches/s, {1 / speed:.2f}s a batch): "
                f"policy loss {mean_loss:.3f}, picks the bot's move {acc:.1%}, value error {rmse:.1f} points, "
                f"gradient {tot['grad'] / done:.2f}{gpu_memory(device)}",
                flush=True,
            )
    seconds = time.time() - started
    return {
        "policy_loss": tot["policy"] / max(tot["n"], 1),
        "accuracy": tot["acc"] / max(tot["n"], 1),
        "value_rmse_points": (tot["value"] / max(tot["nv"], 1)) ** 0.5 * VALUE_SCALE,
        "batches": tot["batches"],
        "seconds": seconds,
        "seconds_per_batch": seconds / max(tot["batches"], 1),
        "mean_gradient": tot["grad"] / max(tot["batches"], 1),
    }


def evaluate_vs_bots(net: PolicyNet, games: int, device: torch.device, opponents: tuple[str, ...] = ("heuristic",)) -> dict[str, Any]:
    """The network taking its best micro move, against each bot (the same seeds, the seats swapped): its mean score, the bot's, its win rate.
    Only the heuristic bot by default: the random and the greedy bots are far too weak to say anything (owner, 2026-10-26)."""
    net.eval()
    out: dict[str, Any] = {}
    for opp in opponents:
        mine, theirs, wins = [], [], 0.0
        for k in range(games):
            seed, seat = 50_000 + k // 2, k % 2
            agent = NNAgent(LocalNet(net), explore=False)
            bot = bots.BOTS[opp]()
            res = arena.play_game([agent, bot] if seat == 0 else [bot, agent], seed, random.Random(seed))
            a, b = res.scores[seat], res.scores[1 - seat]
            mine.append(a)
            theirs.append(b)
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
        out[opp] = {
            "games": games,
            "agent_score": round(float(np.mean(mine)), 1),
            "bot_score": round(float(np.mean(theirs)), 1),
            "win_rate": round(wins / games, 3),
        }
        print(f"  vs {opp}: network {out[opp]['agent_score']} against {out[opp]['bot_score']} (wins {out[opp]['win_rate']:.0%}, {games} games)", flush=True)
    return out


def evaluate_with_search(net: PolicyNet, games: int) -> dict[str, Any]:
    """The network with the bundle search against heuristic v3 (a few games: the search takes a while)."""
    from .brains import NetBrain
    from .bundle_search import BundleBot, SearchConfig

    net.eval()
    mine, theirs = [], []
    for k in range(games):
        seed, seat = 60_000 + k // 2, k % 2
        bot = BundleBot(NetBrain(LocalNet(net)), SearchConfig())
        other = bots.heuristic()
        res = arena.play_game([bot, other] if seat == 0 else [other, bot], seed, random.Random(seed))
        mine.append(res.scores[seat])
        theirs.append(res.scores[1 - seat])
        print(f"  with the bundle search, game {k + 1}/{games}: {mine[-1]} against {theirs[-1]}", flush=True)
    return {"games": games, "agent_score": round(float(np.mean(mine)), 1) if mine else 0.0, "bot_score": round(float(np.mean(theirs)), 1) if theirs else 0.0}


def alpha(a: argparse.Namespace) -> None:
    root = Path(a.models)
    root.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint.clear_pause(root)
    checkpoint.install_signal_handler()
    print(f"the alpha: network {a.preset}, {a.games} games of bots, {a.epochs} epochs, on {device}", flush=True)
    t0 = time.time()
    ex, scores = make_data(a.games, a.seed, a.workers)
    lengths = [b for b in [ex.bundles]]
    print(
        f"data: {len(ex.policy)} choices, {len(ex.value)} positions after a bundle, {ex.bundles} bundles "
        f"({len(ex.policy) / max(ex.bundles, 1):.1f} moves a bundle); the bots scored {np.mean(scores):.1f} on average "
        f"({gate.share_of_reference(float(np.mean(scores)))}) ({time.time() - t0:.0f}s)",
        flush=True,
    )
    assert lengths
    if a.people:
        people, found = dataset.load_examples(Path(a.people), a.imitate, solo=a.people_solo)
        print(f"games of people: {found}; {len(people.policy)} choices, {len(people.value)} positions after a bundle", flush=True)
        ex = dataset.mix(ex, people, a.people_share, seed=a.seed)
        print(f"data with the games of people: {len(ex.policy)} choices, {len(ex.value)} positions after a bundle", flush=True)
    start_epoch = 1
    if a.resume and checkpoint.exists(root):
        net, opt_state, meta, rng_state = checkpoint.load(root, device)
        opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
        opt.load_state_dict(opt_state)
        checkpoint.restore_rng(rng_state)
        start_epoch = int(meta["iteration"]) + 1
        print(f"resuming after epoch {meta['iteration']}", flush=True)
    else:
        net = new_net(a.preset).to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
        print(f"network {a.preset}: {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M parameters", flush=True)
    rng = np.random.default_rng(a.seed + start_epoch)
    paused = False
    for epoch in range(start_epoch, a.epochs + 1):
        t1 = time.time()
        st = train_epoch(net, opt, ex, device, rng, a.batch, a.log_every)
        print(
            f"epoch {epoch}/{a.epochs}: policy loss {st['policy_loss']:.3f}, picks the bot's move {st['accuracy']:.1%}, "
            f"value error {st['value_rmse_points']:.1f} points ({time.time() - t1:.0f}s; {int(st['batches'])} batches, {st['seconds_per_batch']:.2f}s a batch, "
            f"mean gradient {st['mean_gradient']:.2f}{gpu_memory(device)}); "
            f"about {(time.time() - t1) * (a.epochs - epoch) / 3600:.1f} hours for the epochs left",
            flush=True,
        )
        gate.log_metrics(root, {"kind": "alpha-epoch", "epoch": epoch, **st})
        checkpoint.save(root, net, opt, {"iteration": epoch, "best": 0.0, "champion": None, "parent": None, "args": {k: v for k, v in vars(a).items()}})
        if checkpoint.pause_requested(root) and epoch < a.epochs:
            print("paused: the checkpoint is saved (alpha --resume to go on)", flush=True)
            paused = True
            break
    if paused:
        checkpoint.clear_pause(root)
        return
    print("evaluating:", flush=True)
    ev = evaluate_vs_bots(net, a.eval_games, device)
    search = evaluate_with_search(net, a.search_eval_games) if a.search_eval_games > 0 else None
    shown = ev["heuristic"]["agent_score"]
    print(f"mean score against heuristic v3: {shown} ({gate.share_of_reference(shown)})", flush=True)
    version = registry.save_version(
        root,
        net,
        None,
        {
            "iterations": a.epochs,
            "games_per_iteration": a.games,
            "lr": a.lr,
            "players": 2,
            "network": f"transformer {net.cfg.layers} layers, {net.cfg.d_model} wide, {sum(p.numel() for p in net.parameters()) / 1e6:.0f}M parameters",
            "features": "v3 (bundles: the class of each move)",
            "alpha": True,
            "bundle_search_eval": search,
        },
        ev,
    )
    print(f"saved as {version} (for testing: it has to be approved by the owner before anyone can play it)", flush=True)
    gate.log_metrics(root, {"kind": "alpha", "version": version, "against_bots": ev, "with_search": search})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["alpha", "pause"])
    ap.add_argument("--models", default="models_alpha")
    ap.add_argument("--games", type=int, default=300)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--preset", default="small", choices=list(PRESETS))
    ap.add_argument("--workers", type=int, default=min(6, max(1, (os.cpu_count() or 4) - 2)))
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--log-every", type=float, default=60.0, help="seconds between the lines of progress inside an epoch")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--eval-games", type=int, default=10, help="games against each bot")
    ap.add_argument("--search-eval-games", type=int, default=2, help="games with the bundle search against heuristic v3 (0: none)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--people", default="", help="a folder with the downloaded archive of games (games with people and with the model)")
    ap.add_argument("--people-share", type=float, default=0.3, help="about this share of the data is from the archive (repeated if there are few games)")
    ap.add_argument("--people-solo", action="store_true", help="also the games of one player (against the rival) of the archive")
    ap.add_argument("--imitate", type=float, default=0.0, help="weight of the exact moves of the people as policy examples (0: the games teach the value only)")
    a = ap.parse_args()
    if a.cmd == "pause":
        checkpoint.request_pause(Path(a.models))
        print("pause requested: the run stops at the end of the epoch that it is in")
        return
    alpha(a)


if __name__ == "__main__":
    main()
