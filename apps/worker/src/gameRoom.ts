import type { Options } from "@seti/protocol";
// The Durable Object "GameRoom": a thin adapter that gives the game room (core/room.ts) storage, WebSockets and an alarm.
import { publicReplay } from "./core/archive.js";
import type { Identity } from "./core/auth.js";
import type { ClockSettings } from "./core/clock.js";
import { D1Sink } from "./core/d1.js";
import { HttpEngine } from "./core/engine.js";
import { EngineArchive } from "./core/engineArchive.js";
import { makeSigner } from "./core/engineAuth.js";
import { type Connection, GameRoom, type ServerMessage, type Store, type SubmitResult } from "./core/room.js";
import type { Env } from "./env.js";

/** What a socket remembers across hibernation. */
interface Attachment {
  id: string;
  identity: Identity | null;
}

class DoStore implements Store {
  constructor(private readonly storage: DurableObjectStorage) {}
  get<T>(key: string): Promise<T | undefined> {
    return this.storage.get<T>(key);
  }
  async put(key: string, value: unknown): Promise<void> {
    await this.storage.put(key, value);
  }
  async clear(): Promise<void> {
    await this.storage.deleteAll();
  }
  async list<T>(prefix: string): Promise<T[]> {
    const m = await this.storage.list<T>({ prefix });
    return [...m.values()];
  }
}

export class GameRoomDO implements DurableObject {
  private readonly room: GameRoom;

  constructor(
    private readonly ctx: DurableObjectState,
    env: Env,
  ) {
    const sign = env.ENGINE_SIGNING_KEY ? makeSigner(env.ENGINE_SIGNING_KEY, "worker") : undefined;
    this.room = new GameRoom({
      store: new DoStore(ctx.storage),
      engine: new HttpEngine(env.ENGINE_URL, undefined, sign),
      sink: new D1Sink(env.DB as unknown as ConstructorParameters<typeof D1Sink>[0]),
      archive: new EngineArchive(env.ENGINE_URL, undefined, sign),
      defer: (work) => ctx.waitUntil(work),
      now: () => Date.now(),
      newSeed: () => {
        const [hi = 0, lo = 0] = crypto.getRandomValues(new Uint32Array(2));
        return (hi % 0x1fffff) * 0x100000000 + lo; // below 2^53, so the JSON number is exact
      },
      connections: () => this.ctx.getWebSockets().map((ws) => this.connection(ws)),
      setAlarm: async (at) => {
        if (at === null) await ctx.storage.deleteAlarm();
        else await ctx.storage.setAlarm(at);
      },
    });
  }

  /** The Worker has already checked the token; it passes the identity in a header (only the Worker can reach this object). */
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const identity = JSON.parse(request.headers.get("x-identity") ?? "null") as Identity | null;
    if (url.pathname === "/ws") return this.upgrade(request, identity);
    if (url.pathname === "/meta") return json((await this.room.publicMeta()) ?? null);
    // The log and the replay give the seed and so the hidden information away: only a finished game shows them.
    if (url.pathname === "/log" || url.pathname === "/replay") {
      const file = await this.room.replayFile();
      if (file === null) return json({ ok: false, code: "not_finished", message: "the game is not over" }, 403);
      return json(url.pathname === "/log" ? file.actions : publicReplay(file));
    }
    if (identity === null) return json({ ok: false, code: "unauthorized", message: "sign in first" }, 401);
    if (url.pathname === "/init") {
      const b = (await request.json()) as { id: string; options: Options; clock: ClockSettings; rated: boolean };
      return json(await this.room.init(b.id, b.options, b.clock, b.rated, identity));
    }
    if (url.pathname === "/join") return json(await this.room.join(identity));
    if (url.pathname === "/leave") return json(await this.room.leave(identity));
    if (url.pathname === "/resign") return json(await this.room.resign(identity));
    return json({ ok: false, code: "not_found", message: "no such route" }, 404);
  }

  private async upgrade(request: Request, identity: Identity | null): Promise<Response> {
    if (request.headers.get("upgrade") !== "websocket") return new Response("expected a WebSocket", { status: 426 });
    const pair = new WebSocketPair();
    const [client, server] = [pair[0], pair[1]];
    const att: Attachment = { id: crypto.randomUUID(), identity };
    this.ctx.acceptWebSocket(server);
    server.serializeAttachment(att);
    if (identity !== null) await this.room.touch(identity);
    await this.room.connect(this.connection(server));
    return new Response(null, { status: 101, webSocket: client });
  }

  private connection(ws: WebSocket): Connection {
    const att = ws.deserializeAttachment() as Attachment;
    return { id: att.id, who: att.identity?.id ?? null, send: (m: ServerMessage) => ws.send(JSON.stringify(m)) };
  }

  async webSocketMessage(ws: WebSocket, message: string | ArrayBuffer): Promise<void> {
    const conn = this.connection(ws);
    const att = ws.deserializeAttachment() as Attachment;
    let msg: { t?: string; seq?: number; seat?: number; action?: Record<string, unknown> };
    try {
      msg = JSON.parse(typeof message === "string" ? message : new TextDecoder().decode(message));
    } catch {
      conn.send({ t: "error", code: "bad_message", message: "the message is not JSON" });
      return;
    }
    if (msg.t === "ping") {
      if (att.identity !== null) await this.room.touch(att.identity);
      return;
    }
    if (att.identity === null) {
      conn.send({ t: "error", code: "spectator", message: "spectators cannot act" });
      return;
    }
    const res: SubmitResult =
      msg.t === "action" && typeof msg.seq === "number" && msg.action !== undefined
        ? await this.room.submit(att.identity, msg.seq, msg.action)
        : msg.t === "resign"
          ? await this.room.resign(att.identity)
          : msg.t === "kick" && typeof msg.seat === "number"
            ? await this.room.kick(att.identity, msg.seat)
            : { ok: false, code: "bad_message", message: "unknown message" };
    if (!res.ok) conn.send({ t: "error", code: res.code, message: res.message, ...(res.legal ? { legal: res.legal } : {}) });
  }

  async webSocketClose(ws: WebSocket, code: number): Promise<void> {
    ws.close(code, "closed");
  }

  async alarm(): Promise<void> {
    await this.room.onAlarm();
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}
