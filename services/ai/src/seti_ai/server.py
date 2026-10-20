"""The inference server of training: the games are played by worker processes on the CPU cores, the network runs on the GPU in one process that serves them all.

A worker sends the tokens and the legal moves of a position and waits for the scores of the moves and the value; the server collects the requests that
are waiting (up to `MAX_BATCH`, or after a short wait), runs them as one batch and answers each. The weights are loaded by a message from the trainer, so
that every game of an iteration is played with the same network.
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
    """The loop of the server process: `("load", path)` puts a network in, `("stop",)` ends; any other message is a request (worker, tokens, toks, nums)."""
    torch.set_num_threads(2)
    device = torch.device(device_name)
    net = None
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
                net = net_from(msg[1], device).eval()
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
        if not batch or net is None:
            continue
        with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=use_amp):
            b = collate([(m[2], m[3], m[4]) for m in batch], device)
            logits, values = net(b)
        logits_np = logits.float().cpu().numpy()
        values_np = values.float().cpu().numpy()
        for i, m in enumerate(batch):
            resp_qs[m[1]].put((logits_np[i, : m[3].shape[0]].copy(), float(values_np[i])))


class Client:
    """What a worker holds: it asks the server for the scores of a position. It has the same `evaluate` as a local network."""

    def __init__(self, worker: int, req_q: Any, resp_q: Any) -> None:
        self.worker, self.req_q, self.resp_q = worker, req_q, resp_q

    def evaluate(self, tokens: features.Tokens, toks: NDArray[np.int32], nums: NDArray[np.float32]) -> tuple[NDArray[np.float32], float]:
        self.req_q.put(("eval", self.worker, tokens, toks, nums))
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
