import {
  authLockedOut,
  changePassword,
  createSession,
  issueRecoveryCode,
  login,
  newRecoveryCode,
  normalizeCode,
  noteAuthFailure,
  recoverAccount,
  renewRecoveryCode,
  setPasswordByAdmin,
  signup,
  userForSession,
} from "@/lib/auth";
import { SqliteDb, migrationSql } from "@/lib/db";
import { describe, expect, it } from "vitest";

const memory = () => new SqliteDb(":memory:", migrationSql());

describe("the recovery code, the password change and the administrator's reset", () => {
  it("makes a code of 20 letters and digits in four groups, without the signs that look alike", () => {
    for (let i = 0; i < 50; i++) {
      const code = newRecoveryCode();
      expect(code).toMatch(/^[A-HJ-NP-Z2-9]{5}(-[A-HJ-NP-Z2-9]{5}){3}$/);
    }
    expect(normalizeCode("k7rt2 qw9hd-3mxpb zE4NA")).toBe("K7RT2QW9HD3MXPBZE4NA");
  });

  it("sets a new password with the code, once: the code then stops working and a new one is made", async () => {
    const db = memory();
    const u = await signup(db, "Ann", "password1");
    const code = await issueRecoveryCode(db, u.id);
    const { token } = await createSession(db, u.id);
    const out = await recoverAccount(db, "ann", code.toLowerCase(), "newpassword1");
    expect(out.user.id).toBe(u.id);
    expect(out.code).not.toBe(code);
    expect((await login(db, "Ann", "newpassword1")).id).toBe(u.id);
    await expect(login(db, "Ann", "password1")).rejects.toThrow("wrong");
    expect(await userForSession(db, token)).toBeNull(); // the sessions of the old password ended
    await expect(recoverAccount(db, "Ann", code, "another-one-1")).rejects.toThrow("The username or the recovery code is wrong.");
    expect((await recoverAccount(db, "Ann", out.code, "another-one-1")).user.id).toBe(u.id); // the new code works
  });

  it("gives the same message for an unknown name, an account without a code, a wrong code and a guest-style name", async () => {
    const db = memory();
    const u = await signup(db, "Bob", "password1");
    await issueRecoveryCode(db, u.id);
    const msg = "The username or the recovery code is wrong.";
    await expect(recoverAccount(db, "nobody", "AAAAA-AAAAA-AAAAA-AAAAA", "newpassword1")).rejects.toThrow(msg);
    await expect(recoverAccount(db, "Bob", "AAAAA-AAAAA-AAAAA-AAAAA", "newpassword1")).rejects.toThrow(msg);
    const v = await signup(db, "Cyd", "password1"); // never got a code
    expect(v.id).not.toBe(u.id);
    await expect(recoverAccount(db, "Cyd", "AAAAA-AAAAA-AAAAA-AAAAA", "newpassword1")).rejects.toThrow(msg);
  });

  it("refuses a new password that is too short, and keeps the old one and the code", async () => {
    const db = memory();
    const u = await signup(db, "Dee", "password1");
    const code = await issueRecoveryCode(db, u.id);
    await expect(recoverAccount(db, "Dee", code, "short")).rejects.toThrow("password");
    expect((await login(db, "Dee", "password1")).id).toBe(u.id);
    expect((await recoverAccount(db, "Dee", code, "longenough1")).user.id).toBe(u.id);
  });

  it("changes the password of a player who gives the current one, and ends the other sessions", async () => {
    const db = memory();
    const u = await signup(db, "Eve", "password1");
    const { token } = await createSession(db, u.id);
    await expect(changePassword(db, u.id, "wrong-one", "newpassword1")).rejects.toThrow("The current password is wrong.");
    await changePassword(db, u.id, "password1", "newpassword1");
    expect((await login(db, "Eve", "newpassword1")).id).toBe(u.id);
    expect(await userForSession(db, token)).toBeNull();
    await expect(changePassword(db, u.id, "newpassword1", "short")).rejects.toThrow("password");
  });

  it("makes a new recovery code for a player who gives the password, and the old code stops working", async () => {
    const db = memory();
    const u = await signup(db, "Flo", "password1");
    const first = await issueRecoveryCode(db, u.id);
    await expect(renewRecoveryCode(db, u.id, "nope")).rejects.toThrow("The password is wrong.");
    const second = await renewRecoveryCode(db, u.id, "password1");
    expect(second).not.toBe(first);
    await expect(recoverAccount(db, "Flo", first, "newpassword1")).rejects.toThrow("wrong");
    expect((await recoverAccount(db, "Flo", second, "newpassword1")).user.id).toBe(u.id);
  });

  it("lets the administrator set a password: the player logs in with it, other sessions end, a guest or unknown id is refused", async () => {
    const db = memory();
    const u = await signup(db, "Gus", "password1");
    const { token } = await createSession(db, u.id);
    expect(await setPasswordByAdmin(db, u.id, "from-the-admin1")).toBe(true);
    expect((await login(db, "Gus", "from-the-admin1")).id).toBe(u.id);
    expect(await userForSession(db, token)).toBeNull();
    expect(await setPasswordByAdmin(db, "no-such-id", "from-the-admin1")).toBe(false);
    await expect(setPasswordByAdmin(db, u.id, "short")).rejects.toThrow("password");
  });

  it("locks an address out after five failures in a quarter of an hour", async () => {
    const db = memory();
    const now = 1_000_000;
    for (let i = 0; i < 4; i++) await noteAuthFailure(db, "1.2.3.4", now + i);
    expect(await authLockedOut(db, "1.2.3.4", now + 10)).toBe(false);
    await noteAuthFailure(db, "1.2.3.4", now + 5);
    expect(await authLockedOut(db, "1.2.3.4", now + 10)).toBe(true);
    expect(await authLockedOut(db, "5.6.7.8", now + 10)).toBe(false);
    expect(await authLockedOut(db, "1.2.3.4", now + 16 * 60_000)).toBe(false);
  });
});

