# Deploying the website

The website is a Cloudflare Worker (decision D30): Next.js built with OpenNext (`@opennextjs/cloudflare`). It reads the D1 database through a binding, calls
the game Worker (`WORKER_URL`) and the engine service (`ENGINE_URL`) with `fetch`, and its images and scripts are static assets of the same Worker.
Settings that are not secret are in `apps/web/wrangler.toml`. The owner runs these steps (CLAUDE.md rule 7).

## Settings

- Variables (`wrangler.toml`): `DB_MODE=d1`, `WORKER_URL`, `WORKER_WS_URL` (the browser's WebSocket address), `ENGINE_URL`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, `TURNSTILE_SITE_KEY`.
  `AUTH_ISSUER` is only a name that the site and the game Worker agree on (`seti-web`); it is not a URL.
- Secrets (`wrangler secret put NAME`, from `apps/web`):
  - `AUTH_PRIVATE_KEY`: PKCS8 PEM of the ES256 key that signs the tokens for the game Worker (its public key is the game Worker's `AUTH_PUBLIC_KEY`).
  - `ENGINE_SIGNING_KEY`: PKCS8 PEM of the key that signs requests to the engine (its public key is the `web` entry of the engine's `ENGINE_TRUSTED_KEYS`, see `docs/deploy-engine.md`).
  - `TURNSTILE_SECRET_KEY`: the secret of the Turnstile widget (D29). Without it the site refuses signup, login and guest play. The widget's domain list must contain the site's address.
- The database binding `DB` is the D1 database `seti`, migrations in `apps/worker/migrations`: `wrangler d1 migrations apply seti --remote` (from `apps/worker`).

## Build and deploy

OpenNext's Cloudflare build does not work with Windows paths. On Linux or macOS: `cd apps/web && pnpm exec opennextjs-cloudflare build && pnpm exec wrangler deploy`.
On Windows use WSL: install Node 22 and pnpm 10 in WSL, run `tools/deploy/build-web-wsl.sh` (it builds a copy in `~/seti`), copy `~/seti/apps/web/.open-next` back to
`apps/web/.open-next`, and run `pnpm exec wrangler deploy` in `apps/web` from Windows with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` set.

## Images

`python tools/web/build_assets.py` cuts every card into its own 300 px WebP and writes the solar system discs, all with a hash of the content in the file name,
plus `public/_headers` (one year, `immutable`, for `/assets/*` and `/_next/static/*`). Run it again when the source images change, then rebuild and deploy.

## The game page

`GameView` (apps/web/src/components) draws a game for the live page and for the replay: the base board (`main-board-assembled.png`) with the three discs at their own
scales, the four star-ring boards in the order of the game, probes, orbiters and landers, the discovery spaces and every player's score and publicity marker; the
card row and the two alien species (face down until discovered) on the left; the publicity track and the twelve tech stacks (cut out of the board and turned the right
way up) to the right of the board; the moves of the player to act in a bar on top; the tracker of all players floating at the right edge; the hand in a foldable panel in the
bottom left corner. The moon token on the rotation dial marks the disc that turns next. Where things are on the board picture is in `src/lib/geometry.ts` (measured on the picture). Income, tucked cards, missions
and end-of-game cards come from the engine's view (`view.trackers`), the turn counter from `state.turn`.
`/demo` shows the page with a sample game (`python -m uv run python ../../tools/web/make_sample_view.py`, run from `services/engine`), without signing in.

## Local development

`pnpm --filter @seti/web dev` with a `.env.local` (see `.env.example`): a local SQLite file stands in for D1, and `TURNSTILE_*` can use Cloudflare's test keys.
`wrangler dev` of the built site needs a Linux or macOS host with a recent system library (it does not run in WSL with Ubuntu 20.04).

## Open points

- There is no password reset: a player who loses the password loses the account (D29).
- The takedown contact (seti.web.tobiko11@gmail.com) is in the footer (`apps/web/src/app/layout.tsx`) and in `LEGAL.md`; change both if it changes.
