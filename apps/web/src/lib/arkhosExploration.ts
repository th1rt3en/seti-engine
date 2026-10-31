// The exploration cards of Arkhos (EXP-ARK-01, EXP-ARK-02, EXP-ARK-04) as the players can know them.

/** The board sends this when the exploration deck is clicked: the preview of the deck opens. */
export const EXPLORATION_PREVIEW_EVENT = "seti-exploration-preview";

/** The 9 exploration cards of Arkhos, by the ids of the card data. */
export const EXPLORATION_CARDS = Array.from({ length: 9 }, (_, i) => `ET ${33 + i}`);

/**
 * The cards that the next exploration reveal can show. Nobody knows the order of the deck or which 4 cards are set aside, so every card that is
 * not revealed is possible. With the deck empty the next reveal shuffles everything again (the revealed cards and the 4 set aside), and then all 9
 * are possible. The revealed cards go back at each shuffle, so this changes whenever the deck is shuffled.
 */
export function possibleExploration(deckSize: number, revealed: string[]): string[] {
  return deckSize === 0 ? EXPLORATION_CARDS : EXPLORATION_CARDS.filter((c) => !revealed.includes(c));
}
