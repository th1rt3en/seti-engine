import { describe, expect, it } from "vitest";
import { statGroups } from "../src/lib/gameStatRows";

const value = (groups: ReturnType<typeof statGroups>, title: string, label: string, c: Record<string, number>): string | undefined =>
  groups
    .find((g) => g.title === title)
    ?.lines.find((l) => l.label === label)
    ?.value(c);

describe("the statistics of one game", () => {
  const a = {
    "action.launch": 3,
    "data.lost": 9,
    "data.computer": 7,
    "incomerate.r1.credit": 3,
    "incomerate.r5.energy": 4,
    "tech.probe-dot": 1,
    "gold.Income-A.points": 22,
    "gold.Income-A.times": 2,
  };
  const b = { "action.launch": 1, "publicity.visit.mars": 2, "publicity.visit.comet": 1 };
  const groups = statGroups([a, b]);

  it("a counter that is missing is 0", () => {
    expect(value(groups, "Actions", "Launch", a)).toBe("3");
    expect(value(groups, "Actions", "Scan", a)).toBe("0");
  });

  it("data used in other ways is what was lost less what went into the computer", () => {
    expect(value(groups, "Data", "Used in other ways", a)).toBe("2");
    expect(value(groups, "Data", "Used in other ways", b)).toBe("0");
  });

  it("publicity from planets adds the planets and leaves out comets and asteroids", () => {
    expect(value(groups, "Publicity gained", "From planets", b)).toBe("2");
    expect(value(groups, "Publicity gained", "From comets", b)).toBe("1");
  });

  it("the rounds, the techs and the gold faces that appear in some player's counters have a row", () => {
    expect(groups.find((g) => g.title.startsWith("Income"))?.lines.map((l) => l.label)).toEqual(["Round 1", "Round 5"]);
    expect(value(groups, "Income at the end of each round (credit / energy / card)", "Round 5", a)).toBe("0 / 4 / 0");
    expect(value(groups, "Tech researched", "Twin Probes", a)).toBe("1");
    expect(value(groups, "Gold scoring tiles (points)", "Income-A", a)).toBe("22");
  });
});
