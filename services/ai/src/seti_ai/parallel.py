"""Self-play and gate games in several processes. The search is Python on the CPU (the engine and the encoding of the views take most of its time, the network
call a small part), so one process uses one core of twelve; each worker here has its own copy of the network (on the GPU) and plays whole games.

    workers = Workers(4, "net.pt", champion_path="champion.pt")
    for game in workers.play(jobs): ...        # `jobs`: (seed, SelfPlayConfig, kind) for each game, the results as they finish
    workers.close()

A worker is started with the path of the weights (not the weights themselves), so a new `Workers` for each iteration is cheap; a game is a pure function of its
seed, so the result does not depend on the worker that plays it.
"""

from __future__ import annotations

import copy
import multiprocessing
import random
from collections.abc import Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from typing import Any

import torch

from . import arena, selfplay, views
from .agent import LocalNet, net_from
from .bundle_search import BundleBot, SearchConfig
from .mcts import make_search

_W: dict[str, Any] = {}


def _init(net_path: str, champion_path: str | None, device: str) -> None:
    torch.set_num_threads(1)
    dev = torch.device(device)
    net = net_from(net_path, dev).eval()
    _W["net"] = net
    _W["brain"] = selfplay.make_brain(LocalNet(net))
    if champion_path:
        champ = net_from(champion_path, dev).eval()
        _W["champion"] = selfplay.make_brain(LocalNet(champ))
    views.set_irreversible(net.cfg.irreversible)


def _play(job: tuple[int, selfplay.SelfPlayConfig, int]) -> selfplay.SelfPlayGame:
    seed, cfg, kind = job
    return selfplay.play(_W["brain"], seed, cfg, kind=kind)


def _duel(job: tuple[int, int, SearchConfig]) -> tuple[int, int]:
    """The network against the champion, both with the search: (the network's score, the champion's), the network in `seat`."""
    seed, seat, cfg = job
    a = BundleBot(_W["brain"], copy.copy(cfg), make_search(_W["brain"], cfg))
    b = BundleBot(_W["champion"], copy.copy(cfg), make_search(_W["champion"], cfg))
    res = arena.play_game([a, b] if seat == 0 else [b, a], seed, random.Random(seed))
    return int(res.scores[seat]), int(res.scores[1 - seat])


class Workers:
    def __init__(self, n: int, net_path: str, champion_path: str | None = None, device: str = "cuda") -> None:
        self.pool = ProcessPoolExecutor(n, mp_context=multiprocessing.get_context("spawn"), initializer=_init, initargs=(net_path, champion_path, device))

    def _run(self, fn: Any, jobs: list[Any]) -> Iterator[tuple[int, Any]]:
        """The results as they finish, with the index of the job."""
        pending: dict[Future[Any], int] = {self.pool.submit(fn, j): i for i, j in enumerate(jobs)}
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for f in done:
                yield pending.pop(f), f.result()

    def play(self, jobs: list[tuple[int, selfplay.SelfPlayConfig, int]]) -> Iterator[tuple[int, selfplay.SelfPlayGame]]:
        return self._run(_play, jobs)

    def duel(self, jobs: list[tuple[int, int, SearchConfig]]) -> Iterator[tuple[int, tuple[int, int]]]:
        return self._run(_duel, jobs)

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
