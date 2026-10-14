// A resource exchange (RES-06): "trade 2 cards / 2 credits / 2 energy for:" with one button for each thing the engine lets the player get.
// The moves all come from the engine; for a card of the display the player then clicks the card in the card row.
import type { Move } from "@/lib/moves";
import { CreditIcon, DeckCardIcon, DisplayCardIcon, EnergyIcon } from "./Icons";

const GIVE: Record<string, string> = { credit: "2 credits", energy: "2 energy", card: "2 cards" };

export function TradeButtons({
  moves,
  onPlay,
  onPickRow,
}: {
  /** The exchange moves with the same thing given. */
  moves: Move[];
  onPlay: (m: Move) => void;
  /** The player wants a card of the display: the moves that take one, to be chosen by clicking a card of the row. */
  onPickRow: (moves: Move[]) => void;
}) {
  const give = String(moves[0]?.give ?? "card");
  const one = (get: string): Move | undefined => moves.find((m) => m.get === get);
  const row = moves.filter((m) => m.get === "card" && String(m.source).startsWith("row:"));
  const deck = moves.find((m) => m.get === "card" && m.source === "deck");
  const credit = one("credit");
  const energy = one("energy");
  return (
    <span className="trade">
      <span className="tradelabel">Trade {GIVE[give] ?? give} for:</span>
      {credit ? (
        <button type="button" onClick={() => onPlay(credit)}>
          <CreditIcon /> 1 credit
        </button>
      ) : null}
      {energy ? (
        <button type="button" onClick={() => onPlay(energy)}>
          <EnergyIcon /> 1 energy
        </button>
      ) : null}
      {row.length > 0 ? (
        <button type="button" onClick={() => onPickRow(row)}>
          <DisplayCardIcon /> 1 display card
        </button>
      ) : null}
      {deck ? (
        <button type="button" onClick={() => onPlay(deck)}>
          <DeckCardIcon /> 1 deck card
        </button>
      ) : null}
    </span>
  );
}
