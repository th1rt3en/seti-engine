# Deployment status (2026-10-19)

Deployed with the owner's permission. No secret is written in this file. Version numbers change with every deploy: read the current ones with `gcloud run services describe seti-engine --region us-central1` and `wrangler deployments list` in `apps/worker` and `apps/web`.

| Part | Where | State |
|---|---|---|
| Engine service | Cloud Run `seti-engine`, project `freestyle-190711`, `us-central1`, https://seti-engine-725889947830.us-central1.run.app | Deployed (revision seti-engine-00043-6r8 on 2026-10-19). Public URL; every request except `/health` must be signed (D16a). Env: `ENGINE_TRUSTED_KEYS`, `WEB_CONCURRENCY`. Writes the archive to `gs://temp-common-storage/seti-engine/games/...` with the default service account (checked). Deploy: `gcloud run deploy seti-engine --source . --region us-central1` from `services/engine`. |
| Game Worker | Cloudflare `seti-worker`, https://seti-worker.tobiko11.workers.dev | Deployed (version 42fca6ee on 2026-10-19). Secrets `AUTH_PUBLIC_KEY`, `ENGINE_SIGNING_KEY`. Admin routes guarded by `x-admin-key` (D36). |
| Website | Cloudflare `seti-web`, https://seti-web.tobiko11.workers.dev | Deployed (D30). Secrets `AUTH_PRIVATE_KEY`, `ENGINE_SIGNING_KEY`, `TURNSTILE_SECRET_KEY`, and the admin passphrase hash (D36). Build in WSL (`tools/deploy/build-web-wsl.sh`), then `wrangler deploy` in `apps/web` (`docs/deploy-web.md`). |
| Database | Cloudflare D1 `seti` (`466fc48e-8908-4f65-bbe7-6677706eeec8`, region `enam`) | Migrations 0001 (schema), 0002 (usernames) and 0003 (admin attempts) are in `apps/worker/migrations`. Check with `wrangler d1 migrations list seti` that all three are applied before a release. |
| Turnstile | Cloudflare widget `seti-web`, domain `seti-web.tobiko11.workers.dev` | Created. |

Deploy order for a release that changes the engine and the clients: engine first, then the Worker, then the website (the Worker and the website tolerate an older engine, the other way round does not always hold).

Not tested live: a signup with the real Turnstile widget in a browser (1.0 checklist, section C).
