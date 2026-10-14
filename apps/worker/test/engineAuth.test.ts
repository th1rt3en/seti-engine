// Signed requests to the engine service (decision D16).
import { generateKeyPairSync } from "node:crypto";
import { createHash } from "node:crypto";
import { importSPKI, jwtVerify } from "jose";
import { describe, expect, it } from "vitest";
import { HttpEngine } from "../src/core/engine.js";
import { EngineArchive } from "../src/core/engineArchive.js";
import { makeSigner } from "../src/core/engineAuth.js";

const { privateKey, publicKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
const privatePem = privateKey.export({ type: "pkcs8", format: "pem" }).toString();
const publicPem = publicKey.export({ type: "spki", format: "pem" }).toString();

describe("the request signer", () => {
  it("binds the token to the method, the path and the body, with a short life and a fresh id", async () => {
    const sign = makeSigner(privatePem, "worker", () => 1_000_000_000_000);
    const body = JSON.stringify({ options: { players: 2 } });
    const a = (await sign("post", "/new", body)).authorization as string;
    const b = (await sign("post", "/new", body)).authorization as string;
    expect(a.startsWith("Bearer ")).toBe(true);
    const { payload, protectedHeader } = await jwtVerify(a.slice(7), await importSPKI(publicPem, "ES256"), {
      currentDate: new Date(1_000_000_000_000),
    });
    expect(protectedHeader.alg).toBe("ES256");
    expect(payload).toMatchObject({
      iss: "worker",
      iat: 1_000_000_000,
      exp: 1_000_000_030,
      htm: "POST",
      htu: "/new",
      bsh: createHash("sha256").update(body).digest("base64url"),
    });
    const second = (await jwtVerify(b.slice(7), await importSPKI(publicPem, "ES256"), { currentDate: new Date(1_000_000_000_000) }))
      .payload;
    expect(second.jti).not.toBe(payload.jti);
  });

  it("signs what the engine client and the archive writer send, with the same body that is signed", async () => {
    const sign = makeSigner(privatePem, "worker");
    const seen: { url: string; method: string; auth: string; body: string }[] = [];
    const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
      seen.push({
        url: String(input),
        method: String(init?.method),
        auth: new Headers(init?.headers).get("authorization") ?? "",
        body: String(init?.body),
      });
      return new Response(JSON.stringify({ state: {}, events: [], legal: [] }));
    }) as typeof fetch;
    await new HttpEngine("https://e", fetcher, sign).newGame({ players: 2 } as never);
    await new EngineArchive("https://e", fetcher, sign).put("p", { x: 1 });
    const key = await importSPKI(publicPem, "ES256");
    for (const [i, path, method] of [
      [0, "/new", "POST"],
      [1, "/archive", "PUT"],
    ] as const) {
      const call = seen[i];
      const { payload } = await jwtVerify(call?.auth.slice(7) ?? "", key);
      expect(payload).toMatchObject({
        htm: method,
        htu: path,
        bsh: createHash("sha256")
          .update(call?.body ?? "")
          .digest("base64url"),
      });
    }
  });

  it("sends no authorization without a key (development)", async () => {
    let auth: string | null = "unset";
    const fetcher = (async (_u: RequestInfo | URL, init?: RequestInit) => {
      auth = new Headers(init?.headers).get("authorization");
      return new Response(JSON.stringify({ state: {}, events: [], legal: [] }));
    }) as typeof fetch;
    await new HttpEngine("https://e", fetcher).newGame({ players: 2 } as never);
    expect(auth).toBeNull();
  });
});
