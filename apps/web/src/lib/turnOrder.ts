// The order of play of a round: the player with the starting marker first, then the others by seat. The marker moves one seat on at the end of every round
// (the engine's `_end_round`: ROUND-03), so the order is worked out again from `state.start_player` of every view that the page gets.

/** The players in the order they play this round. */
export function turnOrder<T extends { index: number }>(players: T[], startPlayer: number): T[] {
  const n = players.length;
  const place = (p: T): number => (((p.index - startPlayer) % n) + n) % n;
  return [...players].sort((a, b) => place(a) - place(b));
}

/** The players in the order of play of the first round: it never changes during the game (the pills, and the keys 1 to 4 that open the boards, follow it). */
export function firstRoundOrder<T extends { index: number }>(players: T[], startPlayer: number, round: number): T[] {
  const n = players.length;
  if (n === 0) return [];
  const first = (((startPlayer - (Math.min(round, 5) - 1)) % n) + n) % n; // the marker moves one seat on at the end of each round
  return turnOrder(players, first);
}

const ORDINALS = ["1st", "2nd", "3rd", "4th"];

/** "1st", "2nd" ... for the place (from 0) in the order of play. */
export const ordinal = (rank: number): string => ORDINALS[rank] ?? `${rank + 1}th`;
