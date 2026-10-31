// The preview of an alien deck: which cards of the species the player cannot account for yet. The decks are secret, and so are the cards in an
// opponent's hand, so every card of the species that the player has not seen could be in the deck or in an opponent's hand. A card that shows up
// in front of the player (played, discarded, a mission, tucked, face up, or in their own hand) leaves that list, and it can come back: the draw deck
// is shuffled again from the discard pile when it runs out (RES-04). Nothing here needs more than the view that the player is sent.
import type { View } from "@seti/protocol";
import cards from "../generated/cards.json";

/** The board sends this (with the species as `detail`) when the deck of a species is clicked: the preview of its cards opens. */
export const ALIEN_PREVIEW_EVENT = "seti-alien-preview";

const CARDS = cards as unknown as Record<string, { species?: string; deck?: string }>;
const HIDDEN = "?";

/** The alien cards of a species, in the order of the card data. Arkhos has security cards, not a species deck. */
export function speciesCards(species: string): string[] {
  return Object.entries(CARDS)
    .filter(([, c]) => c.deck === "alien" && c.species === species)
    .map(([id]) => id);
}

export interface DeckPreview {
  /** Not seen by the player: in the deck, or in an opponent's hand (or, for the Exertians, in their hand or played face down). */
  possible: string[];
  /** In the player's own hand (the Exertian cards held or played face down are theirs too). */
  yours: string[];
  /** Out in the open: discarded, played as a mission or a message, tucked, kept, or lying face up beside the deck. */
  revealed: string[];
}

/** The cards that the player can see anywhere in their view, split into their own and the open ones. */
function seen(view: View): { yours: Set<string>; open: Set<string> } {
  const s = view.state;
  const yours = new Set<string>();
  const open = new Set<string>();
  const put = (set: Set<string>, ids: readonly (string | undefined | null)[]) => {
    for (const id of ids) if (typeof id === "string" && id !== HIDDEN) set.add(id);
  };
  put(open, [...s.discard, ...s.aside, s.playing ?? null, ...s.species.map((sp) => sp.face_up ?? null)]);
  for (const p of s.players) {
    const mine = p.index === view.viewer;
    put(mine ? yours : open, [...p.hand, ...p.exertian_hand]);
    put(mine ? yours : open, p.exertian_played); // an opponent's cards played face down are "?" until the game is over
    put(open, [
      ...p.tucked,
      ...p.kept_cards,
      ...p.end_cards,
      ...p.completed_missions,
      ...p.missions.map((m) => m.card),
      ...p.message_cards.map((m) => m.card),
    ]);
  }
  return { yours, open };
}

/** What the player knows of the cards of a species (null: nothing to show, the species has no alien cards). */
export function deckPreview(view: View, species: string): DeckPreview | null {
  const all = speciesCards(species);
  if (all.length === 0) return null;
  const { yours, open } = seen(view);
  return {
    possible: all.filter((c) => !yours.has(c) && !open.has(c)),
    yours: all.filter((c) => yours.has(c)),
    revealed: all.filter((c) => open.has(c) && !yours.has(c)),
  };
}
