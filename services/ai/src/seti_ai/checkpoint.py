"""Pause and resume of a training run, at any time.

Everything that is needed to go on is saved at the end of every round: the network and the optimizer, the round number, the best score so far, the settings
of the run and the random generators. A file `PAUSE` in the models folder (made by `python -m seti_ai.train pause`) or Ctrl+C asks the run to stop: it finishes
the small batch of games that is being played (a few seconds), does not save a half round (the checkpoint of the last full round is the state to go on from)
and exits, so that the processor, the graphics card and the memory are free at once. `--resume` goes on from the checkpoint. If the machine is switched off or
the process is killed, the same checkpoint is there: at most the round in progress is lost (about two minutes).

A checkpoint is written to a temporary file and moved into place, so a power cut cannot leave a half file.
"""

from __future__ import annotations

import os
import random
import signal
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .agent import NetConfig, PolicyNet

_STOP = {"requested": False}


def folder(root: Path) -> Path:
    return root / "checkpoint"


def path(root: Path) -> Path:
    return folder(root) / "latest.pt"


def exists(root: Path) -> bool:
    return path(root).exists()


def request_pause(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "PAUSE").write_text(time.strftime("%Y-%m-%dT%H:%M:%S") + "\n", encoding="utf-8")


def clear_pause(root: Path) -> None:
    (root / "PAUSE").unlink(missing_ok=True)
    _STOP["requested"] = False


def pause_requested(root: Path) -> bool:
    return _STOP["requested"] or (root / "PAUSE").exists()


def install_signal_handler() -> None:
    """Ctrl+C asks for a pause instead of ending the run in the middle of a round."""

    def handler(signum: int, frame: Any) -> None:
        _STOP["requested"] = True
        print("pause requested: finishing the games in progress ...", flush=True)

    signal.signal(signal.SIGINT, handler)
    if hasattr(signal, "SIGBREAK"):  # Ctrl+Break on Windows
        signal.signal(signal.SIGBREAK, handler)


def save(root: Path, net: PolicyNet, opt: torch.optim.Optimizer, meta: dict[str, Any]) -> None:
    folder(root).mkdir(parents=True, exist_ok=True)
    state = {
        "config": dict(net.cfg.__dict__),
        "net": {k: v.detach().cpu() for k, v in net.state_dict().items()},
        "opt": opt.state_dict(),
        "meta": meta,
        "rng": {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()},
    }
    tmp = path(root).with_suffix(".tmp")
    torch.save(state, tmp)
    os.replace(tmp, path(root))


def load(root: Path, device: torch.device) -> tuple[PolicyNet, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """The network, the optimizer state, the meta data and the random generators of the last checkpoint."""
    saved = torch.load(path(root), map_location="cpu", weights_only=False)
    net = PolicyNet(NetConfig(**saved["config"])).to(device)
    net.load_state_dict(saved["net"])
    return net, saved["opt"], saved["meta"], saved["rng"]


def restore_rng(rng: dict[str, Any]) -> None:
    random.setstate(rng["python"])
    np.random.set_state(rng["numpy"])
    torch.set_rng_state(rng["torch"])


def status(root: Path) -> str:
    if not exists(root):
        return "no checkpoint"
    saved = torch.load(path(root), map_location="cpu", weights_only=False)
    m = saved["meta"]
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(path(root).stat().st_mtime))
    text = (
        f"checkpoint of round {m['iteration']} ({stamp}), network {saved['config']['layers']} layers x {saved['config']['d_model']}, "
        f"best score against the heuristic bot {m.get('best')}"
    )
    return text + ("; a pause is requested" if (root / "PAUSE").exists() else "")
