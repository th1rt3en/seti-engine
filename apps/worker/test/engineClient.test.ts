import { describe, expect, it } from "vitest";
import { HttpEngine, IllegalAction } from "../src/core/engine.js";

// The Worker may be deployed before the engine: an engine without /apply/views answers 404, and the client uses /apply and /project instead.

function service(hasViews: boolean) {
  const calls: string[] = [];
  const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input)).pathname;
    calls.push(path);
    const body = JSON.parse(String(init?.body)) as { action?: { type: string }; viewer?: number | null };
    if (path === "/apply/views") {
      if (!hasViews) return new Response("{}", { status: 404 });
      if (body.action?.type === "bad") return Response.json({ message: "no", legal: [{ type: "score" }] }, { status: 422 });
      return Response.json({ result: { state: { n: 1 }, events: [], legal: [] }, views: [{ viewer: 0 }, { viewer: null }] });
    }
    if (path === "/apply") {
      if (body.action?.type === "bad") return Response.json({ message: "no", legal: [{ type: "score" }] }, { status: 422 });
      return Response.json({ state: { n: 1 }, events: [], legal: [] });
    }
    return Response.json({ viewer: body.viewer ?? null });
  }) as typeof fetch;
  return { calls, engine: new HttpEngine("https://e", fetcher) };
}

describe("the engine client: a move and the views in one call", () => {
  it("uses /apply/views when the engine has it", async () => {
    const { calls, engine } = service(true);
    const out = await engine.applyWithViews({} as never, { type: "score" }, [0, null]);
    expect(calls).toEqual(["/apply/views"]);
    expect(out.views).toEqual([{ viewer: 0 }, { viewer: null }]);
  });

  it("falls back to /apply and one /project for each viewer when the engine is older, and remembers it", async () => {
    const { calls, engine } = service(false);
    const out = await engine.applyWithViews({} as never, { type: "score" }, [0, null]);
    expect(calls).toEqual(["/apply/views", "/apply", "/project", "/project"]);
    expect(out.views).toEqual([{ viewer: 0 }, { viewer: null }]);
    calls.length = 0;
    await engine.applyWithViews({} as never, { type: "score" }, [1]);
    expect(calls).toEqual(["/apply", "/project"]); // it does not ask again
  });

  it("an illegal move is refused with the legal moves, either way", async () => {
    for (const hasViews of [true, false]) {
      const { engine } = service(hasViews);
      await expect(engine.applyWithViews({} as never, { type: "bad" }, [0])).rejects.toBeInstanceOf(IllegalAction);
    }
  });
});
