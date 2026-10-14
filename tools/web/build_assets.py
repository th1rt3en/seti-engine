"""Prepare the images the website serves, optimized for a Cloudflare Worker's static assets (decision D30).

* Every card is cut from its sheet and saved as its own small WebP (300 px wide), so a player downloads only the cards on screen
  instead of two 2.8 MB sheets.
* Every file name carries a hash of its content, so the files can be cached for a year (`public/_headers`) and a changed image gets a new URL.
* The solar-system discs are saved once each.

Writes apps/web/public/assets/{cards,discs}/*.webp, apps/web/public/_headers, apps/web/src/generated/{assets,solar}.json and
packages/assets/PROVENANCE.md (CLAUDE.md rule 8: every imported asset is in the provenance manifest).
Run from the repo root: python tools/web/build_assets.py
"""

import hashlib
import io
import json
import math
import pathlib
import shutil
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "assets"
PUB = ROOT / "apps" / "web" / "public"
OUT = PUB / "assets"
GEN = ROOT / "apps" / "web" / "src" / "generated"

CARD_WIDTH = 440  # shown at 130 to 190 px, and about 400 px when hovered
CARD_QUALITY = 78

# tracker sheet name -> (source file, columns, rows)
SHEETS = {
    "cards-1.webp": ("cards-main-deck-en-sheet-1.png", 10, 7),
    "cards-2.webp": ("cards-main-deck-en-sheet-2.png", 10, 7),
    "anomalies.webp": ("cards-alien-anomalies-en-sheet.png", 5, 2),
    "centaurians.webp": ("cards-alien-centaurians-en-sheet.png", 5, 2),
    "exertians.webp": ("cards-alien-exertians-en-sheet.png", 5, 3),
    "mascamites.webp": ("cards-alien-mascamites-en-sheet.png", 5, 2),
    "oumuamua.webp": ("cards-alien-oumuamua-en-sheet.png", 5, 2),
}

# cards whose cell on the sheet is empty and that the owner supplied as single pictures
CARD_FILES = {"117": "card-lunar-gateway-en.png"}

# The hexagon icons of the main actions, cut from the player aid (x0, y0, x1, y1); the light page around each hexagon is made transparent.
ACTION_ICON_SOURCE = "player-aid-iconography-en.png"
ACTION_ICONS = {
    "launch": (1166, 205, 1278, 328),
    "orbit": (1166, 332, 1278, 455),
    "land": (1166, 453, 1278, 576),
    "scan": (1166, 570, 1278, 693),
}
ACTION_ICON_SIZE = 112

SCORE_ICON_BOX = (2987, 3941, 3107, 4061)  # the globe on the scoring track of the base board (next to the 100 and the 1), the icon of victory points
SCORE_ICON_RADIUS = 50
RIVAL_CARDS_SOURCE = "solo-rival-action-cards-sheet.png"  # 5 x 4 cells: S.1 to S.19, then the back
RIVAL_CARD_WIDTH = 330

BOARD_WIDTH = 1800  # the base board is 3507 x 5612 px; it is shown at most about 900 CSS px wide
BOARD_SOURCE = "main-board-assembled.png"

# The nearby-stars ring is four boards of two stars each, placed in a random order each game (`sector_order` of the game state).
# Position p of the assembled picture covers p * 90 to p * 90 + 90 degrees counter-clockwise from the 3 o'clock direction.
STAR_RING = "solar-sector-ring-nearby-stars-assembled.png"
STAR_BOARD_POSITION = {2: 0, 3: 1, 4: 2, 1: 3}  # board id -> position in the assembled picture

# The stars in the assembled picture of the ring, by the 45 degree wedge (counter-clockwise from the 3 o'clock direction) that each fills.
STAR_AT_HOME = ["Barnard's Star", "Sirius A", "Vega", "Procyon", "Beta Pictoris", "61 Virginis", "Proxima Centauri", "Kepler 22"]

SPECIES_BOARDS = {
    "back": "alien-board-back-face-down.png",
    "anomalies": "alien-board-anomalies.png",
    "centaurians": "alien-board-centaurians.png",
    "exertians": "alien-board-exertians.png",
    "mascamites": "alien-board-mascamites.png",
    "oumuamua": "alien-board-oumuamua.png",
}

