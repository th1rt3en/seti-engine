import { describe, expect, it } from "vitest";
import { ACCOUNT_TABLE_LIMIT, GUEST_TABLE_LIMIT, overTableLimit } from "../src/core/limits.js";

describe("the open tables of a player", () => {
  it("a guest can have 1 table open, an account 10", () => {
    expect(GUEST_TABLE_LIMIT).toBe(1);
    expect(ACCOUNT_TABLE_LIMIT).toBe(10);
    expect(overTableLimit(false, 0)).toBeNull();
    expect(overTableLimit(false, 1)).not.toBeNull();
    expect(overTableLimit(true, 9)).toBeNull();
    expect(overTableLimit(true, 10)).not.toBeNull();
  });

  it("tells an account to finish its tables, names the limit and says that solo tables can be resigned from the profile", () => {
    const m = overTableLimit(true, 10)?.message ?? "";
    expect(overTableLimit(true, 10)?.code).toBe("table_limit");
    expect(m).toContain("finish your tables");
    expect(m).toContain("10 tables");
    expect(m).toContain("resign your solo tables from your profile without any repercussion");
    expect(m).not.toContain("create an account");
  });

  it("tells a guest that an account can have up to 10 tables open", () => {
    const m = overTableLimit(false, 1)?.message ?? "";
    expect(m).toContain("1 table");
    expect(m).toContain("create an account to have up to 10 open tables");
    expect(m).toContain("resign your solo tables");
  });
});
