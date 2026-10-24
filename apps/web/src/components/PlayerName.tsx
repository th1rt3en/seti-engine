"use client";
// The name of a player in a game (the panels, the results, the clocks): a link to the profile in a new tab. The numbers of the players, seat by seat, come
// from the page that shows the game (the table or the replay) through this context, so that the panels need not be given them one by one.
import { createContext, useContext } from "react";
import { PlayerLink } from "./PlayerLink";

export const PlayerNumsContext = createContext<(number | null)[]>([]);
/** The color of each seat (the CSS color of its player color): a name is written in the color of its player. */
export const PlayerColorsContext = createContext<string[]>([]);

export function PlayerName({ seat, name, className }: { seat: number; name: string; className?: string }) {
  const nums = useContext(PlayerNumsContext);
  const color = useContext(PlayerColorsContext)[seat];
  return <PlayerLink num={nums[seat] ?? null} name={name} className={className} style={color ? { color } : undefined} />;
}
