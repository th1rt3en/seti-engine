"""Make a sample game view for the design preview page (apps/web/src/app/demo).

Plays a random 3-player game for a while with the engine and writes what player 0 would see. Run from services/engine:
    python -m uv run python ../../tools/web/make_sample_view.py
"""

import json
import pathlib
import random

from seti_engine.engine import apply, start
from seti_engine.models import Options
from seti_engine.projection import project

OUT = pathlib.Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "generated" / "sample-view.json"
STEPS = 420
WEIGHT = {
    "launch": 8, "orbit": 8, "land": 8, "scan": 6, "research": 5, "play_card": 6, "move_probe": 4, "place_data": 3, "analyze": 3, "pass": 0.15,
}  # fmt: skip



def richness(state) -> int:  # type: ignore[no-untyped-def]
    """How much there is to see: points, discovered species, probes, orbiters and landers."""
    planets = sum(len(p.orbiters) + len(p.landers) for p in state.planets.values())
    return sum(p.score for p in state.players) + 40 * sum(sp.discovered for sp in state.species) + 3 * len(state.probes) + 4 * planets


def main() -> None:
    best = None
    best_score = -1
    for seed in range(1, 7):
        rnd = random.Random(seed)
        r = start(Options(players=3, seed=seed))
        for _ in range(STEPS):
            if not r.legal or r.state.phase == "finished":
                break
            r = apply(r.state, rnd.choices(r.legal, weights=[WEIGHT.get(m["type"], 1) for m in r.legal])[0])
            s = r.state
            if s.phase == "play" and 2 <= s.round <= 4 and s.current_player == 0 and not s.pending and r.legal:
                score = richness(s)
                if score > best_score:
                    best, best_score = s, score
    assert best is not None
    view = project(best, 0)
    OUT.write_text(json.dumps(view.model_dump(mode="json"), separators=(",", ":")), encoding="utf-8")
    s = best
    print(
        f"round {s.round}, turn {s.turn}, {len(s.probes)} probes, scores {[p.score for p in s.players]}, "
        f"species discovered {[x.discovered for x in s.species]} -> {OUT.name} ({OUT.stat().st_size // 1000} KB)"
    )


if __name__ == "__main__":
    main()
