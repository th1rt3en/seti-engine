// The states of the alien boards made by the engine for the review page (tools/web/make_board_states.py): every place that a marker can be put at has a
// place on the picture of its board, and every space of a board has one.
import type { View } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import states from "../src/generated/board-states.json";
import { SPECIES_SPACES } from "../src/lib/speciesSpaces";
import { buildSpots } from "../src/lib/targets";

interface Pair {
  species: string[];
  prompts: unknown;
  markers: unknown;
}
const PAIRS = states as unknown as Pair[];

describe("the alien boards", () => {
  it("the table of the places has a place for every space of every board", () => {
    for (const pair of PAIRS) {
      const view = pair.prompts as View;
      view.state.species.forEach((slot, i) => {
        const name = pair.species[i] as string;
        expect(slot.species, `the species of the slot ${i}`).toBe(name);
        for (const [colour, spaces] of Object.entries(slot.board)) {
          const places = SPECIES_SPACES[name]?.[colour] ?? [];
          expect(places.length, `${name} ${colour}`).toBe(spaces.length);
        }
      });
    }
  });

  it("every place that the engine offers on a board is highlighted somewhere on it", () => {
    for (const pair of PAIRS) {
      const view = pair.prompts as View;
      const { spots, handled } = buildSpots(view);
      const placed = (view.legal as { type: string; space?: string }[]).filter(
        (m) => m.type === "place_trace" && (m.space === "board" || m.space === "sample" || m.space === "overflow"),
      );
      const missing = placed.filter((m) => !handled.has((view.legal as unknown[]).indexOf(m)));
      expect(missing, `${pair.species.join("+")}: moves without a place on the board`).toEqual([]);
      expect(spots.length).toBeGreaterThanOrEqual(placed.length);
    }
  });

  it("the markers of the review states are on spaces that exist", () => {
    for (const pair of PAIRS) {
      const view = pair.markers as View;
      view.state.species.forEach((slot, i) => {
        const name = pair.species[i] as string;
        for (const [colour, spaces] of Object.entries(slot.board)) {
          spaces.forEach((players, k) => {
            if (players.length === 0) return;
            expect(SPECIES_SPACES[name]?.[colour]?.[k], `${name} ${colour}[${k}] holds markers but has no place`).toBeTruthy();
          });
        }
      });
    }
  });
});
