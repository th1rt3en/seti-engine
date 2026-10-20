"""The inference server of training: the games are played by worker processes on the CPU cores, the networks run on the GPU in one process that serves
them all.

A worker sends the tokens and the legal moves of a position, and the name of the network that should answer, and waits for the scores of the moves and
the value; the server collects the requests that are waiting (up to `MAX_BATCH`, or after a short wait), runs them in batches (one for each network)
and answers each. The weights are loaded by a message from the trainer, so that every game of a round is played with the same network. Several
networks can be loaded at once under different names: the network that is trained ("main") and the frozen snapshots of the opponent pool (`pool.py`).
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import time
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray

from . import features
from .agent import collate, net_from

MAX_BATCH = 48
WAIT = 0.002  # seconds to wait for more requests when a batch is not full


def serve(req_q: Any, resp_qs: list[Any], ctl_q: Any, device_name: str) -> None:
    """The loop of the server process: `("load", name, path)` puts a network in, `("stop",)` ends; any other message is a request
    ("eval", worker, name, tokens, toks, nums)."""
    torch.set_num_threads(2)
    device = torch.device(device_name)
    nets: dict[str, Any] = {}
    use_amp = device.type == "cuda"
    while True:
        batch: list[Any] = []
        try:
            msg = req_q.get(timeout=1.0)
        except queue.Empty:
            continue
        deadline = time.time() + WAIT
        while True:
            if msg[0] == "load":
                nets[msg[1]] = net_from(msg[2], device).eval()
                ctl_q.put(("loaded", msg[1]))
            elif msg[0] == "stop":
                return
            else:
                batch.append(msg)
            if len(batch) >= MAX_BATCH:
                break
            try:
                msg = req_q.get(timeout=max(0.0, deadline - time.time()))
            except queue.Empty:
                break
        by_name: dict[str, list[Any]] = {}
        for m in batch:
            by_name.setdefault(m[2], []).append(m)
        for name, group in by_name.items():
            net = nets.get(name)
            if net is None:
                for m in group:
                    resp_qs[m[1]].put((np.zeros(m[4].shape[0], dtype=np.float32), 0.0))
                continue
            with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=use_amp):
                b = collate([(m[3], m[4], m[5]) for m in group], device)
                logits, values = net(b)
            logits_np = logits.float().cpu().numpy()
            values_np = values.float().cpu().numpy()
            for i, m in enumerate(group):
                resp_qs[m[1]].put((logits_np[i, : m[4].shape[0]].copy(), float(values_np[i])))


class Client:
    """What a worker holds: it asks the server for the scores of a position. `with_model` gives the same client for another network (a snapshot)."""

    def __init__(self, worker: int, req_q: Any, resp_q: Any, model: str = "main") -> None:
        self.worker, self.req_q, self.resp_q, self.model = worker, req_q, resp_q, model

    def with_model(self, name: str) -> Client:
        return Client(self.worker, self.req_q, self.resp_q, name)

    def evaluate(self, tokens: features.Tokens, toks: NDArray[np.int32], nums: NDArray[np.float32]) -> tuple[NDArray[np.float32], float]:
        self.req_q.put(("eval", self.worker, self.model, tokens, toks, nums))
        logits, value = self.resp_q.get()
        return logits, value


def start_server(workers: int, device_name: str) -> tuple[Any, Any, list[Any], Any, Any]:
    """Start the server process; returns (process, request queue, response queues, control queue, context)."""
    ctx = mp.get_context("spawn")
    req_q = ctx.Queue()
    resp_qs = [ctx.Queue() for _ in range(workers)]
    ctl_q = ctx.Queue()
    proc = ctx.Process(target=serve, args=(req_q, resp_qs, ctl_q, device_name), daemon=True)
    proc.start()
    return proc, req_q, resp_qs, ctl_q, ctx
