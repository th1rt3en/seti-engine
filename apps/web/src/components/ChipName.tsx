"use client";
// The name of a player in the score chips: pressing it opens the board of that player (the computer, the techs and the data), on a phone as well as on a wide screen.
import { OPEN_BOARD_EVENT } from "@/lib/boardEvent";

export function ChipName({ player, name }: { player: number; name: string }) {
  return (
    <button
      type="button"
      className="chipname"
      title="Look at this player's board"
      onClick={() => window.dispatchEvent(new CustomEvent(OPEN_BOARD_EVENT, { detail: player }))}
    >
      {name}
    </button>
  );
}
