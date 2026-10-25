// The Worker: checks the caller's token and routes game requests to the right GameRoom Durable Object.
//   POST /games                 create a game (token), body {options, clock, rated}; answers {id}
//   POST /games/:id/join        take a seat (token)
//   POST /games/:id/leave       leave the lobby (token)
//   POST /games/:id/start       the host starts the game once every seat is taken (token)
//   POST /games/:id/bot-add     the host adds an AI to the lobby (token), body {model, consent: true}
//   POST /games/:id/bot-remove  the host removes an AI from the lobby (token), body {seat}
//   POST /games/:id/resign      resign a game that is being played (token; the website uses it for "resign" on the profile page)
//   GET  /games/:id             public data of the game
//   GET  /games/:id/log         the action log (seed + log replay the game), once the game is over
//   GET  /games/:id/replay      everything needed for a replay (header, actions with their events, result), once the game is over
//   GET  /games/:id/ws?token=   WebSocket; without a token the connection is a spectator
//   GET  /health
import type { Options } from "@seti/protocol";
import { AuthError, type Identity, verifyToken } from "./core/auth.js";
import type { ClockSettings } from "./core/clock.js";
import { makeSigner } from "./core/engineAuth.js";
import { makeErrorReporter } from "./core/errorReport.js";
import { overTableLimit } from "./core/limits.js";
import { validClock, validOptions } from "./core/validate.js";
import type { Env } from "./env.js";

export { GameRoomDO as GameRoom } from "./gameRoom.js";

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

async function identify(request: Request, env: Env, url: URL): Promise<Identity | null> {
  const header = request.headers.get("authorization");
  const token = header?.startsWith("Bearer ") ? header.slice(7) : url.searchParams.get("token");
  if (!token) return null;
  return verifyToken(token, { publicKeyPem: env.AUTH_PUBLIC_KEY, issuer: env.AUTH_ISSUER, audience: env.AUTH_AUDIENCE });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    try {
      return await handle(request, env);
    } catch (e) {
      // an unexpected error: it is stored as an object in the bucket (core/errorReport.ts) and the caller gets a plain 500
      const sign = env.ENGINE_SIGNING_KEY ? makeSigner(env.ENGINE_SIGNING_KEY, "worker") : undefined;
      const url = new URL(request.url);
      ctx.waitUntil(makeErrorReporter(env.ENGINE_URL, sign).report("worker", e, { method: request.method, route: url.pathname }));
      return json({ ok: false, code: "internal", message: "internal error" }, 500);
    }
  },
} satisfies ExportedHandler<Env>;

