import { describe, expect, it } from "vitest";
import { BOT_TIMEOUT_MS, HttpBotClient } from "../src/core/botClient.js";

describe("the AI client", () => {
  it("gives up on a request that hangs, below the limit of Cloud Run (300 s)", async () => {
    let signal: AbortSignal | null | undefined;
    const fetcher = (async (_url: RequestInfo | URL, init?: RequestInit) => {
      signal = init?.signal;
      return Response.json({ action: { type: "pass" }, plan: [] });
    }) as typeof fetch;
    const reply = await new HttpBotClient("https://ai", fetcher).move({
      model: "v1",
      options: {},
      actions: [],
      seat: 0,
      plan: [],
    } as never);
    expect(reply.action).toEqual({ type: "pass" });
    expect(signal).toBeInstanceOf(AbortSignal);
    expect(BOT_TIMEOUT_MS).toBeLessThan(300_000);
  });

  it("an answer that is not 200 is a failure", async () => {
    const fetcher = (async () => new Response("{}", { status: 503 })) as typeof fetch;
    await expect(new HttpBotClient("https://ai", fetcher).move({} as never)).rejects.toThrow("503");
  });
});
