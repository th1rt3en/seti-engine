"""Convert the owner-supplied Space Agencies pictures to small WebP files for the website (D35). Only the WebP files are committed; the
originals (large JPG and PNG sheets) stay outside the repository.

Usage: python tools/web/build_expansion_assets.py <folder with the unzipped sheets> [<more folders>]
(the folders hold the files named in SHEETS, SINGLES and TOKENS below; they are found by file name anywhere under the given folders).
Writes apps/web/public/assets/expansion/**.webp, apps/web/src/generated/expansion-assets.json and packages/assets/PROVENANCE-expansion.md.
"""

import hashlib
import io
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "apps" / "web" / "public" / "assets" / "expansion"
GEN = ROOT / "apps" / "web" / "src" / "generated"
CARD_W = 440

# sheet file -> (prefix, folder, cell width, cell height, columns, rows, number of cells used)
SHEETS = {
    "space-agencies-main-deck-cards.jpg": ("main", "cards", 744, 1040, 10, 7, 46),
    "quickstart-cards.jpg": ("qs", "quickstart", 744, 1040, 6, 4, 21),
    "glyphids-cards.jpg": ("gly", "glyphids", 744, 1040, 5, 2, 10),
    "amoeba-cards.jpg": ("amo", "amoeba", 744, 1040, 5, 2, 10),
    "arkhos-exploration-cards.jpg": ("exp", "arkhos", 1040, 744, 3, 3, 9),
    "arkhos-security-cards-1.jpg": ("sec1", "arkhos", 744, 1040, 2, 2, 4),
    "arkhos-security-cards-2.jpg": ("sec2", "arkhos", 744, 1040, 2, 2, 4),
    "arkhos-security-cards-3.jpg": ("sec3", "arkhos", 744, 1040, 2, 2, 4),
    "space-agencies-rival-action-cards.jpg": ("rival", "solo", 744, 1042, 2, 2, 4),
    "space-agencies-organizations.jpg": ("org", "organizations", 1384, 1040, 6, 2, 11),
}
# whole pictures: file -> (folder, name, width)
SINGLES = {
    "quickstart-card-back.jpg": ("quickstart", "back", CARD_W),
    "glyphid-card-back.jpg": ("glyphids", "card-back", CARD_W),
    "amoeba-card-back.jpg": ("amoeba", "card-back", CARD_W),
    "arkhos-exploration-cards-back.jpg": ("arkhos", "exploration-back", CARD_W),
    "arkhos-security-back-blue.jpg": ("arkhos", "security-back-blue", CARD_W),
    "arkhos-security-back-pink.jpg": ("arkhos", "security-back-pink", CARD_W),
    "arkhos-security-back-yellow.jpg": ("arkhos", "security-back-yellow", CARD_W),
    "space-agencies-long-term-objective-1.jpg": ("objectives", "long-term-1", 380),
    "space-agencies-long-term-objective-2.jpg": ("objectives", "long-term-2", 380),
    "space-agencies-long-term-objective-3.jpg": ("objectives", "long-term-3", 380),
    "alien-board-arkhos.png": ("boards", "arkhos", 500),
    "alien-board-glyphids.png": ("boards", "glyphids", 777),
    "alien-board-amoeba.png": ("boards", "amoeba", 573),
    "alien-board-glyphids-track-variant-a.png": ("boards", "glyphids-track-a", 750),
    "alien-board-glyphids-track-variant-b.png": ("boards", "glyphids-track-b", 750),
    "alien-board-glyphids-track-variant-c.png": ("boards", "glyphids-track-c", 750),
}
# small tokens and icons: kept at their size, with transparency
TOKENS = [
    "token-signal.png",
    "token-futurespan.png",
    "icon-credit.png",
    "icon-energy.png",
    "icon-exofossil.png",
    "icon-publicity.png",
    "icon-score.png",
    *(f"xenolab-tile-{i}{s}.png" for i in (1, 2, 3) for s in ("", "-back")),
    *(f"organelle-token-{n}.png" for n in ("1-card", "1-data", "1-pub", "2-score", "4-score", "back")),
    *(f"glyphids-token-{c}.png" for c in ("back", "black", "bue", "cyan", "orange", "pink", "red", "yellow")),
]


def find(folders: list[pathlib.Path], name: str) -> pathlib.Path:
    for f in folders:
        hits = sorted(f.rglob(name))
        if hits:
            return hits[0]
    raise FileNotFoundError(name)


