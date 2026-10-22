import { describe, expect, it } from "vitest";
import { type StatRow, aggregate, parseFilter, spreadOf } from "../src/lib/stats";

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

  it("can leave the AI's rows out while the people of the same games still count, or keep only the AI's", () => {
    const rows = [
      row({ gameId: "a", seat: 0, userId: "u1", counters: { "action.launch": 4 } }),
      row({ gameId: "a", seat: 1, userId: "bot:v001:0", counters: { "action.launch": 10 } }),
      row({ gameId: "b", seat: 0, userId: "u2", counters: { "action.launch": 2 } }),
    ];
    const people = aggregate(rows, parseFilter({ who: "people" }));
    expect(people.rows).toBe(2);
    expect(people.mean["action.launch"]).toBe(3);
    expect(people.games).toBe(2); // the game with the AI is still a game of this person
    const ai = aggregate(rows, parseFilter({ who: "ai" }));
    expect(ai.rows).toBe(1);
    expect(ai.mean["action.launch"]).toBe(10);
    expect(aggregate(rows, parseFilter({ who: "everybody" })).rows).toBe(3); // anything else is everybody
    expect(aggregate(rows, any).rows).toBe(3);
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

  it("the spread: the lowest, the highest and the standard deviation of a counter over the players (a player without it counts as 0)", () => {
    const rows = [
      row({ gameId: "a", seat: 0, counters: { "action.scan": 2 } }),
      row({ gameId: "a", seat: 1, counters: { "action.scan": 6 } }),
      row({ gameId: "b", seat: 0, counters: {} }),
      row({ gameId: "b", seat: 1, counters: { "action.scan": 4 } }),
    ];
    const sp = aggregate(rows, any).spread["action.scan"];
    expect(sp?.min).toBe(0);
    expect(sp?.max).toBe(6);
    expect(sp?.std).toBeCloseTo(Math.sqrt(5), 10); // mean 3: deviations -1, 3, -3, 1 -> variance 5
    expect(spreadOf([5]).std).toBe(0);
    expect(spreadOf([])).toEqual({ min: 0, max: 0, std: 0 });
  });

  it("the spread of the final scores of the players of each species", () => {
    const rows = [
      row({ gameId: "a", seat: 0, score: 100, species: ["anomalies"] }),
      row({ gameId: "a", seat: 1, score: 200, species: ["anomalies"] }),
    ];
    const sp = aggregate(rows, any).species[0];
    expect(sp?.avgScore).toBe(150);
    expect(sp?.spread).toEqual({ min: 100, max: 200, std: 50 });
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
    expect(a.gold).toEqual([{ face: "Income-A", times: 3, avgPoints: 10, spread: { min: 8, max: 11, std: Math.sqrt(2) } }]);
    expect(a.techs).toEqual([{ tech: "probe-dot", share: 0.5 }]);
    expect(a.rounds).toEqual([2, 5]);
  });

  it("counts what a tech did over the players who have it, and only over them", () => {
    const rows = [
      row({ counters: { "stats.version": 2, "tech.probe-link": 1, "techuse.probe-link.asteroids": 4 } }),
      row({ seat: 1, counters: { "stats.version": 2, "tech.probe-link": 1, "techuse.probe-link.asteroids": 2 } }),
      row({ seat: 2, counters: { "stats.version": 2, "techuse.probe-link.asteroids": 9 } }), // counted for a tech that the player does not own at the end (a borrowed one): left out
      row({
        seat: 3,
        counters: {
          "stats.version": 2,
          "tech.computer-dot": 1,
          "techuse.computer-dot.top": 2,
          "techuse.computer-dot.vp": 4,
          "techuse.computer-dot.bottom": 1,
        },
      }),
      row({ seat: 4, counters: { "stats.version": 2 } }),
    ];
    const use = aggregate(rows, any).techUse;
    expect(use).toHaveLength(12);
    const skimmer = use.find((t) => t.tech === "probe-link");
    expect(skimmer).toMatchObject({ players: 2 });
    expect(skimmer?.metrics).toEqual([
      { key: "asteroids", label: "Avg asteroids moved into", mean: 3, total: 6, spread: { min: 2, max: 4, std: 1 } },
    ]);
    const memory = use.find((t) => t.tech === "computer-dot");
    expect(memory?.metrics.map((m) => [m.key, m.total])).toEqual([
      ["vp", 4],
      ["bottom", 1],
    ]);
    expect(memory?.metrics[1]?.label).toBe("Avg 1 credit spaces filled");
    expect(use.find((t) => t.tech === "probe-dot")).toMatchObject({ players: 0, metrics: [] }); // nothing to count
    expect(use.find((t) => t.tech === "telescope-cross")).toMatchObject({ players: 0 });
    expect(use.map((t) => t.tech).slice(0, 5)).toEqual(["probe-dot", "probe-link", "probe-branch", "probe-cross", "telescope-dot"]);
  });

  it("filters by the alien species of the game and by the organization the player picked", () => {
    const rows = [
      row({ gameId: "a", seat: 0, species: ["anomalies", "mascamites"], org: "xenolab", counters: { "action.launch": 4 } }),
      row({ gameId: "a", seat: 1, species: ["anomalies", "mascamites"], org: "fenwick_research_center", counters: { "action.launch": 2 } }),
      row({ gameId: "b", seat: 0, species: ["oumuamua", "centaurians"], org: "xenolab", counters: { "action.launch": 6 } }),
    ];
    // the species keeps every player of the games that have it
    const withSpecies = aggregate(rows, parseFilter({ species: "mascamites" }));
    expect([withSpecies.games, withSpecies.rows, withSpecies.mean["action.launch"]]).toEqual([1, 2, 3]);
    // the organization keeps the players who picked it, whatever the game
    const withOrg = aggregate(rows, parseFilter({ org: "xenolab" }));
    expect([withOrg.games, withOrg.rows, withOrg.mean["action.launch"]]).toEqual([2, 2, 5]);
    // both together: the players with the organization in the games with the species
    const both = aggregate(rows, parseFilter({ species: "oumuamua", org: "xenolab" }));
    expect([both.games, both.rows, both.mean["action.launch"]]).toEqual([1, 1, 6]);
    expect(aggregate(rows, parseFilter({ species: "arkhos" })).rows).toBe(0);
    // a name that is not a species or an organization of the engine is no filter
    expect(parseFilter({ species: "klingons", org: "../x" })).toMatchObject({ species: null, org: null });
    expect(aggregate(rows, parseFilter({ species: "klingons" })).rows).toBe(3);
  });

  it("works the newer counters out over the rows that have them: the rows of games that could not be replayed again count as nothing there", () => {
    const rows = [
      row({ seat: 0, counters: { "stats.version": 2, "probes.launched": 6, "action.launch": 2, "probes.launched.other": 4 } }),
      row({ seat: 1, counters: { "stats.version": 2, "probes.launched": 4, "action.launch": 2, "probes.launched.other": 2 } }),
      row({ seat: 2, counters: { "probes.launched": 10, "action.launch": 1 } }), // an old row: no "other", and no version
    ];
    const a = aggregate(rows, any);
    expect(a.fresh.rows).toBe(2);
    // over the rows that have them the numbers add up: launched = launch actions + the others
    expect(a.fresh.mean["probes.launched"]).toBe(5);
    expect(a.fresh.mean["action.launch"]).toBe(2);
    expect(a.fresh.mean["probes.launched.other"]).toBe(3);
    expect(a.fresh.mean["probes.launched"]).toBe((a.fresh.mean["action.launch"] ?? 0) + (a.fresh.mean["probes.launched.other"] ?? 0));
    // over all the rows they would not
    expect(a.mean["probes.launched"]).toBeCloseTo(20 / 3);
    expect(a.fresh.spread["probes.launched"]).toMatchObject({ min: 4, max: 6 });
  });

  it("no game gives zeros, not errors", () => {
    expect(aggregate([], any)).toMatchObject({ games: 0, rows: 0, orgs: [], species: [] });
  });
});
