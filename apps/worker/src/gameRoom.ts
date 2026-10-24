import type { Options } from "@seti/protocol";
// The Durable Object "GameRoom": a thin adapter that gives the game room (core/room.ts) storage, WebSockets and an alarm.
import { publicReplay } from "./core/archive.js";
import type { Identity } from "./core/auth.js";
import { HttpBotClient } from "./core/botClient.js";
import type { ClockSettings } from "./core/clock.js";
import { D1Sink } from "./core/d1.js";
import { HttpEngine } from "./core/engine.js";
import { EngineArchive } from "./core/engineArchive.js";
import { makeSigner } from "./core/engineAuth.js";
import { type ErrorReporter, makeErrorReporter } from "./core/errorReport.js";
import { type Connection, GameRoom, type ServerMessage, type Store, type SubmitResult } from "./core/room.js";
import { messageText } from "./core/validate.js";
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
  private readonly errors: ErrorReporter;

  constructor(
    private readonly ctx: DurableObjectState,
    env: Env,
  ) {
    const sign = env.ENGINE_SIGNING_KEY ? makeSigner(env.ENGINE_SIGNING_KEY, "worker") : undefined;
    this.errors = makeErrorReporter(env.ENGINE_URL, sign);
    this.room = new GameRoom({
      store: new DoStore(ctx.storage),
      engine: new HttpEngine(env.ENGINE_URL, undefined, sign),
      ...(env.BOT_URL ? { bot: new HttpBotClient(env.BOT_URL, undefined, sign) } : {}),
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
    try {
      return await this.handle(request);
    } catch (e) {
      this.ctx.waitUntil(this.errors.report("game-room", e, { route: new URL(request.url).pathname }));
      return json({ ok: false, code: "internal", message: "internal error" }, 500);
    }
  }

  private async handle(request: Request): Promise<Response> {
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
    // the administrator's routes: the Worker has checked the key, and only the Worker can reach this object
    if (url.pathname === "/admin-info") return json((await this.room.adminInfo()) ?? null);
    if (url.pathname === "/admin-seed") return json((await this.room.adminSeed()) ?? null);
    if (url.pathname === "/admin-cancel") return json(await this.room.adminCancel());
    if (identity === null) return json({ ok: false, code: "unauthorized", message: "sign in first" }, 401);
    if (url.pathname === "/init") {
      const b = (await request.json()) as { id: string; options: Options; clock: ClockSettings; rated: boolean };
      return json(await this.room.init(b.id, b.options, b.clock, b.rated, identity));
    }
    if (url.pathname === "/join") return json(await this.room.join(identity));
    if (url.pathname === "/leave") return json(await this.room.leave(identity));
    if (url.pathname === "/start") return json(await this.room.startGame(identity));
    if (url.pathname === "/bot-add") {
      const b = (await request.json()) as { model?: string; consent?: boolean };
      return json(await this.room.addBot(identity, String(b.model ?? ""), b.consent === true));
    }
    if (url.pathname === "/bot-remove") {
      const b = (await request.json()) as { seat?: number };
      return json(await this.room.removeBot(identity, Number(b.seat)));
    }
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
    try {
      await this.onMessage(ws, message);
    } catch (e) {
      this.ctx.waitUntil(this.errors.report("game-room", e, { where: "websocket message" }));
      this.connection(ws).send({ t: "error", code: "internal", message: "internal error" });
    }
  }

  private async onMessage(ws: WebSocket, message: string | ArrayBuffer): Promise<void> {
    const conn = this.connection(ws);
    const att = ws.deserializeAttachment() as Attachment;
    let msg: { t?: string; id?: number; seq?: number; seat?: number; text?: string; action?: Record<string, unknown> };
    const text = messageText(message);
    if (text === null) {
      conn.send({ t: "error", code: "bad_message", message: "the message is too big" });
      return;
    }
    try {
      const parsed: unknown = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error("not an object");
      msg = parsed as typeof msg;
    } catch {
      conn.send({ t: "error", code: "bad_message", message: "the message is not JSON" });
      return;
    }
    // the action of a move is an object with a type: the engine says whether it is legal, and nothing else is let through
    if (
      msg.action !== undefined &&
      (typeof msg.action !== "object" || msg.action === null || Array.isArray(msg.action) || typeof msg.action.type !== "string")
    ) {
      conn.send({ t: "error", code: "bad_message", message: "the move is not valid" });
      return;
    }
    if (msg.t === "ping") {
      if (att.identity !== null) await this.room.touch(att.identity);
      return;
    }
    if (msg.t === "chat") {
      // everybody who is signed in can write, a spectator too; somebody who is not signed in only reads
      if (att.identity === null) conn.send({ t: "error", code: "sign_in", message: "sign in (or play as a guest) to chat" });
      else {
        const said = await this.room.chat(att.identity, typeof msg.text === "string" ? msg.text : "");
        if (!said.ok) conn.send({ t: "error", code: said.code, message: said.message });
      }
      return;
    }
    if (att.identity === null) {
      conn.send({ t: "error", code: "spectator", message: "spectators cannot act" });
      return;
    }
    if (msg.t === "preview") {
      const changes = msg.action ? await this.room.preview(att.identity, msg.action) : null;
      conn.send({ t: "preview", id: typeof msg.id === "number" ? msg.id : 0, changes });
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
    try {
      await this.room.onAlarm();
    } catch (e) {
      this.ctx.waitUntil(this.errors.report("game-room", e, { where: "alarm" }));
      throw e; // the runtime retries an alarm that failed
    }
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}
