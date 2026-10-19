import { createHash, generateKeyPairSync } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import moveTypes from "@/generated/move-types.json";
import { adminToken, checkPassphrase, lockedOut, noteFailure, validAdminToken } from "@/lib/admin";
import { countAccounts, deleteAccount, listAccounts, resetRating, setRating } from "@/lib/adminData";
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
import { glyphIconReward } from "@/lib/glyphids";
import { LABELS, cardName, cornerGlyph, describeMove, groupMoves, handMoveText, irreversibleText } from "@/lib/moves";
import {
  allPlayers,
  computeStats,
  countEndedGames,
  countPlayingGames,
  createdRecently,
  endedGames,
  leaderboard,
  lobbyGames,
  playingGames,
  profile,
} from "@/lib/queries";
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
    expect(games[0]).toMatchObject({
      id: "open",
      rated: true,
      players: 3,
      seats: ["Ann"],
      clock: "24 h per turn",
      host: "Ann",
      expansion: false,
    });
  });

  it("lists the games in progress and the games that are over (resigned ones too) in pages, and leaves sandbox games out", async () => {
    const { db, ann, bob } = await seed();
    const add = async (id: string, status: string, options: object, ended: number | null, reason: string | null, result: object | null) => {
      await db.run(
        "INSERT INTO games (id, status, options_json, clock_json, rated, created_at, started_at, ended_at, reason, result_json) VALUES (?, ?, ?, ?, 0, 1, 2, ?, ?, ?)",
        id,
        status,
        JSON.stringify(options),
        JSON.stringify({ kind: "per_turn", ms: 86_400_000 }),
        ended,
        reason,
        result === null ? null : JSON.stringify(result),
      );
      await db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES (?, 0, ?, ?, 1)", id, ann.id, ann.name);
      await db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES (?, 1, ?, ?, 1)", id, bob.id, bob.name);
    };
    await db.run("UPDATE games SET ended_at = 100 WHERE id = 'done'");
    await add("quit", "finished", { players: 2 }, 200, "resigned", { forfeit: 1 });
    await add("practice", "finished", { players: 1, sandbox: true }, 300, "completed", null);
    await add("live", "playing", { players: 2 }, null, null, null);
    await add("play-sandbox", "playing", { players: 1, sandbox: true }, null, null, null);
    expect(await countEndedGames(db)).toBe(2);
    expect(await countPlayingGames(db)).toBe(1);
    const over = await endedGames(db, 1, 0); // the latest first, one on a page
    expect(over).toHaveLength(1);
    expect(over[0]).toMatchObject({ id: "quit", reason: "resigned", forfeit: "Bob" });
    expect((await endedGames(db, 1, 1))[0]).toMatchObject({ id: "done", reason: "completed", forfeit: null });
    expect(over[0]?.seats.map((x) => x.name)).toEqual(["Ann", "Bob"]);
    expect((await playingGames(db, 10, 0)).map((g) => g.id)).toEqual(["live"]);
    expect(await playingGames(db, 10, 1)).toEqual([]);
  });

  it("lists every registered player by name, with the starting rating when unrated, and finds by name", async () => {
    const { db } = await seed();
    const carl = await signup(db, "carl", "password1");
    const all = await allPlayers(db);
    expect(all.map((r) => r.name)).toEqual(["Ann", "Bob", "carl"]); // guests left out, any case sorted together
    expect(all.find((r) => r.user_id === carl.id)).toMatchObject({ rating: 0, rated_games: 0, games: 0 });
    expect((await allPlayers(db, "AN")).map((r) => r.name)).toEqual(["Ann"]);
    expect(await allPlayers(db, "%")).toEqual([]); // a wildcard is not a wildcard
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
    // the answers to a decision are one group; the free actions that may interrupt it (FREE-00) and the undo have groups of their own
    expect(groupMoves([{ type: "scan_earth" }, { type: "scan_done" }], true)).toHaveLength(1);
    expect(groupMoves([{ type: "scan_earth" }, { type: "move_energy" }, { type: "undo" }], true).map((g) => g.title)).toEqual([
      "Your choice",
      "Free actions",
      "Undo",
    ]);
    // the free actions that are answers to a decision of their own (data overflow) stay with it
    expect(groupMoves([{ type: "place_data" }, { type: "data_done" }], true, true)).toHaveLength(1);
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

describe("clock presets (D26, D34)", () => {
  it("turn-based play has three speeds in days, each also available without a clock", async () => {
    const { CLOCK_PRESETS } = await import("@/lib/worker");
    const DAY = 86_400_000;
    const HOUR = 3_600_000;
    expect(CLOCK_PRESETS.tb_slow?.clock).toEqual({ kind: "bank", initialMs: 4 * DAY, incrementMs: 12 * HOUR });
    expect(CLOCK_PRESETS.tb_normal?.clock).toEqual({ kind: "bank", initialMs: 3 * DAY, incrementMs: 9 * HOUR });
    expect(CLOCK_PRESETS.tb_fast?.clock).toEqual({ kind: "bank", initialMs: 2 * DAY, incrementMs: 6 * HOUR });
    expect(CLOCK_PRESETS.none).toMatchObject({ mode: "both", clock: { kind: "none" } });
    const modes = (m: string) =>
      Object.entries(CLOCK_PRESETS)
        .filter(([, p]) => p.mode === m || p.mode === "both")
        .map(([k]) => k);
    expect(modes("realtime")).toEqual(["none", "fast", "normal", "slow"]);
    expect(modes("turnbased")).toEqual(["none", "tb_fast", "tb_normal", "tb_slow"]);
  });

  it("describes a clock in words, in minutes or in days", async () => {
    const { describeClock, spanText } = await import("@/lib/queries");
    expect(spanText(90_000)).toBe("1 min 30 s");
    expect(spanText(3 * 86_400_000)).toBe("3 days");
    expect(describeClock(JSON.stringify({ kind: "bank", initialMs: 450_000, incrementMs: 150_000 }))).toBe(
      "7 min 30 s + 2 min 30 s per turn",
    );
    expect(describeClock(JSON.stringify({ kind: "bank", initialMs: 4 * 86_400_000, incrementMs: 12 * 3_600_000 }))).toBe(
      "4 days + 12 h per turn",
    );
    expect(describeClock(JSON.stringify({ kind: "none" }))).toBe("no clock");
  });
});

describe("profile statistics", () => {
  const row = (rank: number | null, score: number | null, rated: number, options: object) => ({
    rank,
    score,
    rated_counted: rated,
    options_json: JSON.stringify(options),
  });

  it("counts wins, the win rate and the games by number of players, leaving the sandbox out", () => {
    const s = computeStats([
      row(1, 120, 1, { players: 2 }),
      row(2, 90, 1, { players: 3, expansion: true }),
      row(1, 100, 0, { players: 1 }),
      row(1, 10, 0, { players: 1, sandbox: true }),
    ]);
    expect(s).toMatchObject({
      games: 3,
      wins: 2,
      winRate: 67,
      ratedGames: 2,
      ratedWins: 1,
      avgScore: 103,
      bestScore: 120,
      expansionGames: 1,
    });
    expect(s.byPlayers).toEqual({ "2": { games: 1, wins: 1 }, "3": { games: 1, wins: 0 }, solo: { games: 1, wins: 1 } });
  });

  it("has no win rate without a game", () => {
    expect(computeStats([])).toMatchObject({ games: 0, winRate: null, avgScore: null, bestScore: null });
  });
});

describe("the prompts of the hand", () => {
  it("says what the free corner of a Glyphids card gives, or that it gives nothing", () => {
    const m = { type: "discard_free", card: "GL.1" };
    expect(cornerGlyph("GL.1")).toBe("orange");
    expect(handMoveText(m, { reward: { t: "credit", n: 1 } })).toContain("the orange glyph gives 1 credit");
    expect(handMoveText(m, { reward: null })).toContain("not on the translation board, so you gain nothing");
    expect(cornerGlyph("1")).toBeNull();
  });

  it("finds the reward of a placed glyph from the sides of the strips", () => {
    const extra = { sides: [0, 1], top: [null, "orange", null], bottom: ["red", null, null, null] };
    expect(glyphIconReward(extra, "orange")).toEqual({ t: "energy", n: 1 }); // top side 0, second slot
    expect(glyphIconReward(extra, "red")).toEqual({ t: "card_random", n: 1 }); // bottom side 1, first slot
    expect(glyphIconReward(extra, "blue")).toBeNull();
  });

  it("asks about a move that cannot be undone in one short sentence", () => {
    expect(irreversibleText({ type: "pass" })).toBe("Pass now? You will see the end-of-round cards.");
    expect(irreversibleText({ type: "take_card", source: "deck" })).toBe("Draw from the deck? You will see the card.");
    expect(irreversibleText({ type: "end_turn" }).length).toBeLessThan(60);
  });
});

describe("the administrator's page", () => {
  const hash = "scrypt$stand-in$hash";

  it("accepts a signed cookie until it expires, and nothing else", () => {
    const t = adminToken(1_000, hash);
    expect(validAdminToken(t, 2_000, hash)).toBe(true);
    expect(validAdminToken(t, 1_000 + 3 * 3_600_000, hash)).toBe(false); // two hours
    expect(validAdminToken(`${t}x`, 2_000, hash)).toBe(false);
    expect(validAdminToken(t, 2_000, "another key")).toBe(false);
    expect(validAdminToken(undefined, 2_000, hash)).toBe(false);
    expect(validAdminToken(t, 2_000, "")).toBe(false); // no passphrase set: the page is closed
  });

  it("checks the passphrase against its hash, and locks an address out after five failures in a quarter of an hour", async () => {
    const stored = await hashPassword("brave#otter!472");
    expect(await checkPassphrase("brave#otter!472", stored)).toBe(true);
    expect(await checkPassphrase("brave#otter!473", stored)).toBe(false);
    expect(await checkPassphrase("anything", "")).toBe(false);
    const db = memory();
    for (let i = 0; i < 5; i++) {
      expect(await lockedOut(db, "1.2.3.4", 1_000 + i)).toBe(false);
      await noteFailure(db, "1.2.3.4", 1_000 + i);
    }
    expect(await lockedOut(db, "1.2.3.4", 2_000)).toBe(true);
    expect(await lockedOut(db, "5.6.7.8", 2_000)).toBe(false);
    expect(await lockedOut(db, "1.2.3.4", 1_000 + 16 * 60_000)).toBe(false);
  });

  it("sets and resets a rating and deletes an account that is in no open game", async () => {
    const db = memory();
    const ann = await signup(db, "Ann", "password1");
    const bob = await signup(db, "Bob", "password1");
    await setRating(db, ann.id, 1777, 5);
    expect((await listAccounts(db, "", 10, 0)).find((u) => u.name === "Ann")).toMatchObject({ rating: 1777 });
    await setRating(db, ann.id, 1600, 6);
    expect((await listAccounts(db, "ann", 10, 0))[0]).toMatchObject({ rating: 1600 });
    await resetRating(db, ann.id);
    expect((await listAccounts(db, "Ann", 10, 0))[0]?.rating).toBeNull();
    await db.run("INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES ('g', 'playing', '{}', '{}', 1, 1)");
    await db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES ('g', 0, ?, 'Bob', 1)", bob.id);
    expect(await deleteAccount(db, bob.id)).toBe(false); // in a game that is being played
    expect(await deleteAccount(db, ann.id)).toBe(true);
    expect(await countAccounts(db, "")).toBe(1);
  });
});

describe("creating a game twice by accident", () => {
  it("is refused for fifteen seconds after the player created a game", async () => {
    const db = memory();
    const ann = await signup(db, "Ann", "password1");
    const bob = await signup(db, "Bob", "password1");
    expect(await createdRecently(db, ann.id, 100_000)).toBe(false);
    await db.run(
      "INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES ('g', 'playing', '{}', '{}', 0, 100_000)",
    );
    await db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES ('g', 0, ?, 'Ann', 1)", ann.id);
    await db.run("INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES ('g', 1, ?, 'Bob', 1)", bob.id);
    expect(await createdRecently(db, ann.id, 105_000)).toBe(true);
    expect(await createdRecently(db, bob.id, 105_000)).toBe(false); // Bob only joined: a seat that is not the first is no creation
    expect(await createdRecently(db, ann.id, 120_000)).toBe(false);
  });
});

describe("the lobby filter and the leaderboard search", () => {
  const game = (over: Record<string, unknown>) =>
    ({
      id: "g",
      rated: false,
      players: 2,
      seats: ["a"],
      clock: "",
      host: "a",
      promo: false,
      expansion: false,
      organizations: false,
      solo: false,
      mode: "realtime",
      ...over,
    }) as never;

  it("tells real time from turn-based and no clock", async () => {
    const { clockMode } = await import("@/lib/queries");
    expect(clockMode(JSON.stringify({ kind: "none" }))).toBe("none");
    expect(clockMode(JSON.stringify({ kind: "bank", initialMs: 450_000, incrementMs: 150_000 }))).toBe("realtime");
    expect(clockMode(JSON.stringify({ kind: "bank", initialMs: 3 * 86_400_000, incrementMs: 9 * 3_600_000 }))).toBe("turnbased");
  });

  it("keeps the games that match every point of the filter", async () => {
    const { filterLobby } = await import("@/lib/queries");
    const games = [
      game({ id: "1", players: 2, rated: true, mode: "realtime" }),
      game({ id: "2", players: 3, rated: false, expansion: true, mode: "turnbased" }),
      game({ id: "3", players: 4, rated: true, mode: "none" }),
    ];
    const ids = (f: object) => filterLobby(games, f).map((g) => g.id);
    expect(ids({})).toEqual(["1", "2", "3"]);
    expect(ids({ players: "any", rated: "" })).toEqual(["1", "2", "3"]);
    expect(ids({ rated: "rated" })).toEqual(["1", "3"]);
    expect(ids({ rated: "casual" })).toEqual(["2"]);
    expect(ids({ expansion: "yes" })).toEqual(["2"]);
    expect(ids({ expansion: "no", mode: "none" })).toEqual(["3"]);
    expect(ids({ players: "3", mode: "turnbased" })).toEqual(["2"]);
    expect(ids({ players: "4", mode: "realtime" })).toEqual([]);
  });

  it("finds a player by a part of the name and by the number of rated games", async () => {
    const { leaderboard } = await import("@/lib/queries");
    const db = memory();
    for (const [id, name, rating, games] of [
      ["u1", "Ann_2", 300, 12],
      ["u2", "Annabel", 250, 3],
      ["u3", "Bob", 400, 30],
    ] as const) {
      await db.run("INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES (?, ?, NULL, 'x', 0, 0)", id, name);
      await db.run("INSERT INTO ratings (user_id, rating, games, updated_at) VALUES (?, ?, ?, 0)", id, rating, games);
    }
    expect((await leaderboard(db)).map((r) => r.name)).toEqual(["Bob", "Ann_2", "Annabel"]);
    expect((await leaderboard(db, 100, "ann")).map((r) => r.name)).toEqual(["Ann_2", "Annabel"]);
    expect((await leaderboard(db, 100, "ann", 10)).map((r) => r.name)).toEqual(["Ann_2"]);
    expect((await leaderboard(db, 100, "_")).map((r) => r.name)).toEqual(["Ann_2"]);
    expect(await leaderboard(db, 100, "nobody")).toEqual([]);
  });
});

describe("the rating changes of a game", () => {
  it("lists them by rank, and nothing for a game that was not rated", async () => {
    const { gameRatingChanges } = await import("@/lib/queries");
    const db = memory();
    await db.run("INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES ('g1', 'finished', '{}', '{}', 1, 0)");
    for (const [id, name] of [
      ["a", "Ann"],
      ["b", "Bob"],
    ] as const)
      await db.run("INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES (?, ?, NULL, 'x', 0, 0)", id, name);
    await db.run("INSERT INTO rating_history (game_id, user_id, rating_before, rating_after, rank, at) VALUES ('g1', 'b', 100, 90, 2, 0)");
    await db.run("INSERT INTO rating_history (game_id, user_id, rating_before, rating_after, rank, at) VALUES ('g1', 'a', 100, 140, 1, 0)");
    expect((await gameRatingChanges(db, "g1")).map((r) => [r.name, r.rating_before, r.rating_after])).toEqual([
      ["Ann", 100, 140],
      ["Bob", 100, 90],
    ]);
    expect(await gameRatingChanges(db, "g2")).toEqual([]);
  });
});
