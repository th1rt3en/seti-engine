import { describe, expect, it } from "vitest";
import { type StatRow, aggregate, matches, parseFilter, spreadOf } from "../src/lib/stats";

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
const any = parseFilter({ who: "all" }); // every row; the default of the page is the people

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
    expect(aggregate(rows, parseFilter({ who: "all" })).rows).toBe(3);
    expect(parseFilter({}).who).toBe("people"); // the default
    expect(parseFilter({ who: "anything" }).who).toBe("people");
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

  it("the sources of a resource: the mean of each over the players, with how they differ; the publicity of moving is split by what was visited", () => {
    const rows = [
      row({
        gameId: "a",
        counters: {
          "gain.card.credit": 4,
          "gain.income.credit": 6,
          "gain.move.publicity": 5,
          "publicity.visit.comet": 2,
          "publicity.visit.mars": 1,
        },
      }),
      row({
        gameId: "b",
        counters: { "gain.card.credit": 2, "gain.income.credit": 6, "gain.move.publicity": 1, "publicity.visit.asteroid": 1 },
      }),
    ];
    const g = aggregate(rows, any).gains;
    // the credits are in groups: income, organization, alien effects, missions, quick start cards, technologies, and the others
    expect(g.credit?.map((x) => [x.key, x.mean])).toEqual([
      ["group_income", 6],
      ["other", 3],
    ]);
    expect(g.credit?.[1]?.spread).toEqual({ min: 2, max: 4, std: 1 });
    expect(g.credit?.[1]?.parts).toEqual([{ key: "card", mean: 3 }]);
    const pub = Object.fromEntries((g.publicity ?? []).map((x) => [x.key, x.mean]));
    expect(pub).toEqual({ group_probe: 2, other: 1 }); // the visits (1 + 0.5 + 0.5) are one group; the rest of the moves is in the others
  });

  it("what a resource was spent on, and the quick start cards that were kept (version 8 rows only)", () => {
    const v = { "stats.version": 8 };
    const rows = [
      row({
        gameId: "a",
        score: 90,
        won: true,
        counters: {
          ...v,
          "spend.play_card.credit": 6,
          "spend.launch.credit": 2,
          "quick.SR.1": 1,
          "quick.SR.3": 1,
          "quickoffered.SR.1": 1,
          "quickoffered.SR.3": 1,
        },
      }),
      row({
        gameId: "b",
        score: 70,
        won: false,
        counters: { ...v, "spend.play_card.credit": 2, "quick.SR.1": 1, "quickoffered.SR.1": 1, "quickoffered.SR.3": 1 },
      }),
      row({ gameId: "c", score: 300, counters: { "spend.play_card.credit": 50 } }), // an older row: nothing was counted
    ];
    const a = aggregate(rows, any);
    expect(a.spends.credit?.map((x) => [x.key, x.mean])).toEqual([
      ["play_card", 4],
      ["launch", 1],
    ]);
    const sr1 = a.quick.find((q) => q.id === "SR.1");
    expect(sr1).toMatchObject({ players: 2, offered: 2, keepRate: 1, winRate: 0.5 });
    expect(a.quick.find((q) => q.id === "SR.3")).toMatchObject({ players: 1, offered: 2, keepRate: 0.5 });
    expect(sr1?.avgScore).toBe(80);
    expect(a.quick.map((q) => q.id)).toEqual(["SR.1", "SR.3"]);
  });

  it("the credits of the others are told by action, and the alien sources are one group", () => {
    const rows = [
      row({
        counters: {
          "gain.move.credit": 5,
          "gainmove.exchange.credit": 3,
          "gain.trace.credit": 1,
          "gain.alien.credit": 2,
          "gain.tech.credit": 4,
        },
      }),
    ];
    const credit = aggregate(rows, any).gains.credit ?? [];
    const by = Object.fromEntries(credit.map((x) => [x.key, x]));
    expect(by.group_alien?.mean).toBe(3);
    expect(by.group_tech?.mean).toBe(4);
    expect(by.other?.parts).toEqual([
      { key: "move_exchange", mean: 3 },
      { key: "move", mean: 2 }, // what the engine did not tell by action (older rows)
    ]);
  });

  it("the final score comes in parts (version 3 rows only)", () => {
    const rows = [
      row({ counters: { "stats.version": 3, "gain.card.vp": 10, "final.cards": 12, "final.gold": 8 } }),
      row({ gameId: "b", counters: { "gain.card.vp": 20 } }), // an older row: no parts
    ];
    const vp = Object.fromEntries((aggregate(rows, any).gains.vp ?? []).map((x) => [x.key, x.mean]));
    expect(vp).toEqual({ group_card: 15, final_cards: 12, final_gold: 8 });
  });

  it("the cards played: by the players who played them, with the round, the final score, the win and the organization", () => {
    const v = { "stats.version": 3 };
    const rows = [
      row({ gameId: "a", score: 100, won: true, org: "xenolab", counters: { ...v, "card.17.r2": 1, "card.40.r3": 1 } }),
      row({ gameId: "b", score: 80, won: false, org: "xenolab", counters: { ...v, "card.17.r4": 1 } }),
      row({ gameId: "c", score: 60, won: false, org: "stratus_core", counters: { ...v, "card.17.r4": 2 } }),
      row({ gameId: "d", score: 200, counters: { "card.17.r2": 5 } }), // an old row: its cards were not counted
    ];
    const a = aggregate(rows, any);
    expect(a.cardRows).toBe(3);
    const c17 = a.cards.find((x) => x.id === "17");
    expect(c17).toMatchObject({ players: 3, plays: 4, winRate: 1 / 3, rounds: { 2: 1, 4: 3 } });
    expect(c17?.avgScore).toBeCloseTo(80);
    expect(c17?.avgRound).toBeCloseTo((2 + 4 * 3) / 4);
    expect(c17?.share).toBe(1);
    expect(c17?.orgs).toEqual([
      { org: "xenolab", n: 2 },
      { org: "stratus_core", n: 1 },
    ]);
    expect(a.cards[0]?.id).toBe("17"); // the most played first
  });

  it("several species or organizations count as any of them", () => {
    const r1 = row({ gameId: "a", species: ["anomalies", "mascamites"], org: "xenolab" });
    const r2 = row({ gameId: "b", species: ["oumuamua", "centaurians"], org: "stratus_core" });
    const r3 = row({ gameId: "c", species: ["exertians", "arkhos"], org: null });
    const rows = [r1, r2, r3];
    const kept = (f: Parameters<typeof parseFilter>[0]) => rows.filter((r) => matches(r, parseFilter(f))).map((r) => r.gameId);
    expect(kept({ who: "all" })).toEqual(["a", "b", "c"]);
    expect(kept({ who: "all", species: "mascamites,oumuamua" })).toEqual(["a", "b"]);
    expect(kept({ who: "all", org: "xenolab,stratus_core" })).toEqual(["a", "b"]); // a player with no organization is in none of them
    expect(kept({ who: "all", species: ["arkhos", "oumuamua"], org: "stratus_core" })).toEqual(["b"]);
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
    expect(parseFilter({ species: "klingons", org: "../x" })).toMatchObject({ species: [], org: [] });
    // several: `a,b` or the name twice, in a fixed order, without repeats and without what is not known
    expect(parseFilter({ species: "oumuamua,anomalies,anomalies,klingons", org: ["xenolab", "stratus_core"] })).toMatchObject({
      species: ["anomalies", "oumuamua"],
      org: ["stratus_core", "xenolab"],
    });
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

  it("averages the counters of a species over the players of the games where it was discovered, and only over them", () => {
    const rows = [
      row({ seat: 0, counters: { "alien.mascamites.games": 1, "mascamites.delivered": 3, "alien.mascamites.sample.vp": 4 } }),
      row({ seat: 1, counters: { "alien.mascamites.games": 1, "mascamites.delivered": 1 } }),
      row({ seat: 2, counters: { "mascamites.delivered": 9 } }), // a game where it was not discovered: not counted
    ];
    const a = aggregate(rows, any).alien;
    expect(a.mascamites?.rows).toBe(2);
    expect(a.mascamites?.mean["mascamites.delivered"]).toBe(2);
    expect(a.mascamites?.mean["alien.mascamites.sample.vp"]).toBe(2);
    expect(a.mascamites?.spread["mascamites.delivered"]).toMatchObject({ min: 1, max: 3 });
    expect(a.amoeba?.rows).toBe(0); // no game with the species
  });
  it("the techs by type and by where they came from (version 9 rows only), and the research share of each tech", () => {
    const rows = [
      row({ counters: { "stats.version": 9, "tech.probe-dot": 1, "techcat.probe": 1, "techcat.computer": 1, "techorigin.research": 2 } }),
      row({ counters: { "stats.version": 9, "techcat.probe": 1, "techorigin.alien": 1, "techorigin.research": 0 } }),
      row({ counters: { "stats.version": 8, "techcat.probe": 4, "techorigin.card": 9 } }), // an older row: no origins
    ];
    const a = aggregate(rows, any);
    expect(a.techOrigins.map((x) => [x.key, x.mean])).toEqual([
      ["research", 1],
      ["alien", 0.5],
    ]);
    expect(a.techTypes.map((x) => x.key)).toEqual(["probe", "computer"]);
    expect(a.techUse.find((t) => t.tech === "probe-dot")?.share).toBeCloseTo(1 / 3);
  });
  it("the play rate, the discard rate, the mission completion and the end-of-game points of a card (version 10 rows)", () => {
    const v = { "stats.version": 10 };
    const rows = [
      row({
        counters: {
          ...v,
          "cardheld.7": 1,
          "card.7.r2": 1,
          "cardmission.7": 1,
          "cardheld.9": 1,
          "cardcorner.9": 1,
          "cardend.12": 6,
          "cardheld.12": 1,
          "card.12.r1": 1,
        },
      }),
      row({ counters: { ...v, "cardheld.7": 1, "cardheld.9": 1, "card.9.r3": 1 } }),
      row({ counters: { "stats.version": 9, "cardheld.7": 1 } }), // an older row: nothing was counted
    ];
    const cards = aggregate(rows, any).cards;
    const by = (id: string) => cards.find((c) => c.id === id);
    expect(by("7")).toMatchObject({ held: 2, playRate: 0.5, discardRate: 0, missionRate: 1 });
    expect(by("9")).toMatchObject({ held: 2, playRate: 0.5, discardRate: 0.5, discards: 1 });
    expect(by("12")).toMatchObject({ held: 1, playRate: 1, endAvg: 6 });
  });

  it("works out the statistics of many rows with many counters in a time a Worker can afford (error 1102)", () => {
    // the real rows have about 250 counters each; the page used to scan every counter name for every row, resource and species (quadratic)
    const species = ["centaurians", "mascamites", "exertians", "oumuamua", "amoeba", "arkhos", "glyphids", "anomalies"];
    const rows = Array.from({ length: 300 }, (_, i) => {
      const counters: Record<string, number> = { "stats.version": 12, "alien.arkhos.games": 1 };
      for (const res of ["credit", "energy", "card", "publicity", "data", "vp", "move"]) {
        for (let k = 0; k < 12; k++) {
          counters[`gain.src${k}.${res}`] = k + 1;
          counters[`spend.use${k}.${res}`] = k;
        }
        for (const sp of species) counters[`alien.${sp}.part.${res}`] = 1;
      }
      for (let c = 0; c < 60; c++) {
        counters[`card.${c}.r${(c % 5) + 1}`] = 1;
        counters[`cardheld.${c}`] = 1;
      }
      return row({ gameId: `g${i}`, score: 100 + i, won: i % 2 === 0, counters });
    });
    const t = performance.now();
    const a = aggregate(rows, any);
    expect(performance.now() - t).toBeLessThan(1500); // about 150 ms here; the quadratic version took several seconds
    expect(a.cards.find((c) => c.id === "7")).toMatchObject({ players: 300, plays: 300, held: 300, playRate: 1 });
    expect(a.alien.arkhos?.mean["alien.arkhos.all.credit"]).toBe(1);
  });
});
