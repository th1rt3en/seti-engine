"""Cuts more icons out of the player aid (the same picture and the same method as the action icons of tools/web/build_assets.py):

- the hexagons of the Research action (with the "take a tech of any type" symbol in it) and of Pass (the red cross), as printed;
- the mission icon: the silver card as printed next to "Complete a mission", once without its green check mark (a mission that was played) and once with it
  (a mission that was completed). The card is drawn again in the colours of the printed one and the printed check mark is put on it, so that both
  icons are exactly the same card.

Needs Pillow and numpy.   python cut_action_icons.py <assets/player-aid-iconography-en.png> <apps/web/public/assets/icons>
Prints the entries for `apps/web/src/generated/assets.json` (the file names carry the first 10 characters of the sha256 of their bytes).
"""

import hashlib
import io
import json
import math
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HEX_BOXES = {"research": (1166, 822, 1278, 945), "pass": (1166, 950, 1278, 1073)}  # like launch (1166, 205, 1278, 328)
HEX_SIZE = 112
MISSION_BOX = (1826, 262, 1900, 346)  # the card and its check mark, on the light green of the free actions
MISSION_HEIGHT = 72


def clear_background(im: Image.Image, tolerance: int = 40) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    ref = px[0, 0]
    close = lambda c: max(abs(c[0] - ref[0]), abs(c[1] - ref[1]), abs(c[2] - ref[2])) <= tolerance  # noqa: E731
    seen = np.zeros((h, w), dtype=bool)
    todo = deque([*((x, y) for x in range(w) for y in (0, h - 1)), *((x, y) for y in range(h) for x in (0, w - 1))])
    while todo:
        x, y = todo.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y, x] or not close(px[x, y]):
            continue
        seen[y, x] = True
        px[x, y] = (0, 0, 0, 0)
        todo.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def hexagon_mask(im: Image.Image, margin: float = 1.0) -> Image.Image:
    w, h = im.size
    radius, cx, cy = h / 2 + margin, w / 2, h / 2
    px = im.load()
    for y in range(h):
        for x in range(w):
            dx, dy = abs(x + 0.5 - cx), abs(y + 0.5 - cy)
            if dx > radius * math.sqrt(3) / 2 or dy > radius - dx / math.sqrt(3):
                px[x, y] = (0, 0, 0, 0)
    return im


def save(im: Image.Image, out: Path, name: str) -> str:
    buf = io.BytesIO()
    im.save(buf, "WEBP", method=6, quality=90, alpha_quality=95)
    data = buf.getvalue()
    final = f"{name}.{hashlib.sha256(data).hexdigest()[:10]}.webp"
    (out / final).write_bytes(data)
    return f"/assets/icons/{final}"


def mission_icons(aid: Image.Image) -> tuple[Image.Image, Image.Image]:
    crop = aid.crop(MISSION_BOX).convert("RGB")
    a = np.asarray(crop).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > r + 35) & (g > b + 35)  # the check mark
    dark = (r < 130) & (g < 130) & (b < 130) & ~green  # the outline of the card
    ys, xs = np.nonzero(dark)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()  # the card (the check mark reaches beyond its corner, but it is green, not dark)
    cw, ch = x1 - x0 + 1, y1 - y0 + 1
    outline = tuple(int(v) for v in np.median(a[dark], axis=0))
    top = tuple(int(v) for v in a[y0 + 8, x0 + cw // 2])  # the white upper half
    bottom = tuple(int(v) for v in a[y1 - 8, x0 + 8])  # the grey lower half (left of the check mark)
    k = 8  # drawn big and made small, for smooth edges
    card = Image.new("RGBA", (crop.width * k, crop.height * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    box = (x0 * k, y0 * k, (x1 + 1) * k - 1, (y1 + 1) * k - 1)
    radius = int(0.14 * cw * k)
    d.rounded_rectangle(box, radius=radius, fill=top, outline=outline, width=int(2.4 * k))
    inner = Image.new("RGBA", card.size, (0, 0, 0, 0))
    di = ImageDraw.Draw(inner)
    di.rectangle((x0 * k + int(2.4 * k), y0 * k + int(ch * 0.46 * k), (x1 + 1) * k - int(2.4 * k), (y1 + 1) * k - int(2.4 * k)), fill=bottom)
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius - int(2.4 * k), fill=255)
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (box[0] + int(2.4 * k), box[1] + int(2.4 * k), box[2] - int(2.4 * k), box[3] - int(2.4 * k)), radius=max(2, radius - int(2.4 * k)), fill=255
    )
    card.paste(inner, (0, 0), Image.composite(inner.split()[3], Image.new("L", card.size, 0), mask))
    played = card.resize(crop.size, Image.LANCZOS)
    # the printed check mark, with soft edges, on top of the same card
    soft = Image.fromarray((green * 255).astype("uint8")).resize(crop.size, Image.LANCZOS)
    check = crop.convert("RGBA")
    check.putalpha(soft)
    done = played.copy()
    done.alpha_composite(check)
    bbox = done.getbbox()
    pad = 2
    box_out = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(crop.width, bbox[2] + pad), min(crop.height, bbox[3] + pad))
    fit = lambda im: im.crop(box_out).resize((round(MISSION_HEIGHT * (box_out[2] - box_out[0]) / (box_out[3] - box_out[1])), MISSION_HEIGHT), Image.LANCZOS)  # noqa: E731
    return fit(played), fit(done)


if __name__ == "__main__":
    Image.MAX_IMAGE_PIXELS = None
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    aid = Image.open(src).convert("RGBA")
    result: dict[str, str] = {}
    for name, box in HEX_BOXES.items():
        icon = hexagon_mask(clear_background(aid.crop(box)), margin=-3)
        icon = icon.resize((HEX_SIZE, round(HEX_SIZE * icon.height / icon.width)), Image.LANCZOS)
        result[name] = save(icon, out, name)
    played, done = mission_icons(aid)
    result["mission"] = save(played, out, "mission")
    result["mission-done"] = save(done, out, "mission-done")
    print(json.dumps(result, indent=1))
