# Plan: an AI that learns from the games played on the site

Status: proposal for the owner. Nothing here is decided. It becomes part of the project only when the owner approves it and the decisions below are
entered in the decision log of `docs/PLAN.md` (D38 and on), as CLAUDE.md rule 9 asks. Written 2026-10-20.

## 1. The goal, in words that can be tested

Build a player (a "bot") that can sit at a table in a web game, plays only legal moves, sees only what its seat may see, and gets better over time from
the games that are played on the site (human games, and games it plays against itself). Three uses, in this order of value:

1. **An opponent** for solo practice and for tables that lack a player (a bot seat), with a few strengths.
2. **A benchmark**: how good is a score of 237 against the rival at 3 stars? What does the strongest play look like?
3. **Balance and analysis**: which organizations, species and cards win in strong play (this feeds the statistics page).

Success is measured, not felt (section 8): the bot beats the rival of the solo game at each difficulty, then beats a heuristic bot, then holds its own
against the better human players of the site in 2-player games.

## 2. What the project already has (the starting position)

- A pure, deterministic engine with `apply(state, action)` that returns the new state, the events and the list of legal moves. The legal moves come from
  the engine: a bot never invents a move.
- `project(state, viewer)`: exactly what one seat may see. This is the **observation** of the bot (CLAUDE.md rule 6 holds for the bot too).
- Every game is archived (seed + actions + events), and the engine now counts statistics per player (`stats.py`).
- Elo and a solo high score board: ready-made yardsticks.
- The solo rival: a rule-based opponent, so a first benchmark exists.

## 3. What makes this hard (be honest about it)

| Problem | Why it matters | What the plan does about it |
|---|---|---|
| Hidden information (deck order, hands, face-down tiles and cards) | A plain search over the true state would cheat. | The bot only gets the projected view. Search samples ("determinizes") the unknown cards consistently with what the seat has seen. |
| Long games with many small decisions (about 240 actions in a solo game, several decisions per turn) | Credit assignment is slow; a game is slow to simulate. | A fast in-process simulator, a value estimate of the final score margin, and learning the decision steps (not only whole turns). |
| A huge, changing action space (cards, spots, organizations, species, the expansion) | A fixed output layer does not fit. | Score each legal move with a network that reads the state and the move together (variable-size legal list). |
| Rules change while we test | We saw 3 finished games that the engine can no longer replay. Old logs then lose their meaning. | Version the rules (section 4, step 0) and store training records with the rules version. Never mix versions. |
| Few human games | A few friends' games are not enough to train on. | Self-play does the bulk of the learning. Human games warm-start it, and they are the test set. |
| Cost | Self-play needs a lot of simulated games. | Start small (solo and 2 players, base game), measure the simulation speed first, and stop if the price is too high (gates). |

## 4. The plan, in steps (each step ends with something that works and a gate)

### Step 0. Foundations (before any learning)
- **Rules version.** The engine gets a version number that changes whenever a rule or a card changes. Every archive and every training record carries it. A
  tool replays old archives only when the versions match, and says so otherwise.
- **Speed.** Measure how many engine steps per second one core does (in-process, no HTTP). Profile and fix the slowest parts (state copies, the
  projection, `legal_moves`). Target: a whole solo game in a few seconds. This number decides what is affordable.
- **An observation and an action encoding.** A fixed layout of numbers for a view (resources, the board and the discs, the card row, the hand as card
  ids, the tracks, the species, the pending decision) and for a legal move (its type and its parameters). Unit tests prove it is stable and loses nothing.
- **Gate:** the speed is known, and a random bot plays 1000 games through the new interface without error.

