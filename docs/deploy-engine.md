# Deploying the engine service

The engine is a stateless HTTP service (decision D5). The owner runs these steps; the agents do not deploy (CLAUDE.md rule 7).

## Run it locally

```
cd services/engine
python -m uv sync --extra service
python -m uv run uvicorn seti_engine.service:app --port 8080
```

## Build the image

`services/engine/Dockerfile` builds a small image that serves the app on `$PORT` (Cloud Run sets it).

```
docker build -t seti-engine services/engine
docker run --rm -p 8080:8080 -e PORT=8080 seti-engine
```

## Cloud Run (owner)

- Deploy the image as a private service (no public invoker); only the Worker's service account may call it. The service does not authenticate callers itself.
- Simultaneous games: a move is CPU work and one Python process uses one core, so the image starts `WEB_CONCURRENCY` uvicorn workers (default 2). Give the instance as many CPUs as workers (for example `--cpu 2` with the default; on 2026-10-22 the service runs on 1 CPU and 1 GiB, which the owner found enough by watching its use), set Cloud Run concurrency to about 20 to 40 requests per instance, and let it scale out (`--max-instances` to the budget). The service keeps no state, so any number of instances can serve one game.
- Set a minimum of 1 instance to avoid cold starts (docs/PLAN.md risks). The service needs no database and no secrets.
- Request signing (D16): set the environment variable `ENGINE_TRUSTED_KEYS` to a JSON object with the public keys (PEM, `\n` for line breaks) of the callers:
  `{"worker": "-----BEGIN PUBLIC KEY-----\n...", "web": "-----BEGIN PUBLIC KEY-----\n..."}`. Every request except `/health` must carry a token signed
  by one of them. On Cloud Run (the variable `K_SERVICE` is set) a service without these keys refuses every request, so it can never run open by mistake.
  Make a key pair with `openssl ecparam -name prime256v1 -genkey -noout | openssl pkcs8 -topk8 -nocrypt -out worker.pem` and
  `openssl pkey -in worker.pem -pubout -out worker.pub.pem` (the same for `web`). The private key goes to the caller (below), the public key to the service.
  A token is used once per instance, so a request cannot be replayed to the instance that served it.

## The game archive endpoint (D25)

`PUT /archive` writes one file of a game's log to the bucket `temp-common-storage` (`ARCHIVE_BUCKET` changes the bucket) using the access token of the Cloud Run
service account from the metadata server. No key is stored. The service account needs *Storage Object Creator* on the bucket. The endpoint accepts only paths of the
form `seti-engine/games/YYYY/MM/DD/<table number>.json` (one file for a whole game, written again as the game goes on). For local use set `ARCHIVE_DIR` to write into a folder.

## What the Worker must do

- Keep the game state and the action log; call `POST /apply` with the stored state and the player's action.
- Send each client only `POST /project` output for that player, never the raw state (rule 6).
- Send a player only the `legal` moves of their own view.

## Error reports (2026-10-19)
Unexpected errors of the engine, the game Worker (and its Durable Objects) and the website are stored as one JSON object each in the same bucket as the game archive (`temp-common-storage`, or `ARCHIVE_BUCKET`):

`gs://temp-common-storage/seti-engine/errors/<YYYY-MM-DD>/<HHMMSS>-<source>-<id>.json` (the day and the time are UTC; `source` is `engine`, `worker`, `game-room` or `web`)

Each object has `source`, `at`, `message` and `detail` (the route, and the stack). The Worker and the website send their reports with `PUT /errors` (signed like every request); the engine writes its own. The paths are made by the engine, so a caller cannot choose where to write, and long text is cut. Each process sends at most 20 reports a minute. Reading them: `gcloud storage ls gs://temp-common-storage/seti-engine/errors/2026-10-19/` and `gcloud storage cat <object>`. Nobody is alerted: look at the folder. A report that fails to be stored is dropped.
