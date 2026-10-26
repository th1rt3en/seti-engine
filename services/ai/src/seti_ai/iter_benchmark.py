"""How long a training iteration takes on this machine, measured on a few games and one pass of training, with a new network that is thrown away.
It trains nothing that is kept: no checkpoint, no buffer and no version is written, and it needs no go because there is nothing to resume or serve.

    python -m seti_ai.iter_benchmark --preset medium --search mcts --games 4 --epochs 1

It prints the seconds of a game (self-play), the number of examples that a game gives, the seconds of a training pass over that many examples, and from them
the estimate for an iteration of `--plan-games` games with `--plan-epochs` epochs over the last `--plan-buffer` iterations (the planning of a run).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch

from . import iterate, views
from .agent import PRESETS, new_net
from .bundle_search import SearchConfig
from .mcts import MCTSConfig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", default="medium", choices=list(PRESETS))
    ap.add_argument("--search", choices=["bundle", "mcts"], default="mcts")
    ap.add_argument("--simulations", type=int, default=48)
    ap.add_argument("--worlds", type=int, default=4)
    ap.add_argument("--leaves", type=int, default=4)
    ap.add_argument("--branch", type=int, default=6)
    ap.add_argument("--games", type=int, default=4, help="self-play games to time")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--plan-games", type=int, default=20)
    ap.add_argument("--plan-epochs", type=int, default=2)
    ap.add_argument("--plan-buffer", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=0, help="processes that play the games (0: one process)")
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(a.seed)
    net = new_net(a.preset).to(device)
    views.set_irreversible(net.cfg.irreversible)
    size = sum(p.numel() for p in net.parameters()) / 1e6
    search = MCTSConfig(simulations=a.simulations, worlds=a.worlds, leaves=a.leaves, branch=a.branch) if a.search == "mcts" else SearchConfig()
    s = iterate.Settings(
        models=Path("."), selfplay_games=a.games, workers=a.workers, epochs=a.epochs, batch=a.batch, seed=a.seed, search=search, bot_share=0.25
    )
    print(f"{a.preset} network, {size:.1f}M parameters, on {device}; search: {a.search} {vars(search) if a.search == 'mcts' else ''}", flush=True)

    t0 = time.time()
    out = iterate.self_play_data(net, 1, s, iterate.net_brain)
    assert out is not None
    data, info = out
    play = time.time() - t0
    per_game = play / a.games
    per_search = play / max(1, info["searches"])
    choices, positions = len(data.policy), len(data.value)
    print(
        f"self-play: {a.games} games in {play:.0f}s = {per_game:.0f}s a game, {info['searches']} searches ({per_search:.2f}s each), "
        f"{info['steps'] / a.games:.0f} steps a game; {choices / a.games:.0f} policy examples and {positions / a.games:.0f} value positions a game",
        flush=True,
    )

    net.train()
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4, weight_decay=0.01)
    t1 = time.time()
    epochs = iterate.train_on(net, opt, data, s, device, np.random.default_rng(1))
    train = (time.time() - t1) / a.epochs
    per_example = train / max(1, choices + positions)
    print(
        f"training: {train:.1f}s for one pass over {choices} + {positions} examples = {per_example * 1000:.2f} ms an example; last epoch {epochs[-1]}",
        flush=True,
    )

    mix = (choices + positions) / a.games  # examples of one game
    kept = a.plan_buffer * a.plan_games * mix  # examples in the buffer at the steady state
    pass_s = per_example * kept
    iteration = a.plan_games * per_game + a.plan_epochs * pass_s
    print(
        f"plan: {a.plan_games} games a iteration, {a.plan_epochs} epochs over the last {a.plan_buffer} iterations ({kept:.0f} examples): "
        f"self-play {a.plan_games * per_game / 60:.0f} min + training {a.plan_epochs * pass_s / 60:.0f} min = about {iteration / 60:.0f} min an iteration "
        f"(without the evaluation and the gate)",
        flush=True,
    )


if __name__ == "__main__":
    main()
