"""Generate the data files of the website from the engine: apps/web/src/generated/cards.json (names of the cards) and move-types.json
(every kind of move the engine offered in random games, so a test can check that each has a label).

Run from services/engine: python -m uv run python ../../tools/web/sync_data.py
"""

import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))
sys.path.insert(0, str(ROOT / "services" / "engine" / "tests"))

from seti_engine import tables  # noqa: E402
from seti_engine.engine import apply, start  # noqa: E402
from seti_engine.models import Options  # noqa: E402

OUT = ROOT / "apps" / "web" / "src" / "generated"
PROGRESS = {"play_card", "orbit", "land", "land_free", "analyze", "place_data", "scan", "research", "complete_mission", "cover", "deliver_sample"}


def move_types() -> dict[str, list[str]]:
    seen: dict[str, set[str]] = {}
    for players, difficulty in ((2, 3), (3, 3), (4, 3), (1, 3), (1, 5)):
        for seed in range(40):
            rnd = random.Random(seed)
            r = start(Options(players=players, seed=seed, difficulty=difficulty))
            for _ in range(20000):
                if not r.legal:
                    break
                good = [m for m in r.legal if m["type"] in PROGRESS or (m["type"] == "place_trace" and m["space"] != "overflow")]
                m = rnd.choice(good) if good and rnd.random() < 0.8 else rnd.choice(r.legal)
                seen.setdefault(m["type"], set()).update(m)
                r = apply(r.state, m)
    return {k: sorted(v - {"type"}) for k, v in sorted(seen.items())}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cards = {cid: {k: c[k] for k in ("name", "cost", "income", "sector", "species", "deck")} for cid, c in tables.cards().items()}
    (OUT / "cards.json").write_text(json.dumps(cards, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "move-types.json").write_text(json.dumps(move_types(), indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT)
