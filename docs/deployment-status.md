# Deployment status (2026-10-14)

Deployed with the owner's permission. No secret is written in this file.

| Part | Where | State |
|---|---|---|
| Engine service | Cloud Run `seti-engine`, project `freestyle-190711`, `us-central1`, https://seti-engine-725889947830.us-central1.run.app | Deployed, 0 to 1 instances. Public URL; every request except `/health` must be signed (D16a). Env: `ENGINE_TRUSTED_KEYS`, `WEB_CONCURRENCY`. Writes the archive to `gs://temp-common-storage/seti-engine/games/...` with the default service account (checked). |
| Game Worker | Cloudflare `seti-worker`, https://seti-worker.tobiko11.workers.dev | Deployed. Secrets `AUTH_PUBLIC_KEY`, `ENGINE_SIGNING_KEY`. Tested end to end (create, play, resign, archive, replay). |
| Website | Cloudflare `seti-web`, https://seti-web.tobiko11.workers.dev | Deployed (D30). Secrets `AUTH_PRIVATE_KEY`, `ENGINE_SIGNING_KEY`, `TURNSTILE_SECRET_KEY`. Tested: pages, signup, session, creating a game, the game page. |
| Database | Cloudflare D1 `seti` (`466fc48e-8908-4f65-bbe7-6677706eeec8`, region `enam`) | Migrations 0001 and 0002 applied. Empty (test data removed). |
| Turnstile | Cloudflare widget `seti-web`, domain `seti-web.tobiko11.workers.dev` | Created. |

Removed: the Cloud Run `seti-web` service, its Artifact Registry package and its Cloud Build source archive. Not used: Secret Manager.

Not tested live: a signup with the real Turnstile widget in a browser, and the game page in a browser.
