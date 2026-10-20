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


# the kinds of step of a card effect that mark a signal, a trace, land a probe or scan (for the filters of the card page)
SIGNAL_STEPS = {
    "signal_color", "sig_star", "sig_probe", "sig_planet", "sig_any", "sig_earth", "sig_each_color", "sig_twice", "sig_in_rich_sector",
    "sig_each_marked", "sig_next_anomaly", "hand_signals", "deck_signals", "row_scan", "signal_oumuamua", "probes_sig",
}  # fmt: skip
TECH_COLORS = {"probe": "orange", "telescope": "pink", "computer": "blue"}  # BOARD-50


def effect_tags(steps: list[dict]) -> set[str]:
    """What the effect of a card does, by the kind of its steps (the steps inside an "if" or an "optional" count too)."""
    tags: set[str] = set()
    for st in steps:
        t = st.get("t")
        if t == "launch":
            tags.add("launch")
        elif t in ("land_free", "orbit_land_free"):
            tags.add("land")
        elif t in ("scan_free", "row_scan"):
            tags.add("scan")
        elif t in ("trace", "trace_same", "trace_vp"):
            tags.add("trace")
        elif t == "move":
            tags.add("move")
        elif t == "research":
            tags.add("tech")
            cat = st.get("cat")
            for c in ("probe", "telescope", "computer") if cat == "any" else str(cat).split("_"):
                if c in TECH_COLORS:
                    tags.add(f"tech_{TECH_COLORS[c]}")
        if t in SIGNAL_STEPS:
            tags.add("signal")
        for key in ("then", "r"):
            if isinstance(st.get(key), list):
                tags |= effect_tags([x for x in st[key] if isinstance(x, dict)])
    return tags


def card_catalog() -> list[dict]:
    """Every card of the main deck, the alien decks and the expansion, with what the card page filters on."""
    from seti_engine import card_defs

    out = []
    for cid, c in tables.cards().items():
        d = card_defs.CARDS.get(cid)
        mission = (d or {}).get("mission")
        kind = "quick" if mission and mission["kind"] == "quick" else "mission" if mission else "end" if d and "end" in d else "none"
        out.append(
            {
                "id": cid,
                "name": c["name"],
                "deck": c["deck"],
                "species": c["species"],
                "income": c["income"],
                "sector": c["sector"],
                "cost": c["cost"],
                "free": sorted({str(f[0]).split(":")[0] for f in c["free"]}),
                "type": kind,
                "tags": sorted(effect_tags((d or {}).get("fx", []))),
                "known": d is not None,
            }
        )
    return out


QUICK_PICTURES = {
    "SR.1": "qs-06", "SR.2": "qs-07", "SR.3": "qs-10", "SR.4": "qs-11", "SR.5": "qs-05", "SR.6": "qs-09", "SR.7": "qs-16",
    "SR.8": "qs-15", "SR.9": "qs-04", "SR.10": "qs-03", "SR.11": "qs-08", "SR.12": "qs-17", "SR.13": "qs-12", "SR.14": "qs-14",
    "SR.15": "qs-18", "SR.16": "qs-19", "SR.17": "qs-13", "SR.18": "qs-01", "SR.19": "qs-00", "SR.20": "qs-20", "SR.21": "qs-02",
}  # the picture of each quick start card (the Q.n of the picture is not the id SR.n)


def card_places() -> dict[str, dict[str, list[str]]]:
    """The places that the effects and the missions of a card name (for the highlight when a card is hovered): `planets` are planets to orbit or land on
    (the planet board), `visits` are planets to move a probe onto (the space of the solar system, where the planet lies now), `colors` are sector colors.
    A card that names none is left out."""
    from seti_engine import card_defs

    def add_planet(out: dict[str, set[str]], v: object, kind: str) -> None:
        for pl in v if isinstance(v, list) else [v]:
            if isinstance(pl, str) and pl not in ("*", "any", ""):
                out[kind].add(pl.lower())

    def walk(x: object, out: dict[str, set[str]]) -> None:
        if isinstance(x, dict):
            is_visit = x.get("k") == "visit" or x.get("e") == "visit"  # a visit is a move onto the planet's space (FAQ-18)
            for k, v in x.items():
                if k in ("planet", "planets"):
                    add_planet(out, v, "visits" if is_visit else "planets")
                elif k == "color" and isinstance(v, str) and v in ("red", "yellow", "blue", "black"):
                    out["colors"].add(v)
                walk(v, out)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v, out)

    res: dict[str, dict[str, list[str]]] = {}
    for cid, d in card_defs.CARDS.items():
        out: dict[str, set[str]] = {"planets": set(), "visits": set(), "colors": set()}
        walk(d, out)
        if out["planets"] or out["visits"] or out["colors"]:
            res[cid] = {k: sorted(v) for k, v in out.items()}
    return res


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cards = {cid: {k: c[k] for k in ("name", "cost", "income", "sector", "species", "deck", "free")} for cid, c in tables.cards().items()}
    (OUT / "cards.json").write_text(json.dumps(cards, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "card-catalog.json").write_text(json.dumps(card_catalog(), indent=0, sort_keys=True) + "\n", encoding="utf-8")
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
        elif it["group"] == "Main deck (promo cards)" and first == "SE":
            images["_".join(it["title"].split(" ")[:3])] = it["key"]  # SE_EN_03, SE_DE_04
        elif it["group"] == "Glyphids cards":
            images[f"GL.{first.split('.')[1]}"] = it["key"]
        elif it["group"] == "Amoeba cards":
            images[f"AM.{first.split('.')[1]}"] = it["key"]
        elif it["group"] == "Arkhos exploration cards":
            images[it["title"]] = it["key"]  # the ids of the engine are the printed names, "ET 33"
        elif it["group"] == "Arkhos security cards":
            images[f"AK.{first.split('.')[1]}"] = it["key"]
    # organizations: the picture is named after the number printed on the card (the title of the transcription starts with it)
    by_number = {int(it["title"].split(" ", 1)[0]): it["key"] for it in tr["items"] if it["key"].startswith("org-")}
    for oid, o in tables.organizations().items():
        images[oid] = by_number[o["number"]]
    # quick start cards: the pictures carry their own numbers (Q.n), the engine ids (SR.n) are in another order; matched by what they show
    images.update(QUICK_PICTURES)
    (OUT / "expansion-card-images.json").write_text(json.dumps(images, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "card-places.json").write_text(json.dumps(card_places(), indent=0, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "move-types.json").write_text(json.dumps(move_types(), indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT)
