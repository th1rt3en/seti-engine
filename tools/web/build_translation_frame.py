"""The frame of the Glyphids translation board, without its slots, strips, reward icons and scoring bar (those are drawn by the page, crisp).

From the clean arrangement (picture "a") of the translation board supplied by the owner: the outside of the board is made transparent, the generator
watermark is removed, and the slots (3 on the top row, 4 on the bottom row, shaped like combs, each row with the strip behind it) are repainted pure
black with smooth edges that follow their outline, so that the compression noise of the supplied picture is gone.

Usage: python tools/web/build_translation_frame.py   (reads the picture `boards/glyphids-track-a` from apps/web/src/generated/expansion-assets.json,
which this script leaves unchanged; it writes apps/web/public/assets/expansion/boards/glyphids-frame.<hash>.webp and adds the key `boards/glyphids-frame`)."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "apps" / "web" / "public"
EXP_PATH = ROOT / "apps" / "web" / "src" / "generated" / "expansion-assets.json"
SOURCE = ROOT / "tools" / "web" / "source" / "glyphids-track-a.webp"  # the supplied picture, kept out of the repository: see the usage

exp = json.loads(EXP_PATH.read_text(encoding="utf-8"))
src = Image.open(PUB / exp["boards/glyphids-track-a"].lstrip("/")).convert("RGB")
W, H = src.size  # 750 x 690
arr = np.array(src).astype(int)
lum = arr.mean(axis=2)

# 1. the outside of the board (flood from the corners over the black background; the frame is lighter, and its thin gaps are closed first)
solid = Image.fromarray(((lum > 28) * 255).astype("uint8")).filter(ImageFilter.MaxFilter(7))
for corner in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
    if solid.getpixel(corner) == 0:
        ImageDraw.floodfill(solid, corner, 128)
outside = np.array(solid) == 128
sat = arr.max(axis=2) - arr.min(axis=2)
outside[630:, 585:] |= (lum[630:, 585:] < 45)
outside[630:, 600:] |= (sat[630:, 600:] < 40) | (lum[630:, 600:] < 45)  # the generator watermark (white, not green) beside the lower right corner of the frame
outside[686:, :] = True  # stray dashes under the frame

# the old scoring bar (gold, along the top; the page draws a new one)
gold = np.zeros((H, W), bool)
gold[:100] = (arr[:100, :, 0] > arr[:100, :, 1] + 6) & (lum[:100] > 60)
gold_img = Image.fromarray((gold * 255).astype("uint8")).filter(ImageFilter.MaxFilter(9))
gold = np.array(gold_img) > 0
outside |= gold
outside[:100] |= np.array(Image.fromarray((outside[:100] * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))) > 0

# 2. the slots: two combs (a strip with a rounded tooth above each hole), drawn smooth at 4x
TOP_HOLES, BOTTOM_HOLES = [200, 375, 545], [112, 290, 468, 640]
COMBS = (  # (strip box, tooth centre y, tooth half width, tooth half height, neck half width, holes)
    ((112, 262, 638, 338), 160, 74, 62, 24, TOP_HOLES),
    ((58, 515, 692, 620), 445, 70, 62, 24, BOTTOM_HOLES),
)
big = 4
mask = Image.new("L", (W * big, H * big), 0)
draw = ImageDraw.Draw(mask)
for (x0, y0, x1, y1), cy, rx, ry, neck, holes in COMBS:
    draw.rounded_rectangle((x0 * big, y0 * big, x1 * big, y1 * big), radius=18 * big, fill=255)
    for cx in holes:
        draw.ellipse(((cx - rx) * big, (cy - ry) * big, (cx + rx) * big, (cy + ry) * big), fill=255)
        draw.rectangle(((cx - neck) * big, (cy) * big, (cx + neck) * big, (y0 + 10) * big), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(9 * big)).point(lambda v: 255 if v > 120 else 0)  # rounds the joints between tooth, neck and strip
mask = mask.filter(ImageFilter.GaussianBlur(big * 0.6)).resize((W, H), Image.LANCZOS)

# 3. the frame: the supplied picture, the slots repainted black, the outside transparent (with a smooth edge)
frame = src.convert("RGBA")
black_layer = Image.new("RGBA", (W, H), (0, 0, 0, 255))
frame = Image.composite(black_layer, frame, mask)
keep = Image.fromarray(((~outside) * 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
edge = keep.filter(ImageFilter.MedianFilter(9))  # evens the ragged lower edge left by the watermark
keep.paste(edge.crop((0, 600, W, H)), (0, 600))
frame.putalpha(keep)

folder = PUB / "assets" / "expansion" / "boards"
tmp = folder / "glyphids-frame.tmp.webp"
frame.save(tmp, "WEBP", quality=92, alpha_quality=95)
digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
final = folder / f"glyphids-frame.{digest}.webp"
tmp.replace(final)
exp["boards/glyphids-frame"] = f"/assets/expansion/boards/{final.name}"
EXP_PATH.write_text(json.dumps(exp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(exp["boards/glyphids-frame"])
