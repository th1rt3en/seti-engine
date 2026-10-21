"""Cuts the publicity track out of the main board picture (the lower part of the board is printed upside down, so it is turned 180 degrees). The box is the one
of tools/web/build_assets.py, 80 pixels taller at the lower end of the turned picture, so that the publicity icon under the 0 is whole. The page's coordinates
of the markers (`PUBLICITY_CELL`, measured from the top of the picture) do not change. Needs Pillow.

    python crop_publicity.py <assets/main-board-assembled.png> <apps/web/public/assets/board>

Prints the entry for `apps/web/src/generated/assets.json`. The file name carries the first 10 characters of the sha256 of its bytes, like the others.
"""

import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BOX = (2636, 4070, 3330, 5420)  # build_assets.py has (2636, 4150, 3330, 5420): the top of the box is the bottom of the turned picture
src, out = Path(sys.argv[1]), Path(sys.argv[2])
pub = Image.open(src).crop(BOX).rotate(180)
buf = io.BytesIO()
pub.save(buf, "WEBP", method=6, quality=82, alpha_quality=90)
data = buf.getvalue()
name = f"publicity.{hashlib.sha256(data).hexdigest()[:10]}.webp"
(out / name).write_bytes(data)
print(json.dumps({"src": f"/assets/board/{name}", "w": pub.width, "h": pub.height}))
