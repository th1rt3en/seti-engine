import { describe, expect, it } from "vitest";
import { pageOf } from "../src/lib/queries";

describe("the pages of a leaderboard", () => {
  it("counts the pages, takes a page past the last as the last, and anything that is no number as the first", () => {
    expect(pageOf(0, undefined, 25)).toEqual({ page: 1, pages: 1, offset: 0 });
    expect(pageOf(25, "1", 25)).toEqual({ page: 1, pages: 1, offset: 0 });
    expect(pageOf(26, "2", 25)).toEqual({ page: 2, pages: 2, offset: 25 });
    expect(pageOf(60, "9", 25)).toEqual({ page: 3, pages: 3, offset: 50 });
    expect(pageOf(60, "abc", 25).page).toBe(1);
    expect(pageOf(60, "-4", 25).page).toBe(1);
    expect(pageOf(60, "2.7", 25).page).toBe(2);
  });
});
