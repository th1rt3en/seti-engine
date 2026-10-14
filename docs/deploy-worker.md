# Deploying the Worker and the GameRoom Durable Object

The owner runs these steps; the agents do not deploy, touch secrets or change DNS (CLAUDE.md rule 7).

## What it is

`apps/worker` is a Cloudflare Worker with the Durable Object `GameRoom` (one object per game) and a D1 database.
The Worker checks the player's token, then routes to the game's object. The object keeps the game state and the action log, talks to the
engine service for every move, tells each player their own view over a WebSocket, runs the clocks with an alarm, and writes to D1
only when a game starts and when it ends (decision D6).

## Routes

| Route | What |
|---|---|
| `POST /games` | create a game; body `{options, clock, rated}`; answers `{ok, id}` (needs a token) |
| `POST /games/:id/join`, `POST /games/:id/leave` | take a seat, leave the lobby (token) |
| `GET /games/:id` | public data of the game (status, seats, options with the seed once started) |
| `GET /games/:id/log` | the action log; the seed plus the log replay the game |
| `GET /games/:id/ws?token=...` | WebSocket; without a token the connection is a spectator |
| `GET /health` | |

Client messages: `{t:"action", seq, action}` (seq is the number of actions the client has seen, so a repeated message does nothing),
`{t:"resign"}`, `{t:"ping"}`. Server messages: `lobby`, `view` (the engine's projection for that seat, with the legal moves for the player
to act and the clocks), `error` (with the legal moves for an illegal action), `ended`.

## Steps (owner)

1. `pnpm install`
2. `wrangler d1 create seti`, copy the database id into `apps/worker/wrangler.toml`.
3. `wrangler d1 migrations apply seti` (applies `apps/worker/migrations`).
4. Set `ENGINE_URL` (the Cloud Run service, see `docs/deploy-engine.md`), `AUTH_ISSUER` and `AUTH_AUDIENCE` in `wrangler.toml`.
5. `wrangler secret put AUTH_PUBLIC_KEY` (the PEM public key whose private key the website signs tokens with, ES256) and
   `wrangler secret put ENGINE_SIGNING_KEY` (the PKCS8 PEM private key of the `worker` entry of the engine's `ENGINE_TRUSTED_KEYS`, see `docs/deploy-engine.md`).
6. `pnpm --filter @seti/worker build` checks the bundle (a dry run); `wrangler deploy` in `apps/worker` publishes it.

## Tokens (decision D16)

The website issues a short-lived ES256 JWT with `sub` (user or guest id), `name`, `reg: true` for registered accounts, `iss` and `aud`.
Only registered accounts can play rated games.

## Open points for the owner

- (Resolved, D24) No minimum length for rated games. In games of 3 or 4 players a negative clock lets another player kick; the others share first place.
- (Resolved, D26) Clock speeds: fast 5 min + 1 min 30 s, normal 7 min 30 s + 2 min 30 s, slow 10 min + 3 min 30 s.
- (Resolved, D27a) A lobby whose players all disappear is destroyed after about a minute: clients ping every 15 s and a silent player is taken to have left.
- (Resolved) The pairwise Elo formula was confirmed by the owner on 2026-10-13.
- Real-time clock defaults (the bank and the increment) and the turn-based limits are settings of the lobby; their defaults come with the website.
- (Resolved, D16a) The engine service checks signed requests.

## The game archive in Google Cloud Storage (D25)

Every started game is written to the bucket `temp-common-storage`, under `seti-engine/games/YYYY/MM/DD/<game id>/`, so that a replay can be built later.
The Worker holds no Google key: it sends each file to the engine service (`PUT /archive`, the same `ENGINE_URL` and signed requests as the moves), and the engine
service, on Cloud Run, writes it with the credentials of its own service account. What the owner does:

1. Give the Cloud Run service account of the engine service the role *Storage Object Creator* on `temp-common-storage` (plus *Storage Object Viewer* for whoever reads the logs back).
   If the bucket has another name, set the environment variable `ARCHIVE_BUCKET` on the engine service.
2. Nothing else: there is no archive secret or setting in the Worker. If the service account cannot write, the engine service answers 503, the Worker logs
   "archive ... failed, will retry" and retries (at the next action, and every minute after the game ended).

For local development set `ARCHIVE_DIR=some/folder` when you run the engine service: the files are then written there instead.

Layout and format: `src/core/archive.ts`. Rebuild a game from a downloaded folder or file:
`cd services/engine && python -m uv run python ../../tools/engine/replay_log.py <seti-engine/games/.../ID folder or replay.json>`.

## Many games at once

Every game is its own Durable Object, so games do not slow each other down, and each handles one message at a time. The shared part is the engine
service: it is stateless and scales out on Cloud Run. A test with 12 games (2 and 3 players) played at once against a local engine with 2 workers
finished 2136 actions in 9 s (`SETI_ENGINE_URL=... pnpm --filter @seti/worker test`).