def save(im: Image.Image, folder: str, name: str, width: int | None, quality: int = 80) -> str:
    if width is not None and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=6)
    digest = hashlib.sha256(buf.getvalue()).hexdigest()[:10]
    d = OUT / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.{digest}.webp").write_bytes(buf.getvalue())
    return f"/assets/expansion/{folder}/{name}.{digest}.webp"


def main(folders: list[pathlib.Path]) -> None:
    for old in OUT.rglob("*.webp") if OUT.exists() else []:
        old.unlink()
    manifest: dict[str, str] = {}
    prov = [
        "# Provenance of the Space Agencies pictures",
        "",
        "Owner-supplied sheets (czechgames.com pictures), cut and converted by `tools/web/build_expansion_assets.py`. Only the WebP results are in",
        "the repository; the original files are not. Do not edit by hand.",
        "",
        "| Source file | Served as |",
        "|---|---|",
    ]
    for fname, (prefix, folder, cw, ch, cols, rows, used) in SHEETS.items():
        sheet = Image.open(find(folders, fname)).convert("RGB")
        width = 560 if prefix == "org" else CARD_W
        for k in range(used):
            r, c = divmod(k, cols)
            cell = sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            manifest[f"{prefix}-{k:02d}"] = save(cell, folder, f"{prefix}-{k:02d}", width)
        prov.append(f"| `{fname}` | `apps/web/public/assets/expansion/{folder}/{prefix}-NN.<hash>.webp` ({used} cells) |")
    # the data icon (a blue diamond with binary digits) is not among the supplied icons: it is cut from the line "Don't gain any (data) from them" of
    # the main-deck card Pandora Satellite (tile 37 of the sheet), the white around the diamond made transparent
    main = Image.open(find(folders, "space-agencies-main-deck-cards.jpg")).convert("RGB")
    r_, c_ = divmod(37, 10)
    tile = main.crop((c_ * 744, r_ * 1040, (c_ + 1) * 744, (r_ + 1) * 1040)).crop((350, 782, 428, 860))
    mask = Image.new("L", tile.size, 0)
    cx, cy, half = 38.0, 38.5, 31.5
    ImageDraw.Draw(mask).polygon([(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)], fill=255)
    icon = tile.convert("RGBA")
    icon.putalpha(mask.filter(ImageFilter.GaussianBlur(0.7)))
    manifest["tokens/icon-data"] = save(icon.crop((4, 4, 73, 74)), "tokens", "icon-data", None, 90)
    prov.append(f"| `space-agencies-main-deck-cards.jpg` (Pandora Satellite, the data icon in its text) | `{manifest['tokens/icon-data']}` |")
    # the fourth arrangement of the translation board strips (top strip of picture a, bottom strip of picture b) has no picture: it is composed
    # from the two (the owner asked for four pictures, A-044)
    top = Image.open(find(folders, "alien-board-glyphids-track-variant-a.png")).convert("RGBA")
    bottom = Image.open(find(folders, "alien-board-glyphids-track-variant-b.png")).convert("RGBA")
    composed = bottom.copy()
    composed.paste(top.crop((0, 0, top.width, 430)), (0, 0))
    manifest["boards/glyphids-track-d"] = save(composed, "boards", "glyphids-track-d", None, 85)
    prov.append(f"| `alien-board-glyphids-track-variant-a.png` (above y 430) and `-b.png` (below) | `{manifest['boards/glyphids-track-d']}` (composed) |")
    for fname, (folder, name, width) in SINGLES.items():
        manifest[f"{folder}/{name}"] = save(Image.open(find(folders, fname)).convert("RGB"), folder, name, width)
        prov.append(f"| `{fname}` | `{manifest[f'{folder}/{name}']}` |")
    for fname in TOKENS:
        stem = fname.rsplit(".", 1)[0]
        manifest[f"tokens/{stem}"] = save(Image.open(find(folders, fname)).convert("RGBA"), "tokens", stem, None, 90)
        prov.append(f"| `{fname}` | `{manifest[f'tokens/{stem}']}` |")
    GEN.mkdir(parents=True, exist_ok=True)
    (GEN / "expansion-assets.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "packages" / "assets" / "PROVENANCE-expansion.md").write_text("\n".join(prov) + "\n", encoding="utf-8")
    print(len(manifest), "files")


if __name__ == "__main__":
    main([pathlib.Path(a) for a in sys.argv[1:]])
