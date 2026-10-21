import { describe, expect, it } from "vitest";
import { type GameRow, botRecords, describeRecord } from "../src/lib/botRecord";

const game = (id: string, ...players: [string, number | null][]): GameRow[] =>
  players.map(([user_id, rank]) => ({ game_id: id, user_id, rank }));
const none = new Map<string, number>();

describe("the record of the AI against people", () => {
  it("counts wins and ties, and moves the rating by the opponents' ratings", () => {
    const rows = [
      ...game("g1", ["bot:v001:0", 2], ["u1", 1]),
      ...game("g2", ["bot:v001:0", 1], ["u1", 2]),
      ...game("g3", ["u2", 1], ["bot:v001:0", 1]),
    ];
    const r = botRecords(rows, new Map([["u1", 0]])).get("v001");
    expect(r).toMatchObject({ games: 3, wins: 1.5, winRate: 0.5, provisional: true });
    // game 1: lost (K 60, expected 0.5) -> -30; game 2: won (K 60, expected 0.457) -> about +33; game 3: a tie against 0 (K 60)
    const exp = (a: number, b: number): number => 1 / (1 + 10 ** ((b - a) / 400));
    const r1 = 60 * (0 - exp(0, 0));
    const r2 = r1 + 60 * (1 - exp(r1, 0));
    expect(r?.rating).toBe(Math.round(r2 + 60 * (0.5 - exp(r2, 0))));
  });

  it("ignores games without a person, unfinished ranks and other versions are kept apart", () => {
    const rows = [
      ...game("g1", ["bot:v001:0", 1], ["bot:v001:1", 2]),
      ...game("g2", ["bot:v001:0", null], ["u1", null]),
      ...game("g3", ["bot:v002:0", 1], ["u1", 2]),
    ];
    const rec = botRecords(rows, none);
    expect(rec.has("v001")).toBe(false);
    expect(rec.get("v002")).toMatchObject({ games: 1, wins: 1 });
  });

  it("a person's higher rating makes a win worth more", () => {
    const rows = game("g1", ["bot:v001:0", 1], ["u1", 2]);
    const weak = botRecords(rows, new Map([["u1", 0]])).get("v001")?.rating ?? 0;
    const strong = botRecords(rows, new Map([["u1", 600]])).get("v001")?.rating ?? 0;
    expect(strong).toBeGreaterThan(weak);
  });

  it("says in words what it knows", () => {
    expect(describeRecord(undefined)).toBe("no games against people yet");
    expect(describeRecord({ games: 1, wins: 1, winRate: 1, rating: 30, provisional: true })).toBe(
      "wins 100% of 1 game against people · rating about 30 (rough)",
    );
    expect(describeRecord({ games: 12, wins: 3, winRate: 0.25, rating: -40, provisional: false })).toBe(
      "wins 25% of 12 games against people · rating about -40",
    );
  });
});