# The lower part of the base board (publicity track, tech stacks, rotation dial) is printed upside down, so these parts are cut out and
# turned half a turn. The 12 slots of the tech board were found on the picture (x0, y0, x1, y1 of the dark space where the tiles lie), in
# the order they are printed (left to right); the glyph of a slot is the one printed in its corner.
TECH_SLOTS = {
    "computer": [(168, 4656, 352, 4904), (368, 4656, 552, 4904), (568, 4656, 752, 4904), (768, 4660, 952, 4908)],
    "probe": [(1000, 5000, 1176, 5248), (1200, 5004, 1376, 5248), (1400, 5004, 1576, 5252), (1600, 5004, 1772, 5252)],
    "telescope": [(168, 5192, 344, 5436), (368, 5192, 544, 5436), (568, 5192, 744, 5440), (768, 5196, 944, 5440)],
}
TECH_GLYPH_BY_SLOT = ["cross", "branch", "link", "dot"]  # left to right as printed (upside down)
TECH_MARGIN = (8, 205, 8, 22)  # left, top, right, bottom around the dark space: the tech's own icons are in the part below it once turned
PUBLICITY_BOX = (2636, 4150, 3330, 5420)  # the red 0 to 10 strip with the reminders beside it (3 publicity: 1 card, 6 publicity: research a tech)
BONUSES = {"vp3": "3vp", "card": "card", "energy": "energy", "publicity": "publicity"}
TILE_WIDTH = 175
MOON_SOURCE = "texture-moon-disc.png"  # the moon token that marks the next disc to rotate
MOON_SIZE = 160
TWO_POINT_SOURCE = "tab-green-2vp-first-taker-tile.png"  # the +2 tile on top of each tech stack (turned half a turn like the stacks it lies on)
RIVAL_BOARDS = ["1-2-star", "3-star", "4-star", "5-star"]
RIVAL_BOARD_WIDTH = 1500  # shown at most about 900 CSS px wide
OBJECTIVE_WIDTH = 240  # the objective tiles are 470 px squares, shown at about 120 px
CARD_BACK_SOURCE = "card-back-sunny-radio-telescope.png"  # the back of the main deck
BACKGROUND_SOURCE = "skybox-milky-way.jpg"
BACKGROUND_WIDTH = 2400

DISCS = {
    "disc-1": "solar-disc-1-mercury-venus-earth.png",
    "disc-2": "solar-disc-2-mars-asteroids.png",
    "disc-3": "solar-disc-3-jupiter-saturn.png",
    "disc-3-oumuamua": "solar-disc-3-with-oumuamua.png",
}


def save(im: Image.Image, folder: str, name: str, **opts: object) -> str:
    """Write the image under a name with its content hash; returns the URL path."""
    buf = io.BytesIO()
    im.save(buf, "WEBP", method=6, **opts)
    data = buf.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:10]
    target = OUT / folder / f"{name}.{digest}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/assets/{folder}/{name}.{digest}.webp"


