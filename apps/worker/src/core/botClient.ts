// The AI service as the room sees it (services/ai/src/seti_ai/lobby_server.py): one signed request for each move of an AI seat.
import type { Signer } from "./engineAuth.js";
import type { BotClient, BotReply, BotRequest } from "./room.js";

/** A request to the AI is given up after this long, below the 300 s that Cloud Run allows a request: a request that hangs keeps the room's invocation open and counts as an error. */
export const BOT_TIMEOUT_MS = 280_000;

export class HttpBotClient implements BotClient {
  private readonly fetcher: typeof fetch;

  constructor(
    private readonly baseUrl: string,
    fetcher?: typeof fetch,
    private readonly sign?: Signer,
  ) {
    // The global fetch must be called without this object as its `this` (Workers throw "Illegal invocation" otherwise).
    this.fetcher = fetcher ?? ((input, init) => fetch(input, init));
  }

  async move(req: BotRequest): Promise<BotReply> {
    const path = "/move";
    const payload = JSON.stringify(req);
    const res = await this.fetcher(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", ...(this.sign ? await this.sign("POST", path, payload) : {}) },
      body: payload,
      signal: AbortSignal.timeout(BOT_TIMEOUT_MS),
    });
    if (res.status !== 200) throw new Error(`the AI service answered ${res.status}`);
    return (await res.json()) as BotReply;
  }
}
