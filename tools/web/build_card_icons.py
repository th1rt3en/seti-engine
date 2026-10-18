"""Cuts two small icons out of printed cards, for the player tracker: the Exertian danger symbol (from the Exertian card ET.45) and the Centaurian time
capsule with its "+15" (from the Centaurian card ET.31). The page around each icon is made transparent; the results are WebP files in
apps/web/public/assets/icons and the keys `danger` and `capsule` of `printedIcons` in apps/web/src/generated/assets.json.

Usage (from the repository root, after tools/web/build_assets.py, which rewrites assets.json):  python tools/web/build_card_icons.py
The sources are the card pictures that are already in the repository (apps/web/public/assets/cards)."""

import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "apps" / "web" / "src" / "generated" / "assets.json"
PUBLIC = ROOT / "apps" / "web" / "public"
OUT = PUBLIC / "assets" / "icons"
HEIGHT = 96  # the height of the icons, in pixels
# name -> (card, box of the icon on the card picture of 440 x 613 px: left, top, right, bottom)
ICONS = {
    "danger": ("ET.45", (224, 308, 288, 400)),  # the Exertian symbol on its cross, without the number of the card
    "capsule": ("ET.31", (72, 326, 146, 414)),  # the green capsule with its "+15"
}


def clear_background(im: Image.Image, tolerance: int = 40) -> Image.Image:
    """Makes the part of the picture that touches its border and has the colour of the corner transparent (the page around an icon)."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    ref = px[0, 0]
    seen = np.zeros((h, w), dtype=bool)
    todo = deque([*((x, y) for x in range(w) for y in (0, h - 1)), *((x, y) for y in range(h) for x in (0, w - 1))])
    while todo:
        x, y = todo.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y, x]:
            continue
        c = px[x, y]
        if max(abs(c[0] - ref[0]), abs(c[1] - ref[1]), abs(c[2] - ref[2])) > tolerance:
            continue
        seen[y, x] = True
        px[x, y] = (0, 0, 0, 0)
        todo.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def main() -> None:
    assets = json.loads(GEN.read_text(encoding="utf-8"))
    cards = assets["cards"]
    printed = assets.setdefault("printedIcons", {})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (card, box) in ICONS.items():
        pic = Image.open(PUBLIC / cards[card].lstrip("/")).convert("RGB").crop(box)
        icon = clear_background(pic)
        icon = icon.crop(icon.getbbox())  # the transparent margin goes
        icon = icon.resize((round(HEIGHT * icon.width / icon.height), HEIGHT), Image.LANCZOS)
        tmp = OUT / f"{name}.tmp.webp"
        icon.save(tmp, "WEBP", quality=92, alpha_quality=95)
        digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
        final = OUT / f"{name}.{digest}.webp"
        tmp.replace(final)
        old = printed.get(name)
        if old and old != f"/assets/icons/{final.name}":
            (PUBLIC / old.lstrip("/")).unlink(missing_ok=True)
        printed[name] = f"/assets/icons/{final.name}"
        print(name, printed[name])
    GEN.write_text(json.dumps(assets, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
