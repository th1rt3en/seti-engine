import { buildSpots } from "@/lib/targets";
import type { View } from "@seti/protocol";
import { describe, expect, it } from "vitest";

/** A view with the parts that the places on the board are made from: planets, species, and the legal moves with their notes. */
function view(legal: Record<string, unknown>[], notes: (Record<string, unknown> | null)[]): View {
  return {
    state: {
      planets: { mars: { orbiters: [0], landers: [], moon_landers: {} }, saturn: { orbiters: [], landers: [], moon_landers: {} } },
      species: [{ species: "mascamites" }, { species: "anomalies" }],
      disc_angles: [0, 0, 2],
    },
    legal,
    notes,
  } as unknown as View;
}

describe("the places on the board that moves can be made at", () => {
  it("puts landing, orbiting and a moon at their own place, and skips a move of the same place", () => {
    const v = view(
      [
        { type: "orbit", probe: "a" },
        { type: "orbit", probe: "b" },
        { type: "land", probe: "a" },
        { type: "land", probe: "a", moon: "Titan" },
        { type: "pass" },
      ],
      [
        { action: "orbit", planet: "mars", moon: null, free: false, cost: { credit: 1, energy: 1 } },
        { action: "orbit", planet: "mars", moon: null, free: false, cost: { credit: 1, energy: 1 } },
        { action: "land", planet: "mars", moon: null, free: false, cost: { energy: 2 } },
        { action: "land", planet: "saturn", moon: "Titan", free: false, cost: { energy: 3 } },
        null,
      ],
    );
    const { spots, handled } = buildSpots(v);
    expect(spots.map((s) => s.id)).toEqual(["orbit:mars", "land:mars", "moon:Titan"]);
    expect([...handled].sort()).toEqual([0, 1, 2, 3]); // the second orbit move is the same place as the first: it needs no button either
    expect(handled.has(4)).toBe(false); // a move with no place stays a button
    expect(spots[0]?.move).toBe(0);
  });

  it("makes a wedge of the star ring for a sector, and a circle for a discovery space", () => {
    const v = view(
      [
        { type: "mark_signal", sector: 3 },
        { type: "place_trace", slot: 0, space: "discovery", color: "pink" },
        { type: "place_trace", slot: 1, space: "overflow", color: "blue" },
        { type: "place_trace", slot: 0, space: "board", color: "yellow", index: 2 },
        { type: "place_trace", slot: 0, space: "sample", color: "blue", index: 0 },
      ],
      [
        { sector: 3, star: "Vega", color: "red" },
        { slot: 0, species: null, color: "pink", space: "discovery", rewards: [] },
        { slot: 1, species: null, color: "blue", space: "overflow", rewards: [] },
        { slot: 0, species: "mascamites", color: "yellow", space: "board", rewards: [] },
        { slot: 0, species: "mascamites", color: "blue", space: "sample", rewards: [] },
      ],
    );
    const { spots, handled } = buildSpots(v);
    expect(spots.map((s) => s.id)).toEqual(["sector:3", "trace:0:discovery:pink", "trace:1:overflow:blue", "trace:0:board:yellow:2"]);
    expect(spots[0]?.shape.kind).toBe("path");
    expect(spots[1]?.shape.kind).toBe("circle");
    expect(handled.has(4)).toBe(false); // a sample space of the Mascamites has no place: it stays a button
  });
});

describe("the deck of a species", () => {
  it("makes the deck and the face-up card two places beside the board of that species", () => {
    const v = view(
      [
        { type: "take_alien", source: "deck" },
        { type: "take_alien", source: "face_up" },
      ],
      [
        { slot: 1, alien: "deck", card: null },
        { slot: 1, alien: "face_up", card: "ET.3" },
      ],
    );
    const { spots, handled } = buildSpots(v);
    expect(spots.map((s) => s.id)).toEqual(["alien:1:deck", "alien:1:face_up"]);
    expect(spots.every((s) => s.shape.kind === "rect")).toBe(true);
    expect(handled.size).toBe(2);
    const [deck, faceUp] = spots.map((s) => (s.shape.kind === "rect" ? s.shape : null));
    expect(deck && faceUp && faceUp.y > deck.y && faceUp.x === deck.x).toBe(true); // one under the other, in a column
  });
});

describe("a signal in the sector with 'Oumuamua", () => {
  it("is made in the sector or on the tile, two places", () => {
    const v = view(
      [
        { type: "signal_where", where: "sector" },
        { type: "signal_where", where: "tile" },
      ],
      [
        { sector: 4, star: "Vega", color: "red" },
        { sector: 4, star: "Vega", color: "red", oumuamua_tile: true },
      ],
    );
    const { spots, handled } = buildSpots(v);
    expect(spots.map((s) => s.id)).toEqual(["sector:4", "oumuamua-tile"]);
    expect(spots.map((s) => s.shape.kind)).toEqual(["path", "circle"]);
    expect(handled.size).toBe(2);
  });
});

describe("the places of the Space Agencies expansion", () => {
  it("puts a glyph token, an organelle, a marker to remove and a probe step at their own places", () => {
    const v = view(
      [
        { type: "decipher", glyph: "red", row: "bottom", index: 1 },
        { type: "decipher", glyph: "blue", row: "bottom", index: 1 },
        { type: "pick_organelle", space: "IB" },
        { type: "amoeba_remove", color: "pink", index: 0 },
        { type: "od_step", probe: "p1", to: [2, 3] },
        { type: "org_main", org: "xenolab", tile: "scan" },
        { type: "pass" },
      ],
      [null, null, null, null, null, null, null],
    );
    const { spots, handled } = buildSpots(v);
    expect(spots.filter((s) => s.panel === "glyphids").map((s) => s.glyph)).toEqual(["red", "blue"]); // two kinds for one hole
    expect(spots.find((s) => s.id === "organelle:IB")?.panel).toBe("amoeba");
    expect(spots.find((s) => s.id === "amoeba:pink:0")?.panel).toBe("amoeba");
    expect(spots.find((s) => s.id.startsWith("od:"))?.panel).toBeUndefined(); // on the board itself
    expect(spots.find((s) => s.id === "org:5")?.panel).toBe("org");
    expect(handled.has(6)).toBe(false);
    expect([...handled].sort()).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("offers the security card of the decision's color for a breach", () => {
    const v = {
      ...view([{ type: "breach" }, { type: "skip_breach" }], [null, null]),
    } as unknown as View;
    (v.state as unknown as { pending: unknown[] }).pending = [{ kind: "breach", player: 0, data: { color: "pink" } }];
    const { spots } = buildSpots(v);
    expect(spots.map((s) => s.id)).toEqual(["breach:pink"]);
  });
});
