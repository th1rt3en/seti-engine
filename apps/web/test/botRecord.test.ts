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
    // the players' rule: game 1 is lost below the floor of 100, so the rating stays 0; game 2 is won (K 60, expected 0.5) -> +30; game 3 is a tie
    // against 0 (K 60, expected 0.54 for a rating of 30) -> a small loss, rounded to a whole point after every game
    const exp = (a: number, b: number): number => 1 / (1 + 10 ** ((b - a) / 400));
    const r2 = Math.round(60 * (1 - exp(0, 0)));
    expect(r2).toBe(30);
    expect(r?.rating).toBe(r2 < 100 ? (0.5 - exp(r2, 0) < 0 ? r2 : Math.round(r2 + 60 * (0.5 - exp(r2, 0)))) : r2);
  });

  it("follows the rule of the players' ratings: below 100 a loss costs nothing, and the rating never drops below 100 once it is there", () => {
    const lose = (id: string) => game(id, ["bot:v001:0", 2], ["u1", 1]);
    const win = (id: string) => game(id, ["bot:v001:0", 1], ["u1", 2]);
    const rating = (rows: GameRow[]): number => botRecords(rows, new Map([["u1", 0]])).get("v001")?.rating ?? -1;
    expect(rating([...lose("a"), ...lose("b"), ...lose("c")])).toBe(0); // losing from the start: nothing is lost
    expect(rating([...win("a"), ...lose("b")])).toBe(30); // below 100 the loss costs nothing
    // wins take the rating above 100 (K 60, then 40, then 20): from there a loss costs something but never below 100
    const wins = Array.from({ length: 12 }, (_, i) => win(`w${i}`)).flat();
    expect(rating(wins)).toBeGreaterThan(100);
    const many = [...wins, ...Array.from({ length: 40 }, (_, i) => lose(`l${i}`)).flat()];
    expect(rating(many)).toBe(100);
    // at 100 or above, one loss is a real loss, down to the floor at the lowest
    expect(rating([...wins, ...lose("z")])).toBeLessThan(rating(wins));
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
