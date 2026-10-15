"""The pictures of the Anomaly tokens (ALIEN-ANO-01), converted to WebP and added to apps/web/src/generated/assets.json (`anomalyTokens`, keyed by the
column color and the side: "blue-0").

Usage: python tools/web/build_anomaly_tokens.py DIR   where DIR holds the pictures supplied by the owner under the names in FILES.
Only the converted WebP files are committed, never the originals."""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "apps" / "web" / "src" / "generated" / "assets.json"
OUT = ROOT / "apps" / "web" / "public" / "assets" / "species"
# file -> (column color, side as in docs/spec/data/alien-boards.json, quarter turns counter-clockwise to make the colored end point left)
FILES = {
    "3.png": ("blue", 1, 0),  # 1 energy
    "4.png": ("blue", 0, 0),  # 1 data
    "5.png": ("pink", 1, 0),  # 4 points
    "6.png": ("yellow", 1, 0),  # 2 publicity
    "7.png": ("pink", 0, 1),  # 1 credit (the picture is upright)
    "8.png": ("yellow", 0, 0),  # 1 card (not supplied as a file yet)
}
WIDTH = 264

src = Path(sys.argv[1])
assets = json.loads(GEN.read_text(encoding="utf-8"))
tokens: dict[str, str] = {}
OUT.mkdir(parents=True, exist_ok=True)
for name, (color, side, turns) in FILES.items():
    path = src / name
    if not path.exists():
        print("missing", name, "-> the token is drawn instead")
        continue
    img = Image.open(path).convert("RGBA")
    if turns:
        img = img.rotate(90 * turns, expand=True)
    img = img.resize((WIDTH, round(WIDTH * img.height / img.width)), Image.LANCZOS)
    tmp = OUT / "anomaly.tmp.webp"
    img.save(tmp, "WEBP", quality=90, alpha_quality=95)
    digest = hashlib.sha1(tmp.read_bytes()).hexdigest()[:10]
    final = tmp.with_name(f"anomaly-{color}-{side}.{digest}.webp")
    tmp.replace(final)
    tokens[f"{color}-{side}"] = f"/assets/species/{final.name}"
assets["anomalyTokens"] = tokens
GEN.write_text(json.dumps(assets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(tokens)
