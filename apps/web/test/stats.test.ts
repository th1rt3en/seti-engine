import { describe, expect, it } from "vitest";
import { type StatRow, aggregate, parseFilter } from "../src/lib/stats";

const row = (over: Partial<StatRow>): StatRow => ({
  gameId: "g1",
  seat: 0,
  userId: "u1",
  players: 2,
  rated: true,
  expansion: false,
  rank: 1,
  won: true,
  score: 100,
  org: null,
  orgOffered: [],
  species: ["anomalies", "mascamites"],
  counters: {},
  eloDelta: null,
  ...over,
});
const any = parseFilter({});

describe("statistics", () => {
  it("the filter keeps the games with the chosen number of players, expansion and rating", () => {
    const rows = [
      row({ gameId: "a", players: 2, counters: { "action.launch": 4 } }),
      row({ gameId: "b", players: 3, counters: { "action.launch": 2 } }),
      row({ gameId: "c", players: 3, rated: false, expansion: true, counters: { "action.launch": 6 } }),
    ];
    expect(aggregate(rows, any).mean["action.launch"]).toBe(4);
    expect(aggregate(rows, parseFilter({ players: "3" })).mean["action.launch"]).toBe(4);
    expect(aggregate(rows, parseFilter({ players: "3", expansion: "no" })).mean["action.launch"]).toBe(2);
    expect(aggregate(rows, parseFilter({ rated: "no" })).games).toBe(1);
    expect(aggregate(rows, parseFilter({ players: "9" })).rows).toBe(3); // not a number of players: any
  });

  it("the scores: the final scores in order, their mean, the best, and the share of the players who won", () => {
    const rows = [
      row({ gameId: "a", seat: 0, score: 250, won: true }),
      row({ gameId: "a", seat: 1, score: 130, won: false }),
      row({ gameId: "b", seat: 0, score: 100, won: false }),
      row({ gameId: "b", seat: 1, score: 220, won: true }),
    ];
    const s = aggregate(rows, any);
    expect(s.scores).toEqual([100, 130, 220, 250]);
    expect(s.avgScore).toBe(175);
    expect(s.bestScore).toBe(250);
    expect(s.winRate).toBe(0.5);
    const none = aggregate([], any);
    expect(none.scores).toEqual([]);
    expect(none.avgScore).toBe(0);
    expect(none.bestScore).toBe(0);
  });

  it("organizations: the pick rate, the win rate and the Elo change of those who picked it", () => {
    const rows = [
      row({ gameId: "a", seat: 0, org: "x", orgOffered: ["x", "y"], won: true, eloDelta: 20 }),
      row({ gameId: "a", seat: 1, org: "z", orgOffered: ["x", "z"], won: false, eloDelta: -20 }),
      row({ gameId: "b", seat: 0, org: "y", orgOffered: ["x", "y"], won: true, rated: false, eloDelta: null }),
    ];
    const orgs = Object.fromEntries(aggregate(rows, any).orgs.map((o) => [o.org, o]));
    expect(orgs.x).toMatchObject({ offered: 3, picked: 1, winRate: 1, eloDelta: 20, eloGames: 1 });
    expect(orgs.x?.pickRate).toBeCloseTo(1 / 3);
    expect(orgs.y).toMatchObject({ offered: 2, picked: 1, eloDelta: null });
    expect(orgs.z).toMatchObject({ offered: 1, picked: 1, pickRate: 1, winRate: 0, eloDelta: -20 });
  });

  it("an alien species: the average final score of the players of the games that have it", () => {
    const rows = [
      row({ gameId: "a", score: 100, species: ["anomalies", "centaurians"] }),
      row({ gameId: "a", seat: 1, score: 60, species: ["anomalies", "centaurians"] }),
      row({ gameId: "b", score: 50, species: ["anomalies", "exertians"] }),
    ];
    const sp = Object.fromEntries(aggregate(rows, any).species.map((s) => [s.species, s]));
    expect(sp.anomalies).toMatchObject({ games: 2, avgScore: 70 });
    expect(sp.exertians).toMatchObject({ games: 1, avgScore: 50 });
  });

  it("gold tile faces, techs and the rounds with an income", () => {
    const rows = [
      row({ counters: { "gold.Income-A.points": 22, "gold.Income-A.times": 2, "tech.probe-dot": 1, "incomerate.r2.credit": 4 } }),
      row({ seat: 1, counters: { "gold.Income-A.points": 8, "gold.Income-A.times": 1, "incomerate.r5.credit": 6 } }),
    ];
    const a = aggregate(rows, any);
    expect(a.gold).toEqual([{ face: "Income-A", times: 3, avgPoints: 10 }]);
    expect(a.techs).toEqual([{ tech: "probe-dot", share: 0.5 }]);
    expect(a.rounds).toEqual([2, 5]);
  });

  it("no game gives zeros, not errors", () => {
    expect(aggregate([], any)).toMatchObject({ games: 0, rows: 0, orgs: [], species: [] });
  });
});
