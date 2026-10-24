import { describe, expect, it } from "vitest";
import { publicEntry } from "../src/core/publicLog.js";

const entry = (action: Record<string, unknown>, events: Record<string, unknown>[] = []) => ({ seq: 3, seat: 1, action, at: 0, events });

describe("the log that every client sees (rule 6)", () => {
  it("does not show which card was tucked, taken as end-of-round card or played face down", () => {
    for (const type of ["tuck", "take_round_card", "play_exertian", "pol_pick"]) {
      const shown = publicEntry(entry({ type, card: "17" }));
      expect(shown.action).toEqual({ type });
    }
    const tucked = publicEntry(entry({ type: "tuck", card: "17" }, [{ type: "tuck", player: 1, card: "17" }]));
    expect(tucked.events).toEqual([{ type: "tuck", player: 1 }]);
  });

  it("shows the cards that are public: played, discarded, bought from the display", () => {
    expect(publicEntry(entry({ type: "play_card", card: "17" })).action).toEqual({ type: "play_card", card: "17" });
    expect(publicEntry(entry({ type: "discard", card: "17" })).action).toEqual({ type: "discard", card: "17" });
    expect(publicEntry(entry({ type: "exchange", give: "card", cards: ["1", "2"], get: "credit" })).action).toMatchObject({
      cards: ["1", "2"],
    });
    const played = publicEntry(entry({ type: "play_card", card: "17" }, [{ type: "play_card", player: 1, card: "17" }]));
    expect(played.events).toEqual([{ type: "play_card", player: 1, card: "17" }]);
    expect({ seq: played.seq, seat: played.seat }).toEqual({ seq: 3, seat: 1 });
  });
});

describe("a card drawn from the deck", () => {
  it("is named for the player who drew it and hidden from the others", () => {
    const e = entry({ type: "end_turn" }, [{ type: "draw_card", player: 1, card: "17" }]);
    expect(publicEntry(e, 1).events[0]).toEqual({ type: "draw_card", player: 1, card: "17" });
    expect(publicEntry(e, 0).events[0]).toEqual({ type: "draw_card", player: 1 });
    expect(publicEntry(e, null).events[0]).toEqual({ type: "draw_card", player: 1 });
  });
});

describe("the moves of the simultaneous setup", () => {
  const entry = (type: string, seat: number, extra: object = {}) => ({
    seq: 3,
    seat,
    action: { type, seat, ...extra },
    at: 0,
    events: [{ type: "tuck", player: seat, card: "55" }],
  });
  it("are not shown to the other players (only their place in the log stays); the player sees their own", () => {
    for (const type of ["choose_org", "choose_quick", "setup_tuck", "setup_untuck"]) {
      const e = entry(type, 0, { card: "55", org: "x", cards: ["a"] }) as never;
      expect(publicEntry(e, 1)).toEqual({ seq: 3, seat: 0, action: { type: "setup_hidden" }, events: [] });
      expect(publicEntry(e, null)).toMatchObject({ action: { type: "setup_hidden" } });
      expect((publicEntry(e, 0).action as { type: string }).type).toBe(type);
    }
    expect(publicEntry(entry("setup_lock", 0) as never, 1).action).toMatchObject({ type: "setup_lock" }); // who has locked in is public
  });
});
