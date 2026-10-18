// The bindings and settings of the Worker (wrangler.toml; secrets are set by the owner, never committed).
export interface Env {
  GAME_ROOM: DurableObjectNamespace;
  DB: D1Database;
  /** The URL of the engine service on Cloud Run. */
  ENGINE_URL: string;
  /** Secret: the PKCS8 PEM ES256 private key with which the Worker signs its requests to the engine service (decision D16). */
  ENGINE_SIGNING_KEY?: string;
  /** The public key (PEM, SPKI) that checks the tokens issued by the website. */
  AUTH_PUBLIC_KEY: string;
  AUTH_ISSUER: string;
  AUTH_AUDIENCE: string;
  /** Secret: the key with which the website's administrator page calls the admin routes (cancelling games). */
  ADMIN_WORKER_KEY?: string;
}
