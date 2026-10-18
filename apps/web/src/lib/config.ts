// Settings from the environment (see .env.example). Nothing secret is committed.
export interface Config {
  /** The Worker, as the server reaches it. */
  workerUrl: string;
  /** The Worker, as the browser reaches it for the WebSocket (ws:// or wss://). */
  workerWsUrl: string;
  /** The engine service, used for the replay viewer. */
  engineUrl: string;
  /** PKCS8 PEM ES256 private key that signs the website's requests to the engine service (decision D16). Empty in development. */
  engineSigningKey: string;
  /** PKCS8 PEM private key (ES256) that signs the tokens the Worker checks. */
  authPrivateKey: string;
  authIssuer: string;
  authAudience: string;
  /** "sqlite" keeps the data in a local file (development); "d1" uses the Cloudflare D1 REST API. */
  dbMode: "sqlite" | "d1";
  sqlitePath: string;
  cfAccountId: string;
  cfDatabaseId: string;
  cfApiToken: string;
  /** Cloudflare Turnstile (the challenge on signup and login). Without a secret the check is skipped in development and refuses in production. */
  turnstileSiteKey: string;
  turnstileSecret: string;
  /** Secret: the scrypt hash (as made by `hashPassword`) of the passphrase of the administrator's page. Empty: the page is closed. */
  adminPassphraseHash: string;
  /** Secret: the key that the site presents to the Worker for the administrator's routes (cancelling games). */
  adminWorkerKey: string;
}

export function loadConfig(env: Record<string, string | undefined> = process.env): Config {
  return {
    workerUrl: env.WORKER_URL ?? "http://127.0.0.1:8787",
    workerWsUrl: env.NEXT_PUBLIC_WORKER_WS_URL ?? env.WORKER_WS_URL ?? "ws://127.0.0.1:8787",
    engineUrl: env.ENGINE_URL ?? "http://127.0.0.1:8765",
    engineSigningKey: (env.ENGINE_SIGNING_KEY ?? "").replace(/\\n/g, "\n"),
    authPrivateKey: (env.AUTH_PRIVATE_KEY ?? "").replace(/\\n/g, "\n"),
    authIssuer: env.AUTH_ISSUER ?? "http://localhost:3000",
    authAudience: env.AUTH_AUDIENCE ?? "seti-worker",
    dbMode: env.DB_MODE === "d1" ? "d1" : "sqlite",
    sqlitePath: env.SQLITE_PATH ?? ".data/dev.sqlite",
    cfAccountId: env.CF_ACCOUNT_ID ?? env.CLOUDFLARE_ACCOUNT_ID ?? "",
    cfDatabaseId: env.CF_D1_DATABASE_ID ?? "",
    cfApiToken: env.CF_API_TOKEN ?? env.CLOUDFLARE_API_TOKEN ?? "",
    turnstileSiteKey: env.TURNSTILE_SITE_KEY ?? "",
    turnstileSecret: env.TURNSTILE_SECRET_KEY ?? "",
    adminPassphraseHash: env.ADMIN_PASSPHRASE_HASH ?? "",
    adminWorkerKey: env.ADMIN_WORKER_KEY ?? "",
  };
}
