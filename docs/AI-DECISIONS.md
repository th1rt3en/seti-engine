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

Built: 2 players, base game, no expansion, no solo, no promo cards, any species (random). Other scopes need their own features (organizations, new species) and
their own runs: the expansion and 3 to 4 players change the game a lot. Recommendation: finish 2 players first, as you asked.

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