### Step 1. Heuristic bots and the bot seat
- A bot interface (`choose(view) -> one of view.legal`) in a new package `services/ai/`. It contains **no rule logic**; it only picks among legal moves.
- Bot 0: random. Bot 1: greedy (value of the move from the engine's own notes: score, resources, tracks). Bot 2: a hand-made heuristic player.
- A **bot seat** in a game: the Worker asks the bot service for a move when it is the bot's turn (the same clock rules, a bot answers in seconds).
- **Gate:** Bot 1 or 2 finishes games, never stalls, and beats random clearly in 2-player and solo games. A person can play against it on the site.

### Step 2. The data pipeline from the real games
- For each finished game the Worker (or a job) writes decision records: observation (the projected view of the player to act), the legal list, the move
  chosen, who the player was (id hashed), the rules version, and the final result. Stored in GCS as compressed files, one folder per rules version.
- Humans and bots are marked apart. Only completed games count (same rule as the statistics).
- A tool to rebuild the data of the archived games of the current rules version (like `backfill_stats.py`).
- **Consent and privacy** (see the owner's decisions): the site says that games may be used to build the bot; names are replaced by hashes in the data.
- **Gate:** a dataset report (number of games, decisions, humans against bots) and a check that replaying a record reproduces the view.

### Step 3. Learn from the humans (imitation)
- Train a network that gives, for a view and a legal move, how likely a good human is to choose it (behaviour cloning), and a value head that predicts the
  final score margin of the seat to act.
- Stack: PyTorch, training outside the website (a local GPU machine or a rented one), models exported to ONNX for the service.
- **Gate:** the network picks the human's move in the top 3 clearly more often than a random pick, and its value tracks the real result better than the
  score so far. If the human data is too thin, say so and go to step 4 with the heuristic bot's games as the starting data.

### Step 4. Self-play (the part that makes it strong)
- Start from the step 3 network (or the heuristic bot). Play games bot against bot (and against the rival in solo) at scale, with a search that uses the
  network: determinized Monte Carlo tree search (information-set sampling) with the network as prior and value. Train on the results. Repeat.
- Begin with **solo** and **2 players, base game**, fixed rule version. Add 3 and 4 players and then the expansion only after the first works.
- Every cycle produces a numbered checkpoint kept in GCS with its rules version, the data used, and its evaluation.
- **Gate (per cycle):** the new checkpoint must beat the previous one in a fixed match set (same seeds, seats swapped) with a margin that is not noise.
  If three cycles in a row bring nothing, stop and report.

### Step 5. Evaluation that cannot be fooled
- A fixed **match set**: seeds, player counts, seats swapped, so every checkpoint plays the same games.
- Yardsticks: the score against the rival at each solo difficulty; win rate against the heuristic bots; **Elo among bots** (the site's Elo code, a separate
  rating that never mixes with the human one); and the win rate against human games' stored results where the seed and the first moves can be compared.
- The solo high score board shows the bot's best scores as a reference line.
- A stronger test with the owner and experienced players: blind games, where a person does not know if the seat is a bot.

### Step 6. Put it on the site
- The bot runs as a service (CPU, a small network in ONNX; search budget set per strength). Strengths: "easy" (an early checkpoint or fewer search
  simulations), "normal", "strong".
- Bot seats are labelled, never rated for humans, and not allowed in rated games (the owner may change this later).
- The Worker times a bot's move and falls back to a fast move if the service is late, so a table never waits.

### Step 7. The loop that learns from the web
- A scheduled job (weekly, or when enough new games exist): build the new dataset, fine-tune or continue self-play, evaluate with the gate of step 5,
  write a candidate checkpoint.
- **Nothing is deployed on its own** (CLAUDE.md rule 7). A passing candidate is reported to the owner with its numbers, and the owner approves putting it
  on the site. A rules change starts a new line of checkpoints (step 0).
- Human games feed the loop in three ways: as extra training data, as the test set, and as the hard cases (positions where the bot and the human
  disagree and the human won).

## 5. Where it lives in the repository

- `services/ai/`: encoding, bots, search, training scripts, evaluation (Python, type hints, tests, `ruff` and `mypy` clean like the engine).
- `services/engine/`: only small additions (the rules version, the observation helpers if they belong with the state). **No learning code and no rule
  changes for the sake of the AI.**
- `apps/worker/`: the bot seat and the decision-record writer. `apps/web/`: the lobby option "add a bot" and the labels.
- `docs/`: this plan, a model card for each released checkpoint (data, rules version, strength, known weaknesses).

## 6. Tests and rules for the AI code

- A bot may only return a move that is in `view.legal`; a test plays thousands of games and checks it.
- A bot never reads anything but its projected view. A test gives it a view and a state whose hidden parts differ and checks that its choice does
  not change (the hidden-information leak test).
- Same seed and same checkpoint give the same game (determinism), so a result can be reproduced.
- The engine stays the only place where rules live. If the bot finds a position that looks wrong, it is reported as a possible rules bug.

## 7. Costs and effort (rough, to be replaced by measured numbers at the gate of step 0)

| Step | Work | Compute |
|---|---|---|
| 0 Foundations | large (speed and encoding) | none |
| 1 Heuristic bots, bot seat | medium | none |
| 2 Data pipeline | medium | small (GCS) |
| 3 Imitation | medium | one GPU for hours |
| 4 Self-play | the long part, many cycles | a GPU and many CPU cores for days; this is where the money goes |
| 5 Evaluation | medium, then steady | CPU |
| 6 On the site | medium | one small service (CPU) |
| 7 Loop | small once the rest exists | the cost of step 4, repeated |

The honest expectation: a bot that plays sensibly and beats the solo rival is reachable (steps 0 to 3, maybe 4). A bot that beats strong human players of this
game needs the whole of step 4 and a lot of compute, and may not be reached. The gates exist to find that out early and cheaply.

## 8. What the owner decides

1. **Purpose and scope**: opponent first (recommended), then the benchmark and the balance analysis. Base game, solo and 2 players first; the expansion later.
2. **Compute budget** and where training runs (a local GPU machine, or rented cloud GPUs), and a monthly limit.
3. **Consent**: how the site tells players that games may be used to build the bot (a line at signup and on the game over panel), whether it is opt-out, and
   whether guests' games are used.
4. **Bots at the table**: labelled and unrated (recommended); allowed in rated games or not; bot names.
5. **Release rule**: a new checkpoint goes live only after the owner approves it (recommended) and after the gate numbers are shown.
6. **Rules freeze**: the training uses one rules version at a time. Changes to rules or cards start a new line, so a short freeze before each long
   training run is needed.
7. **Stack**: PyTorch and ONNX (recommended) against a simpler tree-search-only bot with no neural network.

## 9. First actions if this plan is approved

1. Add the rules version to the engine and the archives, and measure the engine's speed in-process (step 0).
2. Write the observation and action encoding with its tests.
3. Build Bot 0 and Bot 1 and a small tool that plays N games between two bots and reports wins, scores and time.
4. Report the numbers to the owner. They decide whether steps 2 to 4 are affordable.

## 10. Decisions of the owner so far (2026-10-20) and where the work stands

- **Offline bots for training only.** Random, greedy and heuristic bots exist in `services/ai/src/seti_ai/bots.py`. They are not part of the website.
- **The objective is the agent's own final score**, starting with 2-player games (base game). The reward of a decision is the score its seat gains until
  its next decision; the sum is the seat's own final score (`train.py`).
- **Training happens on the owner's computer** (Windows, 12 cores, an RTX 3060). Nothing is trained in the cloud. `services/ai/run_training.sh` starts a run:
  first a copy of the heuristic bot (behaviour cloning), then self-play with PPO, saving a numbered version when it improves.
- **Only a versioned model is deployed**, and only after the owner approves it. Each version is a folder `models/vNNN/` with the weights and a manifest
  (`registry.py`). `models/` is not in git.
- **The statistics of every version are public.** `seti_ai.publish` writes the manifests of the versions to the table `bot_versions` of the site's database
  (migration 0007) and the page `/bots` ("AI" in the menu) shows them to everybody: the final scores and the win rate against each training bot, how
  the version was trained, which rules version, and which version (if any) is served to players.
- Not built yet: the service that serves a version to a bot seat at a table, the data pipeline from human games, the search (step 4 of the plan).

## 11. The network and its features (decided 2026-10-20, replaces the first version)

**The rule for the features.** Everything that a player sees, the agent sees; nothing that a player cannot see. The agent is given the projected view of the
seat to act (`project(state, seat)`), whole: `features.py` walks every field of it, so a new field of the engine is seen at once and nothing is chosen by
hand. The hidden parts arrive as `"?"` (the deck, the other hand, face-down tiles, an undiscovered species), so only their count is seen. The check is in
`tests/test_features.py` (changing the deck order, the other hand, the hidden tiles or an undiscovered species changes nothing) and the list of what is seen
is generated by `seti_ai.visible_info` into `docs/ai-visible-info.md`. The check found one leak that is fixed in the engine: the face-down board of an
undiscovered species had the number of spaces of its species (a face-down Mascamite board has 4 spaces on a color, the others 5).

**What is excluded** (`features.EXCLUDED`): the seed, the random generator, the undo data, the gain bookkeeping and the text log (not information about the
game), the final scores (they only exist at the end) and the lists that are encoded another way (the legal moves, their notes, the reach of the probes, the
previews of the rotations).

**Seats are relative.** The seat to act is player 0 and the others follow in turn order, so that both seats of a game look the same to the network.

**Entities are tokens.** The view is cut into entities: each player, sector, planet, probe, tech stack, gold tile, species (and each part of its per-species
state), pending decision, tracker, the solo rival and objectives, and each card in front of a seat or in the card row (the card's name and where it lies);
the rest of the game is one token. A token is the sum of the learned vectors of its features (a feature is a path in the view and its value, hashed into
32768 slots). A game position is about 50 to 70 tokens.

**The network** (`agent.py`), after ZeusAI (Paolini et al., "Learning to Play 7 Wonders Duel Without Human Supervision", arXiv 2406.00741): a transformer
encoder over the entity tokens, with learned embeddings for each component and no encoded rules (costs and effects are learned from play). Our changes:
- the policy is over the legal moves: each move (its tokens, the engine's note of its cost and rewards, its numbers) is a query that attends to the position
  and to the other moves (a small decoder), and gets one score; the softmax is over the legal moves only;
- the value head reads a summary token and gives the points the seat will still gain (our objective is the seat's own score, where ZeusAI predicts the
  chance to win).

**Size.** ZeusAI's network has 12 layers, 12 heads, 768 wide and about 92M parameters for 7 Wonders Duel, and it learned from about 420,000 games with a
search of up to 1000 simulations a move. SETI has a much larger state (roughly ten times the entities, species with their own boards, techs, cards with free
actions), so its capacity should be at least that. On this machine (one RTX 3060, 12 cores) the games are the limit, not the size of the network, so there
are three presets of the same network (`PRESETS`):

| Preset | Layers x width x heads | Parameters | Use |
|---|---|---|---|
| small | 4 x 256 x 4 | 14M | tests and quick experiments |
| base | 8 x 512 x 8 | 53M | where training starts |
| large | 12 x 768 x 12 | 144M | ZeusAI's depth and width plus the larger embeddings; when the number of games allows it |

The size is a setting, so the same code trains any of them. A new size starts a new line of versions (weights do not carry over); a larger network can be
trained from the games that the smaller one played.

**What ZeusAI did that we do not do yet.** It trained with AlphaZero-style search: the policy learned to copy the visit counts of a Monte Carlo tree search
at each move (the search is what makes the training signal strong). Ours is policy-gradient self-play (PPO) after a warm start from the heuristic bot (it
started its value head from 35,000 games of rule-based players too). The search is the next big step: it needs a fast, copyable simulator (the engine) and a
way to handle the hidden cards (determinization: sample the cards the seat cannot see). It is step 4 of this plan.

**Lessons that we took from it.** Sparse rewards take very many games to be discovered (its science victory took about 100,000 games): our reward is dense
(the score gained at each decision), and the end-of-game points are added to the last decision. Stalling must not pay: games have a step limit and an
unfinished game is penalised (our first run learned to play longer and longer games, up to 244,000 decisions in 96 games, with the score falling). The
move that only takes back (undo) is not offered to the agent.
