"""The icon of the analyze action: the hexagon cut from the rival action card S.1 (apps/web/public/assets/solo), because the player aid and the
player board pictures are not in the asset repo (docs/asset-gaps.md). A hexagon mask removes the card's background. Run from the repo root; it
writes the picture into apps/web/public/assets/icons and adds it to `actionIcons` in apps/web/src/generated/assets.json."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "apps" / "web" / "src" / "generated" / "assets.json"
PUB = ROOT / "apps" / "web" / "public"
BOX = (46, 52, 100, 106)  # the hexagon on the 330 x 459 picture of card S.1
SIZE = 112
UP = 8

assets = json.loads(GEN.read_text(encoding="utf-8"))
card = Image.open(PUB / assets["rivalCards"]["S.1"].lstrip("/")).convert("RGBA")
icon = card.crop(BOX).resize((54 * UP, 54 * UP), Image.LANCZOS)
mask = Image.new("L", icon.size, 0)
pts = [(27, 1.5), (51.5, 15), (51.5, 40), (27, 53), (2.5, 40), (2.5, 15)]
ImageDraw.Draw(mask).polygon([(x * UP, y * UP) for x, y in pts], fill=255)
icon.putalpha(mask)
icon = icon.resize((SIZE, SIZE), Image.LANCZOS)
tmp = PUB / "assets" / "icons" / "analyze.tmp.webp"
icon.save(tmp, "WEBP", quality=90, alpha_quality=95)
digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
final = tmp.with_name(f"analyze.{digest}.webp")
tmp.replace(final)
assets["actionIcons"]["analyze"] = f"/assets/icons/{final.name}"
GEN.write_text(json.dumps(assets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(final)
