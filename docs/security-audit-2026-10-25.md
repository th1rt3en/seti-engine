# Security audit, 2026-10-25

Scope: the website (`apps/web`), the Worker and `GameRoom` (`apps/worker`), the engine and AI services (`services/engine`, `services/ai` lobby server), the deploy workflow and the dependencies. Method: reading the code of every entry point, `pnpm audit --prod`, `pip-audit`, a search of the repository for secrets. Nothing was attacked live; nothing was changed. Findings are ranked by what an attacker can do now that the site is public.

## What is in place (checked)

- **SQL**: every value is a bound parameter; the few interpolated names are constants (`ids.ts`, `queries.ts`), `LIKE` input is escaped. No injection found.
- **XSS**: no `dangerouslySetInnerHTML`, `innerHTML`, `eval`. Chat and names are rendered as React text. Guest names are ASCII only, usernames are `[A-Za-z0-9_.-]{3,24}`. Chat lines are stripped of control characters and cut to 300 characters.
- **Passwords and sessions**: scrypt with a random salt, constant-time comparison, the same message for an unknown user and a wrong password; the session token is 256 random bits, only its SHA-256 is stored; cookie is `httpOnly`, `secure`, `SameSite=lax`; password change and recovery end all sessions.
- **Recovery and password change**: 5 wrong tries per address and 15 minutes (`auth_attempts`). The administrator's passphrase has the same lock (`admin_attempts`), a signed cookie of 2 hours, `SameSite=strict`, path `/admin`.
- **Worker**: the public routes are a whitelist; `/admin/*` needs `x-admin-key` (constant-time compare); the Durable Object cannot be reached except through the Worker; the log, replay and seed of a game are only given when it is finished; WebSocket messages are limited to 8 KiB and validated; options and clock are validated; one open table per guest, ten per account; one new game per player every 15 seconds.
- **Hidden information**: every view is projected by the engine per seat (checked in `sendView`); the seed is only served to the administrator.
- **Engine and AI services**: every request but `/health` carries an ES256 JWT with the method, path and SHA-256 of the body, a 30 second life and a single-use id; on Cloud Run they refuse everything when no trusted key is set (fail closed).
- **Secrets**: none in the repository or its history (searched for private keys and common token formats); `.env*` and `.dev.vars*` are ignored; the workflow has `permissions: contents: read` and runs only by hand (`workflow_dispatch`).
- **Headers**: nosniff, `X-Frame-Options: DENY`, referrer policy, permissions policy, HSTS.

## Rate limiting: not implemented (the main gap)

The only limits are the ones above (failed recovery/password/admin tries per address, the table limits, one game per 15 seconds, one chat line per second per player held in memory of the room). **There is no general rate limit** and no Cloudflare rate-limiting rule or binding in `wrangler.toml`. Consequences, from most to least serious:

1. **Anonymous cost amplification on the engine (high).** Every WebSocket connection to a game, with or without a token, makes the Worker ask the engine for a view (`sendView` calls `/project`) and send the whole log. `GET /api/replay/:id?step=N` (no sign-in) makes the website replay the game on the engine for each request. A script can open thousands of sockets or replay requests and drive Cloud Run CPU and cost, and slow real games.
2. **Login is not rate limited (high).** `loginAction` has only the Turnstile challenge; there is no lockout per account or per address, so a password can be guessed at the speed that a person (or a solving service) passes Turnstile. Signup and guest creation likewise: unlimited accounts and guests (database growth, spam tables, chat spam by many guests).
3. **Seated players can spam the engine (medium).** `preview` messages (two engine calls each) and `propose_undo` have no throttle except the undo cooldown; an active player can send many previews per second.
4. **Unbounded bodies (medium).** `POST /games` and `bot-add` read `request.json()`/`text()` with no size cap; the engine service reads the whole body before it checks the signature.
5. **No limit per address on connections, chat across guests, or table creation across guests.**

## Other findings

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | **High** | `next@15.5.27` is in use. Advisories fixed in 15.5.28: a DoS in Server Actions (applies), and an unauthenticated RCE in Image Optimization (not reachable: `images.unoptimized` is true). `pnpm audit --prod` also lists `undici`, `postcss`, `glob`, `body-parser` (13: 1 critical, 7 high, 5 moderate); all but `next` are build-time dependencies of OpenNext/Wrangler. | Update `next` to the latest 15.5.x and `@opennextjs/cloudflare`; run the tests. |
| 2 | Medium | Names such as "Administrator" or "Table" can be taken by a guest or a user. The chat shows system lines under those names (seat null), so a player can impersonate the administrator. | Reserve those names at signup and for guests (case-insensitive); mark system lines with a flag the client styles. |
| 3 | Medium | The Content-Security-Policy is report-only, and uses `'unsafe-inline'` for scripts. It blocks nothing. | Collect reports, then enforce; move to nonces if Next allows. |
| 4 | Low | Python: `certifi` 2026.7.22 (PYSEC-2026-4320). | Update to 2026.10.19. |
| 5 | Low | The replay cache of request ids is per process: with several Cloud Run instances a signed request could be replayed once to another instance within its 30 seconds. | Acceptable; the body and path are bound. |
| 6 | Low | The `GCP_SA_KEY` in GitHub is a long-lived key. Actions are pinned to tags, not commit SHAs. | Use Workload Identity Federation; pin actions by SHA. |
| 7 | Low | The WebSocket token goes in the query string (`?token=`): it can appear in logs. It lives 5 minutes and is single-purpose. | Send it as the first message instead. |
| 8 | Info | `torch.load` of the AI model files is pickle-based; safe only because the files are built by you into the image. | Keep the model files private; prefer `weights_only=True`. |

## Proposed order of work

1. Update `next` (finding 1) and `certifi`.
2. Rate limiting: Cloudflare rate-limiting rules in front of the site and the Worker (per address: login, signup, guest, the WebSocket upgrade, the replay API), plus in the room: a per-connection message rate, a cap on connections per address, a throttle on `preview`, and body size caps; a per-account lockout on login after repeated failures; a cached replay step.
3. Reserve system names (finding 2).
4. Enforce the CSP after a week of reports.
