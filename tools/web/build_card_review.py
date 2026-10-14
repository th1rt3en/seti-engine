"""Build the card review page: every card image next to the card as transcribed and the code the engine runs for it.

The owner reads it (as an artifact) to check the transcription against the printed cards (docs/PLAN.md decision D29 is not involved; this is
the owner's confirmation of the card data in CLAUDE.md "Open items"). Run from the repo root:
    python tools/web/build_card_review.py OUTPUT.html
It needs the engine package on the path (it adds services/engine/src itself) and the images from tools/web/build_assets.py.
"""

import base64
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from seti_engine import card_defs  # noqa: E402

ASSETS = ROOT / "apps" / "web" / "public"
CARD_IMAGES = json.loads((ROOT / "apps" / "web" / "src" / "generated" / "assets.json").read_text(encoding="utf-8"))["cards"]
DATA = {c["id"]: c for c in json.loads((ROOT / "docs" / "spec" / "data" / "card-definitions.json").read_text(encoding="utf-8"))}
VERIFIED = {r["id"]: r for r in json.loads((ROOT / "docs" / "spec" / "data" / "card-verification.json").read_text(encoding="utf-8"))["rows"]}

GROUPS = {
    "base": "Base deck",
    "alien-base": "Alien cards",
}


def crop(card_id: str) -> str:
    """The card's own image, as a data URI (the page is a single file)."""
    data = (ASSETS / CARD_IMAGES[card_id].lstrip("/")).read_bytes()
    return "data:image/webp;base64," + base64.b64encode(data).decode()


def code(defn: dict) -> str:
    """One line per key, and one line per step, so a card reads like its effect."""
    out = []
    for key, val in defn.items():
        if isinstance(val, list):
            out.append(f"{key}: [")
            out += [f"  {json.dumps(s, separators=(', ', ': '))}" for s in val]
            out.append("]")
        elif isinstance(val, dict) and "circles" in val:
            head = {k: v for k, v in val.items() if k != "circles"}
            out.append(f"{key}: {json.dumps(head, separators=(', ', ': '))} circles: [")
            out += [f"  {json.dumps(c, separators=(', ', ': '))}" for c in val["circles"]]
            out.append("]")
        else:
            out.append(f"{key}: {json.dumps(val, separators=(', ', ': '))}")
    return "\n".join(out)


def order(card_id: str) -> tuple[int, int, str]:
    if card_id.isdigit():
        return (0, int(card_id), "")
    prefix, _, n = card_id.partition(".")
    return (1, int(n) if n.isdigit() else 0, prefix)


cards = []
all_defs = {**card_defs.CARDS, **card_defs.ALIEN_CARDS}
for cid in sorted(all_defs, key=order):
    if cid not in CARD_IMAGES:
        print("no image for", cid, file=sys.stderr)
        continue
    d = DATA.get(cid, {})
    group = GROUPS.get(DATA.get(cid, {}).get("group", ""), "Other")
    cards.append(
        {
            "id": cid,
            "name": d.get("name") or VERIFIED.get(cid, {}).get("name", ""),
            "group": group,
            "cost": d.get("cost"),
            "costType": d.get("cost_type"),
            "income": d.get("income"),
            "sector": d.get("sector"),
            "free": d.get("free_action"),
            "text": d.get("repo_effects", []),
            "additions": d.get("owner_additions", []),
            "note": d.get("owner_note", ""),
            "unparsed": d.get("unparsed", []),
            "ownerStatus": VERIFIED.get(cid, {}).get("status", ""),
            "code": code(all_defs[cid]),
            "img": crop(cid),
        }
    )

template = (ROOT / "tools" / "web" / "card_review.template.html").read_text(encoding="utf-8")
page = template.replace("/*CARDS*/[]", json.dumps(cards, ensure_ascii=False))
out = pathlib.Path(sys.argv[1])
out.write_text(page, encoding="utf-8")
print(f"{len(cards)} cards, {out.stat().st_size / 1e6:.1f} MB -> {out}")
_ = html  # (kept for quick local edits of the template)
