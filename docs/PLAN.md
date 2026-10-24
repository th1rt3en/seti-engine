# SETI Engine: Plan and Decision Log

Status: approved by the project owner on 2026-10-12. Changes to anything here need the owner's sign-off and a new entry in the decision log (section 2).

## 1. Goal

A website for the board game SETI (Czech Games Edition) where users can sign up for rated games or play anonymously. Players can play 1 to 4 player games, real time or turn based.

- The rules engine follows the official rulebook exactly (`docs/rules/SETI-rulebook-EN-2024-09-17.pdf`).
- Assets come from https://github.com/Ender-Wiggin2019/seti (permission given by the repo owner).
- Fan project, non-commercial. CGE has not been contacted. We take the project down on CGE's request.

## 2. Decision log

| ID | Decision | Notes |
|---|---|---|
| D1 | The rulebook PDF is the source of truth for rules. | Official FAQ and errata also count. Ambiguities are logged and ruled on by the owner (D14). |
| D2 | Fan project, non-commercial, with takedown on CGE's request. | Footer disclaimer, a takedown contact, `LEGAL.md`, and per-file asset provenance. |
| D3 | Assets come from the Ender-Wiggin2019/seti repo. | The owner has permission from that repo's owner and none from CGE. The owner keeps the written confirmation. Missing assets get placeholders and are listed in `docs/asset-gaps.md`, which is reported to the owner. |
| D4 | The engine is written in Python. | Pure, deterministic and I/O-free. |
| D5 | Architecture is Option B: the Python engine is a stateless service on Cloud Run, and a thin TypeScript Durable Object owns game state. | The DO holds state, WebSockets, timers and the D1 checkpoints. For each action it calls `apply(state, action)` on the engine. Option A (a Python Worker and DO) is not used. It stays open only as a later experiment, because the engine's JSON interface would not change. |
| D6 | Game state lives on Cloudflare: one Durable Object per game, plus D1. | The DO writes to D1 at checkpoints only (game start, game end, optionally every N actions). |
| D7 | The website is Next.js (TypeScript) on Cloud Run. | Game traffic goes directly from the browser to the Worker over WebSocket. The website does not proxy it. |
| D8 | Games are event-sourced: a seed plus an ordered action log. | This gives replay, spectating, audit and bug repro. The same seed and log must give the same state. |
| D9 | The client is not trusted, and hidden information is projected per player on the server. | The browser never receives hands or deck order it shouldn't see. |
| D10 | The engine returns the legal moves with every state update, and the UI offers only those. | No client-side rule logic and no client-side prediction. |
| D11 | Types are shared via JSON Schema generated from the pydantic models, with TypeScript types generated from that. | The protocol can't drift between Python and TypeScript. |
| D12 | Solo mode is in scope for 1.0. | The bot follows the rulebook. Solo is also the main rule test bench before alpha. |
| D13 | Both real-time and turn-based play. | Each game has a clock setting. The DO alarm drives the timers. Async play has email notifications through a queue. |
| D14 | Rulebook ambiguities go to `docs/spec/ambiguities.md`, and the owner rules on them. | An agent that hits an ambiguity records it and stops. It does not guess. |
| D15 | Rated play (2 to 4 players) ships at 1.0 with Elo (start 0, K 60/40/20 by games played, floor 100: see D37). | The multiplayer formula is in section 6. Guests and solo games are never rated. |
| D16 | Auth is self-hosted sessions with anonymous guest tokens. | A guest can upgrade to an account and keep their history. The website issues short-lived signed JWTs, which the Worker and the engine verify with a public key. |
| D17 | Claude agents do the work, under the owner's supervision. | Conventions are in `CLAUDE.md`. Review gates are in section 5. |
| D18 | Agents don't deploy, touch secrets or change DNS. | They write the infrastructure code, and the owner runs the deploys. |
| D19 | The Space Agencies expansion (`docs/rules/SE2_rulebook_EN_13_lowres.pdf`) is in scope as an optional module. Games run with or without it. | The engine takes an options object (`expansion: bool`, plus sub-options such as organizations and quick start cards). Base-game behavior must not change when the expansion is off. The expansion has its own spec area (`EXP-`) and its own test suite. The expansion's own rules: 4 rounds with organizations, neutral quick-start markers for 1 to 2 players, and solo changes. |
| D20 | English only. | All non-English assets were removed (`docs/asset-removals.md`). No localization work in 1.0. |
| D21 | Supplied assets live in `assets/` with labels in `assets/MANIFEST.md`. | The owner reviews the labels. Items marked `probable` or `unidentified` must be confirmed before the UI relies on them. |
| D22 | Expansion work is deprioritized until the owner has a source for all expansion assets. Priority order: base game (including its solo mode) first, expansion after. | Applies to engine implementation, spec writing, tests, backend and UI work for the expansion. The design must still leave room for it (D19): the options object, the `EXP-` rule-ID area and card-group separation stay in the architecture, but nothing expansion-specific is built or scheduled. The expansion rulebook may be read for design questions only. The expansion card tracker stays available for the owner. Revisit when the owner reports the assets are sourced; see `docs/asset-gaps.md` items 2 and 3 for what is missing. |
| D23 | The two cards SE EN 01 ("Not a planet since 2006") and SE EN 02 ("Gateway to Mars") are promo cards, not part of the base game or the expansion. The game has an option to include or exclude them at the start. | Engine option `promo_cards: bool`, independent of the expansion option. Default: excluded, so the standard game uses the 138-card base deck. How the cards enter the game when included (shuffled into the deck or otherwise) and the rules for the Pluto space are not in either rulebook; see `docs/spec/ambiguities.md` A-001. The lobby needs a matching checkbox when creating a game. Rated games: ruling pending, see A-001. Expansion-priority decision D22 does not apply to this option, which belongs to the base game. |
| D24 | Rated games have no minimum length: a rated game with registered players counts however it ends (completed, resignation, timeout, kick) and however short it was. In a game of 3 or 4 players a clock running out does not end the game. While a player's clock is in the negative, any other player can kick them. The game ends at once and all the other players share first place; the kicked player is ranked behind them. Games of 1 or 2 players still end when a clock runs out. (Owner, 2026-10-13.) | `MIN_RATED_ACTIONS_PER_PLAYER` is removed. A bank clock may go negative and stays negative after the player acts (the increment is added to the negative balance). The Worker has a `kick` message (`room.kick`); a kick is only accepted for a seat whose clock is negative. Elo treats the others as tied with each other and ahead of the kicked player (pairwise, section 6). |
| D25 | Every game that started, rated or friendly, completed or not, is logged to Google Cloud Storage in a format from which a replay of everything that happened can be built. The replay viewer is part of the website. The bucket is `temp-common-storage`. The server runs on Cloud Run, which already has the access, so no service account key is used. (Owner, 2026-10-13.) | The Worker runs on Cloudflare and cannot use Cloud Run's credentials, so it sends each archive file to the engine service (`PUT /archive`) and that service, on Cloud Run, writes it with its own service account. This is a change to the plan's "the engine never calls out": the rules engine stays pure, and only the service wrapper (`archive_store.py`, which accepts nothing but archive paths) does this I/O. If the owner prefers a separate Cloud Run service for it, only `ENGINE_URL` for the archive changes. The bucket is shared, so everything lives under `seti-engine/games/YYYY/MM/DD/` (the day the game started, UTC), and a game is ONE file named by its table number, `<table number>.json` (owner, 2026-10-24: one object to read instead of a folder of hundreds): the header, all the actions and the result (format `seti-game-log/1`, see `apps/worker/src/core/archive.ts`). A game in progress is written at its start and then every 20 actions, and the file is written for the last time when the game ends or is cancelled. `undo` and the moves that were taken back are not in the file (the log kept by the room has them). Games archived before that date stay in the old layout (`<game id>/header.json`, `actions/<seq>.json`, `result.json`, `replay.json`); the tools read both. Each action carries the events the engine reported. Failed writes are retried. `services/engine/src/seti_engine/replay.py` and `tools/engine/replay_log.py` rebuild and verify a game from the files. The public replay and log endpoints answer only for finished games, because the seed gives away the hidden information. D1 keeps the log of finished games too (D8 stays). A lobby that never started has nothing to replay and is not archived. |
| D26 | The clock has three speeds: slow, normal and fast. Each has a starting time, which is also the maximum, and an increment added for each turn. Fast: 5 min + 1 min 30 s. Normal: 7 min 30 s + 2 min 30 s. Slow: 10 min + 3 min 30 s. (Owner, 2026-10-13.) | All three are bank clocks; a bank never holds more than its starting time. "No clock" stays available. The values are in `CLOCK_PRESETS` in `apps/web/src/lib/worker.ts`. The per-turn clock stays in the Worker but is not offered by the lobby. |
| D27 | A player who creates a lobby joins it at once and can send out its link. A lobby that becomes empty is destroyed: its stored data and its list entry are deleted, and its link leads nowhere. The creator is the host; when the host leaves while others are in the lobby, the player who joined next becomes the host. (Owner, 2026-10-13.) | `Meta.host` and `Meta.joined` (join order) in `apps/worker/src/core/room.ts`. The lobby message names the host. A player who leaves and joins again goes to the back of the line. A lobby whose players all close their browsers without leaving is not cleaned up yet; a timeout for that is not decided. |
| D28 | The seats do not decide the play order: the host is not always the first player. (Owner, 2026-10-13.) | The engine already draws the first player from the seed (setup). In addition the Worker draws who sits in which seat when the game starts (`apps/worker/src/core/seating.ts`, from the same seed, so a replay gives the same seating). Connections are matched to seats by player id when a view is sent, and the view message carries the player names in seat order. Table order after the first player is still the cyclic seat order. |
| D29 | Accounts are a username and a password, no email. Cloudflare Turnstile protects signup, login and guest play. (Owner, 2026-10-13.) | `apps/web/src/lib/auth.ts` (username 3 to 24 letters, digits, dots, dashes, underscores; unique whatever the case, migration `0002_username.sql`), `apps/web/src/lib/turnstile.ts` (server check; without a secret key it is skipped in development and refuses in production). There is no password reset: a lost password cannot be recovered yet. A guest cannot take a registered username. |
| D16a | Request signing (completes D16): the Worker and the website sign every request to the engine service. (Owner, 2026-10-13.) | ES256 JWT in `Authorization: Bearer`, issuer `worker` or `web`, 30 s life, single use, bound to the method, the path and the SHA-256 of the body. The engine checks it with the public keys in `ENGINE_TRUSTED_KEYS` (`services/engine/src/seti_engine/request_auth.py`); on Cloud Run without the keys it refuses everything but `/health`. The single-use list is kept per instance. The bearer token `ENGINE_AUTH_TOKEN` is gone. |
| D27a | A lobby is kept alive by pings: a client in a lobby pings every 15 s, and a player not heard from for 60 s is taken to have left (same effect as leaving: the host passes on, an empty lobby is destroyed). (Owner, 2026-10-13.) | `LOBBY_PING_MS`, `LOBBY_GRACE_MS` in `apps/worker/src/core/room.ts`; the Durable Object alarm checks every 20 s while a game is in its lobby. |
| D30 | Cloud Run runs only the Python engine service. All user-facing web UI runs on Cloudflare: the website is a Cloudflare Worker (Next.js built with OpenNext), next to the game Worker and the D1 database. Static assets are served by Cloudflare, optimized and cached for a year. (Owner, 2026-10-14.) | Replaces "Next.js on Cloud Run" in sections 2 and 3. The site reads D1 through a binding (no REST token), calls the game Worker and the engine over `fetch`, and signs its tokens with WebCrypto (`apps/web/src/lib/jwt.ts`; the Node build of `jose` does not run in a Worker). Images: each card is its own 300 px WebP, every file name carries a hash of its content and `_headers` gives `/assets/*` and `/_next/static/*` `immutable` caching (`tools/web/build_assets.py`). Next's image optimizer is off (`sharp` is replaced by an empty stub package, `packages/sharp-stub`). The site is built under Linux (WSL on Windows), see `docs/deploy-web.md`. The Cloud Run `seti-web` service and its images were deleted. |
| D31 | A player may take back a free trade (2 credits, 2 energy or 2 cards for 1 credit or 1 energy) until their next action. A trade for a card cannot be taken back for now: see A-026. (Owner, 2026-10-14.) | Scope addition (UNDO-01). The engine keeps the state before the trade in `GameState.undo` (never sent to a player) and offers the move `{"type": "undo"}` while it is set; the log is append-only, the undo is an action like any other, so a replay gives the same state. Any other action clears it. |
| D32 | Moves can be taken back, a free action may interrupt the main action, and sectors are resolved right after the main action. (Owner, 2026-10-14.) | Extends D31. Every move can be taken back, one after the other within the turn, unless it reveals hidden information (a card from the deck, the round pile, a species, the next tech tile); the page warns and asks for a confirmation before such a move. The engine keeps the state at the start of the chain (`GameState.undo`) and the moves since (`undo_log`) and replays them minus the last; `reveals()` in `engine.py` finds the irreversible moves by trying each one, and `move_notes` marks them. A free action may interrupt the main action's decisions but not another free action (`stashed`, `free_active`, FREE-00). Completed sectors are resolved right after the main action (A-005, TURN-05). The card row is refilled after a whole scan but at once for a free action (A-026). |
| D33 | A solo sandbox mode: a one-player practice game without the rival in which cards (and the alien cards of face-up species), resources (credit, energy, data, publicity, exofossils once 'Oumuamua is face up) and the discs can be changed freely. (Owner, 2026-10-14.) | Scope addition. Option `sandbox` (`Options`, only with 1 player, never rated); actions `sandbox_add_card`, `sandbox_resource`, `sandbox_rotate` in `services/engine/src/seti_engine/sandbox.py`, checked by the engine and refused when the option is off; one `sandbox` entry in the legal moves tells the page what is possible. Spec: `docs/spec/sandbox.md` (SANDBOX-01 to SANDBOX-05). Species cannot be revealed from the sandbox, they are discovered by play (ALIEN-01), but the two face-down species can be chosen when the game is created (`Options.sandbox_species`, SANDBOX-06). |
| D34 | The lobby has a switch between real-time and turn-based tables; each has three speeds and an option without time control. Turn-based speeds (days): slow 4 days + 12 h, normal 3 days + 9 h, fast 2 days + 6 h per turn. No email notifications. A "ting" plays in the open page when it becomes the player's turn. (Owner, 2026-10-14.) | Extends D13 and D26. The turn-based speeds are the same bank clock as D26 with days (`CLOCK_PRESETS` in `apps/web/src/lib/worker.ts`; the Worker accepts any bank). Email notifications (D13) are dropped. The sound is made with the Web Audio API in `apps/web/src/lib/turnSound.ts` (unlocked by the first touch of the page, can be switched off, remembered in the browser). |
| D35 | The Space Agencies expansion work starts now: spec, engine, lobby option. (Owner, 2026-10-15.) | Lifts the deferral of D22 (the "assets are sourced" condition is waived by the owner; the work is done as far as the sources allow). Sources: `SE2 rulebook EN 16.pdf`, `SE2 aliens aid EN 14.pdf` and `SETI promo 03 - Space Agencies.pdf` from czechgames.com. The owner told the agent to keep the PDFs out of the repository: they stay in the agent's local environment, and the spec quotes and cites them (`docs/spec/expansion.md`, `expansion-data.md`). Card effects, species boards and tiles that exist only as pictures are not guessed: each is listed in `docs/spec/ambiguities.md` and `docs/asset-gaps.md` and implemented once its picture or text is supplied (CLAUDE.md rules 1, 3, 8). Base-game behavior must not change when the expansion is off (D19); the options are `expansion`, `organizations` and `neutral_quick_start`. |
| D36 | An administrator's page at `/admin`, with no link to it, behind a secret passphrase: accounts (delete, set or reset the rating) and lobbies (cancel one, or all that have had no move for a given number of hours or days). A game that an administrator cancels ends without a result and changes nobody's rating, rated or not. (Owner, 2026-10-18.) | Scope addition. The environment holds only the scrypt hash of the passphrase (`ADMIN_PASSPHRASE_HASH`, a secret of the website's Worker); a signed cookie lasts 2 hours; 5 wrong tries per address in 15 minutes lock the page (table `admin_attempts`, migration 0003). The site calls the Worker's `/admin/games/:id` routes with a shared key (`ADMIN_WORKER_KEY`, a secret of both Workers); the Worker reads the last move from the room (decision D6 is kept: no write to D1 for each move). Files: `apps/web/src/app/admin`, `lib/admin.ts`, `lib/adminData.ts`, `apps/worker/src/worker.ts` (`admin`), `core/room.ts` (`adminInfo`, `adminCancel`). |
| D37 | The rating system changes: everybody starts at 0; K is 60 for a player's first 10 rated games, 40 for the next 10, then 20; a rating never drops below 100, and a player below 100 does not lose anything by losing (the player who beat them still gains as normal). (Owner, 2026-10-18.) | Replaces the starting rating 1500 and K = 20 of D15. `apps/worker/src/core/elo.ts` (`kFor`, `FLOOR`, `START_RATING`), `ratings.ts` and the D1 sink (which reads the number of rated games of each player before the game). There were no ratings in the database when it changed, so none was converted; the website shows 0 for an unrated player. |
| D38 | Every player and every game has an integer number, and the addresses of their pages use it: `/players/12`, `/games/345`, `/replay/345`. A name of a player, wherever it is written, links to their profile and opens it in a new tab. (Owner, 2026-10-22.) | The long ids (a user's uuid, a game's Durable Object id) stay the keys everywhere else; the tables `user_nums` and `game_nums` (migration 0008, autoincrement keys: a number is given once, in the order things were made, and never again, even for a destroyed lobby) say which number is which id. The old addresses with the long id still work and redirect (permanently) to the number. The Worker numbers a game when its lobby is recorded; the site numbers a player when the account or guest is made, and the token carries it (`num`) so that the game page can link the names of the players (the lobby and view messages and the archive header carry `num`; the public replay keeps it and drops the user id). An AI seat has no number and no link. Files: `apps/web/src/lib/ids.ts`, `components/PlayerLink.tsx`, `components/PlayerName.tsx`. Release order: the migration, then the Worker, then the website. |
| D39 | In a game with the organization module (2 or more players) every player chooses the organization and the quick start cards at the same time, in secret, and locks the choice in; all the clocks run until the player locks in; nothing that anybody chose is shown to the others (not in the views, not in the public log) until everybody has locked in. Then the choices are made public and the starts are resolved in turn order. The cards that the players tuck for income at the start are chosen at the same time too, in a second step once the starts are resolved; in a game without organizations (2 or more players) the tuck of the setup (SETUP-36) is that step alone (owner, 2026-10-24). (Owner, 2026-10-23; the rulebook says the players choose at the same time, EXP-ORG-04.) | A new option of the game `simul_setup`, set by the Worker when the game starts, so that the games started before keep their log (the choices one after another) and replay as they were. The engine holds one open decision for each player (`setup_choice`); the moves name their seat; a view lists the seats that may move (`acting`); the room, the clocks and the AI service ask `acting` instead of one seat to act. The logic is in `orgs.py` (EXP-ORG-14), the Worker only checks that a player moves for their own seat. |
| D40 | A guest can have 1 table open at a time (a lobby or a game in progress) and an account 10. Creating or joining a table over the limit is refused with a message that names the limit, says to finish the tables first, says that solo tables can be resigned from the profile without any repercussion and, to a guest, that an account allows up to 10. (Owner, 2026-10-24.) | `apps/worker/src/core/limits.ts` (`overTableLimit`); the Worker counts the player's rows of `game_players` in games with status `lobby` or `playing` before it makes or joins a table (`openTables` in `worker.ts`); a table that the player already sits at is not counted twice. |

## 3. Architecture

```
Browser (Next.js UI)
   |  HTTPS                         |  WebSocket (JWT)
   v                                v
Cloudflare Worker: web app   Cloudflare Worker -> Durable Object "GameRoom"
(signup, lobby, profile,           |  state, WebSockets, timers, hidden-info projection
 leaderboard, replay)              |  HTTPS, signed request
   |                               v
   |                         Cloud Run: engine service (Python, stateless)
   |                               apply(state, action) -> new state, events, legal moves
   |                         GCS bucket: the log of every game (D25), written by the engine service on Cloud Run
   +---- reads ----> D1 (users, sessions, games, ratings, event logs) <---- checkpoint writes from the DO
```

Engine service contract:
- `POST /new_game`: player count, seed, options. Returns the initial state.
- `POST /apply`: state and action. Returns the new state, the events, the legal moves and the pending decision.
- `POST /legal_moves`: state. Returns the legal moves.
- The engine is stateless. It authenticates requests from the DO, takes the RNG seed from the state, and never calls out.
- The state sent over the wire is the full server-side state. The DO projects it per player before sending it to clients.

D1 tables (initial): `users`, `sessions`, `games`, `game_players`, `game_events` (or compressed log blobs), `ratings`, `rating_history`.

Monorepo (pnpm and Turborepo for TS, uv for Python):

```
apps/web/            Next.js site
apps/worker/         Cloudflare Worker and the GameRoom DO
services/engine/     Python engine and its HTTP wrapper
packages/protocol/   JSON Schema and generated TS types
packages/assets/     imported assets and the provenance manifest
docs/                rules, spec, plan, asset-gaps, ambiguities
```

## 4. Phases

| Phase | Work | Output |
|---|---|---|
| 0 | Scaffold the monorepo, CI and agent conventions. Clone the asset repo and write the asset inventory. Timing spike of Option B. | Go/no-go on the architecture, `docs/asset-gaps.md` |
| 1 | Rules spec from the PDF, with numbered rule IDs, setup tables, the solo-mode spec, an ambiguity log and the FAQ/errata. Freeze the first protocol schema. | `docs/spec/`, reviewed by the owner |
| 2 | Engine core: state, actions, turn flow, board and rotation, all systems, cards, scoring, solo bot. | Full headless 1 to 4 player games |
| 3 | Engine verification: per-rule tests, rulebook worked examples as scenarios, a random-play fuzzer, replay and determinism checks. | Coverage report keyed by rule ID |
| 4 | Backend: engine service, DO `GameRoom`, D1 schema and migrations, auth, Elo, timers, reconnects. | Playable through a CLI or test client |
| 5 | Website: lobby, game UI driven by legal moves, profiles, leaderboard, replay viewer, guest-to-account upgrade. | Internal alpha |
| 6 | Hardening: play-tests with experienced players, abuse controls, load tests, observability. Alpha, then beta, then 1.0 rated launch. | Launch |

**Expansion (D22, lifted by D35):** the phases above covered the base game only; the owner started the expansion work on 2026-10-15 (D35). Its parts: spec (`EXP-` rules), cards, organizations and quick-start setup, the three new alien species, the 4-round variant, signal tokens, and solo changes.

Phases 4 and 5 can overlap with 2 and 3 once the protocol schema is frozen.

## 5. Review gates for the owner

1. Phase 0: the architecture spike result.
2. Phase 0: `docs/asset-gaps.md`.
3. Phase 1: the spec, and every entry in `docs/spec/ambiguities.md`.
4. Before alpha.
5. Before rated play opens (beta to 1.0).

Everything else is gated by CI: tests, types, lint, and coverage by rule ID.

## 6. Rating system (D15)

- Elo, starting rating 0 (D37). K = 60 for a player's first 10 rated games, 40 for the next 10, then 20. A rating never drops below 100, and a player below 100 loses nothing by losing; the player who beat them gains as usual (expected scores use the real ratings).
- 2 players: standard Elo.
- 3 and 4 players: treat the game as pairwise matchups between every pair of players. Each pair uses the standard expected score and the actual score (1 win, 0.5 tie, 0 loss, from the final ranking). A player's change is the sum over opponents of K/(n-1) times (actual minus expected), with the K of that player, so one game can move a rating by at most K. (With the floor of D37 the changes of a game no longer add up to zero.)
- Ranking ties follow the rulebook's tiebreak. If the rulebook leaves a tie, the pair counts as a draw.
- Only rated games with 2 to 4 registered players count. Guests and solo games are never rated.
- Abandoning a rated game, or timing out, counts as a loss to every other player. There is no minimum game length (D24).
- A kick (D24) ranks every other player first (a draw among them) and the kicked player behind them.
- Confirmed by the owner (2026-10-13): the pairwise formula is correct; each player is compared with every other player. Implemented in `apps/worker/src/core/elo.ts` and tested.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Rules fidelity | Rule-ID traceability, FAQ and errata, the fuzzer, review by a separate agent against the rulebook text, and play-tests with experienced players |
| Card effect volume | Declarative effects for the common cases, code for the rest, and a test per card |
| Legal exposure | D2 and D3. Takedown readiness. |
| Cross-cloud latency (DO to engine) | Per-move cost is tens of ms and fine for a board game. Measured in the Phase 0 spike. |
| Engine cold starts on Cloud Run | Min instances of 1 at launch |
| D1 limits | Checkpointed writes and compressed logs |
| Rating integrity | Timeout and abandon rules, a minimum game length, and collusion heuristics |
