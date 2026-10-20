# The AI: every decision point, for the owner's approval

Status 2026-10-20: **training is stopped and will not be started again without the owner's explicit approval.** Nothing in this file is final until the
owner has answered it. Each point says what is built now, what the alternatives are, what each costs, and what I recommend. The numbers come from the
runs so far and are marked as measured or estimated.

## 0. What exists today

- `services/ai` (Python 3.12, PyTorch 2.11 with CUDA): features, the network, offline bots, the arena, training, versions, the publisher of statistics.
- Two lines of versions in `services/ai/models/` (local, not in git):
  - v001 to v003: the first network (a feed-forward net over 1,158 hand-picked numbers, 1.1M parameters), trained for 54 rounds; stopped when its games
    grew longer and longer (it learned to stall).
  - v004 to v008: the second network (transformer, 53M parameters, whole-view features), trained for 50 rounds, stopped on request. v008 scored 103 against the
    heuristic bot's 35 (19 wins in 20 games), 98 against random's 3 and 97 against the greedy bot's 23. These bots are weak players: the numbers say that the
    agent learned the game's basics, not that it plays well against people.
- No tree search is built. No version is served to players. `/bots` shows v001 and v002 (the old line) as "testing".

## 1. The objective and the reward

| Point | Built now | Alternatives | Effect | Recommendation |
|---|---|---|---|---|
| What is maximised | the seat's **own final score** (your instruction) | the chance to win (ZeusAI: +1/-1); the margin over the opponent; a mix | with its own score only, the agent does not mind helping the opponent or ignore blocking; in a 2-player game the winner is decided by the margin | own score now; add the margin once the agent plays well, because it is what decides a game |
| Reward at each decision | the board score gained until the seat's next decision, divided by 20; the last decision also gets what the end adds (end-of-game cards, gold tiles, danger loss) | only the final score (sparse) | dense reward makes learning faster; the end-game points reach the agent only at the last decision, so planning for them is learned slowly | keep; check later that end-game scoring is being used |
| Discount and advantage | no discount (1.0), GAE with lambda 0.95 | discount 0.99 | the game is finite and the whole score matters | keep |
| Stalling | a limit of 3,000 decisions per game, a penalty of 20 points for a game that is not finished, the undo move is never offered | none | the first run learned to play 12 times longer games while its score fell | keep |

## 2. The scope of the first training

**Changed by the owner (2026-10-20): the scope includes the Space Agencies expansion, with organizations and quick start cards.** 2 players first; 3 and 4 players later,
each with its own model. No solo, no promo cards. The agent is trained on both kinds of game: the base game and the expansion game with organizations and quick start
cards (the choice of the organization and of the two quick start cards are decisions it learns to make). The features do not need a change: they are made from the
whole view, so the organizations, the signal tokens, the new species (Arkhos, Glyphids, Amoeba) and the state of the expansion are seen as they are; the options of
the game are in the view, so the agent knows which kind of game it plays. The heuristic bot and the tuning of it play both kinds of game.

## 3. What the agent sees (decided with you: everything a player sees)

- The projected view of the seat to act, whole, so a new field of the engine is seen at once. Hidden parts arrive as "?" and only their count is seen.
- Seats are made relative (the seat to act is player 0). Species-specific data (`species.extra`) is renumbered by key names (markers, owners ...); a key with a
  different name keeps absolute player numbers. This is a known weak point (section 12).
- Each entity is a token: a player, a sector, a planet, a probe, a tech stack, a gold tile, a species and each part of its own state, a pending decision, a
  tracker, the solo rival and objectives, each card in a zone (name + zone + position), and one token for the rest of the game. A token is the sum of the learned
  vectors of its features; a feature is a path in the view and its value, hashed into 32,768 slots.
