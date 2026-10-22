// Short names for the twelve techs. The tiles show only icons, so these names are our own, made from what each tech does (docs/spec, the tech board).
// The engine names a stack by its category and glyph, for example "probe-dot".
export const TECH_INFO: Record<string, { name: string; effect: string }> = {
  "probe-dot": { name: "Twin Probes", effect: "Up to 2 probes in space at the same time." },
  "probe-link": {
    name: "Asteroid Skimmer",
    effect: "Asteroids give 1 publicity when you move onto them, and leaving them costs no extra movement.",
  },
  "probe-branch": { name: "Soft Landers", effect: "Landing costs 1 less energy." },
  "probe-cross": { name: "Moon Rover", effect: "Land on a planet's moon instead of the planet, at the same cost." },
  "telescope-dot": { name: "Earth Scope", effect: "When you scan, mark a signal in a sector next to Earth instead of Earth's sector." },
  "telescope-link": { name: "Mercury Scope", effect: "When you scan, pay 1 publicity to mark an extra signal in a sector with Mercury." },
  "telescope-branch": {
    name: "Card Scope",
    effect: "When you scan, discard a card from your hand to mark an extra signal in a matching sector.",
  },
  "telescope-cross": { name: "Scan Booster", effect: "When you scan, pay 1 energy to launch a probe or to gain 1 movement." },
  "computer-dot": { name: "Credit Memory", effect: "A new computer space: 2 points on the upper space, 1 credit on the lower." },
  "computer-link": { name: "Energy Memory", effect: "A new computer space: 2 points on the upper space, 1 energy on the lower." },
  "computer-branch": { name: "Card Memory", effect: "A new computer space: 2 points on the upper space, 1 card on the lower." },
  "computer-cross": { name: "Publicity Memory", effect: "A new computer space: 2 points on the upper space, 2 publicity on the lower." },
};

/**
 * What is counted for each tech once a player has it (the engine's `techuse.<tech>.<key>` counters, services/engine/src/seti_engine/stats.py `tech_use`). The first tech
 * of each type has nothing to count (the Twin Probes has no effect to follow; the blue techs only give their spaces).
 */
export interface TechMetric {
  key: string;
  label: string;
}

const BLUE = (bottom: string): TechMetric[] => [
  { key: "vp", label: "VP they gave" }, // the times the upper space was filled is this divided by 2: not shown
  { key: "bottom", label: `${bottom} spaces filled` },
];

export const TECH_METRICS: Record<string, TechMetric[]> = {
  "probe-dot": [],
  "probe-link": [{ key: "asteroids", label: "Asteroids moved into" }],
  "probe-branch": [{ key: "lands", label: "Landing actions (1 energy saved each)" }],
  "probe-cross": [{ key: "moons", label: "Moons landed on" }],
  "telescope-dot": [{ key: "adjacent", label: "Scans of a sector next to Earth's" }],
  "telescope-link": [{ key: "mercury", label: "Signals in Mercury's sector (1 publicity each)" }],
  "telescope-branch": [{ key: "discards", label: "Cards discarded for a signal" }],
  "telescope-cross": [
    { key: "launches", label: "Probes launched (1 energy each)" },
    { key: "moves", label: "Free movements gained" },
  ],
  "computer-dot": BLUE("1 credit"),
  "computer-link": BLUE("1 energy"),
  "computer-branch": BLUE("1 card"),
  "computer-cross": BLUE("2 publicity"),
};

/** The twelve techs in the order of the board: probe, telescope, computer, each dot, link, branch, cross. */
export const TECH_ORDER: string[] = ["probe", "telescope", "computer"].flatMap((c) =>
  ["dot", "link", "branch", "cross"].map((g) => `${c}-${g}`),
);

export const techName = (category: string, glyph: string): string => TECH_INFO[`${category}-${glyph}`]?.name ?? `${category} tech ${glyph}`;
