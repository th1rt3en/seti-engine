// The picture of a card: a card of the base game or of the alien species (generated/assets.json) or of the Space Agencies expansion
// (generated/expansion-assets.json, found through generated/expansion-card-images.json).
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";
import expansionImages from "../generated/expansion-card-images.json";

const BASE = assets.cards as Record<string, string>;
const EXPANSION = expansionAssets as Record<string, string>;
const OF = expansionImages as Record<string, string>;

export function cardImage(id: string): string | undefined {
  const key = OF[id];
  return BASE[id] ?? (key === undefined ? undefined : EXPANSION[key]);
}

/** The back of the deck of a species (the base species have their own, Glyphids and Amoeba come with the expansion). */
export function alienBack(species: string): string | undefined {
  return (assets.alienBacks as Record<string, string>)[species] ?? EXPANSION[`${species}/card-back`];
}
