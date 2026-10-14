// ES256 JSON Web Tokens signed with WebCrypto, which works the same in Node and in a Cloudflare Worker (the Node build of the `jose` library
// does not run inside a Worker). Only signing is needed here: the Worker and the engine service verify the tokens.

const b64url = (bytes: ArrayBuffer | Uint8Array | string): string => {
  const data = typeof bytes === "string" ? new TextEncoder().encode(bytes) : new Uint8Array(bytes);
  let s = "";
  for (const b of data) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

async function importPrivateKey(pem: string): Promise<CryptoKey> {
  const body = pem.replace(/-----(BEGIN|END) PRIVATE KEY-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(body), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey("pkcs8", der, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
}

/** A signed ES256 token. `claims` are the payload; `iat` and `exp` are added from `now` (ms) and `lifetimeSeconds`. */
export async function signJwt(
  pem: string,
  claims: Record<string, unknown>,
  lifetimeSeconds: number,
  now: () => number = () => Date.now(),
): Promise<string> {
  const iat = Math.floor(now() / 1000);
  const head = b64url(JSON.stringify({ alg: "ES256", typ: "JWT" }));
  const payload = b64url(JSON.stringify({ ...claims, iat, exp: iat + lifetimeSeconds }));
  // WebCrypto's ECDSA signature is the raw r||s that JWT wants
  const sig = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    await importPrivateKey(pem),
    new TextEncoder().encode(`${head}.${payload}`),
  );
  return `${head}.${payload}.${b64url(sig)}`;
}