describe("the error report of the website", () => {
  it("sends the error to /errors, and at most 20 a minute", async () => {
    const { reportError, resetReportLimit } = await import("@/lib/errorReport");
    resetReportLimit();
    const urls: string[] = [];
    const bodies: string[] = [];
    const fetcher = (async (url: string, init: RequestInit) => {
      urls.push(url);
      bodies.push(String(init.body));
      return new Response("{}");
    }) as unknown as typeof fetch;
    const cfg = { engineUrl: "https://engine", engineSigningKey: "" };
    for (let i = 0; i < 30; i++) await reportError(cfg, new Error("boom"), { route: "/lobby" }, fetcher, () => 1000);
    expect(urls).toHaveLength(20);
    expect(urls[0]).toBe("https://engine/errors");
    const body = JSON.parse(bodies[0] ?? "{}");
    expect(body.source).toBe("web");
    expect(body.message).toBe("Error: boom");
    expect(body.detail.route).toBe("/lobby");
    resetReportLimit();
    await reportError(cfg, "plain text", {}, (async () => {
      throw new Error("engine down");
    }) as unknown as typeof fetch);
  });
});

describe("the settings kept with the account", () => {
  it("keeps only the known keys with a valid value, and gives them back", async () => {
    const { cleanSettings, getSettings, saveSettings } = await import("@/lib/userSettings");
    expect(
      cleanSettings({
        "seti-turn-sound": "0",
        "seti-hand-scale": "1.3",
        "seti-turn-notify": "yes",
        other: "1",
        "seti-confirm-irreversible": 1,
      }),
    ).toEqual({
      "seti-turn-sound": "0",
      "seti-hand-scale": "1.3",
    });
    expect(cleanSettings(null)).toEqual({});
    expect(cleanSettings({ "seti-hand-scale": "9" })).toEqual({});
    const db = memory();
    const u = await signup(db, "Hal", "password1");
    expect(await getSettings(db, u.id)).toEqual({});
    await saveSettings(db, u.id, { "seti-turn-sound": "0" });
    await saveSettings(db, u.id, { "seti-turn-sound": "1", "seti-hand-scale": "0.8" });
    expect(await getSettings(db, u.id)).toEqual({ "seti-turn-sound": "1", "seti-hand-scale": "0.8" });
  });
});
