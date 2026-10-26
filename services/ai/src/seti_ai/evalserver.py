"""The one process that holds the networks for a run of games in many processes (parallel.py): the workers send the positions they want scored, the server
collects what is waiting from all of them, runs it on the GPU in batches and sends each worker its answers.

Why: a process that imports torch and starts CUDA holds about 3 GB, so six workers with their own copy of the network filled the memory of a 32 GB PC
(docs/AI-BETA-PLAN.md). The workers of `pworker.py` never import torch (the search is Python and numpy on the CPU); this process is the only one with the
GPU libraries besides the trainer.

    python -m seti_ai.evalserver --clients N --device cuda      (started by parallel.Workers; the key is in the environment variable SETI_KEY)

It prints `PORT <n>` when it listens, accepts N connections, and answers: ("load", name, path) with ("loaded", name, config) and ("many", name, items) with the
list of (scores of the moves, value) of the items; ("stop",) ends it. The numbers are those of `LocalNet.evaluate_many` (float32), whoever asks.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from multiprocessing.connection import Listener, wait
from typing import Any

import torch

from .agent import LocalNet, net_from

REPLY_AFTER = 0.002  # seconds to wait for more requests when some are waiting


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, required=True)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    torch.set_num_threads(2)
    device = torch.device(a.device)
    key = bytes.fromhex(os.environ["SETI_KEY"])
    listener = Listener(("127.0.0.1", 0), authkey=key)
    print(f"PORT {listener.address[1]}", flush=True)
    conns: list[Any] = [listener.accept() for _ in range(a.clients)]
    nets: dict[str, LocalNet] = {}
    while True:
        ready: list[Any] = list(wait(conns))
        waiting: list[tuple[Any, str, list[Any]]] = []
        while ready:  # the requests that are there, then those that come in the next moments (a worker sends one request and waits for its answer)
            for c in ready:
                try:
                    msg = c.recv()
                except (EOFError, OSError):
                    conns.remove(c)
                    continue
                try:
                    if msg[0] == "stop":
                        return
                    if msg[0] == "load":
                        net = net_from(msg[2], device).eval()
                        nets[msg[1]] = LocalNet(net)
                        c.send(("loaded", msg[1], dict(net.cfg.__dict__)))
                    elif msg[0] == "many":
                        waiting.append((c, msg[1], msg[2]))
                except Exception:  # a bad request is answered, not fatal
                    c.send(("error", traceback.format_exc()))
            ready = list(wait(conns, timeout=REPLY_AFTER)) if conns else []
        by_name: dict[str, list[tuple[Any, list[Any]]]] = {}
        for c, name, items in waiting:
            by_name.setdefault(name, []).append((c, items))
        for name, group in by_name.items():
            flat = [it for _, items in group for it in items]
            try:
                answers = nets[name].evaluate_many(flat)
            except Exception:
                for c, _ in group:
                    c.send(("error", traceback.format_exc()))
                continue
            at = 0
            for c, items in group:
                c.send(("answers", answers[at : at + len(items)]))
                at += len(items)
        if not conns:
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
