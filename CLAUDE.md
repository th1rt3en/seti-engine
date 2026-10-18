# SETI Engine

A fan-made, non-commercial website for the board game SETI (CGE). Players can sign up for rated games or play anonymously. Read `docs/PLAN.md` first: it holds the approved decisions (D1 to D18), the architecture and the phases. Do not contradict it. If you think a decision is wrong, say so to the owner and don't work around it.

## Hard rules

1. **The rulebook is the source of truth.** `docs/rules/SETI-rulebook-EN-2024-09-17.pdf` for the base game, plus the official FAQ and errata once they're added under `docs/rules/`. For the Space Agencies expansion (optional, D19; work started by the owner on 2026-10-15, D35) the sources are the rulebook `SE2 rulebook EN 16`, the alien aid `SE2 aliens aid EN 14` and the promo sheet `SETI promo 03 - Space Agencies` from czechgames.com. The owner keeps these PDFs out of the repository; download them into a scratch folder and cite them from the spec (`docs/spec/expansion.md`). Base-game behavior must not change when the expansion is off. Card effects, boards and tiles that exist only as pictures are never guessed: list them in `docs/spec/ambiguities.md` and `docs/asset-gaps.md` and wait for the picture or text. The project is English only (D20). Never implement a rule from memory or from another game's conventions.
2. **Cite rule IDs.** Every rule in the spec has an ID (`docs/spec/`). Code that implements a rule has a comment with its ID, and every rule ID has at least one test that names it.
3. **Ambiguity means stop.** If the rulebook is unclear or contradicts itself, add an entry to `docs/spec/ambiguities.md` (the rule text with page, the readings, the consequences) and stop that piece of work. Do not pick a reading. The owner rules on it, and the ruling is copied into the spec.
4. **The engine is pure and deterministic.** No I/O, no clock, no global state, and no unseeded randomness. The same seed and action log must always give the same state.
5. **The engine is the only place rules live.** The Worker, the website and the UI contain no rule logic. The UI offers only the legal moves the engine returns.
6. **Hidden information never leaves the server unprojected.** Hands and deck order go to a player only if that player may see them.
7. **No deploys, secrets or DNS changes.** Write the infrastructure code and instructions, and the owner runs them. Never commit secrets.
8. **Report missing assets.** If an asset isn't in the asset repo, use a placeholder, add it to `docs/asset-gaps.md` and mention it in your report. Every imported asset is recorded in the provenance manifest.
9. **Don't change the plan quietly.** Architecture or scope changes need the owner's approval and a new decision-log entry.

## Architecture (summary)

- `services/engine/`: Python engine, stateless HTTP service on Cloud Run. `apply(state, action)` returns the new state, events, legal moves and the pending decision.
- `apps/worker/`: TypeScript Cloudflare Worker and the `GameRoom` Durable Object (state, WebSockets, timers, per-player projection, D1 checkpoints).
- `apps/web/`: Next.js on a Cloudflare Worker via OpenNext (signup, lobby, profile, leaderboard, replay, game UI). Cloud Run runs only the Python engine (D30).
- `packages/protocol/`: JSON Schema generated from the pydantic models, and the TS types generated from it. Never hand-edit generated files.
- `packages/assets/`: imported assets and the provenance manifest.
- Games are event-sourced: a seed plus an ordered action log.
- Promo cards SE EN 01 and SE EN 02 are an optional game setting (D23), separate from the expansion; default off. Rules for them are pending ruling A-001.
- Every started game is archived to GCS (D25) and replayable; the engine service signs-checks requests (D16a); lobbies and clocks follow D24 to D28 in `docs/PLAN.md`.
- Rating: Elo, pairwise for 3 to 4 players, start 0, K 60/40/20 by rated games played, floor 100 with no loss below it (D37, `docs/PLAN.md` section 6). Only rated games with registered players count.

## Commands

Run Python commands from `services/engine/`. `uv` is installed as a Python module on this machine, so use `python -m uv` if `uv` isn't on PATH.

- Setup: `python -m uv sync`
- Engine tests: `python -m uv run pytest`
- Engine lint and types: `python -m uv run ruff check` and `python -m uv run mypy`
- TypeScript: `pnpm install`, `pnpm test`, `pnpm lint`, `pnpm typecheck` (pnpm may need installing first: `npm i -g pnpm`). Worker tests: `pnpm --filter @seti/worker test`; with the engine service running, `SETI_ENGINE_URL=http://127.0.0.1:8765 pnpm --filter @seti/worker test` also plays whole games through the room. On this Windows machine pnpm is not on the PATH: run `node "C:\Program Files (x86)\Nodist\bin\node_modules\pnpm\bin\pnpm.cjs" ...` in PowerShell.
- Website: `pnpm --filter @seti/web dev` (needs `.env.local`, see `apps/web/.env.example`), `pnpm --filter @seti/web build` (a plain Next build; the Cloudflare build needs Linux, see `docs/deploy-web.md`); a local end-to-end check of the whole backend: `node apps/web/scripts/e2e-local.mjs` with the engine and `wrangler dev --local` running (see the script's header). Regenerate the web data after engine changes: `cd services/engine && python -m uv run python ../../tools/web/sync_data.py`
- Regenerate the protocol: `cd services/engine && python -m uv run python ../../tools/engine/gen_protocol.py`, then `pnpm --filter @seti/protocol generate` (or `npx json-schema-to-typescript@15 -i schema/protocol.schema.json -o src/types.ts` in `packages/protocol`)
- Rebuild a game from its archive: `cd services/engine && python -m uv run python ../../tools/engine/replay_log.py <replay.json or downloaded game folder>`. Card review page for the owner: `python tools/web/build_card_review.py OUT.html`.
- Run the engine service: `cd services/engine && python -m uv sync --extra service && python -m uv run uvicorn seti_engine.service:app --port 8080` (see `docs/deploy-engine.md`)
- Sync spec data into the engine: `python tools/engine/sync_data.py` (run from repo root)
- Rebuild the rule index: `python tools/spec/build_index.py`
- Rule coverage report by rule ID: `python tools/engine/rule_coverage.py [-v]` (run from repo root)

## Conventions

- Python: 3.12 or newer, type hints everywhere, pydantic models for state and actions, `ruff` and `mypy --strict` clean, tests with `pytest` and `hypothesis` for property tests.
- TypeScript: strict mode, Biome for lint and format (same as the asset repo).
- Commits: Conventional Commits (the asset repo uses commitlint).
- One system or card group per task and per branch. Agents working in parallel use separate worktrees and don't edit each other's files.
- Tests come with the code. A rule isn't done until its tests exist and pass. Card effects need one test per card.
- Verification that matters: scripted scenarios from the rulebook's worked examples, a random-play fuzzer (no crashes, no stuck states, invariants hold), and replay equals live state.
- A review agent checks rules changes against the rulebook text itself, not against the implementer's summary.

## Workflow

- The owner reviews at gates: the architecture spike, the asset gaps, the spec and every ambiguity ruling, before alpha, and before rated play opens (`docs/PLAN.md` section 5).
- When you finish a task, report what you did, what you tested, what you couldn't verify, and any ambiguities or missing assets you found. Don't claim completion if tests fail or a step was skipped.
- Legal: the project is a fan project, non-commercial, and is taken down on CGE's request. Keep the disclaimer and the takedown contact in the site footer, and don't add anything that suggests CGE's endorsement.
