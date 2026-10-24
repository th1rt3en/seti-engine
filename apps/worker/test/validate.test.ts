import { describe, expect, it } from "vitest";
import { MAX_MESSAGE_BYTES, messageText, validClock, validOptions } from "../src/core/validate.js";

describe("the options of a new table", () => {
  it("lets through what the lobby sends", () => {
    expect(validOptions({ players: 2 })).toBe(true);
    expect(
      validOptions({ players: 1, difficulty: 3, sandbox: true, sandbox_species: ["anomalies", null], promo_cards: false, seed: 12345 }),
    ).toBe(true);
    expect(
      validOptions({ players: 4, expansion: true, organizations: true, beginner_organizations: true, neutral_quick_start: false }),
    ).toBe(true);
  });

  it("refuses anything that is not a known option of the right type", () => {
    for (const bad of [
      null,
      "players",
      [],
      {},
      { players: 5 },
      { players: 0 },
      { players: 2.5 },
      { players: "2" },
      { players: 2, difficulty: 9 },
      { players: 2, seed: -1 },
      { players: 2, seed: 1.5 },
      { players: 2, seed: 2 ** 60 },
      { players: 2, expansion: "yes" },
      { players: 2, rated: true },
      { players: 2, __proto__x: 1 },
      { players: 1, sandbox_species: "anomalies" },
      { players: 1, sandbox_species: ["a", "b", "c"] },
      { players: 1, sandbox_species: ["<script>alert(1)</script>", null] },
    ])
      expect(validOptions(bad), JSON.stringify(bad)).toBe(false);
  });
});

describe("the clock of a new table", () => {
  it("accepts the three kinds with sensible times", () => {
    expect(validClock({ kind: "none" })).toBe(true);
    expect(validClock({ kind: "per_turn", ms: 60_000 })).toBe(true);
    expect(validClock({ kind: "bank", initialMs: 300_000, incrementMs: 90_000 })).toBe(true);
  });

  it("refuses an unknown kind, a missing, negative, infinite or absurd time", () => {
    for (const bad of [
      null,
      [],
      { kind: "other" },
      { kind: "per_turn" },
      { kind: "per_turn", ms: -1 },
      { kind: "per_turn", ms: Number.POSITIVE_INFINITY },
      { kind: "bank", initialMs: 1000, incrementMs: -1 },
      { kind: "bank", initialMs: 1000 * 3600 * 24 * 400, incrementMs: 0 },
      { kind: "bank", initialMs: "1000", incrementMs: 0 },
    ])
      expect(validClock(bad), JSON.stringify(bad)).toBe(false);
  });
});

describe("the messages of a WebSocket", () => {
  it("passes a small message and refuses a big one", () => {
    expect(messageText('{"t":"ping"}')).toBe('{"t":"ping"}');
    const bytes = new TextEncoder().encode('{"t":"ping"}');
    expect(messageText(bytes.buffer.slice(0) as ArrayBuffer)).toBe('{"t":"ping"}');
    expect(messageText("x".repeat(MAX_MESSAGE_BYTES + 1))).toBeNull();
    expect(messageText(new ArrayBuffer(MAX_MESSAGE_BYTES + 1))).toBeNull();
  });
});
