// Where things are on the base board picture (assets/main-board-assembled.png, 3507 x 5612 px). Every number was measured on that picture:
// the centre is the middle of the sun hole, the rings are the printed circles of the base disc, the score spaces follow the gold spaces
// 25, 50 and 70. Nothing here is a game rule: the engine says where a probe or a marker is, this file only says where that is on the picture.

export const BOARD = { w: 3507, h: 5612 };
export const CENTER = { x: 1752.5, y: 3062.6 };

/** The three discs are scans of different resolution: board pixels per image pixel, and the size of each image. */
export const DISC = {
  1: { scale: 1.886, size: 396 },
  2: { scale: 1.886, size: 608 },
  3: { scale: 1.54, size: 1008 },
} as const;

/** Sector `s` covers 45 s to 45 s + 45 degrees counter-clockwise from the 3 o'clock direction (the engine's convention, BOARD-10). */
export const sectorDegrees = (sector: number): number => 22.5 + 45 * sector;

/** The printed circles that bound ring 1 to 4: from the edge of the sun to the end of ring 1, and so on (a space is the part of a ring in one sector). */
export const RING_BOUNDS = [150, 372, 573, 771, 975];

/** The middle of ring 1 to 4 (index 0 is unused), in board pixels from the centre. */
export const RING_RADIUS = [0, 270, 485, 660, 870];

/** The ring of nearby stars: four boards of two stars (a 1400 px picture cut into four 700 px quarters, drawn at this scale). */
export const STAR = { scale: 2.02, quarter: 700, midRadius: 1193 };
/**
 * Where the markers of a sector's winners lie, as places on the 700 px picture of the star board the star is on (measured on the pictures).
 * `first` is the space of the first win reward, where the first winner's marker lies and covers it (FAQ-12, SECTOR-14); a star whose first and later
 * rewards are alike has none (Proxima Centauri, Sirius A, 61 Virginis): all its winners lie on the capsule. From the second win on, the markers follow the printed capsule beside the star, which has three small circles (`guide`, the one nearest the star first), like orbiters
 * and landers follow the guide line of a planet; more markers than circles go on in the same direction at the same distance.
 */
export const WIN_SPOTS: Record<string, { board: number; first?: [number, number]; guide: [number, number][] }> = {
  "Proxima Centauri": {
    board: 1,
    first: [205, 613],
    guide: [
      [161, 596],
      [201, 581],
      [242, 565],
    ],
  },
  "Kepler 22": {
    board: 1,
    first: [568, 250],
    guide: [
      [537, 312],
      [514, 348],
      [490, 382],
    ],
  },
  "Sirius A": {
    board: 2,
    first: [313, 128],
    guide: [
      [325, 171],
      [287, 152],
      [248, 133],
    ],
  },
  "Barnard's Star": {
    board: 2,
    first: [565, 458],
    guide: [
      [596, 524],
      [608, 566],
      [618, 606],
    ],
  },
  Vega: {
    board: 3,
    first: [455, 133],
    guide: [
      [522, 110],
      [564, 100],
      [606, 90],
    ],
  },
  Procyon: {
    board: 3,
    first: [130, 450],
    guide: [
      [162, 386],
      [185, 351],
      [210, 316],
    ],
  },
  "Beta Pictoris": {
    board: 4,
    first: [132, 240],
    guide: [
      [108, 178],
      [95, 136],
      [82, 105],
    ],
  },
  "61 Virginis": {
    board: 4,
    first: [383, 567],
    guide: [
      [371, 525],
      [410, 546],
      [449, 565],
    ],
  },
};

/** The `n`-th place (0 is the second win) of a star's capsule; beyond the third circle the line goes on at the same distance. */
export function winGuideSpot(guide: [number, number][], n: number): [number, number] {
  const last = guide.length - 1;
  const a = guide[last - 1] ?? guide[0];
  const b = guide[last];
  if (!a || !b) return [0, 0];
  if (n <= last) return guide[n] ?? b;
  return [b[0] + (b[0] - a[0]) * (n - last), b[1] + (b[1] - a[1]) * (n - last)];
}

/** Board id -> its position (0 to 3) in the assembled picture of the ring. */
export const STAR_BOARD_HOME: Record<number, number> = { 2: 0, 3: 1, 4: 2, 1: 3 };

export const polar = (radius: number, degrees: number): { x: number; y: number } => ({
  x: CENTER.x + radius * Math.cos((degrees * Math.PI) / 180),
  y: CENTER.y - radius * Math.sin((degrees * Math.PI) / 180),
});

/** The score track: spaces 1 to 100 run clockwise around the board; 0 and 100 share the space at the bottom right. */
export const TRACK = { radius: 1525, degrees50: 145.53, step: 3.592 };
export const scoreDegrees = (score: number): number => TRACK.degrees50 - TRACK.step * ((score % 100 === 0 ? 100 : score % 100) - 50);

/** The publicity track is shown on its own, cut out of the board and turned half a turn (see tools/web/build_assets.py): where the cell of
 * publicity 0 is in that picture (450 x 1270 px) and how far apart the cells are; the players' markers sit side by side. */
