// Token verification (decision D16). The website issues short-lived signed JWTs; the Worker checks them with the public key.
import { importSPKI, jwtVerify } from "jose";

export interface Identity {
  /** A user id, or a guest id for an anonymous player. */
  id: string;
  name: string;
  /** True for a registered account; only registered players can play rated games. */
  registered: boolean;
  /** The player's number (the integer in the address of their profile), from the token; the site assigns it. Absent for a game started before it existed. */
  num?: number;
  /** Set for a seat taken by the AI model (never in a token): the model version that plays it. */
  bot?: { model: string };
}

export interface AuthConfig {
  publicKeyPem: string;
  issuer: string;
  audience: string;
  algorithm?: string;
}

export class AuthError extends Error {}

export async function verifyToken(token: string, cfg: AuthConfig): Promise<Identity> {
  try {
    const key = await importSPKI(cfg.publicKeyPem, cfg.algorithm ?? "ES256");
    const { payload } = await jwtVerify(token, key, { issuer: cfg.issuer, audience: cfg.audience });
    if (typeof payload.sub !== "string" || payload.sub === "") throw new AuthError("the token has no subject");
    const name = typeof payload.name === "string" ? payload.name : "Guest";
    const num = Number.isInteger(payload.num) && (payload.num as number) > 0 ? (payload.num as number) : undefined;
    return { id: payload.sub, name, registered: payload.reg === true, ...(num === undefined ? {} : { num }) };
  } catch (e) {
    if (e instanceof AuthError) throw e;
    throw new AuthError(`invalid token: ${(e as Error).message}`);
  }
}