def clear_background(im: Image.Image, tolerance: int = 40) -> Image.Image:
    """Make the part of the picture that is connected to its border and has the colour of the corner transparent (the page around an icon)."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    ref = px[0, 0]
    close = lambda c: max(abs(c[0] - ref[0]), abs(c[1] - ref[1]), abs(c[2] - ref[2])) <= tolerance  # noqa: E731
    seen = np.zeros((h, w), dtype=bool)
    todo = deque([*((x, y) for x in range(w) for y in (0, h - 1)), *((x, y) for y in range(h) for x in (0, w - 1))])
    while todo:
        x, y = todo.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y, x] or not close(px[x, y]):
            continue
        seen[y, x] = True
        px[x, y] = (0, 0, 0, 0)
        todo.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def hexagon_mask(im: Image.Image, margin: float = 1.0) -> Image.Image:
    """Keep only the pointy-top hexagon that fills the picture (the corners of the crop may hold parts of the page next to the icon)."""
    w, h = im.size
    radius, cx, cy = h / 2 + margin, w / 2, h / 2
    px = im.load()
    for y in range(h):
        for x in range(w):
            dx, dy = abs(x + 0.5 - cx), abs(y + 0.5 - cy)
            if dx > radius * math.sqrt(3) / 2 or dy > radius - dx / math.sqrt(3):
                px[x, y] = (0, 0, 0, 0)
    return im


def star_slots(ring: Image.Image) -> dict[str, dict[str, float]]:
    """The curved slot of every star (the cut-out where its data tokens lie), found as the holes of the ring picture.

    A slot is exactly as long as the data of its star (a token is as wide as the slot), so the tokens lie at equal steps along it, the first
    at the counter-clockwise end. For every star: the radius of the middle of the slot, the angles of its two ends relative to the middle of
    the star's wedge, and the width of the slot (all in pixels and degrees of the 1400 px picture).
    """
    alpha = np.array(ring)[:, :, 3]
    size = alpha.shape[0]
    centre = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size]
    radius = np.hypot(xx - centre, yy - centre)
    hole = (alpha < 128) & (radius > 505) & (radius < 680)
    step = 2
    small = hole[: size // step * step, : size // step * step].reshape(size // step, step, size // step, step).mean(axis=(1, 3)) > 0.6
    seen = np.zeros(small.shape, bool)
    found: list[tuple[float, float, float, float, float]] = []
    for y0 in range(small.shape[0]):
        for x0 in range(small.shape[1]):
            if not small[y0, x0] or seen[y0, x0]:
                continue
            queue, cells = deque([(y0, x0)]), []
            seen[y0, x0] = True
            while queue:
                y, x = queue.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < small.shape[0] and 0 <= nx < small.shape[1] and small[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            if len(cells) < 150:
                continue
            px = np.array([c[1] * step + step / 2 for c in cells])
            py = np.array([c[0] * step + step / 2 for c in cells])
            r = np.hypot(px - centre, py - centre)
            theta = np.degrees(np.arctan2(-(py - centre), px - centre)) % 360
            if theta.max() - theta.min() > 180:
                theta = np.where(theta > 180, theta - 360, theta)
            found.append((float(np.median(r)), float(r.max() - r.min()), float(theta.min()), float(theta.max()), float((theta.min() + theta.max()) / 2)))
    found.sort(key=lambda f: f[4] % 360)
    if len(found) != len(STAR_AT_HOME):
        raise SystemExit(f"expected {len(STAR_AT_HOME)} star slots, found {len(found)}")
    slots: dict[str, dict[str, float]] = {}
    for home, (r, width, lo, hi, _) in enumerate(found):
        wedge = 22.5 + 45 * home
        slots[STAR_AT_HOME[home]] = {"r": round(r, 1), "width": round(width, 1), "hi": round(hi - wedge, 2), "lo": round(lo - wedge, 2)}
    return slots


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)  # files of an earlier run have other hashes
    GEN.mkdir(parents=True, exist_ok=True)
    provenance: list[tuple[str, str, str]] = []

    sheets = {name: Image.open(SRC / src).convert("RGBA") for name, (src, _, _) in SHEETS.items()}
    defs = json.loads((ROOT / "docs/spec/data/card-definitions.json").read_text(encoding="utf-8"))
    cards: dict[str, str] = {}
    counts: dict[str, int] = {}
    for c in defs:
        if c["group"] not in ("base", "alien-base"):
            continue
        if c["id"] in CARD_FILES:
            card = Image.open(SRC / CARD_FILES[c["id"]]).convert("RGBA")
            card = card.resize((CARD_WIDTH, round(CARD_WIDTH * card.height / card.width)), Image.LANCZOS)
            cards[c["id"]] = save(card, "cards", c["id"], quality=CARD_QUALITY)
            provenance.append((CARD_FILES[c["id"]], cards[c["id"]], "single picture (its cell on the sheet is empty)"))
            continue
        sheet = pathlib.PurePosixPath(c["pos"][0]).name
        _, cols, rows = SHEETS[sheet]
        im = sheets[sheet]
        w, h = im.width / cols, im.height / rows
        row, col = c["pos"][1], c["pos"][2]
        card = im.crop((round(col * w), round(row * h), round((col + 1) * w), round((row + 1) * h)))
        card = card.resize((CARD_WIDTH, round(CARD_WIDTH * card.height / card.width)), Image.LANCZOS)
        cards[c["id"]] = save(card, "cards", c["id"], quality=CARD_QUALITY)
        counts[sheet] = counts.get(sheet, 0) + 1
    for sheet, (src, _, _) in SHEETS.items():
        provenance.append((src, f"apps/web/public/assets/cards/ ({counts.get(sheet, 0)} cards, {CARD_WIDTH} px wide)", "cut from the sheet"))

    discs: dict[str, str] = {}
    for name, src in DISCS.items():
        im = Image.open(SRC / src).convert("RGBA")
        discs[name] = save(im, "discs", name, quality=90)
        provenance.append((src, discs[name], f"{im.width}x{im.height}"))

    board_img = Image.open(SRC / BOARD_SOURCE).convert("RGBA")  # the cut-out edge of the board is transparent
    board_img = board_img.resize((BOARD_WIDTH, round(board_img.height * BOARD_WIDTH / board_img.width)), Image.LANCZOS)
    board = save(board_img, "board", "board", quality=80, alpha_quality=90)
    provenance.append((BOARD_SOURCE, board, f"{board_img.width}x{board_img.height}"))

    ring = Image.open(SRC / STAR_RING).convert("RGBA")
    half = ring.width // 2
    boxes = {0: (half, 0, ring.width, half), 1: (0, 0, half, half), 2: (0, half, half, ring.height), 3: (half, half, ring.width, ring.height)}
    star_boards: dict[str, str] = {}
    for board_id, pos in STAR_BOARD_POSITION.items():
        star_boards[str(board_id)] = save(ring.crop(boxes[pos]), "stars", f"star-board-{board_id}", quality=88, alpha_quality=95)
    provenance.append((STAR_RING, "apps/web/public/assets/stars/ (4 files)", "cut into its four boards"))

    (GEN / "slots.json").write_text(json.dumps(star_slots(ring), indent=1, sort_keys=True) + "\n", encoding="utf-8")

    species: dict[str, str] = {}
    for name, src in SPECIES_BOARDS.items():
        im = Image.open(SRC / src).convert("RGBA")
        species[name] = save(im, "species", name, quality=85)
        provenance.append((src, species[name], f"{im.width}x{im.height}"))

    base = Image.open(SRC / BOARD_SOURCE).convert("RGBA")
    base_for_icons = base

    stacks: dict[str, dict[str, object]] = {}
    for category, slots in TECH_SLOTS.items():
        for k, (x0, y0, x1, y1) in enumerate(slots):
            glyph = TECH_GLYPH_BY_SLOT[k]
            ml, mt, mr, mb = TECH_MARGIN
            crop = base.crop((x0 - ml, y0 - mt, x1 + mr, y1 + mb)).rotate(180)
            # where the tiles lie, in the turned picture
            pocket = {"x": mr, "y": mb, "w": x1 - x0, "h": y1 - y0}
            stacks[f"{category}-{glyph}"] = {"src": save(crop, "stacks", f"{category}-{glyph}", quality=82, alpha_quality=90), "w": crop.width, "h": crop.height, "pocket": pocket}
    provenance.append((BOARD_SOURCE, "apps/web/public/assets/stacks/ (12 files)", "each tech stack cut out and turned 180 degrees"))

    pub = base.crop(PUBLICITY_BOX).rotate(180)
    publicity = {"src": save(pub, "board", "publicity", quality=82, alpha_quality=90), "w": pub.width, "h": pub.height}
    provenance.append((BOARD_SOURCE, publicity["src"], "the publicity track cut out and turned 180 degrees"))

    tiles: dict[str, str] = {}
    for category in TECH_SLOTS:
        for glyph in TECH_GLYPH_BY_SLOT:
            for bonus_key, bonus_file in BONUSES.items():
                mid = "dot-2data" if (category, glyph) == ("telescope", "dot") else glyph  # the telescope dot tile has two data on it
                name = f"tech-tile-{category}-glyph-{mid}-{bonus_file}.png"
                tile = Image.open(SRC / name).convert("RGBA")
                tile = tile.resize((TILE_WIDTH, round(TILE_WIDTH * tile.height / tile.width)), Image.LANCZOS)
                tiles[f"{category}-{glyph}-{bonus_key}"] = save(tile, "tiles", f"{category}-{glyph}-{bonus_key}", quality=85, alpha_quality=90)
    provenance.append(("tech-tile-<category>-glyph-<glyph>-<bonus>.png (48 files)", "apps/web/public/assets/tiles/ (48 files)", f"{TILE_WIDTH} px wide"))

    two_point_img = Image.open(SRC / TWO_POINT_SOURCE).convert("RGBA").rotate(180)
    two_point = save(two_point_img, "tiles", "two-point", quality=90, alpha_quality=95)
    provenance.append((TWO_POINT_SOURCE, two_point, "the +2 first-taker tile"))

    moon_img = Image.open(SRC / MOON_SOURCE).convert("RGBA").resize((MOON_SIZE, MOON_SIZE), Image.LANCZOS)
    moon = save(moon_img, "discs", "moon", quality=90, alpha_quality=95)
    provenance.append((MOON_SOURCE, moon, "the moon token that marks the next disc to rotate"))

    back_img = Image.open(SRC / CARD_BACK_SOURCE).convert("RGBA")
    back_img = back_img.resize((300, round(300 * back_img.height / back_img.width)), Image.LANCZOS)
    card_back = save(back_img, "cards", "back", quality=82)
    provenance.append((CARD_BACK_SOURCE, card_back, "back of the main deck (the draw piles of the rounds)"))

    aid = Image.open(SRC / ACTION_ICON_SOURCE).convert("RGBA")
    action_icons: dict[str, str] = {}
    for name, box in ACTION_ICONS.items():
        icon = hexagon_mask(clear_background(aid.crop(box)), margin=-3)
        icon = icon.resize((ACTION_ICON_SIZE, round(ACTION_ICON_SIZE * icon.height / icon.width)), Image.LANCZOS)
        action_icons[name] = save(icon, "icons", name, quality=90, alpha_quality=95)
        provenance.append((ACTION_ICON_SOURCE, action_icons[name], f"the icon of the {name} action, cut from the player aid"))

    globe = base_for_icons.crop(SCORE_ICON_BOX)
    mask = Image.new("L", globe.size, 0)
    ImageDraw.Draw(mask).ellipse((globe.width / 2 - SCORE_ICON_RADIUS, globe.height / 2 - SCORE_ICON_RADIUS, globe.width / 2 + SCORE_ICON_RADIUS, globe.height / 2 + SCORE_ICON_RADIUS), fill=255)
    globe.putalpha(mask)
    globe = globe.crop((int(globe.width / 2 - SCORE_ICON_RADIUS), int(globe.height / 2 - SCORE_ICON_RADIUS), int(globe.width / 2 + SCORE_ICON_RADIUS), int(globe.height / 2 + SCORE_ICON_RADIUS))).resize((96, 96), Image.LANCZOS)
    score_icon = save(globe, "icons", "score", quality=92, alpha_quality=95)
    provenance.append((BOARD_SOURCE, score_icon, "the globe of the scoring track, the icon of victory points"))

    sheet = Image.open(SRC / RIVAL_CARDS_SOURCE).convert("RGBA")
    cw, ch = sheet.width / 5, sheet.height / 4
    rival_cards: dict[str, str] = {}
    for k in range(20):
        col, row = k % 5, k // 5
        card = sheet.crop((round(col * cw), round(row * ch), round((col + 1) * cw), round((row + 1) * ch)))
        card = card.resize((RIVAL_CARD_WIDTH, round(RIVAL_CARD_WIDTH * card.height / card.width)), Image.LANCZOS)
        rival_cards["back" if k == 19 else f"S.{k + 1}"] = save(card, "solo", f"rival-card-{'back' if k == 19 else k + 1}", quality=84, alpha_quality=92)
    provenance.append((RIVAL_CARDS_SOURCE, "apps/web/public/assets/solo/ (20 files)", "each action card of the rival and its back, cut from the sheet"))

    gold: dict[str, dict[str, object]] = {}
    for tile in json.loads((ROOT / "services/engine/src/seti_engine/data/gold-tiles.json").read_text(encoding="utf-8"))["tiles"]:
        im = Image.open(SRC / f"{tile['image']}.png").convert("RGBA")  # 550 x 488: shown at about 380 px on the board and 480 px when hovered
        gold[f"{tile['tile']}-{tile['side']}"] = {
            "src": save(im, "tiles", f"gold-{tile['tile']}-{tile['side']}", quality=88, alpha_quality=95),
            "per": tile["per"],
            "values": tile["values"],
        }
    provenance.append(("gold-scoring-tile-*.png", "apps/web/public/assets/tiles/ (8 files)", "the gold scoring tiles, 550 px wide"))

    alien_backs: dict[str, str] = {}
    for species_name in ("anomalies", "centaurians", "exertians", "mascamites", "oumuamua"):
        im = Image.open(SRC / f"card-back-alien-{species_name}.png").convert("RGBA")
        im = im.resize((300, round(300 * im.height / im.width)), Image.LANCZOS)
        alien_backs[species_name] = save(im, "cards", f"back-{species_name}", quality=84, alpha_quality=92)
    provenance.append(("card-back-alien-<species>.png", "apps/web/public/assets/cards/ (5 files)", "the backs of the alien decks, 300 px wide"))

    tech_fronts: dict[str, str] = {}
    for category, techs in json.loads((ROOT / "services/engine/src/seti_engine/data/tech-board.json").read_text(encoding="utf-8"))["stacks"].items():
        for tech in techs:
            im = Image.open(SRC / f"tech-tile-{tech['front']}.png").convert("RGBA")  # 175 x 246: the front of a tech tile, shown on the player board
            tech_fronts[f"{category}-{tech['glyph']}"] = save(im, "tiles", f"front-{category}-{tech['glyph']}", quality=90, alpha_quality=95)
    provenance.append(("tech-tile-front-*.png (12 files)", "apps/web/public/assets/tiles/ (12 files)", "the fronts of the tech tiles"))

    rival_boards: dict[str, str] = {}
    for name in RIVAL_BOARDS:
        im = Image.open(SRC / f"rival-board-{name}.png").convert("RGBA")
        im = im.resize((RIVAL_BOARD_WIDTH, round(RIVAL_BOARD_WIDTH * im.height / im.width)), Image.LANCZOS)
        rival_boards[name] = save(im, "solo", f"rival-board-{name}", quality=84, alpha_quality=90)
        provenance.append((f"rival-board-{name}.png", rival_boards[name], f"the solo rival's board, {RIVAL_BOARD_WIDTH} px wide"))

    objectives: dict[str, str] = {}
    tiles_data = json.loads((ROOT / "services/engine/src/seti_engine/data/objectives.json").read_text(encoding="utf-8"))
    for ob in tiles_data["objectives"]:
        im = Image.open(SRC / f"{ob['image']}.png").convert("RGBA")
        im = im.resize((OBJECTIVE_WIDTH, round(OBJECTIVE_WIDTH * im.height / im.width)), Image.LANCZOS)
        objectives[ob["id"]] = save(im, "solo", f"objective-{ob['id']}", quality=86, alpha_quality=92)
    provenance.append(("solo-objective-L*-*.png", f"apps/web/public/assets/solo/ ({len(objectives)} objectives)", f"{OBJECTIVE_WIDTH} px wide"))

    sky = Image.open(SRC / BACKGROUND_SOURCE).convert("RGB")
    sky = sky.resize((BACKGROUND_WIDTH, round(BACKGROUND_WIDTH * sky.height / sky.width)), Image.LANCZOS)
    background = save(sky, "bg", "milky-way", quality=66)
    provenance.append((BACKGROUND_SOURCE, background, "page background"))

    (GEN / "assets.json").write_text(
        json.dumps(
            {"cards": cards, "discs": discs, "board": board, "starBoards": star_boards, "species": species, "stacks": stacks,
             "publicity": publicity, "tiles": tiles, "moon": moon, "twoPoint": two_point, "cardBack": card_back, "background": background,
             "rivalBoards": rival_boards, "objectives": objectives, "actionIcons": action_icons, "scoreIcon": score_icon, "rivalCards": rival_cards, "gold": gold, "alienBacks": alien_backs, "techFronts": tech_fronts},
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    stale = GEN / "cardart.json"  # the sprite-sheet map of the earlier version
    if stale.exists():
        stale.unlink()

    solar = json.loads((ROOT / "services/engine/src/seti_engine/data/solar-system.json").read_text(encoding="utf-8"))
    (GEN / "solar.json").write_text(json.dumps({"ring4": solar["wheels"]["4"]["4"]}, indent=1) + "\n", encoding="utf-8")

    # Cloudflare's static assets read this file: the names carry the hash of the content, so they never change.
    (PUB / "_headers").write_text(
        "/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n\n/_next/static/*\n  Cache-Control: public, max-age=31536000, immutable\n",
        encoding="utf-8",
    )

    prov = [
        "# Asset provenance", "",
        "Images the website serves, converted from the owner-supplied files in `assets/` (labels in `assets/MANIFEST.md`; origin and licence status in",
        "`docs/asset-gaps.md`, section Licensing). Each card is cut from its sheet and saved on its own; the file names carry a hash of the content.",
        "Generated by `tools/web/build_assets.py`; do not edit by hand.", "", "| Source file | Served as | Note |", "|---|---|---|",
    ]
    prov += [f"| `assets/{s}` | `{o}` | {n} |" for s, o, n in provenance]
    (ROOT / "packages/assets/PROVENANCE.md").write_text("\n".join(prov) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.rglob("*.webp"))
    print(f"cards: {len(cards)}, discs: {len(discs)}, {total / 1e6:.1f} MB in all")


if __name__ == "__main__":
    main()
