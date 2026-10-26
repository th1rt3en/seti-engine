// The resources that the statistics follow, with the color of each (the color of its icon): the slices of the pies that are made of resources take them.
export const GAIN_RESOURCES = ["credit", "energy", "card", "data", "publicity", "vp"] as const;
export type GainResource = (typeof GAIN_RESOURCES)[number];

export const RESOURCE_NAMES: Record<string, string> = {
  credit: "Credits",
  energy: "Energy",
  card: "Cards",
  data: "Data",
  publicity: "Publicity",
  vp: "Points",
  move: "Movement",
};

export const RESOURCE_COLORS: Record<string, string> = {
  credit: "#e0a526",
  energy: "#8cc63f",
  card: "#8f9bc4",
  data: "#3f9be0",
  publicity: "#e0525a",
  vp: "#2fa56b",
  move: "#b58be0",
};

/** What a source of a gain is, as the engine names it (the kind of the scope that was open when the resource was gained, engine/trail.py). */
export const SOURCE_NAMES: Record<string, string> = {
  move: "Main and free actions",
  card: "Playing a card",
  corner: "Free corner of a discarded card",
  income: "Income of the round",
  organization: "Organization",
  quick_start: "Quick start cards",
  mission: "Missions",
  tech: "Technologies",
  signal: "Marking a signal",
  sector: "Completing a sector",
  trace: "Life traces",
  anomaly: "Anomaly tokens",
  planet: "Planets: orbiting, landing, moons",
  explore: "Arkhos exploration",
  glyph: "Glyphids glyphs",
  alien: "Alien species effects",
  rival_turn: "The rival's turn",
  rival_computer: "The rival's computer",
  visit_comet: "Visiting a comet",
  visit_asteroid: "Moving into an asteroid field",
  visit_planet: "Visiting a planet",
  final_cards: "End-of-game cards",
  final_gold: "Gold scoring tiles",
  final_exertian: "Exertian cards",
  final_glyphs: "Glyph tokens left",
};

/** The color of each source in the pies: it follows the source, not its rank, so a source keeps its color from one pie to the next (the legend names every slice). */
export const SOURCE_COLORS: Record<string, string> = {
  move: "#3987e5",
  card: "#d95926",
  income: "#199e70",
  corner: "#c98500",
  organization: "#d55181",
  quick_start: "#8f7ae0",
  mission: "#5fb8d6",
  tech: "#b8c43a",
  signal: "#e0b04a",
  sector: "#7fcf8a",
  trace: "#e07b9b",
  anomaly: "#9aa0a6",
  planet: "#d0a06a",
  explore: "#4ec3b0",
  glyph: "#c27bd1",
  alien: "#a3c2ff",
  rival_turn: "#8b949e",
  rival_computer: "#6e7681",
  visit_comet: "#6fd0e8",
  visit_asteroid: "#b09a7a",
  visit_planet: "#4aa87a",
  final_cards: "#e8c15a",
  final_gold: "#c9a227",
  final_exertian: "#d45b3a",
  final_glyphs: "#9b7ede",
};
