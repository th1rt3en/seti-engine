"""What does the value of a network say about each resource? (owner, 2026-10-24)

The network is never told what a resource is worth: it has to learn it from the points the seats really gained to the end of the games. This probe checks
whether it did. It takes turn starts of the games of people, changes one thing of the seat to move (+1 credit, +1 energy, +1 publicity, +1 data in the pool, a
card more in the hand, +1 point for comparison) and asks the value head for the position again. The answer is in points of the final score: the points that
the seat has plus the value, which is the points it still expects to gain. Nothing here changes the network or the games; it only reads them.

    python -m uv run python -m seti_ai.probe --models models_v3 --people archive_new --positions 60
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Callable
from pathlib import Path

import torch
from seti_engine.models import GameState

from . import checkpoint, expert
from .agent import LocalNet
from .selfplay import make_brain


def _more(field: str, n: int = 1) -> Callable[[GameState, int], bool]:
    def change(s: GameState, seat: int) -> bool:
        p = s.players[seat]
        setattr(p, field, getattr(p, field) + n)
        return True

    return change


def _card(s: GameState, seat: int) -> bool:
    if not s.deck:
        return False
    s.players[seat].hand.append(s.deck.pop())  # the top card of the deck, so that the hand has one card more
    return True


CHANGES: dict[str, Callable[[GameState, int], bool]] = {
    "+1 point (to compare)": _more("score"),
    "+1 credit": _more("credits"),
    "+1 energy": _more("energy"),
    "+1 publicity": _more("publicity"),
    "+1 data in the pool": _more("data_pool"),
    "+1 card in the hand": _card,
    "+3 credits": _more("credits", 3),
    "+3 energy": _more("energy", 3),
    "-1 credit": _more("credits", -1),
    "-1 energy": _more("energy", -1),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", type=Path, required=True, help="the folder of the run (its checkpoint)")
    ap.add_argument("--people", type=Path, required=True, help="the folder of the games of people")
    ap.add_argument("--positions", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--solo", action="store_true")
    args = ap.parse_args()
    net, _, meta, _ = checkpoint.load(args.models, torch.device("cpu"))  # the run may be using the GPU: this is small
    brain = make_brain(LocalNet(net))
    found, stats = expert.sample_positions(args.people, args.positions, args.seed, args.solo)
    print(f"network of round {meta.get('iteration')}; {len(found)} positions ({stats})", flush=True)
    deltas: dict[str, list[float]] = {name: [] for name in CHANGES}
    for pos in found:
        base = pos.state.players[pos.seat].score + brain.value(pos.state, pos.seat, pos.history, pos.knowledge)
        for name, change in CHANGES.items():
            s = pos.state.model_copy(deep=True)
            if not change(s, pos.seat):
                continue
            total = s.players[pos.seat].score + brain.value(s, pos.seat, pos.history, pos.knowledge)
            deltas[name].append(total - base)
    print(f"{'change':24} {'mean':>8} {'sd':>7} {'up':>5} {'down':>5} {'n':>4}   (the change in the expected final score, in points)")
    for name, d in deltas.items():
        if not d:
            continue
        sd = statistics.pstdev(d) if len(d) > 1 else 0.0
        print(f"{name:24} {statistics.fmean(d):8.2f} {sd:7.2f} {sum(x > 0 for x in d):5d} {sum(x < 0 for x in d):5d} {len(d):4d}")


if __name__ == "__main__":
    main()
