# Engine progress

Status of the Python rules engine against the spec (`docs/spec/`). Run `python tools/engine/rule_coverage.py` for the live rule-ID coverage.

## Done (base game, 1 to 4 players, solo included)
- Seeded SplitMix64 RNG, event-sourced `apply()`, replay determinism test (A-004). Setup for 2 to 4 players, promo cards option, solar system and rotation.
- Turn flow: launch, move, buy a card, exchange, free-action discard, place data, tuck, pass, income, milestones, end of game.
- Orbit, land (moons, Mars choice), scan as free-order steps with the four telescope techs, signals, sector completion and winners, research, computer techs, analyze, life traces (`rewards.py`, `techs.py`).
- Play a card: all 138 base cards (`card_defs.py`, `cards.py`), quick and triggerable missions, turn effects, end-of-game cards.
- All five species (`species.py`): boards, alien decks, discovery, Anomalies, Centaurian messages, 'Oumuamua tile and exofossils, Exertian cards, milestones and danger, Mascamite samples and capsules.
- Alien cards ET.1 to ET.40 (`alien_steps.py`, `card_defs.ALIEN_CARDS`). The Exertian cards ET.41 to ET.55 follow the species rules.
- Final scoring (`scoring.py`): gold tiles, end-of-game cards, Exertian cards and the danger loss, winners.
- Solo (`rival.py`, `objectives.py`): setup for 5 difficulties, the rival's resources and progress, all 19 action cards, species rules for the rival, passing, objectives and their end-of-round effects, final scores and the winner. `Options(players=1, difficulty=1..5)`.
- Service (`service.py`, `protocol.py`, `projection.py`): stateless HTTP endpoints /new, /apply, /legal, /project, /schema, /health; the per-player projection of hidden information; the generated JSON Schema and TypeScript types in `packages/protocol`; a Dockerfile and `docs/deploy-engine.md` (nothing is deployed).
- Backend (`apps/worker`, outside this engine): the Worker, the `GameRoom` Durable Object, the game room core (lobby, play, clocks, resign and timeout, views, log), the D1 migration and sink, Elo (K = 20, pairwise) and the token check. See `docs/deploy-worker.md`.
- Website (`apps/web`): username signup with Turnstile, guests and their upgrade, lobby with invite links, game page driven by the legal moves (card images, drawn solar system, clocks, kick), leaderboard, profiles, replay viewer; see `docs/deploy-web.md`.
- Archive and replay (D25): every started game is written to `temp-common-storage` through the engine service (`archive_store.py`); `replay.py` and `tools/engine/replay_log.py` rebuild and verify a game. Request signing (D16a): `request_auth.py`.
- Tests: unit and scenario tests for every system, a smoke test per playable card, and random-play fuzzers (uniform and progress-seeking) for 2, 3 and 4 players.

## Next (in order)
1. Website: the species boards and the rival's board are still text (cards and the solar system are drawn); a password reset (D29 has none); `docs/asset-gaps.md`.
2. Typed action union for the protocol (actions are generic objects for now).
3. (Done, D16a) Request signing; the remaining small items are below.

## Known caveats
- No proposals are waiting for the owner.
- Card effects (`card_defs.py`, base and alien cards, 178 in all) were read from the card art and checked against the repo text. The owner confirmed all of them on 2026-10-14 using the card review page (`tools/web/build_card_review.py`). A later correction goes through a test per changed card.
- Per-card tests: a smoke test for every playable card, a value test for each plain effect and a scenario test for each step and mission type. Cards with unusual effects are covered by their scenario test, not one test each.
- (Done 2026-10-14) Data overflow (RES-01): a `data_overflow` decision lets the player place pool data first; sector completions (TURN-05): a `sector_order` decision lets the player choose the order. Only the player whose turn it is is asked about data; the solo rival resolves sectors lowest first.
- A signal in 'Oumuamua's sector asks for the sector or the tile; #120 Orbiting Lagrange Point's return-to-hand check is made before that choice is resolved.
- Parked (D22): Space Agencies expansion.
