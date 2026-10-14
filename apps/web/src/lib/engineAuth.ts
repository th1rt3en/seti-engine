// Signed requests to the engine service (decision D16): the replay viewer calls the engine, so the website signs its requests too
// (issuer "web"). The engine service checks them (services/engine/src/seti_engine/request_auth.py).
import { signJwt } from "./jwt";

const b64url = (bytes: ArrayBuffer): string => Buffer.from(bytes).toString("base64url");

/** The Authorization header for one request; empty without a key (development). */
export async function engineAuth(
  key: string,
  method: string,
  path: string,
  body: string,
  now: () => number = () => Date.now(),
): Promise<Record<string, string>> {
  if (key === "") return {};
  const bsh = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body)));
  const token = await signJwt(key, { iss: "web", jti: crypto.randomUUID(), htm: method.toUpperCase(), htu: path, bsh }, 30, now);
  return { authorization: `Bearer ${token}` };
}
