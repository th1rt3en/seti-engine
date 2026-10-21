# Deploying the AI lobby service

The model that sits in a lobby is played by a small stateless HTTP service (`services/ai/src/seti_ai/lobby_server.py`). The Worker's room asks it for each move
of an AI seat. The owner runs these steps; the agents do not deploy (CLAUDE.md rule 7).

## What it does

`POST /move` gets the game's options, the whole action log, the seat and the rest of the plan it gave last time, replays the game, builds the seat's own view
(its hand, the other hands hidden) and plays the turn with the bundle search on the network. It answers `{action, plan}`; the Worker hands `plan` back with
the next request of the same turn, so the search runs once per turn. A retry after a failure plays the same move (the search is seeded by the seed and the
length of the log). The service holds no game. The request carries the seed: it can see what a player at that seat cannot, so the service is private and its
requests are signed like those of the engine service (D16).

## Which versions are served

Only versions with `approved: true` in `models/index.json`. Approving is the owner's act and never done by training:

```
cd services/ai
python -m uv run python -m seti_ai.publish --models models_alpha --approve v001 --live v001   # approve, and list as the version a host can add
python -m uv run python -m seti_ai.lobby_export --models models_alpha --out serve_models      # copies only approved versions (weights are not in git)
```

`--live` marks the version in the site's table `bot_versions`; the lobby page offers the live versions to the host, and the same version is listed on `/bots`.
The weights never leave this machine except in the image below.

## Build and run

```
cd <repository root>
docker build -f services/ai/Dockerfile -t seti-ai .
docker run --rm -p 8090:8080 -e PORT=8080 seti-ai
```

The image has the CPU build of PyTorch (the small network, 14M parameters, needs no GPU; one bundle takes about 1 to 4 seconds on a laptop core). To try it
without Docker: `python -m uv run --with fastapi --with uvicorn --with cryptography uvicorn seti_ai.lobby_server:app --port 8090` in `services/ai`, with
`SETI_MODELS=models_alpha` and, for a version that is not approved yet, `SETI_ALLOW_UNAPPROVED=1`.

## Cloud Run (owner)

- Deployed 2026-10-22 as `seti-ai` (us-central1, https://seti-ai-725889947830.us-central1.run.app) with a public URL like the engine: every request but `/health` must
  be signed, and an unsigned one gets 401. It carries the seed, so never remove the `ENGINE_TRUSTED_KEYS`. 2 CPUs and 2 GiB, concurrency 4, 0 to 1 instances (a cold start loads the weights, a few seconds).
- `ENGINE_TRUSTED_KEYS`: the same JSON as the engine service (the Worker's public key). Without it a Cloud Run service refuses every request.
- Optional: `SETI_SEARCH` is a JSON object of search settings (`{"samples": 6, "copies": 3}`); `SETI_MODELS` is the folder of the versions (default `/models`).

## The Worker

`BOT_URL` of the game Worker is set to the service's URL in `apps/worker/wrangler.toml`. Without it no AI can be
added to a lobby (the room answers `no_bot`). The Worker signs its requests with the same key it uses for the engine (`ENGINE_SIGNING_KEY`).

## The game with an AI

- The host adds the AI in the lobby after ticking that the game is recorded and used to train the AI. The Worker refuses it otherwise (`consent`). The game is
  never rated, and the seat of an AI has no clock that can run out.
- If the service is down the room asks again every 10 seconds; the human can wait or resign. Nothing is lost: the state is in the room.
- The archive header of such a game names the seat (`bot: {model}`) and keeps the host's agreement (`consent`). The data pipeline refuses a game with a model seat
  and no `consent`.

## From games to training data

```
gcloud storage rsync -r gs://temp-common-storage/seti-engine/games ./archive
cd services/ai
python -m uv run python -m seti_ai.bundle_train alpha --people ../../archive --people-share 0.3 ...   # only with the owner's go (training)
```

`seti_ai.dataset` reads the downloaded folders (a `replay.json` or a game folder), keeps the games played to the end, applies the rule of
`docs/AI-TURN-BUNDLES.md` section 10(b) (a game the model lost: the person's bundles with weight 3, value labels from both seats; a game the model won or tied:
skipped; a game without the model: once), skips and counts a game the engine cannot replay any more, and mixes the examples into the data of the bots by share.
