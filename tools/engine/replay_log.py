"""Rebuild and print a game from its archive (docs/PLAN.md decision D25).

    python tools/engine/replay_log.py path/to/replay.json          # a downloaded replay.json
    python tools/engine/replay_log.py path/to/games/<id>/          # a downloaded folder: header.json, actions/*.json, result.json

Download a game from the bucket first, for example:  gcloud storage cp -r gs://BUCKET/games/<id> .
The tool replays the game with the engine, checks every recorded event against the engine's, and prints one line per action and event.
Run it from services/engine with `python -m uv run python ../../tools/engine/replay_log.py ...` (it needs the engine package).
"""

import json
import sys
from pathlib import Path

from seti_engine import replay


def load(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    actions = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((path / "actions").glob("*.json"))]
    result = path / "result.json"
    return {
        "format": replay.FORMAT,
        "header": json.loads((path / "header.json").read_text(encoding="utf-8")),
        "actions": actions,
        "result": json.loads(result.read_text(encoding="utf-8")) if result.exists() else None,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    file = load(Path(argv[1]))
    # the archives written before the random state became a string were played with a rounded state (replay.steps): their header has no `rngEncoding`
    file["header"].setdefault("rngEncoding", "double")
    names = {s["seat"]: s["name"] for s in file["header"].get("seats", [])}
    for n, entry, result in replay.steps(file):
        if entry is None:
            print("0  start of the game")
            continue
        print(f"{n}  {names.get(entry['seat'], entry['seat'])}: {json.dumps(entry['action'])}")
        for e in result.events:
            print(f"     - {json.dumps(e)}")
    last = replay.verify(file)
    res = file.get("result")
    print("\nverified:", len(file["actions"]), "actions; phase", last.state.phase, "; recorded end:", res["result"]["reason"] if res else "none (not ended)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
