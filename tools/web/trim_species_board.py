"""Trims the edges of a species board of the expansion so that it has the outline of the species boards of the base game (their rounded top and
the three notches at the bottom): the base game's board outline (the alpha of the Mascamites board, which all five share) is eroded by a few
pixels, so that the background of the supplied picture at its edges is cut away, and applied as the alpha of the picture.

Usage: python tools/web/trim_species_board.py glyphids   (the board must be 777 x 1415 like the base species boards)
Rewrites the file in apps/web/public/assets/expansion/boards and its key `boards/<species>` in apps/web/src/generated/expansion-assets.json."""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "apps" / "web" / "public"
BASE = json.loads((ROOT / "apps" / "web" / "src" / "generated" / "assets.json").read_text(encoding="utf-8"))
EXP_PATH = ROOT / "apps" / "web" / "src" / "generated" / "expansion-assets.json"
ERODE = 9  # pixels cut from the edge of the outline

name = sys.argv[1]
exp = json.loads(EXP_PATH.read_text(encoding="utf-8"))


def rewrite(key: str, img: Image.Image) -> str:
    old = PUB / exp[key].lstrip("/")
    stem = old.name.split(".")[0]
    tmp = old.with_name(f"{stem}.tmp.webp")
    img.save(tmp, "WEBP", quality=90, alpha_quality=95)
    digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
    final = old.with_name(f"{stem}.{digest}.webp")
    tmp.replace(final)
    if old != final:
        old.unlink()
    exp[key] = exp[key].rsplit("/", 1)[0] + f"/{final.name}"
    return exp[key]


key = f"boards/{name}"
old = PUB / exp[key].lstrip("/")
board = Image.open(old).convert("RGBA")
outline = Image.open(PUB / BASE["species"]["mascamites"].lstrip("/")).convert("RGBA").split()[3]
assert board.size == outline.size, (board.size, outline.size)
board.putalpha(outline.filter(ImageFilter.MinFilter(ERODE * 2 + 1)))
tmp = old.with_name(f"{name}.tmp.webp")
board.save(tmp, "WEBP", quality=90, alpha_quality=95)
digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
final = old.with_name(f"{name}.{digest}.webp")
tmp.replace(final)
if old != final:
    old.unlink()
exp[key] = exp[key].rsplit("/", 1)[0] + f"/{final.name}"
EXP_PATH.write_text(json.dumps(exp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(exp[key])
