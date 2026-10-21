"""Cuts the "ring 1 + 2 + 3" icon of the rotation dial (the teal one with the wings, top right of the dial) out of the main board picture and splits it
into its three concentric lines, so that the web page can show which disc turns next: the base (the disc and the dot, without the lines) and for each
line two pictures, in colour (inner yellow, middle orange, outer blue as printed) and greyed out. Needs Pillow and numpy.

    python cut_dial_icon.py <board.webp> <out folder>

The files are named with the first 10 characters of their sha256 (like the other web assets); the list of them is printed as json.
"""

import colorsys
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

src, out = Path(sys.argv[1]), Path(sys.argv[2])
board = Image.open(src).convert("RGB")
X0, Y0, N = 1140, 2430, 120  # the part of the board picture that holds the icon
CX, CY = 60.6, 62.1  # the white dot in the middle, in that part
EDGES = (15.5, 24.5, 33.3)  # the dark separators between the lines, and the outer edge of the outer line
SIZE = 34.5  # radius of the cut-out (the dark rim of the disc included)
SCALE = 2
LINES = {"inner": ((7.0, EDGES[0]), 52 / 360), "middle": ((EDGES[0], EDGES[1]), 28 / 360), "outer": ((EDGES[1], EDGES[2]), None)}

a = np.asarray(board.crop((X0, Y0, X0 + N, Y0 + N))).astype(float)
ys, xs = np.mgrid[0:N, 0:N]
r = np.hypot(xs - CX, ys - CY)
teal = np.clip((np.minimum(a[..., 1], a[..., 2]) - a[..., 0] - 28) / 22, 0, 1)  # the lines are teal, from bright (below) to dark (above)
dark = np.array([10.0, 28.0, 36.0])  # what the disc looks like between the lines

big = lambda arr: np.asarray(Image.fromarray(arr.astype("uint8")).resize((N * SCALE, N * SCALE), Image.BICUBIC)).astype(float)  # noqa: E731
pieces: dict[str, np.ndarray] = {}
base = a.copy()
for name, ((lo, hi), hue) in LINES.items():
    alpha = teal * ((r >= lo) & (r < hi))
    layer = a.copy()
    if hue is not None:  # the printed colour of the line is teal: the other two lines are tinted
        for i, j in zip(*np.nonzero(alpha > 0.01), strict=True):
            h, s, v = colorsys.rgb_to_hsv(*(a[i, j] / 255))
            layer[i, j] = np.array(colorsys.hsv_to_rgb(hue, min(1.0, s * 1.15), min(1.0, v * 1.4))) * 255
    pieces[name] = np.dstack([layer, alpha * 255])
    base = base * (1 - alpha[..., None]) + dark * alpha[..., None]
disc = np.clip((SIZE - r) / 1.5, 0, 1)  # the cut-out is a disc
pieces["base"] = np.dstack([base, disc * 255])
for name in LINES:
    pieces[name][..., 3] *= (r < SIZE + 1) * 1.0


def save(name: str, arr: np.ndarray) -> dict[str, str]:
    rgb = big(arr[..., :3])
    alpha = big(np.repeat(arr[..., 3:4], 3, axis=2))[..., 0]
    img = Image.fromarray(np.dstack([rgb, alpha]).astype("uint8"), "RGBA")
    box = (int(CX * SCALE - SIZE * SCALE), int(CY * SCALE - SIZE * SCALE), int(CX * SCALE + SIZE * SCALE), int(CY * SCALE + SIZE * SCALE))
    img = img.crop(box)
    tmp = out / f"{name}.tmp.webp"
    img.save(tmp, "WEBP", lossless=True, quality=100)
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()[:10]
    final = out / f"{name}.{digest}.webp"
    tmp.replace(final)
    return {name: f"/assets/discs/{final.name}"}


out.mkdir(parents=True, exist_ok=True)
result: dict[str, str] = {}
result.update(save("dial-base", pieces["base"]))
for name in LINES:
    result.update(save(f"dial-{name}", pieces[name]))
    grey = pieces[name].copy()
    lum = grey[..., :3] @ np.array([0.3, 0.59, 0.11])
    grey[..., :3] = (lum[..., None] * 0.9 + 25)
    grey[..., 3] *= 0.8
    result.update(save(f"dial-{name}-grey", grey))
print(json.dumps(result, indent=1))
