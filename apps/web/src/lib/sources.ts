// What caused a decision, in a few words for the end of the context bar: "(Helion Assembly)", "(Landing on Mars)". The engine names the cause of
// a decision like the cause of a gain (trail.py); the sources that say nothing (an ordinary move, the income) are left out.
import { ORG_NAMES, cardName } from "./moves";
import { techName } from "./techs";

export type DecisionSource = { kind: string } & Record<string, unknown>;

const cap = (s: unknown): string => {
  const t = String(s);
  return t.charAt(0).toUpperCase() + t.slice(1);
};

export function sourceLabel(src: DecisionSource | null | undefined, stars: string[], species: string[]): string | null {
  if (!src) return null;
  switch (src.kind) {
    case "card":
    case "mission":
    case "quick_start":
      return cardName(src.card);
    case "corner":
      return `free corner of ${cardName(src.card)}`;
    case "organization":
      return ORG_NAMES[String(src.org)] ?? String(src.org);
    case "signal":
      return `signal in ${stars[Number(src.sector)] ?? "a sector"}`;
    case "sector":
      return `${stars[Number(src.sector)] ?? "a sector"} completed`;
    case "planet": {
      const planet = cap(src.planet);
      switch (src.what) {
        case "first_orbit":
        case "orbit":
          return `orbiting ${planet}`;
        case "moon":
          return `landing on ${String(src.moon)}`;
        default:
          return `landing on ${planet}`;
      }
    }
    case "tech": {
      const [category = "", glyph = ""] = String(src.tech).split("-");
      return techName(category, glyph);
    }
    case "trace":
      return `${src.color} trace on ${species[Number(src.slot)] ?? "a species"}`;
    case "explore":
      return `exploration card ${String(src.card)}`;
    case "glyph":
      return `${String(src.glyph)} glyph`;
    default:
      return null;
  }
}
