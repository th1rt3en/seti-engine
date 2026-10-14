"""Prepare the images the website serves, optimized for a Cloudflare Worker's static assets (decision D30).

* Every card is cut from its sheet and saved as its own small WebP (300 px wide), so a player downloads only the cards on screen
  instead of two 2.8 MB sheets.
* Every file name carries a hash of its content, so the files can be cached for a year (`public/_headers`) and a changed image gets a new URL.
* The solar-system discs are saved once each.

Writes apps/web/public/assets/{cards,discs}/*.webp, apps/web/public/_headers, apps/web/src/generated/{assets,solar}.json and
packages/assets/PROVENANCE.md (CLAUDE.md rule 8: every imported asset is in the provenance manifest).
Run from the repo root: python tools/web/build_assets.py
"""

import hashlib
import io
import json
import pathlib
import shutil

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "assets"
PUB = ROOT / "apps" / "web" / "public"
OUT = PUB / "assets"
GEN = ROOT / "apps" / "web" / "src" / "generated"

CARD_WIDTH = 300  # shown at 130 px, and 1.8 times that when hovered
CARD_QUALITY = 78

# tracker sheet name -> (source file, columns, rows)
SHEETS = {
    "cards-1.webp": ("cards-main-deck-en-sheet-1.png", 10, 7),
    "cards-2.webp": ("cards-main-deck-en-sheet-2.png", 10, 7),
    "anomalies.webp": ("cards-alien-anomalies-en-sheet.png", 5, 2),
    "centaurians.webp": ("cards-alien-centaurians-en-sheet.png", 5, 2),
    "exertians.webp": ("cards-alien-exertians-en-sheet.png", 5, 3),
    "mascamites.webp": ("cards-alien-mascamites-en-sheet.png", 5, 2),
    "oumuamua.webp": ("cards-alien-oumuamua-en-sheet.png", 5, 2),
}

DISCS = {
    "disc-1": "solar-disc-1-mercury-venus-earth.png",
    "disc-2": "solar-disc-2-mars-asteroids.png",
    "disc-3": "solar-disc-3-jupiter-saturn.png",
    "disc-3-oumuamua": "solar-disc-3-with-oumuamua.png",
}


def save(im: Image.Image, folder: str, name: str, **opts: object) -> str:
    """Write the image under a name with its content hash; returns the URL path."""
    buf = io.BytesIO()
    im.save(buf, "WEBP", method=6, **opts)
    data = buf.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:10]
    target = OUT / folder / f"{name}.{digest}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/assets/{folder}/{name}.{digest}.webp"


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)  # files of an earlier run have other hashes
    GEN.mkdir(parents=True, exist_ok=True)
    provenance: list[tuple[str, str, str]] = []

    sheets = {name: Image.open(SRC / src).convert("RGBA") for name, (src, _, _) in SHEETS.items()}
    defs = json.loads((ROOT / "docs/spec/data/card-definitions.json").read_text(encoding="utf-8"))
    cards: dict[str, str] = {}
    counts: dict[str, int] = {}
    for c in defs:
        if c["group"] not in ("base", "alien-base"):
            continue
        sheet = pathlib.PurePosixPath(c["pos"][0]).name
        _, cols, rows = SHEETS[sheet]
        im = sheets[sheet]
        w, h = im.width / cols, im.height / rows
        row, col = c["pos"][1], c["pos"][2]
        card = im.crop((round(col * w), round(row * h), round((col + 1) * w), round((row + 1) * h)))
        card = card.resize((CARD_WIDTH, round(CARD_WIDTH * card.height / card.width)), Image.LANCZOS)
        cards[c["id"]] = save(card, "cards", c["id"], quality=CARD_QUALITY)
        counts[sheet] = counts.get(sheet, 0) + 1
    for sheet, (src, _, _) in SHEETS.items():
        provenance.append((src, f"apps/web/public/assets/cards/ ({counts.get(sheet, 0)} cards, {CARD_WIDTH} px wide)", "cut from the sheet"))

    discs: dict[str, str] = {}
    for name, src in DISCS.items():
        im = Image.open(SRC / src).convert("RGBA")
        discs[name] = save(im, "discs", name, quality=90)
        provenance.append((src, discs[name], f"{im.width}x{im.height}"))

    (GEN / "assets.json").write_text(json.dumps({"cards": cards, "discs": discs}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    stale = GEN / "cardart.json"  # the sprite-sheet map of the earlier version
    if stale.exists():
        stale.unlink()

    solar = json.loads((ROOT / "services/engine/src/seti_engine/data/solar-system.json").read_text(encoding="utf-8"))
    (GEN / "solar.json").write_text(json.dumps({"ring4": solar["wheels"]["4"]["4"]}, indent=1) + "\n", encoding="utf-8")

    # Cloudflare's static assets read this file: the names carry the hash of the content, so they never change.
    (PUB / "_headers").write_text(
        "/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n\n/_next/static/*\n  Cache-Control: public, max-age=31536000, immutable\n",
        encoding="utf-8",
    )

    prov = [
        "# Asset provenance", "",
        "Images the website serves, converted from the owner-supplied files in `assets/` (labels in `assets/MANIFEST.md`; origin and licence status in",
        "`docs/asset-gaps.md`, section Licensing). Each card is cut from its sheet and saved on its own; the file names carry a hash of the content.",
        "Generated by `tools/web/build_assets.py`; do not edit by hand.", "", "| Source file | Served as | Note |", "|---|---|---|",
    ]
    prov += [f"| `assets/{s}` | `{o}` | {n} |" for s, o, n in provenance]
    (ROOT / "packages/assets/PROVENANCE.md").write_text("\n".join(prov) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.rglob("*.webp"))
    print(f"cards: {len(cards)}, discs: {len(discs)}, {total / 1e6:.1f} MB in all")


if __name__ == "__main__":
    main()
