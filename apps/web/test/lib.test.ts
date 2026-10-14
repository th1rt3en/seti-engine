import { createHash, generateKeyPairSync } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import moveTypes from "@/generated/move-types.json";
import {
  AuthFailure,
  checkPassword,
  createGuest,
  createSession,
  endSession,
  hashPassword,
  login,
  mintToken,
  signup,
  upgradeGuest,
  userForSession,
} from "@/lib/auth";
import { loadConfig } from "@/lib/config";
import { SqliteDb, migrationSql } from "@/lib/db";
import { engineAuth } from "@/lib/engineAuth";
import { LABELS, cardName, describeMove, groupMoves } from "@/lib/moves";
import { leaderboard, lobbyGames, profile } from "@/lib/queries";
import { verifyTurnstile } from "@/lib/turnstile";
import { createGame, gameMeta } from "@/lib/worker";
import { importSPKI, jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

const memory = () => new SqliteDb(":memory:", migrationSql());

describe("passwords and accounts", () => {
  it("hashes with a salt and checks the password", async () => {
    const a = await hashPassword("correct horse");
    const b = await hashPassword("correct horse");
    expect(a).not.toBe(b);
    expect(await checkPassword("correct horse", a)).toBe(true);
    expect(await checkPassword("wrong", a)).toBe(false);
    expect(await checkPassword("x", "garbage")).toBe(false);
  });

  it("signs up with a username and a password, refuses a taken name (any case) and bad input, and logs in", async () => {
    const db = memory();
    const u = await signup(db, "Ann", "password1");
    expect(u).toMatchObject({ name: "Ann", isGuest: false });
    await expect(signup(db, "ann", "password1")).rejects.toThrow("taken");
    await expect(signup(db, "A", "password1")).rejects.toThrow("username");
    await expect(signup(db, "has space", "password1")).rejects.toThrow("username");
    await expect(signup(db, "me@mail.com", "password1")).rejects.toThrow("username");
    await expect(signup(db, "Bob", "short")).rejects.toThrow("password");
    expect((await login(db, "ANN", "password1")).id).toBe(u.id);
    await expect(login(db, "Ann", "nope")).rejects.toThrow("The username or the password is wrong.");
    await expect(login(db, "ghost", "nope")).rejects.toThrow("The username or the password is wrong.");
  });

  it("a guest can play and later become an account with the same id", async () => {
    const db = memory();
    const g = await createGuest(db, "Visitor");
    expect(g).toMatchObject({ name: "Visitor", isGuest: true });
    await expect(login(db, "nobody", "whatever1")).rejects.toThrow(AuthFailure);
    const up = await upgradeGuest(db, g.id, "Visitor", "password1");
    expect(up).toMatchObject({ id: g.id, isGuest: false });
    expect((await login(db, "visitor", "password1")).id).toBe(g.id);
    await expect(upgradeGuest(db, g.id, "Again", "password1")).rejects.toThrow("Only a guest");
  });

  it("a guest cannot take the name of a registered player, and cannot upgrade to a taken name", async () => {
    const db = memory();
    await signup(db, "Ann", "password1");
    const g = await createGuest(db, "ann");
    expect(g.name).toMatch(/^Guest /);
    await expect(upgradeGuest(db, g.id, "ANN", "password1")).rejects.toThrow("taken");
  });

  it("the database refuses two registered users with the same name", async () => {
    const db = memory();
    await signup(db, "Ann", "password1");
    await expect(
      db.run("INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES ('x', 'ANN', NULL, 'h', 0, 1)"),
    ).rejects.toThrow();
  });
});

describe("Turnstile", () => {
  const cfg = { ...loadConfig({}), turnstileSecret: "secret" };
  const answer = (success: boolean, calls: { body: URLSearchParams }[] = []) =>
    (async (_url: unknown, init?: RequestInit) => {
      calls.push({ body: init?.body as URLSearchParams });
      return new Response(JSON.stringify({ success }));
    }) as typeof fetch;

  it("lets a visitor through only when Cloudflare says the token is good", async () => {
    const calls: { body: URLSearchParams }[] = [];
    expect(await verifyTurnstile("tok", "1.2.3.4", cfg, answer(true, calls), true)).toBe(true);
    expect(calls[0]?.body.get("secret")).toBe("secret");
    expect(calls[0]?.body.get("response")).toBe("tok");
    expect(calls[0]?.body.get("remoteip")).toBe("1.2.3.4");
    expect(await verifyTurnstile("tok", null, cfg, answer(false), true)).toBe(false);
    expect(await verifyTurnstile("", null, cfg, answer(true), true)).toBe(false); // no token: refused without asking
    const down = (async () => {
      throw new Error("offline");
    }) as typeof fetch;
    expect(await verifyTurnstile("tok", null, cfg, down, true)).toBe(false);
  });

  it("without a secret key it is skipped in development and refuses in production", async () => {
    const none = loadConfig({});
    expect(await verifyTurnstile("", null, none, answer(true), false)).toBe(true);
    expect(await verifyTurnstile("", null, none, answer(true), true)).toBe(false);
  });
});

describe("sessions", () => {
  it("a token finds its user until it expires or the user logs out; only a hash is stored", async () => {
    const db = memory();
    const u = await signup(db, "Ann", "password1");
    const { token } = await createSession(db, u.id, 1000);
    expect((await userForSession(db, token, 2000))?.id).toBe(u.id);
    expect(await userForSession(db, token, 1000 + 31 * 86_400_000)).toBeNull();
    expect(await userForSession(db, "other", 2000)).toBeNull();
    expect(await userForSession(db, undefined)).toBeNull();
    const stored = await db.all<{ id: string }>("SELECT id FROM sessions");
    expect(stored[0]?.id).not.toBe(token);
    await endSession(db, token);
    expect(await userForSession(db, token, 2000)).toBeNull();
  });
});

describe("tokens for the Worker", () => {
  it("are signed with the private key and carry the identity", async () => {
    const { privateKey, publicKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
    const cfg = {
      authPrivateKey: privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
      authIssuer: "http://site",
      authAudience: "seti-worker",
    };
    const token = await mintToken({ id: "u1", name: "Ann", isGuest: false }, cfg);
    const key = await importSPKI(publicKey.export({ type: "spki", format: "pem" }).toString(), "ES256");
    const { payload } = await jwtVerify(token, key, { issuer: "http://site", audience: "seti-worker" });
    expect(payload).toMatchObject({ sub: "u1", name: "Ann", reg: true });
    expect((payload.exp ?? 0) - (payload.iat ?? 0)).toBe(300);
    const guest = await mintToken({ id: "g1", name: "G", isGuest: true }, cfg);
    expect((await jwtVerify(guest, key)).payload.reg).toBe(false);
    await expect(mintToken({ id: "u", name: "x", isGuest: true }, { ...cfg, authPrivateKey: "" })).rejects.toThrow("AUTH_PRIVATE_KEY");
  });
});

describe("lobby, leaderboard and profile", () => {
  async function seed() {
    const db = memory();
    const ann = await signup(db, "Ann", "password1");
    const bob = await signup(db, "Bob", "password1");
    const guest = await createGuest(db, "Visitor");
    const game = (id: string, status: string, players: number, rated: number) =>
      db.run(
        "INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES (?, ?, ?, ?, ?, 1)",
        id,
        status,
        JSON.stringify({ players }),
        JSON.stringify({ kind: "per_turn", ms: 86_400_000 }),
        rated,
      );
    const seat = (id: string, n: number, u: { id: string; name: string }) =>
      db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES (?, ?, ?, ?, 1)", id, n, u.id, u.name);
    await game("open", "lobby", 3, 1);
    await seat("open", 0, ann);
    await game("full", "lobby", 2, 0);
    await seat("full", 0, ann);
    await seat("full", 1, bob);
    await game("done", "finished", 2, 1);
    await seat("done", 0, ann);
    await seat("done", 1, bob);
    await db.run("UPDATE game_players SET rank = 1, score = 120 WHERE game_id = 'done' AND seat = 0");
    await db.run("UPDATE games SET rated_counted = 1, reason = 'completed' WHERE id = 'done'");
    await db.run(
      "INSERT INTO ratings (user_id, rating, games, updated_at) VALUES (?, 1510, 1, 1), (?, 1490, 1, 1), (?, 1700, 5, 1)",
      ann.id,
      bob.id,
      guest.id,
    );
    await db.run(
      "INSERT INTO rating_history (game_id, user_id, rating_before, rating_after, rank, at) VALUES ('done', ?, 1500, 1510, 1, 5)",
      ann.id,
    );
    return { db, ann, bob };
  }

  it("lists only the lobby games that still have a free seat", async () => {
    const { db } = await seed();
    const games = await lobbyGames(db);
    expect(games).toHaveLength(1);
    expect(games[0]).toMatchObject({ id: "open", rated: true, players: 3, seats: ["Ann"], clock: "24 h per turn", host: "Ann" });
  });

  it("ranks registered players by rating (guests are left out)", async () => {
    const { db } = await seed();
    expect((await leaderboard(db)).map((r) => [r.name, r.rating])).toEqual([
      ["Ann", 1510],
      ["Bob", 1490],
    ]);
  });

  it("builds a profile with the rating, the history and the recent games", async () => {
    const { db, ann } = await seed();
    const p = await profile(db, ann.id);
    expect(p?.rating).toEqual({ rating: 1510, games: 1 });
    expect(p?.history).toHaveLength(1);
    expect(p?.recent.map((g) => g.id)).toContain("done");
    expect(await profile(db, "nobody")).toBeNull();
  });
});

describe("the Worker client", () => {
  const cfg = {
    ...loadConfig({ WORKER_URL: "http://worker" }),
    authAudience: "seti-worker",
    authIssuer: "http://site",
    authPrivateKey: generateKeyPairSync("ec", { namedCurve: "P-256" }).privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
  };

  it("sends the game with a bearer token", async () => {
    let seen: { url: string; init: RequestInit } | undefined;
    const fetcher = (async (url: string, init: RequestInit) => {
      seen = { url, init };
      return new Response(JSON.stringify({ ok: true, id: "abc" }));
    }) as unknown as typeof fetch;
    const reply = await createGame(
      { id: "u1", name: "Ann", isGuest: false },
      { options: { players: 2 }, clock: { kind: "none" }, rated: true },
      cfg,
      fetcher,
    );
    expect(reply).toEqual({ ok: true, id: "abc" });
    expect(seen?.url).toBe("http://worker/games");
    expect((seen?.init.headers as Record<string, string>).authorization).toMatch(/^Bearer ey/);
    expect(JSON.parse(String(seen?.init.body))).toMatchObject({ rated: true, options: { players: 2 } });
  });

  it("reads a game without a token and returns null for an unknown one", async () => {
    const ok = (async () => new Response(JSON.stringify({ status: "lobby" }))) as unknown as typeof fetch;
    const no = (async () => new Response("no", { status: 404 })) as unknown as typeof fetch;
    expect(await gameMeta("x", cfg, ok)).toEqual({ status: "lobby" });
    expect(await gameMeta("x", cfg, no)).toBeNull();
  });
});

describe("words for the moves (decision D10)", () => {
  it("every kind of move the engine offered in random games has a label", () => {
    const missing = Object.keys(moveTypes).filter((t) => !(t in LABELS));
    expect(missing).toEqual([]);
  });

  it("describes moves with card names, and falls back to the raw move", () => {
    expect(describeMove({ type: "play_card", card: "39" })).toBe("Play 61 Virginis Observation (39)");
    expect(describeMove({ type: "move_probe", probe: "probe1", to: [2, 5] })).toBe("Move probe probe1 to ring 2, sector 5");
    expect(describeMove({ type: "buy_card", source: "row:1" })).toContain("card 2 of the card row");
    expect(describeMove({ type: "never_seen", x: 1 })).toContain("never_seen");
    expect(cardName("ET.1")).toContain("First Contact");
  });

  it("groups the moves of a turn, and answers to a decision stay together", () => {
    const moves = [{ type: "pass" }, { type: "move_energy" }, { type: "end_turn" }, { type: "scan" }];
    expect(groupMoves(moves, false).map((g) => [g.title, g.moves.length])).toEqual([
      ["Main action", 2],
      ["Free actions", 1],
      ["Turn", 1],
    ]);
    expect(groupMoves(moves, true)).toHaveLength(1);
  });
});

describe("signed requests to the engine service", () => {
  it("the website signs with its own key, bound to the method, path and body", async () => {
    const { privateKey, publicKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
    const body = '{"a":1}';
    const h = await engineAuth(privateKey.export({ type: "pkcs8", format: "pem" }).toString(), "post", "/project", body, () => 5_000_000);
    const key = await importSPKI(publicKey.export({ type: "spki", format: "pem" }).toString(), "ES256");
    const { payload } = await jwtVerify(h.authorization?.slice(7) ?? "", key, { currentDate: new Date(5_000_000) });
    expect(payload).toMatchObject({ iss: "web", htm: "POST", htu: "/project", exp: 5030 });
    expect(payload.bsh).toBe(createHash("sha256").update(body).digest("base64url"));
    expect(await engineAuth("", "POST", "/x", "")).toEqual({});
  });
});
