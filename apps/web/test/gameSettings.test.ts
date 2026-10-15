import { parseScale } from "@/lib/gameSettings";
import { describe, expect, it } from "vitest";

describe("the size of the cards in the hand", () => {
  it("is 1 when nothing is kept or the value is not a number, and stays inside its limits", () => {
    expect(parseScale(null)).toBe(1);
    expect(parseScale("abc")).toBe(1);
    expect(parseScale("1.3")).toBeCloseTo(1.3);
    expect(parseScale("0.1")).toBe(0.7);
    expect(parseScale("5")).toBe(1.6);
  });
});
