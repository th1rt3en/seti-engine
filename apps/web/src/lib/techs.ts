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

export const techName = (category: string, glyph: string): string => TECH_INFO[`${category}-${glyph}`]?.name ?? `${category} tech ${glyph}`;
