"""Check where the spaces of the species boards are on their pictures (apps/web/src/lib/speciesSpaces.ts).

Every space of a species board is a ring of its colour (pink, yellow, blue) on the picture. For each space of `SPECIES_SPACES` this looks for the ring of that
colour around the place in the table (a circle of about 58 px, found by voting) and says where it found it and how far that is from the table. A difference of
more than 6 px is marked `<-- off`. The top space of a species board of the base game (a capsule, whose ring is the tube above the reward) is expected to be off.
Needs numpy and pillow:    python tools/web/fit_board_rings.py [anomalies mascamites ...]
"""

import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
ASSETS = WEB / "public" / "assets"
FILES = {
    "anomalies": "species/anomalies.*.webp",
    "centaurians": "species/centaurians.*.webp",
    "exertians": "species/exertians.*.webp",
    "mascamites": "species/mascamites.*.webp",
    "oumuamua": "species/oumuamua.*.webp",
    "arkhos": "expansion/boards/arkhos.*.webp",
    "glyphids": "expansion/boards/glyphids.[0-9a-f]*.webp",
    "amoeba": "expansion/boards/amoeba.*.webp",
}


def table() -> dict[str, dict[str, list[tuple[int, int] | None]]]:
    """`SPECIES_SPACES` of speciesSpaces.ts: species -> colour -> the centre of each space, or None."""
    text = (WEB / "src" / "lib" / "speciesSpaces.ts").read_text(encoding="utf-8")
    start = text.index("export const SPECIES_SPACES")
    out: dict[str, dict[str, list[tuple[int, int] | None]]] = {}
    species = colour = ""
    for line in text[start : text.index("\n};", start)].splitlines()[1:]:
        if m := re.match(r"^  (\w+): \{", line):
            species = m.group(1)
            out[species] = {}
        elif m := re.match(r"^    (\w+): \[(.*)", line):
            colour = m.group(1)
            out[species][colour] = [None if x.group(0) == "null" else (int(x.group(1)), int(x.group(2))) for x in re.finditer(r"\[(\d+), (\d+)\]|null", m.group(2))]
        elif m := re.match(r"^\s+\[(\d+), (\d+)\],?$", line):
            out[species][colour].append((int(m.group(1)), int(m.group(2))))
    return out


def ring_mask(im: np.ndarray, colour: str) -> np.ndarray:
    x = im.astype(np.float32) / 255
    mx, mn = x.max(axis=2), x.min(axis=2)
    d = mx - mn
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    h = np.zeros_like(mx)
    ok = d > 1e-6
    for ch, shift, hi in ((r, 0, mx == r), (g, 2, mx == g), (b, 4, mx == b)):
        sel = ok & hi
        a, c = {0: (g, b), 2: (b, r), 4: (r, g)}[shift]
        h[sel] = ((a - c)[sel] / d[sel] + shift) % 6 if shift == 0 else (a - c)[sel] / d[sel] + shift
    h *= 60
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    if colour == "pink":
        return ((h > 320) | (h < 8)) & (s > 0.55) & (mx > 0.6)
    if colour == "yellow":
        return (h > 36) & (h < 56) & (s > 0.6) & (mx > 0.7)
    return (h > 190) & (h < 212) & (s > 0.65) & (mx > 0.55)


def fit(mask: np.ndarray, cx: int, cy: int, search: int = 60) -> tuple[int, int, int, int]:
    """(votes, x, y, radius) of the circle of the ring pixels that is nearest to (cx, cy)."""
    pad = search + 75
    x0, y0 = max(cx - pad, 0), max(cy - pad, 0)
    ys, xs = np.nonzero(mask[y0 : cy + pad, x0 : cx + pad])
    xs, ys = xs + x0, ys + y0
    best = (0, cx, cy, 58)
    for radius in (52, 54, 56, 58, 60, 62):
        for dy in range(-search, search + 1, 2):
            for dx in range(-search, search + 1, 2):
                dist = np.hypot(xs - (cx + dx), ys - (cy + dy))
                votes = int(((dist > radius - 3) & (dist < radius + 3)).sum())
                if votes > best[0]:
                    best = (votes, cx + dx, cy + dy, radius)
    _, bx, by, br = best
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            dist = np.hypot(xs - (bx + dx), ys - (by + dy))
            votes = int(((dist > br - 3) & (dist < br + 3)).sum())
            if votes > best[0]:
                best = (votes, bx + dx, by + dy, br)
    return best


def main() -> None:
    spaces = table()
    for name in sys.argv[1:] or list(FILES):
        im = np.asarray(Image.open(next(ASSETS.glob(FILES[name]))).convert("RGB"))
        print(f"== {name}")
        for colour, points in spaces[name].items():
            mask = ring_mask(im, colour)
            for k, p in enumerate(points):
                if p is None:
                    continue
                votes, x, y, r = fit(mask, *p)
                off = "  <-- off" if abs(x - p[0]) > 6 or abs(y - p[1]) > 6 else ""
                print(f"  {colour}[{k}] table {p} ring ({x}, {y}) r={r} votes={votes} diff=({x - p[0]:+d},{y - p[1]:+d}){off}")


if __name__ == "__main__":
    main()
