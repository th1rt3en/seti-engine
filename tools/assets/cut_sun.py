"""Cuts the Sun token (item 5, page 2 of the base rulebook) out of the rulebook picture: the page is one raster picture, the token is the warm-colored
blob in it, the paper around it and its soft shadow are grey/lavender. Needs PyMuPDF, Pillow and numpy (not part of the project: install them in a scratch
folder).   python cut_sun.py <rulebook.pdf> <out.png>"""

import sys

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter

pdf, out = sys.argv[1], sys.argv[2]
doc = pymupdf.open(pdf)
pix = doc[1].get_pixmap(dpi=1200, clip=pymupdf.Rect(412, 292, 436, 318))
pix.save(out)
im = Image.open(out).convert("RGB")
a = np.asarray(im).astype(float) / 255
mx, mn = a.max(2), a.min(2)
sat = (mx - mn) / np.maximum(mx, 1e-6)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
warm = (r > b + 0.25) & (r >= g - 0.02)  # amber and orange; the blue arrow and the grey shadow are not
alpha = np.clip((sat - 0.25) / 0.2, 0, 1) * warm
al = Image.fromarray((alpha * 255).astype("uint8")).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
rgba = im.copy()
rgba.putalpha(al)
box = al.point(lambda v: 255 if v > 20 else 0).getbbox()
assert box is not None
# the board has a round hole for the Sun: only the round top of the token is kept, as a disc (found on the 338 x 338 cut-out: middle and radius)
cut = rgba.crop(box)
cx, cy, r = 170, 135, 125
disc = Image.new("L", cut.size, 0)
ImageDraw.Draw(disc).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
cut.putalpha(Image.fromarray(np.minimum(np.asarray(cut.getchannel("A")), np.asarray(disc.filter(ImageFilter.GaussianBlur(1.5))))))
cut.crop((cx - r, cy - r, cx + r, cy + r)).save(out)
print(cut.size, "-> disc", 2 * r)