export const PUBLICITY_CELL = { x0: 130, dx: 80, y0: 1169, dy: 110.3 };

/** The three big empty circles of the rotation dial, where the moon token lies to mark the disc that turns next. The sequence ring 1, rings 1+2,
 * rings 1+2+3 runs counter-clockwise like the rotation itself: top left (the printed starting space), bottom left, right. */
export const DIAL: Record<1 | 2 | 3, { x: number; y: number }> = {
  1: { x: 2133, y: 4851 },
  2: { x: 2131, y: 5186 },
  3: { x: 2435, y: 5020 },
};
/** The circles are about 216 px wide: the moon token is drawn a little smaller so that the ring of the circle shows. */
export const DIAL_POCKET = 190;

/** The two round pockets printed next to the 20 and the 30 space, where the neutral markers wait (2 of them with 1 or 2 players, 1 with 3, none
 * with 4). The one that is taken first is listed first. */
export const NEUTRAL_POCKETS: Record<"20" | "30", { x: number; y: number }[]> = {
  "20": [
    { x: 1240, y: 4643 },
    { x: 1340, y: 4670 },
  ],
  "30": [
    { x: 406, y: 4037 },
    { x: 468, y: 4118 },
  ],
};

/** The planets: where the picture of each one is, and its radius. Orbiters and landers are drawn on the planet. */
export const PLANET: Record<string, { x: number; y: number; r: number }> = {
  mercury: { x: 379, y: 1678, r: 126 },
  venus: { x: 463, y: 1108, r: 182 },
  mars: { x: 990, y: 1178, r: 168 },
  jupiter: { x: 1537, y: 682, r: 280 },
  saturn: { x: 2236, y: 982, r: 196 },
  uranus: { x: 2960, y: 982, r: 163 },
  neptune: { x: 3058, y: 1543, r: 168 },
};

/**
 * The orbit of each planet: a green guide line starts at the bonus space of the first orbiter (upper left of the planet) and runs clockwise over the
 * planet. `bonus` is where the bonus space lies, measured from the planet's centre in planet radii (read from the picture of the board). The
 * orbiters lie on the circle through it around the planet, the first one covering the bonus space.
 */
export const ORBIT_BONUS: Record<string, [number, number]> = {
  mercury: [-1.0, -1.11],
  venus: [-0.88, -0.89],
  mars: [-0.93, -0.97],
  jupiter: [-0.84, -0.85],
  saturn: [-0.83, -1.04],
  uranus: [-0.83, -1.05],
  neptune: [-0.96, -0.9],
};
export const ORBIT_SPACING = 96; // between two orbiters along the ring, in board pixels

/** Where the `k`-th orbiter (0 is the first, on the bonus space) of a planet lies. */
export function orbitSlot(planet: string, k: number): { x: number; y: number } | null {
  const pos = PLANET[planet];
  const bonus = ORBIT_BONUS[planet];
  if (!pos || !bonus) return null;
  const dx = bonus[0] * pos.r;
  const dy = bonus[1] * pos.r;
  const radius = Math.hypot(dx, dy);
  const angle = Math.atan2(dy, dx) + (k * ORBIT_SPACING) / radius; // clockwise on the screen: over the top of the planet
  return { x: pos.x + radius * Math.cos(angle), y: pos.y + radius * Math.sin(angle) };
}

// The landing spaces, measured on the 1800 px wide picture of the board and scaled to board pixels.
const F = BOARD.w / 1800;
const at = (x: number, y: number): { x: number; y: number } => ({ x: x * F, y: y * F });
/**
 * The round landing spaces of each planet: the first lander covers the first circle (its data bonus), the second lander the second (Mars has
 * two). `hex` is the landing reward of the planet; landers beyond the circles lie to the right of it.
 */
export const LAND_SPACES: Record<string, { circles: { x: number; y: number }[]; hex: { x: number; y: number } }> = {
  mercury: { circles: [at(163, 886)], hex: at(197, 860) },
  venus: { circles: [at(195, 608)], hex: at(240, 577) },
  mars: { circles: [at(482, 652), at(457, 607)], hex: at(510, 605) },
  jupiter: { circles: [at(727, 393)], hex: at(790, 355) },
  saturn: { circles: [at(1108, 545)], hex: at(1148, 503) },
  uranus: { circles: [at(1483, 540)], hex: at(1517, 505) },
  neptune: { circles: [at(1522, 843)], hex: at(1567, 803) },
};

/**
 * Landers beyond the circles follow the gold guide line of the planet: a lane that starts at the landing circles and curls up and over the planet,
 * around its landing reward. The lane is modelled as an arc around the reward through the last circle, running clockwise on the screen.
 */
export const LAND_ARC = { spacing: 96 }; // the distance between two landers along the lane, in board pixels

