// The question that asks the player to confirm a place picked on the board: "Confirm landing on Mars for 3 energy?", "Confirm marking a pink trace
// of Mascamites and gain 5 points, 1 publicity?", "Confirm marking signal in Vega sector?". The facts (cost, rewards, names) come from the engine's notes.
import { cardName } from "@/lib/moves";
import type { Note } from "@/lib/targets";
import { ActionIcon } from "./Icons";
import { Cost, Rewards } from "./Reward";

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);

export function SpotPrompt({ note }: { note: Note }) {
  if (!note) return null;
  if (note.alien) {
    return (
      <span className="spotprompt">
        Confirm taking <b>{note.alien === "deck" ? "random card" : cardName(note.card)}</b>?
      </span>
    );
  }
  if (note.action && note.planet) {
    const place = note.moon ? `${note.moon} (${cap(note.planet)})` : cap(note.planet);
    return (
      <span className="spotprompt">
        <ActionIcon name={note.action} size={28} /> Confirm {note.action === "orbit" ? "orbiting" : "landing on"} <b>{place}</b> for{" "}
        <Cost cost={note.cost ?? {}} />?
      </span>
    );
  }
  if (note.space && note.color) {
    const species = note.species ? cap(note.species) : `species ${(note.slot ?? 0) + 1} (not discovered yet)`;
    const where = note.space === "discovery" ? "discovery space" : note.space === "overflow" ? "overflow space" : "space";
    return (
      <span className="spotprompt">
        Confirm marking a <b className={`trace-${note.color}`}>{note.color}</b> trace on the {where} of <b>{species}</b> and gain{" "}
        <Rewards list={note.rewards ?? []} />?
      </span>
    );
  }
  if (note.star) {
    return (
      <span className="spotprompt">
        Confirm marking signal in <b>{note.star}</b> sector?
      </span>
    );
  }
  return null;
}
