import { describe, expect, it } from "vitest";
import { makeErrorReporter } from "../src/core/errorReport.js";

describe("error reports", () => {
  it("sends the error to the engine's /errors with a signature and the stack", async () => {
    const calls: { url: string; init: RequestInit }[] = [];
    const fetcher = (async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response("{}");
    }) as unknown as typeof fetch;
    const sign = async (method: string, path: string) => ({ authorization: `Bearer ${method} ${path}` });
    await makeErrorReporter("https://engine", sign, fetcher).report("worker", new Error("boom"), { route: "/games" });
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe("https://engine/errors");
    expect((calls[0]?.init.headers as Record<string, string>).authorization).toBe("Bearer PUT /errors");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body.source).toBe("worker");
    expect(body.message).toBe("Error: boom");
    expect(body.detail.route).toBe("/games");
    expect(String(body.detail.stack)).toContain("boom");
  });

  it("sends at most 20 reports a minute, and never throws", async () => {
    let n = 0;
    let t = 0;
    const fetcher = (async () => {
      n++;
      throw new Error("the engine is down");
    }) as unknown as typeof fetch;
    const reporter = makeErrorReporter("https://engine", undefined, fetcher, () => t);
    for (let i = 0; i < 50; i++) await reporter.report("worker", "x");
    expect(n).toBe(20);
    t = 61_000;
    await reporter.report("worker", "x");
    expect(n).toBe(21);
  });
});
