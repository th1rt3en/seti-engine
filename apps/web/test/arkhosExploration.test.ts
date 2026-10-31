import { describe, expect, it } from "vitest";
import { EXPLORATION_CARDS, possibleExploration } from "../src/lib/arkhosExploration";

describe("the exploration cards that can come next (EXP-ARK-02, EXP-ARK-04)", () => {
  it("are the nine cards of Arkhos", () => {
    expect(EXPLORATION_CARDS).toHaveLength(9);
    expect(new Set(EXPLORATION_CARDS).size).toBe(9);
  });

  it("are all the cards that are not revealed, as the order of the deck and the cards set aside are secret", () => {
    expect(possibleExploration(5, [])).toEqual(EXPLORATION_CARDS);
    expect(possibleExploration(3, ["ET 33", "ET 40"])).toEqual(EXPLORATION_CARDS.filter((c) => c !== "ET 33" && c !== "ET 40"));
  });

  it("are all nine again when the deck has run out, because the next reveal shuffles the revealed cards in", () => {
    expect(possibleExploration(0, ["ET 33", "ET 34", "ET 35", "ET 36", "ET 37"])).toEqual(EXPLORATION_CARDS);
  });
});
