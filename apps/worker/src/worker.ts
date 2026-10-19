// The Worker: checks the caller's token and routes game requests to the right GameRoom Durable Object.
//   POST /games                 create a game (token), body {options, clock, rated}; answers {id}
//   POST /games/:id/join        take a seat (token)
//   POST /games/:id/leave       leave the lobby (token)
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

function validOptions(o: unknown): o is Options {
  const x = o as Partial<Options> | null;
  return typeof x === "object" && x !== null && Number.isInteger(x.players) && (x.players as number) >= 1 && (x.players as number) <= 4;
}

function validClock(c: unknown): c is ClockSettings {
  const x = c as { kind?: string; ms?: number; initialMs?: number; incrementMs?: number } | null;
  if (x === null || typeof x !== "object") return false;
  if (x.kind === "none") return true;
  if (x.kind === "per_turn") return typeof x.ms === "number" && x.ms > 0;
  return x.kind === "bank" && typeof x.initialMs === "number" && x.initialMs > 0 && typeof x.incrementMs === "number" && x.incrementMs >= 0;
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
    if ((action === "join" || action === "leave" || action === "resign") && request.method === "POST")
      return forward(stub, `/${action}`, headers, "POST");
    return json({ ok: false, code: "not_found", message: "no such route" }, 404);
  }
}

function forward(stub: DurableObjectStub, path: string, headers: Record<string, string>, method = "GET"): Promise<Response> {
  return stub.fetch(`https://room${path}`, { method, headers });
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
  if (request.method === "POST" && action === "cancel") return forward(stub, "/admin-cancel", {}, "POST");
  return json({ ok: false, code: "not_found", message: "no such route" }, 404);
}
