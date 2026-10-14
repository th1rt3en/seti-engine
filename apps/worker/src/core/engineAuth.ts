// Signed requests to the engine service (decision D16). The service checks the token (services/engine/src/seti_engine/request_auth.py):
// ES256, the issuer, a short life, a single use, and the method, the path and the SHA-256 of the body that were signed.
import { SignJWT, importPKCS8 } from "jose";

export type Signer = (method: string, path: string, body: string) => Promise<Record<string, string>>;

const b64url = (bytes: ArrayBuffer): string => {
  let s = "";
  for (const b of new Uint8Array(bytes)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

export function makeSigner(
  privateKeyPem: string,
  issuer: string,
  now: () => number = () => Date.now(),
  newId: () => string = () => crypto.randomUUID(),
): Signer {
  const key = importPKCS8(privateKeyPem.replace(/\n/g, "\n"), "ES256");
  return async (method, path, body) => {
    const bsh = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body)));
    const iat = Math.floor(now() / 1000);
    const token = await new SignJWT({ htm: method.toUpperCase(), htu: path, bsh })
      .setProtectedHeader({ alg: "ES256", typ: "JWT" })
      .setIssuer(issuer)
      .setIssuedAt(iat)
      .setExpirationTime(iat + 30)
      .setJti(newId())
      .sign(await key);
    return { authorization: `Bearer ${token}` };
  };
}
