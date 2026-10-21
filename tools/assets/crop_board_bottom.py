"""Crops the bottom of the main board picture: the tech zone, the rotation dial and the publicity track below the score track are cut away. The new edge follows
the outside of the score track (a half circle around the centre of the board) and has two bumps that keep the places of the independent researcher markers
(the two round pockets next to the 20 space and the two next to the 30 space, with the teal strip that tells how many are used with 1-2, 3 and 4 players).
The picture keeps its size (the coordinates of the page do not change); what is cut away is transparent. Needs Pillow and numpy.

    python crop_board_bottom.py <board.webp> <out.webp> [preview.png]
"""

import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
preview = sys.argv[3] if len(sys.argv) > 3 else None
im = Image.open(src).convert("RGBA")
W, H = im.size
K = W / 3507  # the page's coordinates (geometry.ts) to the picture
CX, CY = 1752.5 * K, 3062.6 * K  # the centre of the board
R_SIDE = 864.0  # the outer edge of the picture at the sides: the grey frame around the score track (the blue ring ends at 838)
R_BOTTOM = 840.0  # the half circle at the bottom hugs the blue ring of the track; it joins the sides over the first 22 degrees below the middle
JOIN = 22.0

# the bumps, in the picture's pixels: the circles of the two pockets, and the strip beside them (a stadium: two end points and a radius)
BUMPS = {
    "30": {"circles": [(208.3, 2071.0, 24), (240.7, 2113.3, 24)], "strip": ((256.7, 2151.7), (300.0, 2180.0), 21)},
    "20": {"circles": [(636.0, 2381.7, 24), (688.3, 2390.0, 24)], "strip": ((721.7, 2396.7), (770.0, 2415.0), 18)},
}
MARGIN = 9  # the bump is a little bigger than what it holds
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)
pts = []
for i in range(0, 1801):  # the lower half circle, from the left (180 degrees) round the bottom to the right (360 degrees)
    ang = 180 + i * 0.1
    below = min(ang - 180, 360 - ang)  # degrees below the horizontal
    r = R_BOTTOM + (R_SIDE - R_BOTTOM) * max(0.0, 1 - below / JOIN)
    pts.append((CX + r * np.cos(np.radians(ang)), CY - r * np.sin(np.radians(ang))))
d.polygon([(CX - R_SIDE, CY - 400), (CX + R_SIDE, CY - 400), *pts[::-1]], fill=255)
for b in BUMPS.values():
    for x, y, r in b["circles"]:
        d.ellipse((x - r - MARGIN, y - r - MARGIN, x + r + MARGIN, y + r + MARGIN), fill=255)
    (x1, y1), (x2, y2), r = b["strip"]
    r += MARGIN
    d.line((x1, y1, x2, y2), fill=255, width=int(2 * r))
    for x, y in ((x1, y1), (x2, y2)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    # fill the gap between the circles and the strip: the hull of the pocket pair joins them
    (ax, ay, _), (bx, by, _) = b["circles"]
    d.line((ax, ay, bx, by), fill=255, width=int(2 * (b["circles"][0][2] + MARGIN)))
    d.line((bx, by, x1, y1), fill=255, width=int(2 * (b["circles"][0][2] + MARGIN)))
# round the corners where a bump meets the half circle, then smooth the edge
mask = mask.filter(ImageFilter.GaussianBlur(7)).point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(1.2))
m = np.asarray(mask).astype(float) / 255
keep = np.ones((H, W))
below = np.arange(H)[:, None] > CY
keep = np.where(below, m, 1.0)  # above the middle of the board the picture's own outline stays
a = np.asarray(im).astype(float)
a[..., 3] *= keep
# a thin dark rim along the new edge, like the outline of the printed board
rim = np.clip(m - np.asarray(mask.filter(ImageFilter.MinFilter(9))).astype(float) / 255, 0, 1) * below
rgb = a[..., :3] * (1 - 0.8 * rim[..., None]) + np.array([12.0, 16.0, 26.0]) * 0.8 * rim[..., None]
a[..., :3] = rgb
out = Image.fromarray(a.astype("uint8"), "RGBA")
out.save(dst, "WEBP", lossless=True, quality=100)
if preview:
    bg = Image.new("RGBA", (W, H), (46, 50, 60, 255))
    bg.alpha_composite(out)
    ys = np.nonzero(np.asarray(out)[..., 3].max(1) > 0)[0]
    bg.crop((0, 0, W, int(ys.max()) + 40)).save(preview)
    print("kept height", int(ys.max()) + 1, "of", H)
