import type { View } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { deckPreview, speciesCards } from "../src/lib/alienDecks";

const player = (index: number, over: Record<string, unknown> = {}) => ({
  index,
  hand: [],
  exertian_hand: [],
  exertian_played: [],
  tucked: [],
  kept_cards: [],
  end_cards: [],
  completed_missions: [],
  missions: [],
  message_cards: [],
  ...over,
});

const view = (players: unknown[], state: Record<string, unknown> = {}): View =>
  ({ viewer: 0, state: { discard: [], aside: [], playing: null, species: [], players, ...state } }) as unknown as View;

describe("the preview of an alien deck", () => {
  it("knows the cards of each species (the Exertians have 15, the others 10, Arkhos has no species deck)", () => {
    expect(speciesCards("exertians")).toHaveLength(15);
    for (const sp of ["mascamites", "anomalies", "oumuamua", "centaurians", "glyphids", "amoeba"])
      expect(speciesCards(sp)).toHaveLength(10);
    expect(deckPreview(view([player(0)]), "nothing")).toBeNull();
  });

  it("lists every card as possible when none has been seen", () => {
    const p = deckPreview(view([player(0), player(1, { hand: ["?", "?"] })]), "mascamites");
    expect(p).toEqual({ possible: speciesCards("mascamites"), yours: [], revealed: [] });
  });

  it("moves a card out of the possible ones when it is shown: the player's own hand, a discard, a mission, a tucked or a face-up card", () => {
    const [a, b, c, d, e, f] = speciesCards("mascamites") as [string, string, string, string, string, string];
    const p = deckPreview(
      view([player(0, { hand: [a] }), player(1, { hand: ["?"], tucked: [b], missions: [{ card: c }], completed_missions: [d] })], {
        discard: [e],
        species: [{ face_up: f }],
      }),
      "mascamites",
    );
    expect(p?.yours).toEqual([a]);
    expect(p?.revealed).toEqual([b, c, d, e, f]);
    expect(p?.possible).toEqual(speciesCards("mascamites").filter((x) => ![a, b, c, d, e, f].includes(x)));
  });

  it("moves a card of an opponent out when they play it, and back when it is hidden again", () => {
    const [a] = speciesCards("centaurians") as [string];
    const hidden = view([player(0), player(1, { hand: ["?"] })]);
    expect(deckPreview(hidden, "centaurians")?.possible).toContain(a);
    const played = view([player(0), player(1, { message_cards: [{ card: a }] })]);
    expect(deckPreview(played, "centaurians")?.possible).not.toContain(a);
    expect(deckPreview(played, "centaurians")?.revealed).toEqual([a]);
  });

  it("keeps all the Exertian cards possible although the deck is empty: the cards of the opponents are hidden, played face down too", () => {
    const [mine] = speciesCards("exertians") as [string];
    const p = deckPreview(
      view(
        [player(0, { exertian_hand: [mine], exertian_played: [] }), player(1, { exertian_hand: ["?", "?", "?"], exertian_played: ["?"] })],
        {
          species: [{ species: "exertians", deck: [] }],
        },
      ),
      "exertians",
    );
    expect(p?.yours).toEqual([mine]);
    expect(p?.possible).toHaveLength(14);
    expect(p?.revealed).toEqual([]);
  });
});
