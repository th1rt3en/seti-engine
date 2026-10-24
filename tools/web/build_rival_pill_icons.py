"""The small icons of the cells of the rival pill, cut from the pictures of the objective tiles (apps/web/public/assets/solo and expansion/objectives):
the three tech icons (the orange, pink and blue chips of probe, telescope and computer techs) and the corner icon of an objective tile and of a
long-term objective tile. The background of a tile is made transparent. Run from the repo root; it writes the pictures into
apps/web/public/assets/icons and adds them to `printedIcons` in apps/web/src/generated/assets.json."""

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "apps" / "web" / "src" / "generated" / "assets.json"
PUB = ROOT / "apps" / "web" / "public" / "assets"
SIZE = 96


def find(pattern: str) -> Image.Image:
    return Image.open(next(PUB.glob(pattern))).convert("RGBA")


def clear_background(im: Image.Image, tolerance: float = 38.0) -> Image.Image:
    """Pixels that look like the tile behind the icon (the color of the corner of the cut) become transparent, softly at the edge."""
    bg = im.getpixel((1, 1))[:3]
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, _ = px[x, y]
            d = ((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2) ** 0.5
            a = 0 if d < tolerance else 255 if d > tolerance * 1.8 else int(255 * (d - tolerance) / (tolerance * 0.8))
            px[x, y] = (r, g, b, 0 if x < 13 and y < 9 else a)  # (the corner badge of the tile reaches into the top left of the cut)
    return out


def save(im: Image.Image, name: str) -> str:
    im = im.resize((SIZE, SIZE), Image.LANCZOS)
    tmp = PUB / "icons" / f"{name}.tmp.webp"
    im.save(tmp, "WEBP", quality=92, alpha_quality=95)
    digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
    final = tmp.with_name(f"{name}.{digest}.webp")
    tmp.replace(final)
    return f"/assets/icons/{final.name}"


CHIP = (34, 40, 98, 104)  # the chip of a tech on the 240 x 239 tiles
CORNER = (0, 0, 54, 54)  # the corner badge of an objective tile (240 px) and of a long-term tile (380 px)
cuts = {
    "tech-probe": clear_background(find("solo/objective-L2-probe-tech-mission.*").crop(CHIP)),
    "tech-telescope": clear_background(find("solo/objective-L2-telescope-tech-mission.*").crop(CHIP)),
    "tech-computer": clear_background(find("solo/objective-L2-computer-tech-trace.*").crop(CHIP)),
    "objective": find("solo/objective-L1-16-vp.*").crop(CORNER),
    "long-term": find("expansion/objectives/long-term-1.*").crop((0, 0, 58, 58)),
}
assets = json.loads(GEN.read_text(encoding="utf-8"))
for name, im in cuts.items():
    assets.setdefault("printedIcons", {})[name] = save(im, name)
GEN.write_text(json.dumps(assets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print({k: assets["printedIcons"][k] for k in cuts})
