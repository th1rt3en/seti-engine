"""Assemble the transcriptions of the Space Agencies pictures (made from the owner-supplied sheets, D35) into one reviewable file:
docs/spec/data/expansion-transcription.json. Each item has a key, a group, a title, the picture keys of apps/web/src/generated/expansion-assets.json,
the transcribed fields and the list of what the transcriber was unsure about. The file is checked by the owner (the verification page).

Usage: python tools/spec/assemble_transcription.py <folder with the transcript JSON files>
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "spec" / "data" / "expansion-transcription.json"
CARD_ID_FIXES = {"main-03.png": "9", "main-06.png": "18"}  # numbers that the transcriber could not read, deduced from the gaps 1 to 42


def fmt(v: object) -> str:
    if isinstance(v, list):
        return "\n".join(fmt(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {fmt(x)}" for k, x in v.items())
    return "" if v is None else str(v)


def fields(d: dict, skip: set[str]) -> list[list[str]]:
    return [[k, fmt(v)] for k, v in d.items() if k not in skip and v not in (None, "", [], {})]


def main(src: pathlib.Path) -> None:
    def load(name: str):  # noqa: ANN202
        newer = src / "v2" / name  # the second reading, made with the owner's icon glossary, replaces the first
        return json.loads((newer if newer.exists() else src / name).read_text(encoding="utf-8"))

    items: list[dict] = []

    def add(key: str, group: str, title: str, pics: list[str], d: dict, skip: set[str] | None = None) -> None:
        items.append(
            {
                "key": key,
                "group": group,
                "title": title,
                "pics": pics,
                "fields": fields(d, (skip or set()) | {"file", "files", "uncertain", "name"}),
                "uncertain": d.get("uncertain", []) if isinstance(d.get("uncertain"), list) else [d.get("uncertain")],
            }
        )

    for name in ("main.json",) if (src / "v2" / "main.json").exists() else ("main-a.json", "main-b1.json", "main-b2.json"):
        for c in json.loads(((src / "v2" / name) if (src / "v2" / name).exists() else (src / name)).read_text(encoding="utf-8")):
            stem = c["file"].rsplit(".", 1)[0]
            if c["file"] in CARD_ID_FIXES:
                c["id"] = CARD_ID_FIXES[c["file"]]
            promo = str(c["id"]).startswith("SE ")
            add(stem, "Main deck (promo cards)" if promo else "Main deck", f"{c['id']} {c['name']}", [stem], c)
    q = load("quickstart.json")
    for c in q["cards"]:
        stem = c["file"].rsplit(".", 1)[0]
        add(stem, "Quick start cards", f"{c['id']}" + (f" {c['name']}" if c.get("name") else ""), [stem], c)
    for o in load("organizations.json")["organizations"]:
        n = int(o["file"].rsplit("-", 1)[1].split(".")[0])
        add(f"org-{n:02d}", "Organizations", f"{o.get('number', '')} {o['name']}", [f"org-{n:02d}"], o)
    sp = load("species-cards.json")
    for g, label in (("glyphids", "Glyphids cards"), ("amoeba", "Amoeba cards")):
        for c in sp[g]:
            stem = c["file"].rsplit(".", 1)[0]
            add(stem, label, f"{c['id']} {c.get('name') or ''}".strip(), [stem], c)
    a = load("arkhos-rival-objectives.json")
    for i, c in enumerate(a["exploration"]):
        add(f"exp-{i:02d}", "Arkhos exploration cards", f"{c.get('id', i)}", [f"exp-{i:02d}"], c)
    for i, c in enumerate(a["security"]):
        add(f"sec{i // 4 + 1}-{i % 4:02d}", "Arkhos security cards", f"{c.get('id', i)} {c.get('name') or ''}".strip(), [f"sec{i // 4 + 1}-{i % 4:02d}"], c)
    for i, c in enumerate(a["rival"]):
        add(f"rival-{i:02d}", "Rival action cards", f"{c.get('id', i)}", [f"rival-{i:02d}"], c)
    for i, c in enumerate(a["objectives"]):
        add(f"objectives/long-term-{i + 1}", "Long-term objectives", f"Long-term objective {i + 1}", [f"objectives/long-term-{i + 1}"], c)
    b = load("boards-tokens.json")
    for key, pic, title in (
        ("arkhos", "boards/arkhos", "Arkhos board"),
        ("glyphids", "boards/glyphids", "Glyphids board"),
        ("amoeba", "boards/amoeba", "Amoeba board"),
    ):
        add(f"board-{key}", "Species boards", title, [pic], b[key])
    add("board-translation", "Species boards", "Glyphids translation board", [f"boards/glyphids-track-{v}" for v in "abc"], b["glyphids_translation"])
    gt = b["glyph_tokens"]
    for t in gt.get("tokens", []):
        stem = t["file"].rsplit(".", 1)[0]
        add(f"tokens/{stem}", "Tokens and tiles", f"Glyph token {t.get('color', '')}", [f"tokens/{stem}"], t)
    for t in b["organelle_tokens"].get("tokens", []):
        stem = t["file"].rsplit(".", 1)[0]
        add(f"tokens/{stem}", "Tokens and tiles", f"Organelle token {t.get('id', '')}".strip(), [f"tokens/{stem}"], t)
    for t in b["xenolab_tiles"]:
        add(f"tokens/xenolab-tile-{t['id']}", "Tokens and tiles", f"Xenolab tile {t['id']}", [f"tokens/xenolab-tile-{t['id']}", f"tokens/xenolab-tile-{t['id']}-back"], t)
    add("tokens/token-futurespan", "Tokens and tiles", "Futurespan token", ["tokens/token-futurespan"], b["futurespan_token"])
    add("tokens/token-signal", "Tokens and tiles", "Signal token", ["tokens/token-signal"], b["signal_token"])
    notes = {"glyph_tokens": {k: v for k, v in gt.items() if k != "tokens"}, "organelle_tokens": {k: v for k, v in b["organelle_tokens"].items() if k != "tokens"}}
    OUT.write_text(json.dumps({"items": items, "notes": notes, "organization_notes": load("organizations.json")["notes"], "quickstart_notes": q["notes"], "quickstart_diff": q["diff_vs_existing"]}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(items), "items")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