async function handle(request: Request, env: Env): Promise<Response> {
  {
    const url = new URL(request.url);
    const parts = url.pathname.split("/").filter(Boolean);
    if (url.pathname === "/health") return json({ status: "ok" });
    // The administrator's routes (the website's admin page calls them with the key that only the site and this Worker hold):
    //   GET  /admin/games/:id          state and last activity of a game
    //   GET  /admin/games/:id/seed     the seed of a game (it gives the hidden cards away: only the administrator reads it)
    //   POST /admin/games/:id/cancel   cancel a lobby or a game that is being played (no rating changes)
    if (parts[0] === "admin") return admin(request, env, parts);
    if (parts[0] !== "games") return json({ ok: false, code: "not_found", message: "no such route" }, 404);

    let who: Identity | null;
    try {
      who = await identify(request, env, url);
    } catch (e) {
      if (e instanceof AuthError) return json({ ok: false, code: "unauthorized", message: e.message }, 401);
      throw e;
    }

    if (parts.length === 1 && request.method === "POST") {
      if (who === null) return json({ ok: false, code: "unauthorized", message: "sign in first" }, 401);
      const body = (await request.json().catch(() => null)) as { options?: unknown; clock?: unknown; rated?: unknown } | null;
      if (body === null || !validOptions(body.options) || !validClock(body.clock ?? { kind: "none" })) {
        return json({ ok: false, code: "bad_request", message: "options or clock are not valid" }, 400);
      }
      const over = overTableLimit(who.registered, await openTables(env, who.id));
      if (over !== null) return json(over, 400);
      const id = env.GAME_ROOM.newUniqueId();
      const res = await env.GAME_ROOM.get(id).fetch("https://room/init", {
        method: "POST",
        headers: { "x-identity": JSON.stringify(who), "content-type": "application/json" },
        body: JSON.stringify({
          id: id.toString(),
          options: body.options,
          clock: body.clock ?? { kind: "none" },
          rated: body.rated === true,
        }),
      });
      const out = (await res.json()) as { ok: boolean };
      return out.ok ? json({ ok: true, id: id.toString() }) : json(out, 400);
    }

    const gameId = parts[1];
    if (gameId === undefined) return json({ ok: false, code: "not_found", message: "no such route" }, 404);
    let stub: DurableObjectStub;
    try {
      stub = env.GAME_ROOM.get(env.GAME_ROOM.idFromString(gameId));
    } catch {
      return json({ ok: false, code: "unknown_game", message: "no such game" }, 404);
    }
    const action = parts[2] ?? "";
    const headers = { "x-identity": JSON.stringify(who) };
    if (action === "ws") {
      const h = new Headers(request.headers);
      h.set("x-identity", JSON.stringify(who));
      return stub.fetch("https://room/ws", { headers: h });
    }
    if (action === "" && request.method === "GET") return forward(stub, "/meta", headers);
    if ((action === "log" || action === "replay") && request.method === "GET") return forward(stub, `/${action}`, headers);
    if (action === "join" && request.method === "POST" && who !== null) {
      // a player who already sits at this table is not counted twice
      const over = overTableLimit(who.registered, await openTables(env, who.id, gameId));
      if (over !== null) return json(over, 400);
    }
    if ((action === "join" || action === "leave" || action === "start" || action === "resign") && request.method === "POST")
      return forward(stub, `/${action}`, headers, "POST");
    if ((action === "bot-add" || action === "bot-remove") && request.method === "POST") {
      return stub.fetch(`https://room/${action}`, {
        method: "POST",
        headers: { ...headers, "content-type": "application/json" },
        body: await request.text(),
      });
    }
    return json({ ok: false, code: "not_found", message: "no such route" }, 404);
  }
}

/** How many tables (lobbies and games in progress) a player has open, not counting `except` (the table that they want to join). */
async function openTables(env: Env, userId: string, except = ""): Promise<number> {
  const row = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM game_players p JOIN games g ON g.id = p.game_id WHERE p.user_id = ? AND g.status IN ('lobby', 'playing') AND g.id != ?",
  )
    .bind(userId, except)
    .first<{ n: number }>();
  return row?.n ?? 0;
}

function forward(stub: DurableObjectStub, path: string, headers: Record<string, string>, method = "GET", body?: string): Promise<Response> {
  return stub.fetch(`https://room${path}`, {
    method,
    headers: body === undefined ? headers : { ...headers, "content-type": "application/json" },
    ...(body === undefined ? {} : { body }),
  });
}

/** A comparison that takes the same time wherever the strings differ. */
function sameKey(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a);
  const y = new TextEncoder().encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

async function admin(request: Request, env: Env, parts: string[]): Promise<Response> {
  const key = request.headers.get("x-admin-key") ?? "";
  if (!env.ADMIN_WORKER_KEY || !sameKey(key, env.ADMIN_WORKER_KEY)) return json({ ok: false, code: "unauthorized", message: "no" }, 401);
  const [, kind, gameId, action] = parts;
  if (kind !== "games" || gameId === undefined) return json({ ok: false, code: "not_found", message: "no such route" }, 404);
  let stub: DurableObjectStub;
  try {
    stub = env.GAME_ROOM.get(env.GAME_ROOM.idFromString(gameId));
  } catch {
    return json({ ok: false, code: "unknown_game", message: "no such game" }, 404);
  }
  if (request.method === "GET" && action === undefined) return forward(stub, "/admin-info", {});
  if (request.method === "GET" && action === "seed") return forward(stub, "/admin-seed", {});
  if (request.method === "POST" && action === "cancel") return forward(stub, "/admin-cancel", {}, "POST");
  if (request.method === "GET" && action === "recent") return forward(stub, `/admin-recent${new URL(request.url).search}`, {});
  if (request.method === "POST" && action === "undo") {
    const body = (await request.json().catch(() => ({}))) as { count?: number };
    return forward(stub, "/admin-undo", {}, "POST", JSON.stringify({ count: Number(body.count ?? 1) }));
  }
  return json({ ok: false, code: "not_found", message: "no such route" }, 404);
}
