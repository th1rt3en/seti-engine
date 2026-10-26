"""Self-play and gate games in several processes. The search is Python on the CPU (the engine and the encoding of the views take most of its time, the network
call a small part), so one process uses one core of twelve.

    workers = Workers(6, "net.pt", champion_path="champion.pt")
    for index, game in workers.play(jobs): ...        # `jobs`: (seed, SelfPlayConfig, kind) for each game, the results as they finish
    workers.close()

The workers (`pworker.py`) never import torch: one more process (`evalserver.py`) holds the networks and answers the positions of all of them in
batches. A process with torch and CUDA holds about 3 GB, which is what made six workers fill the memory of this PC; a worker without them is small.
They talk over local connections with a random key, and are started as plain Python processes (not by `multiprocessing`, which would import this module
again, and torch with it, in every worker). A game is a pure function of its seed, so the result does not depend on the worker that plays it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from multiprocessing.connection import Client, Listener, wait
from typing import Any

from . import selfplay
from .bundle_search import SearchConfig

BELOW_NORMAL = 0x00004000  # the Windows priority class: the programs that the person is using go first, the workers get what is left


def low_priority() -> int:
    """`creationflags` for a process that should not get in the way of the person using the PC (Windows; nothing elsewhere)."""
    return BELOW_NORMAL if sys.platform == "win32" else 0


class Workers:
    def __init__(self, n: int, net_path: str, champion_path: str | None = None, device: str = "cuda") -> None:
        key = os.urandom(16)
        env = {**os.environ, "SETI_KEY": key.hex(), "PYTHONUNBUFFERED": "1"}
        self.server: subprocess.Popen[str] = subprocess.Popen(
            [sys.executable, "-m", "seti_ai.evalserver", "--clients", str(n + 1), "--device", device],
            env=env,
            stdout=subprocess.PIPE,
            text=True,
            creationflags=low_priority(),
        )
        assert self.server.stdout is not None
        first = self.server.stdout.readline().strip()
        if not first.startswith("PORT "):
            raise RuntimeError(f"the evaluation server did not start: {first!r}")
        port = int(first.split()[1])
        self.listener = Listener(("127.0.0.1", 0), authkey=key)
        jobs_port = self.listener.address[1]
        self.procs: list[subprocess.Popen[bytes]] = [
            subprocess.Popen(
                [sys.executable, "-m", "seti_ai.pworker", "--server", str(port), "--jobs", str(jobs_port), "--index", str(i)],
                env=env,
                creationflags=low_priority(),
            )
            for i in range(n)
        ]
        self.ev = Client(("127.0.0.1", port), authkey=key)
        irreversible = True
        for name, path in (("main", net_path), ("champion", champion_path or net_path)):
            self.ev.send(("load", name, path))
            reply = self.ev.recv()
            if reply[0] != "loaded":
                raise RuntimeError(f"the evaluation server could not load {path}: {reply[1]}")
            if name == "main":
                irreversible = bool(reply[2].get("irreversible", True))
        self.conns: list[Any] = [self.listener.accept() for _ in range(n)]
        for c in self.conns:
            c.send(("init", irreversible))

    def _run(self, make: Any, jobs: list[Any]) -> Iterator[tuple[int, Any]]:
        """The results as they finish, with the index of the job; a worker takes the next job as soon as it is free."""
        todo = list(range(len(jobs)))
        busy: dict[Any, int] = {}
        idle = list(self.conns)
        while todo or busy:
            while todo and idle:
                i = todo.pop(0)
                c = idle.pop()
                c.send(make(i, jobs[i]))
                busy[c] = i
            ready: list[Any] = list(wait(list(busy)))
            for c in ready:
                msg = c.recv()
                i = busy.pop(c)
                idle.append(c)
                if msg[0] == "error":
                    raise RuntimeError(f"a worker failed in job {i}: {msg[2]}")
                yield i, msg[2]

    def play(self, jobs: list[tuple[int, selfplay.SelfPlayConfig, int]]) -> Iterator[tuple[int, selfplay.SelfPlayGame]]:
        return self._run(lambda i, j: ("play", i, j[0], j[1], j[2]), jobs)

    def duel(self, jobs: list[tuple[int, int, SearchConfig]]) -> Iterator[tuple[int, tuple[int, int]]]:
        """The network against the champion, both with the search: the scores (the network's, the champion's) with the network in the given seat."""
        return self._run(lambda i, j: ("duel", i, j[0], j[1], j[2]), jobs)

    def close(self) -> None:
        for c in self.conns:
            try:
                c.send(None)
            except (OSError, ValueError):
                pass
        try:
            self.ev.send(("stop",))
        except (OSError, ValueError):
            pass
        everyone: list[Any] = [*self.procs, self.server]
        for p in everyone:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        self.listener.close()