- Left out: the seed, the random generator, undo data, bookkeeping, the text log, the final scores (they only exist at the end), and what is encoded elsewhere
  (the legal moves with the engine's notes, the reach of the probes, the rotation previews).
- Checks: `tests/test_features.py` (the deck order, the other hand, hidden tiles and an undiscovered species change nothing the agent sees);
  `docs/ai-visible-info.md` (the list of everything seen). One leak was found and fixed in the engine (the board of an undiscovered species showed its species by the
  number of spaces); that engine change is committed but **not deployed**.

Decisions for you: whether any seen information should be withheld (for example the discard pile is seen by players and so by the agent); whether the opponent's
past moves (a history) should be given (a player remembers them; today only the position is seen, so the agent has no memory of what the opponent did).

## 4. The network

| Point | Built now | Why | Alternatives |
|---|---|---|---|
| Family | a transformer encoder over the entity tokens, learned embeddings, no encoded rules (ZeusAI's design) | the position is a set of components with no grid; attention lets any entity look at any other; costs and effects are learned | a feed-forward net on a fixed vector (the first line); a graph network |
| Token vector | sum of feature embeddings (EmbeddingBag, 32,768 slots) + an embedding of the entity kind, then a layer norm | hashing needs no list of features, so the whole view can be used | a fixed list of features chosen by hand; a larger or smaller hash space |
| Summary | one extra token that attends to all and feeds the value head | the usual choice | pooling |
| Policy | each legal move is a query (its tokens, the engine's note of cost and rewards, 17 numbers); a small decoder lets the moves attend to the position and to each other; one score each; a softmax over the legal moves | the set of legal moves changes at every decision (up to about 120); an illegal move gets zero chance by construction | a fixed output layer over all possible moves (too many and varying) |
| Value | the points the seat will still gain, in units of 20 points | matches the reward | the chance to win |
| Details | pre-layer-norm, GELU, no dropout, bfloat16 autocast on the GPU | stable and fast on an RTX 3060 | |

**Size** (a setting; the same code trains all three):

| Preset | Layers x width x heads (feed-forward) | Parameters | Of which the feature table |
|---|---|---|---|
| small | 4 x 256 x 4 (1,024) | 14M | 8M |
| **base (used)** | 8 x 512 x 8 (2,048) | 53M | 17M |
| large | 12 x 768 x 12 (3,072) | 144M | 25M |

How the size was chosen. ZeusAI's network for 7 Wonders Duel has 12 layers, 768 wide, 12 heads and about 92M parameters; it learned from about 420,000 games with a
tree search of up to 1,000 simulations a move. SETI's state is larger, so the capacity should be at least comparable eventually ("large" is that size plus the larger
embedding table). The limit on this machine is the number of games, not the size: base trains at about 140 seconds per round of 96 games (measured: 90 s of play, 52 s of
update), and a larger network would need many more games to be used. I chose **base** as the place to start, and I did **not** compare sizes by experiment: the choice
is a judgement from ZeusAI's size, the state size and the speed of this machine. If you want it tested, the experiment is to train small and base for the same number of games and compare.
Weights do not carry over from one size to another; a larger network can learn from the games that a smaller one played.

## 5. How it is trained now

1. **Warm start (imitation).** 400 games of the bots (heuristic, greedy, random in pairs), 72,000 decisions; 6 passes; the network learns to pick the bot's move (64%)
   and the value of positions. Why: a network that starts from nothing plays randomly and earns about 3 points, so almost nothing is learned from the first games. ZeusAI
   did the same for its value head with 35,000 rule-based games.
2. **Self-play with PPO.** Each round: 96 games, half the agent against itself (both seats use the same network), a quarter against the heuristic bot and a quarter against
   the greedy bot; about 16,000 decisions. Then 2 passes of PPO over them: clip 0.2, entropy bonus 0.01, value weight 0.5, batches of 64, AdamW with a learning rate of
   1e-4 and weight decay 0.01, gradient clip 0.5. The agent samples its moves from its own policy while it plays.
3. **Evaluation** every 10 rounds: the agent taking its best move, 20 games against each of the three bots on fixed games with seats swapped. A version is saved when its
   score against the heuristic bot is the best so far. With 20 games the noise is large (a few points); the saved version is not always the best.
4. **Where it runs.** The games are played by 10 worker processes on the CPU cores; one server process on the GPU answers all the workers' requests in batches; the update
   runs on the GPU. Only this PC; nothing is trained in the cloud.

Not done, and open: a pool of earlier versions as opponents (against forgetting and cycling), a schedule for the learning rate, a stopping rule (today: a number of rounds;
I suggest: stop when the evaluation has not improved for 30 rounds), many more games per round, and evaluation against a human.

Measured progress (new line, base network): score in training games 14 (round 1), 31 (6), 66 (20), 80 (36), 86 (50); against the heuristic bot 74 (round 6), 86 (20), 90 (28),
101 (36), 103 (50).

## 6. Tree search (MCTS): not built, the decisions

ZeusAI's strength comes from AlphaZero-style search: at each move it runs up to 1,000 simulations that use the network's policy and value to guide the search, plays a move
chosen by the visit counts, and trains the policy to copy the visit counts and the value to predict the result. SETI differs in four ways that need decisions.

1. **Hidden information.** 7 Wonders Duel has none to speak of; SETI has the deck order, the other hand and face-down tiles and species. A search over the true state
   would cheat. Options: (a) *determinization*: before each search, sample a full state that is consistent with what the seat has seen (shuffle the unseen cards, deal the
   other hand from the unseen cards, pick the undiscovered species from those not yet seen), search it, and repeat with several samples (needs a new function in the engine and
   tests that the sample is consistent with the view); (b) a search over information sets (heavier, better in theory); (c) no search. Recommendation: (a).
2. **Chance.** Draws and some effects are decided by the engine's random state. With a sampled state they are fixed inside a search; sampling many states covers them. ZeusAI
   used "afterstates" (a node with up to 11 random children). Recommendation: determinization first, afterstates later if needed.
3. **Many small decisions.** A turn has several decisions (exchanges, placing data, picking spots). Options: search at every decision, or only at the main actions and the
   decisions with many options. Recommendation: every decision with at least 3 legal moves, a small budget.
4. **Cost.** Each simulation is one engine step (about 0.8 ms) plus a network evaluation (batched on the GPU). With 10 workers I expect about 3,000 simulations a second in
   total (an estimate). A game has about 500 decisions, so with 200 simulations each a game takes about 30 seconds: about 2,500 games a day. ZeusAI's 420,000 games would take
   5 months here. So the full method is not affordable at its scale; what is affordable is a small search (50 to 200 simulations).
5. **Settings to choose:** the exploration constant of the search, noise at the root, the temperature of the move choice (random in training, best in play), the number of
   determinizations, reuse of the tree between decisions, whether the value for the search is the own score (our objective) or the chance to win.

Three ways to go:
- **A. No search.** Keep PPO. Cheapest, limited by what a network can do in one look.
- **B. Search at play time only.** Use the trained network inside a determinized search when the bot plays (and for evaluation). No new training. It shows how much a search adds,
  and it is the cheapest way to a stronger bot; the cost is time per move when serving (a small search of 50 simulations on a CPU server is slow: seconds per move).
- **C. AlphaZero-style training.** Train the policy on the search's visit counts. The strongest and the most expensive; it needs A or B to have shown that search helps.

Recommendation: B first (one engine function plus the search, no training), measure the gain, then decide on C.

## 7. Versions, statistics and serving

- Each saved version has a folder with weights and a manifest (the date, the rules version, the network, how it was trained, the bot versions it was measured against); the
  numbers are published to the site (`/bots`) with `seti_ai.publish`, as "testing", "approved" or "playing". Nothing is approved or served without you.
- Serving is not built. A 53M-parameter transformer on a position of about 60 tokens needs about 4 GFLOP: roughly 0.1 s a decision on a CPU server, so serving the
  policy alone is fine; serving a search is not, without a GPU or a very small search. Decision for you: where a served bot runs (the engine's Cloud Run, a separate CPU
  service, or this PC).

## 8. The bots used as opponents and yardsticks

Random; greedy (a one-step look at the value of resources); heuristic version 2 (the same weights as version 1 plus the advice of the quantified model: cards and missions
first, no scan in round 1). The model's own values taken literally were tried (the "model" bot) and played far worse (9 points against 40), because a one-step bot that
values resources at their full price does not spend them. The BoardGameGeek post is only a short introduction to the same article. The bots are weak; for a real
yardstick we need a stronger opponent (the search of section 6, or human games).

## 9. Known weak points

- Species-specific data and the expansion are in the features but the agent has been trained only on the base game, so it has never seen the expansion pieces.
- The renumbering of the seats inside `species.extra` is by key names; an unknown key keeps absolute numbers.
- 32,768 hash slots: collisions are rare but not zero. A list of structures is read up to 40 entries, a list of names up to 24 by position (and in full as a bag).
- A move has at most 28 tokens; a rare move with more is cut.
- The agent has no memory of the opponent's earlier moves.
- The evaluation uses 20 games a bot: the noise is a few points.
- The version that is saved is the best against one bot; it may not be the best against others.

## 10. What I need from you

1. Objective: own score only for now, or add the margin to the reward (section 1)?
2. Scope: stay with 2 players, base game, until the plateau (section 2)?
3. Network: base (53M) as it is, or test small against base first, or go straight to large (section 4)?
4. Training: the settings of section 5 (games per round, learning rate, opponents, stopping rule), and a pool of earlier versions as opponents?
5. Search: A, B or C, and the budget (section 6)?
6. Memory of the opponent's moves: add it (section 3)?
7. Serving: where, and whether a version needs to beat a threshold before it is shown to you (section 7)?
8. May I deploy the engine fix (the undiscovered species board), which is committed but not deployed?
9. When training may start again.

## 11. The owner's answers (2026-10-20) and what follows from them

| # | Answer | What follows |
|---|---|---|
| 1 | Own score is the metric: it also scales to 3 and 4 players, where a margin does not | keep the reward as built; no margin term |
| 2 | Start with 2 players; separate models for 3 and 4 players later | the features and the code are written for any number of players; one model for each player count |
| 3 | The large network, larger if it can be afforded | preset `large` (144M) is the choice; `xlarge` (310M) was measured: see the table below |
| 4 | Largely agree; an opponent pool of past versions; **improve the heuristic bot first**: it must beat the random bot and the greedy bot at least 70% of the time before the real model is trained against it; search the internet for improvements | the heuristic bot is being improved and measured (section 12); the opponent pool is a part of the training code; no training until the owner approves the plan |
| 5 | AlphaZero-style training, no determinization | see the open question below |
| 6 | Implement memory | the agent is given the history of the actions of both seats (section 13) |
| 7 | A model version needs the owner's manual and explicit approval before it is available to users | a version is only ever "testing" until `seti_ai.publish --approve vNNN` (and `--live`) is run by the owner's order; the site shows no version as playing otherwise |
| 8 | Deploy the engine fix | done (revision seti-engine-00054-6l8) |
| 9 | No training until the owner approves the plan | nothing is trained; only bots play each other (no learning) to measure the heuristic bot |
| 10 | Every game that the deployed model plays against a human must be available for training later | section 14 |

**Answer to the question on 5 (2026-10-20): sample the chance events at the nodes of the tree, as ZeusAI did** (a node for the outcome of a draw or a reveal, with
a limited number of children that grows with the visits; a simulation that reaches a full node continues through one of its existing children). Nothing is built
until the owner approves the plan. What this needs, so that it is decided before the build:
- the engine must say which steps are chance events (a card drawn from the deck, a tile or a card revealed, an alien discovered) and let a search choose the
  outcome of one from what the seat has not seen (the unseen cards), instead of reading the real deck: a function in the engine with tests;
- **the other player's hand is left out (owner, 2026-10-20).** The search uses only public information: the other hand is a count. What is known about it is what was
  seen in public: the cards that the other player took from the display and the cards that an effect showed (`knowledge.py`, kept by the arena and, when a bot is served, by
  the Worker from the action log); every other card in it is unknown and is not guessed. The same holds for the agent's view of the game: it sees the count of the
  other hand and the list of the known cards in it, nothing else. The face-down tiles of the tech stacks stay hidden in the same way.
- the training targets: the visit counts for the policy, and the seat's own final score for the value (our objective).

## 12. The heuristic bot: what the internet says and what was measured

Sources read: the quantified model (seti.ender-wiggin.com/posts/model), its tech article (/posts/tech), a beginner's guide (thetablepriest.com), a review with
advice (Meeple Mountain). The BoardGameGeek threads on opening moves and strategy could not be read by the tool (they are behind a challenge page); if you paste
one I will use it. What the sources say that can be played by a bot: income and one early tech in rounds 1 and 2 (energy more than credits); 2 or 3 cards tucked
for income early; orbit before landing, Mercury and Mars first; discarding a card for its free action is often better than playing it, so play cards for
missions, free moves and end-of-game goals; do not start round 1 with a scan; the late game is scanning with the purple techs; the best techs are Mercury scan
and the launch/move tech (S), the asteroid tech (A+), the landing tech (A); blue techs (computer) are A to S, energy first.

Measured (200 games a match, the same games for both bots, seats swapped; the bar was 70%):

| Bot | against random | against greedy | against version 2 |
|---|---|---|---|
| version 2 (the first weights + the model's play advice) | 100% | 71% (60 games) | - |
| **version 3 (version 2 with energy 0.9 against credit 0.7)** | **100%** (47 to 4 points) | **84.8%** (43 to 24) | **73.5%** (44 to 32) |

What was tried, and the result (each against version 2 or 3, 60 to 200 games): the value of resources and structures fading in the last rounds: worse (42% to 46%
against greedy); the techs valued by their tier (S, A+, A, B of the tech article): no gain (53%, then 42% in the 200-game test together with a lower card value);
more weight on tucked cards: no gain (51%); more weight on orbiting and landing: no gain; energy 1.1: worse (43%); energy 1.3: far worse (4%: it hoards);
no card and mission bonus: no gain (51%); allowing a scan in round 1: no gain (41% against version 2). Only the energy weight of 0.9 helped. So version 3 is the
heuristic bot to train against: it clears the 70% bar against both random (100%) and greedy (85%). The earlier versions are kept as `heuristic_v1` and `heuristic_v2`,
and the model's own values as `model`, so that old numbers can be reproduced; the saved versions of the AI were measured against version 1 and 2.

The sizes of the network, measured on this GPU (RTX 3060, 12 GB) with random positions of 65 entities and 40 moves, no training (`seti_ai.benchmark`):

| Preset | Parameters | One update of a batch of 64 | One answer for a batch of 64 | GPU memory |
|---|---|---|---|---|
| small | 14M | 23 ms | 6 ms | 0.5 GB |
| base | 53M | 87 ms | 24 ms | 1.8 GB |
| large | 144M | 232 ms | 62 ms | 4.5 GB |
| xlarge (1024 wide, 16 layers, 16 heads) | 310M | 472 ms | 126 ms | 9.0 GB |

A round of self-play (about 16,000 decisions, 2 passes) is then about 45 s of update for base, 2 min for large and 4 min for xlarge, plus the time to play the
games. For a search, each simulation needs one answer: about 2,500 positions a second for base, 1,000 for large, 500 for xlarge; at 200 simulations a decision a game
of about 500 decisions costs 100,000 answers: about 40 s (base), 100 s (large), 200 s (xlarge) of GPU: roughly 2,000, 860 and 430 games a day. So the size is not
the limit; the games are. `xlarge` fits in memory (9 of 12 GB: nothing else may use the GPU) and halves the number of games compared with `large`. I recommend `large`.

## 13. Memory of the moves

The agent is given the last 48 actions of both seats as tokens (a card taken from the display is named in the entry), and the list of the cards that the other seat
is known to hold (taken from the display or shown), (who, in turn order relative to the agent; the type; the parameters that are public: a card named
when it was played or discarded face up, not when it was tucked face down; the age of the action). It is part of the view features; the arena and the training
keep the history, and a served bot gets it from the game's action log.

## 14. Games between the deployed model and humans, kept for training

Requirements, to build with the bot seat (after the owner approves a version for serving):
1. The archive of every game (already written to the Google Cloud Storage bucket) says which seats are bots and which model version played them, and the rules
   version (the engine's commit) of the game: in the header of the archive and in the games table of the database.
2. The bot's own decisions are logged in the archive (the policy it chose from, its value estimate, the number of search simulations), because those are the
   targets for AlphaZero-style training; a human's moves are logged as usual.
3. A tool on this PC (`seti_ai.dataset`) copies the new bot games from the bucket, replays each with the engine of its rules version (a copy of the repository
   at that commit, because old games cannot be replayed by newer rules), and turns them into training examples: the positions, the legal moves, the move chosen,
   and the final score of each seat.
4. Human moves in those games are also training data (what the people chose), and a game against a person is a test of the bot (its score, its win rate by
   version, shown on the page of the AI).
5. Consent (decided by the owner, 2026-10-20): when a player adds a model to their lobby, the site warns them that the game data will be collected to train
   the models, and adding the model counts as agreeing to it. The warning is shown before the model is added, the agreement is recorded with the game (who agreed
   and when), and a game without a model is not collected for this. Players are named by a hash in the data.

## 15. Pause and resume at will (owner, 2026-10-20)

The training can be paused whenever the owner needs the PC, and resumed later from where it was. Built (`checkpoint.py`, `train.py`), not yet used on a real run:
- **A checkpoint at the end of every round** with everything needed to go on: the network, the optimizer, the round number, the best score, the settings and the random
  generators, so that the games after a pause are the same as if there had been none. It is written to a temporary file and moved into place, so a power cut cannot
  leave a broken file.
- **Pause:** `python -m seti_ai.train pause` (or Ctrl+C in the window, or a file `PAUSE` in the models folder). The run finishes the small batch of games being played
  (a few seconds; the games are played 12 at a time for this), does not keep a half round, and exits, so the processor, the graphics card and the memory are free at once.
- **Resume:** `python -m seti_ai.train ppo --resume` goes on from the checkpoint of the last full round (the loss is at most the round in progress, about two minutes).
  Without `--resume` or `--fresh` a run refuses to start when a checkpoint exists, so that a checkpoint is never overwritten by mistake. `python -m seti_ai.train status`
  says where the run is.
- **If the machine is switched off or the process is killed:** the same checkpoint is there.
- **The search and the replay buffer (when they are built):** the games are saved in files as they are finished and the buffer is part of the checkpoint, so a pause costs
  no game. The warm start (copying the bots, about 5 minutes) is not paused: it is started again.
- The tuning of the heuristic bot (`seti_ai.tune`) saves its best setting every 4 generations and can start again from it with `--resume`.

## 16. The heuristic bots to come, and the opponent pool (owner, 2026-10-20)

- **Version 4** must score at least **100 points on average** (own score, over base and expansion games with organizations and quick start cards, against the earlier
  heuristic bot) before it is used. It is being made by tuning (section 12): more terms in the value function and a search over its weights.
- **Version 5** must then score at least **150 points on average** on the same measure. A one-step bot with tuned numbers is unlikely to reach that; the plan for it is a
  bot that looks at a whole turn (a search over the moves of one turn, free actions and the main action, with the same value function at the end of the turn) and then
  tunes its numbers the same way. If a deeper look is not enough, I will report where it stalls and what the options are before spending more on it.
- **Both are in the opponent pool of the model's training**, together with the greedy bot, version 3, and the past versions of the model itself (a pool of past versions
  avoids forgetting and cycling). The share of each in the games of a round is a training setting that the owner approves with the plan.
- Order of work: version 4, then version 5, then the owner approves the plan, then (and only then) training starts. Nothing is trained before.
