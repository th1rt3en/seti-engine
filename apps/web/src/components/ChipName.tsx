"use client";
// The name of a player in the score chips: pressing it opens the board of that player (the computer, the techs and the data), on a phone as well as on a wide screen.
import { OPEN_BOARD_EVENT } from "@/lib/boardEvent";
import { useContext } from "react";
import { PlayerColorsContext } from "./PlayerName";

export function ChipName({ player, name }: { player: number; name: string }) {
  const color = useContext(PlayerColorsContext)[player];
  return (
    <button
      type="button"
      className="chipname"
      style={color ? { color } : undefined}
      title="Look at this player's board"
      onClick={() => window.dispatchEvent(new CustomEvent(OPEN_BOARD_EVENT, { detail: player }))}
    >
      {name}
    </button>
  );
}
