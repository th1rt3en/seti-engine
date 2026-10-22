"""Cuts the name of each organization out of the top left corner of its card, for the places that show an organization by its printed name (the stats page).

    python tools/assets/crop_org_names.py

Reads the pictures of the eleven organization cards (`org-00` .. `org-10` in apps/web/src/generated/expansion-assets.json, 560 x 421), cuts the same box from
each (the name on the coloured banner, without the tagline under it), so that all the names have the same size, and writes
apps/web/public/assets/expansion/organizations/name-org-NN.<hash>.webp and apps/web/src/generated/org-names.json ({"org-NN": "/assets/..."}). The file name
carries the first 10 characters of the sha256 of its bytes, like the others. Needs Pillow. The generated json is its own file, so that rebuilding the
expansion assets (tools/web/build_expansion_assets.py) does not remove it.
"""

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
BOX = (0, 3, 262, 31)  # left, top, right, bottom: the banner with the name on one line; the tagline starts below it
EXP = json.loads((WEB / "src" / "generated" / "expansion-assets.json").read_text(encoding="utf-8"))
OUT = WEB / "public" / "assets" / "expansion" / "organizations"

names: dict[str, str] = {}
for key in sorted(k for k in EXP if k.startswith("org-")):
    src = WEB / "public" / EXP[key].lstrip("/")
    card = Image.open(src).convert("RGB")
    assert card.size == (560, 421), (key, card.size)
    crop = card.crop(BOX)
    buf = io.BytesIO()
    crop.save(buf, "WEBP", method=6, quality=90)
    data = buf.getvalue()
    for old in OUT.glob(f"name-{key}.*.webp"):
        old.unlink()
    name = f"name-{key}.{hashlib.sha256(data).hexdigest()[:10]}.webp"
    (OUT / name).write_bytes(data)
    names[key] = f"/assets/expansion/organizations/{name}"
(WEB / "src" / "generated" / "org-names.json").write_text(json.dumps(names, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(len(names), "names cut,", BOX[2] - BOX[0], "x", BOX[3] - BOX[1])
