"""The versions of the model: a folder for each, with its weights and a manifest of what it is and how it did.

    models/v001/model.pt        the weights
    models/v001/manifest.json   the version, the date, the rules version (the engine's git commit), how it was trained, how it plays
    models/index.json           the list of the versions, newest last

The manifest is what the site shows about a version (the statistics of each version are public). Only the folder of a version that the owner has
approved is ever put on a server; training stays on this machine.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agent import PolicyNet, save_net
from .bots import BOT_VERSIONS


def rules_version() -> str:
    """The engine's rules version: for now the git commit of the repository (the rules change with it)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True, cwd=Path(__file__).parent)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def next_version(root: Path) -> str:
    n = 0
    for p in root.glob("v[0-9][0-9][0-9]"):
        n = max(n, int(p.name[1:]))
    return f"v{n + 1:03d}"


def save_version(root: Path, net: PolicyNet, parent: str | None, training: dict[str, Any], evaluation: dict[str, Any], start: str | None = None) -> str:
    version = next_version(root)
    folder = root / version
    folder.mkdir(parents=True, exist_ok=True)
    save_net(net, str(folder / "model.pt"))
    manifest = {
        "version": version,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rules_version": rules_version(),
        "parent": parent,
        "players": training.get("players", 2),
        "features": "v2: every entity of the view as a token (features.py)",
        "network": {"config": asdict(net.cfg), "parameters": sum(p.numel() for p in net.parameters())},
        "opponent_bots": BOT_VERSIONS,  # the evaluation numbers are against these versions of the training bots
        "training": training,
        "evaluation": evaluation,
        "approved": False,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    index = root / "index.json"
    versions = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    versions.append({"version": version, "created": manifest["created"], "evaluation": evaluation, "approved": False})
    index.write_text(json.dumps(versions, indent=1) + "\n", encoding="utf-8")
    return version