/** Where the `k`-th lander (0 is the first) of a planet lies: on its landing circle, the later ones along the gold guide line. */
export function landSlot(planet: string, k: number): { x: number; y: number } | null {
  const land = LAND_SPACES[planet];
  if (!land) return null;
  const circle = land.circles[k];
  if (circle) return circle;
  const last = land.circles[land.circles.length - 1] ?? land.hex;
  const radius = Math.hypot(last.x - land.hex.x, last.y - land.hex.y) || 1;
  const angle = Math.atan2(last.y - land.hex.y, last.x - land.hex.x) + ((k - land.circles.length + 1) * LAND_ARC.spacing) / radius;
  return { x: land.hex.x + radius * Math.cos(angle), y: land.hex.y + radius * Math.sin(angle) };
}

/** The moons, by the lower-case first word of their name in the engine's data: the round landing space of each. */
export const MOON: Record<string, { x: number; y: number }> = {
  io: at(953, 336),
  europa: at(944, 430),
  callisto: at(697, 516),
  ganymede: at(843, 507),
  enceladus: at(1287, 505),
  titan: at(1252, 585),
  titania: at(1618, 535),
  triton: at(1657, 893),
  phobos: at(434, 701),
};

/** The three discovery spaces (pink, yellow, blue) of each alien species: the left group is the first species, the right group the second. */
export const DISCOVERY: { x: number; y: number }[][] = [
  [
    { x: 385, y: 295 },
    { x: 680, y: 370 },
    { x: 975, y: 295 },
  ],
  [
    { x: 2525, y: 295 },
    { x: 2820, y: 370 },
    { x: 3115, y: 295 },
  ],
];

/**
 * The species boards sit above the base board, their three bottom cut-outs around the three discovery spaces of the notch below (the board and
 * its notches are printed so). The picture of a species board is 777 x 1415; its middle cut-out is at x = 388 and the cut-outs are 270 apart.
 */
export const ALIEN = { w: 777, h: 1415, centre: 388, scale: 1, bottom: 331, middleX: [680, 2820] };
export const ALIEN_TOP = ALIEN.bottom - ALIEN.h * ALIEN.scale;

/**
 * The four gold scoring tiles lie against the circle of the board on its right side, one after the other, each with its flat lower edge
 * tangent to the circle and its top turned away from the middle of the board. `radius` is the distance from the centre to the outer edge of the
 * board's circle, the tiles are drawn at `scale` of their picture (550 x 488), and the group is centred on `centreDegrees`.
 */
export const GOLD = { w: 550, h: 488, scale: 0.84, radius: 1640, gap: 6, centreDegrees: 1, stepDegrees: 15.2 };

export function goldPlace(i: number): { x: number; y: number; rotation: number } {
  const degrees = GOLD.centreDegrees + (1.5 - i) * GOLD.stepDegrees; // the first tile is the one highest up
  const at = polar(GOLD.radius + GOLD.gap + (GOLD.h * GOLD.scale) / 2, degrees);
  return { x: at.x, y: at.y, rotation: 90 - degrees };
}

/** How far the tiles reach beyond the right edge of the board picture. */
export const GOLD_EXTRA = 350;

/** Where the markers of the choosers sit on a tile (picture of 550 x 488): the first and the second chooser, then the wide space for the others. */
export const GOLD_SLOTS = [
  { x: 105, y: 248 },
  { x: 228, y: 248 },
  { x: 350, y: 248 },
  { x: 425, y: 248 },
];

/**
 * The deck of a discovered species lies in a column to the right of its board: the back of the deck on top (with the number of cards left over it)
 * and the card that lies face up below it. Sizes in board pixels; the column starts `gap` after the right edge of the board.
 */
export const ALIEN_COLUMN = { w: 381, h: 530, gap: 30, between: 36 }; // the two cards and the space between them end just above the top edge of the board (y = 25), from the top of the species boards

export function alienColumn(slot: number): { deck: { x: number; y: number }; faceUp: { x: number; y: number } } {
  const left = (ALIEN.middleX[slot] ?? 680) - ALIEN.centre * ALIEN.scale;
  const x = left + ALIEN.w * ALIEN.scale + ALIEN_COLUMN.gap;
  const y = ALIEN_TOP;
  return { deck: { x, y }, faceUp: { x, y: y + ALIEN_COLUMN.h + ALIEN_COLUMN.between } };
}

/**
 * The data slot of the 'Oumuamua tile in disc 3 (ring 3, slot 3): three places along the oval, the first at the counter-clockwise end. Measured on the
 * picture of the disc as it lies at rest; the disc turns, so the places turn with it (`disc_angles[2]` steps of 45 degrees counter-clockwise).
 */
export const OUMUAMUA_TILE = { radius: 682, degrees: [172.4, 164.9, 157.5], size: 84 };

export const PLAYER_COLOR: Record<string, string> = {
  green: "#2fbf71",
  red: "#ff5a52",
  purple: "#a56bff",
  white: "#f3f3f3",
};
export const SECTOR_COLOR: Record<string, string> = { yellow: "#e0b000", red: "#d9503c", blue: "#3b82d6", black: "#3a3f47" };

/** The four reward hexes across the top of the Centaurian board, on its picture (777 x 1415 px): the middle of each. A player who reaches their
 * message milestone covers one with their message tile (ALIEN-CEN-04). The tile is drawn at this height on the picture. */
export const CENTAURIAN_HEXES = { y: 130, xs: [230, 337, 445, 553], tileHeight: 170 };
