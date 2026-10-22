import { describe, expect, it } from "vitest";
import { ordinal, turnOrder } from "../src/lib/turnOrder";

const seats = (n: number) => Array.from({ length: n }, (_, index) => ({ index }));
const order = (n: number, start: number): number[] => turnOrder(seats(n), start).map((p) => p.index);

describe("the order of play of a round", () => {
  it("starts with the player who has the marker and goes on by seat", () => {
    expect(order(3, 0)).toEqual([0, 1, 2]);
    expect(order(3, 1)).toEqual([1, 2, 0]);
    expect(order(3, 2)).toEqual([2, 0, 1]);
    expect(order(2, 1)).toEqual([1, 0]);
    expect(order(4, 3)).toEqual([3, 0, 1, 2]);
  });

  it("changes with the marker: every round it is one seat further (ROUND-03), so the labels follow", () => {
    // five rounds of a 3-player game, the marker moving on as the engine does at the end of a round
    let start = 1;
    const firsts: number[] = [];
    const labels: string[][] = [];
    for (let round = 1; round <= 5; round++) {
      const o = turnOrder(seats(3), start);
      firsts.push(o[0]?.index ?? -1);
      labels.push(o.map((p, rank) => `${p.index}:${ordinal(rank)}`));
      start = (start + 1) % 3;
    }
    expect(firsts).toEqual([1, 2, 0, 1, 2]);
    expect(labels[0]).toEqual(["1:1st", "2:2nd", "0:3rd"]);
    expect(labels[1]).toEqual(["2:1st", "0:2nd", "1:3rd"]);
    expect(labels[2]).toEqual(["0:1st", "1:2nd", "2:3rd"]);
  });

  it("does not change the list it is given, and names the places", () => {
    const given = seats(3);
    turnOrder(given, 2);
    expect(given.map((p) => p.index)).toEqual([0, 1, 2]);
    expect([0, 1, 2, 3, 4].map(ordinal)).toEqual(["1st", "2nd", "3rd", "4th", "5th"]);
  });
});
