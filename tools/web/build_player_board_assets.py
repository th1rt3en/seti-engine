"""The player board picture and two printed icons cut from it: the income icon and the random card icon ("card ?").

Usage: python tools/web/build_player_board_assets.py PICTURE   (the picture of the player board supplied by the owner, 1581 x 1183)
Writes apps/web/public/assets/board/player-board.<hash>.webp, apps/web/public/assets/icons/income.*.webp and card-random.*.webp, and adds them to
apps/web/src/generated/assets.json (`playerBoard`, `printedIcons`). Only the converted WebP files are committed, never the picture itself."""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "apps" / "web" / "src" / "generated" / "assets.json"
OUT = ROOT / "apps" / "web" / "public" / "assets"
ICONS = {  # name -> box on the picture, output height
    "income": ((56, 87, 105, 136), 112),  # the rising chart on its badge
    "card-random": ((298, 124, 332, 172), 112),  # the white card with a question mark
}


def save(img: Image.Image, folder: str, name: str, **kw: int) -> str:
    folder_path = OUT / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    tmp = folder_path / f"{name}.tmp.webp"
    img.save(tmp, "WEBP", **kw)
    digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
    final = tmp.with_name(f"{name}.{digest}.webp")
    tmp.replace(final)
    return f"/assets/{folder}/{final.name}"


def cut(board: Image.Image, box: tuple[int, int, int, int], height: int) -> Image.Image:
    """Crop the icon and make everything outside its light shape transparent (the board's dark texture is flooded from the corners)."""
    crop = board.crop(box).convert("RGB")
    lum = crop.convert("L").point(lambda v: 255 if v > 105 else 0)
    flood = lum.copy()
    ImageDraw.floodfill(flood, (0, 0), 128)
    mask = flood.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = crop.convert("RGBA")
    out.putalpha(mask)
    width = round(height * out.width / out.height)
    return out.resize((width, height), Image.LANCZOS)


board = Image.open(sys.argv[1]).convert("RGBA")
assets = json.loads(GEN.read_text(encoding="utf-8"))
assets["playerBoard"] = {"src": save(board, "board", "player-board", quality=88, alpha_quality=90), "w": board.width, "h": board.height}
assets["printedIcons"] = {name: save(cut(board, box, h), "icons", name, quality=92, alpha_quality=95) for name, (box, h) in ICONS.items()}
GEN.write_text(json.dumps(assets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(assets["playerBoard"], assets["printedIcons"])
