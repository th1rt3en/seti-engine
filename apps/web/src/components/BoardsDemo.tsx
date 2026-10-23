"use client";
// A review page for the alien boards: for each pair of species two boards, one with every place that a marker can go to highlighted, one with markers on every
// space. The states are made by the engine (`tools/web/make_board_states.py`); nothing here is a rule.
import { buildSpots } from "@/lib/targets";
import type { View } from "@seti/protocol";
import states from "../generated/board-states.json";
import { BoardView } from "./BoardView";

interface Pair {
  species: string[];
  prompts: unknown;
  markers: unknown;
}

const PAIRS = states as unknown as Pair[];
const NAMES = ["Alice", "Bob", "Cy"];

export function BoardsDemo({ pair, variant }: { pair: number | null; variant: "prompts" | "markers" | null }) {
  const shown = PAIRS.flatMap((p, i) =>
    (["prompts", "markers"] as const).flatMap((v) =>
      (pair !== null && pair !== i) || (variant !== null && variant !== v) ? [] : [{ p, i, v }],
    ),
  );
  return (
    <div className="boardsdemo">
      <h1>Alien boards</h1>
      <p className="muted">
        For each pair of species: <b>prompts</b> (every place that the engine offers, highlighted) and <b>markers</b> (markers of three
        players on every space, several where the space takes several).
      </p>
      {shown.map(({ p, i, v }) => {
        const view = p[v] as View;
        const spots = v === "prompts" ? buildSpots(view).spots : [];
        return (
          <section key={`${i}-${v}`} id={`${p.species.join("-")}-${v}`}>
            <h2>
              {p.species.join(" and ")}: {v}
              {v === "prompts" ? ` (${spots.length} places)` : ""}
            </h2>
            <BoardView view={view} names={NAMES} spots={{ items: spots, selected: null, onSelect: () => undefined }} />
          </section>
        );
      })}
    </div>
  );
}
