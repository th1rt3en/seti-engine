"""A worker of parallel.py: plays whole games for the main process and never imports torch (the networks are in `evalserver.py`, asked over a connection).

    python -m seti_ai.pworker --server PORT --jobs PORT --index I      (started by parallel.Workers; the key is in the environment variable SETI_KEY)

The main process sends ("init", irreversible) first, then jobs: ("play", id, seed, config, kind) and ("duel", id, seed, seat, config); a job is answered with
("done", id, result) or ("error", id, text); None ends the worker.
"""

from __future__ import annotations

import argparse
import copy
import os
import random
import traceback
from multiprocessing.connection import Client
from types import SimpleNamespace
from typing import Any

from . import arena, selfplay, views
from .bundle_search import BundleBot
from .mcts import make_search


class RemoteNet:
    """What `brains.NetBrain` needs from a network, answered by the evaluation server: `evaluate_many` (all the items in one message) and `evaluate`."""

    def __init__(self, conn: Any, name: str, irreversible: bool) -> None:
        self.conn, self.name = conn, name
        self.net = SimpleNamespace(cfg=SimpleNamespace(irreversible=irreversible))  # where NetBrain looks for the setting of the views

    def evaluate_many(self, items: list[Any], chunk: int = 0) -> list[Any]:
        self.conn.send(("many", self.name, items))
        reply = self.conn.recv()
        if reply[0] != "answers":
            raise RuntimeError(f"the evaluation server failed: {reply[1]}")
        return list(reply[1])

    def evaluate(self, tokens: Any, toks: Any, nums: Any) -> Any:
        return self.evaluate_many([(tokens, toks, nums)])[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", type=int, required=True)
    ap.add_argument("--jobs", type=int, required=True)
    ap.add_argument("--index", type=int, required=True)
    a = ap.parse_args()
    key = bytes.fromhex(os.environ["SETI_KEY"])
    ev = Client(("127.0.0.1", a.server), authkey=key)
    jobs = Client(("127.0.0.1", a.jobs), authkey=key)
    init = jobs.recv()
    irreversible = bool(init[1])
    views.set_irreversible(irreversible)
    brain = selfplay.make_brain(RemoteNet(ev, "main", irreversible))
    champion = selfplay.make_brain(RemoteNet(ev, "champion", irreversible))
    while True:
        msg = jobs.recv()
        if msg is None:
            break
        try:
            if msg[0] == "play":
                _, jid, seed, cfg, kind = msg
                jobs.send(("done", jid, selfplay.play(brain, seed, cfg, kind=kind)))
            else:
                _, jid, seed, seat, cfg = msg
                x = BundleBot(brain, copy.copy(cfg), make_search(brain, cfg))
                y = BundleBot(champion, copy.copy(cfg), make_search(champion, cfg))
                res = arena.play_game([x, y] if seat == 0 else [y, x], seed, random.Random(seed))
                jobs.send(("done", jid, (int(res.scores[seat]), int(res.scores[1 - seat]))))
        except Exception:
            jobs.send(("error", msg[1], traceback.format_exc()))


if __name__ == "__main__":
    main()
