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
    for players, difficulty, orgs in ((2, 3, False), (3, 3, False), (4, 3, False), (1, 3, False), (1, 5, False), (2, 3, True), (3, 3, True)):
        for seed in range(40):
            rnd = random.Random(seed)
            extra = {"expansion": True, "organizations": True} if orgs else {}
            r = start(Options(players=players, seed=seed, difficulty=difficulty, **extra))
            if orgs:  # the new species are found at once, so that their moves are played too
                from seti_engine import species

                state = r.state
                state.species[seed % 2].species = ("arkhos", "glyphids", "amoeba")[seed % 3]
                state.species[seed % 2].board = species.new_board(state.species[seed % 2].species)
                state.species[seed % 2].discovery_spaces = ["p0", "p1", "p0"]
                state.species[seed % 2].complete = True
                r = type(r)(state=state, events=r.events, legal=r.legal)
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
    cards = {cid: {k: c[k] for k in ("name", "cost", "income", "sector", "species", "deck", "free")} for cid, c in tables.cards().items()}
    (OUT / "cards.json").write_text(json.dumps(cards, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    orgs = {
        oid: {"name": o["name"], "number": o["number"], "abilities": o["abilities"], "resources": o["starting_resources"], "income": o["income"]}
        for oid, o in tables.organizations().items()
    }
    (OUT / "organizations.json").write_text(json.dumps(orgs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    quick = {qid: {"marks": q["place_text"], "lower": q["lower"]} for qid, q in tables.quick_start_cards().items()}
    (OUT / "quick-start.json").write_text(json.dumps(quick, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # which picture shows which expansion card (the keys of apps/web/src/generated/expansion-assets.json), from the verified transcription
    tr = json.loads((ROOT / "docs" / "spec" / "data" / "expansion-transcription.json").read_text(encoding="utf-8"))
    images: dict[str, str] = {}
    for it in tr["items"]:
        first = it["title"].split(" ", 1)[0]
        if it["group"] == "Main deck":
            images[f"SA.{first}"] = it["key"]
        elif it["group"] == "Glyphids cards":
            images[f"GL.{first.split('.')[1]}"] = it["key"]
        elif it["group"] == "Amoeba cards":
            images[f"AM.{first.split('.')[1]}"] = it["key"]
        elif it["group"] == "Arkhos security cards":
            images[f"AK.{first.split('.')[1]}"] = it["key"]
    (OUT / "expansion-card-images.json").write_text(json.dumps(images, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "move-types.json").write_text(json.dumps(move_types(), indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT)
