# Tree search over turns (MCTS) for the AI: design, for the owner's approval

Status: a proposal. Nothing here is built and no training starts from it (rule: training needs the owner's explicit go, `docs/AI-DECISIONS.md`). It continues section 6
of `docs/AI-DECISIONS.md` ("Tree search (MCTS): not built") for the turn-level model of `docs/AI-TURN-BUNDLES.md`. Written 2026-10-26.

## 1. Where we are, measured

What plays today (`services/ai/src/seti_ai/bundle_search.py`, used in training, in the gate and in the lobby bot):

- at the start of a turn it builds up to about 30 **candidate bundles** (a whole turn each, usually 15 to 25): one greedy and 6 sampled rollouts of the policy on one determinized copy of
  the game, plus up to 24 neighbours (a free action added, removed or moved to the other side of the main action) of the best 2 samples, plus, for a human game,
  the turn the person played;
- each candidate is scored **points gained in the bundle + the network's value of the position after it**; the best 4 are scored again on 3 determinized copies
  (the opponent's hidden cards and the deck order drawn again from what the seat has not seen); the best is played;
- there is **no tree and no opponent reply**: the opponent's move, and everything after the end of the turn, is in the value and nowhere else.

Costs on this PC (from `metrics.jsonl`, iterations 17 to 26): **about 2.4 seconds per search** (a self-play game of about 33 searches takes about 80 s with the GPU), so
a search is up to about 30 candidates (at most 1 + 6 + 24, and the offered ones), so about 0.1 s each. My reading, to be confirmed by profiling at the start of Step 0 (not yet
measured): the time is not the engine (a micro move is about 1 ms) but **one network call per micro move of each rollout, with a batch of 1** (a bundle is 10 to 40 micro
moves, each asking the policy), so the GPU waits between the calls.

What the value is trained to say (`bundle_data.py`): the points that the seat itself gains from the position to the end of the game, from what really happened in the
games that were played (self-play at 45 to 55 points a game, and human games). It does not know the opponent's score or who wins.

Why this limits us (measured in the last 10 iterations): the policy is pulled toward the search's choice, the search trusts the value, and the value error is 4 to 6
points, as large as the gap between two candidates; 10 iterations of the loop did not beat v003 (gate wins 10 to 50%, mean about 33%, `metrics.jsonl`).

## 2. What to build, in four steps, each measured before the next

The principle: **each step is judged by games between the new bot and the current one at the same time per move** (not the same number of simulations), 100 games with the
seats swapped and the same seeds, and the numbers go in this document before the next step starts. A step that does not win is dropped.

### Step 0: make the search fast (no change of what it decides)

Run the rollouts of one search **in lockstep**: all the candidates (and all the determinized copies) advance one micro move together, and the network is called once for the
whole batch. Same candidates, same scores, same result for a given seed (a test: the batched search returns exactly the bundles of the sequential one).

Expected: 10 to 30 times faster (a batch of 64 costs about the same as a batch of 1 on the GPU). It is worth doing alone: self-play and the gate get faster, and the lobby
bot too. Measure: seconds per search, and the identical result.

### Step 1: the opponent's reply (depth 2)

For each of the 4 finalists, after the bundle, let the opponent play its turn with a small search (the same code, 6 candidates, no neighbours), on the same determinized copy,
and score the finalist **from the position after the opponent's reply**. Cost: about 4 times a search, which Step 0 pays for.

Measure: against the bot of Step 0. If this alone wins, we know that the missing opponent reply is part of the plateau.

### Step 2: the tree (PUCT over bundles)

- **Node**: the game at the start of a seat's turn, on one determinized world. **Edge**: a candidate bundle from the generator of section 1, at most 6 per node at first (1 greedy
  + 5 sampled; neighbours only for the best at the root), more added as the node is visited (progressive widening). **Leaf**: value of the network, from the point of view of
  the seat that is to act, passed up with the sign changed for the other seat.
- **Prior of an edge**: the softmax of the policy's log probability of its moves (the sum over the micro moves), normalised over the node's candidates.
- **Selection**: PUCT, `Q + c * P * sqrt(N) / (1 + n)`, `c` about 1.5 (to tune on a few seeds).
- **Hidden information**: **root determinization with an ensemble** (the "root-parallel" form of information-set search): 4 determinized worlds, each with its own tree and
  a quarter of the budget, the visit counts added at the root. Simple, batched, and it covers the hidden cards the way the present search does. Known weakness (strategy
  fusion: a world acts as if it knew its cards) is accepted for now, and written down.
- **Chance**: the random state of the engine is re-drawn at each edge when it is first expanded, so the tree is not built on one lucky draw (afterstate sampling with one
  child per visit, as in ZeusAI, kept simple).
- **Budget**: a number of simulations per turn from 50 to 200, chosen by time. Every expansion is a batch of candidate rollouts, so the cost is dominated by the same
  batched network calls as Step 0. Estimate after Step 0: 50 simulations about 2 to 5 s a turn on the GPU (to be measured, not promised).
- **The bot is played from the visit counts** (the most visited bundle at the root).

Measure: against Step 1 at equal time per move, with the budget as a variable (50, 100, 200).

### Step 3: train on the tree (AlphaZero style), only if Step 2 wins

The policy is trained toward the root visit counts, the value toward the result. The old rule stays: **no human move is imitated**; human positions are searched with the
person's turn as one more candidate, and the policy learns the best bundle found.

## 3. The value, and how a position is judged

Today: own points still to come. Proposed: add a second head, trained on the same positions:

- **score difference**: (own final total − the other seat's final total), scaled; it makes the tree play for a win and deny the opponent, and it is smoother than a win/loss
  flag (an estimate of the chance to win is then a function of it);
- keep the own-points head, so the two can be compared and the step 2 search can use either. Choose by games, not by argument.

Both targets come from positions already in the data (the final totals of both seats are known for every finished game); no new games are needed to try it. A value that is
better calibrated is also the cheapest possible improvement of the present search, so this can be tried first, at Step 0.

## 4. Evaluation (what the gate must say)

- The random and greedy bots are gone from the evaluation (2026-10-26). The yardstick is the heuristic bot v3 and the champion.
- A 10-game gate has a standard error of about 16 points of win rate: the last 10 gates (10 to 50%) cannot tell a worse network from a lucky one. A promotion needs a result
  that a 100-game match (seats swapped, same seeds) supports; with Step 0 this is affordable. A sequential test that stops early can save time.
- Human reference: the fraction of the human best-turn positions where the search finds the person's turn or better (`expert.py` already measures the margin).

## 5. Serving

The lobby bot (`lobby.py`) plays with the bundle search on a 1 CPU, 1 GiB Cloud Run service with an 8-bit copy of the network. Step 0's lockstep batching helps a CPU as well
(matrix products instead of many small ones) but a tree of 50+ simulations will probably not fit that service's time per move. So: Steps 1 to 3 are first for training and
for measuring; what is served changes only after a measurement of the time per move on the service, and the Cloud Run size is not touched without the owner's permission.

## 6. Risks

- **A tree amplifies the value.** With a value that is wrong in the same direction as the policy, more search can make play worse. The score-difference head and the games of
  people (not produced by the network) are the guards; Step 1 is the cheap test of whether the problem is the horizon or the value.
- **Strategy fusion** of the determinized worlds (above).
- **Time**: the estimates above are guesses until Step 0 measures the batch cost; each step has a stop.
- **Not covered by the determinization** (as today): the face-down end-of-round cards, the alien species decks, the Exertian hands, the Arkhos and glyph decks.
- **Solo games**: the rival is the engine, with no hidden choice; the search has no opponent node there (only the engine's own rival turn after each bundle).

## 7. What the owner decides

1. The order: Step 0 and the score-difference head first (both change nothing that is served), then Step 1, then Step 2.
2. Whether a long training run may start only after Step 2 has won in games (my recommendation: yes).
3. The value definition to try: score difference first, win chance as the second.
4. The time per move that the lobby bot is allowed on the service (today seconds on a CPU; a measurement is part of Step 0).

## 8. What was built (2026-10-26, on the owner's order "implement MCTS")

Nothing here is trained or served yet; the Alpha service is unchanged (its networks keep the mark of the irreversible moves as an input and the search of one turn).

- **Step 0, batching**: `bundle_search.play_bundle_g` is a process that yields lists of requests (`logits` of a view, `value` of a position) and is sent the answers;
  `drive` runs many processes in lockstep and answers all their requests with one network call (`NetBrain.answer_many`, `LocalNet.evaluate_many`). A test
  (`tests/test_mcts.py`) checks that a batch gives the same bundles as the same processes alone.
- **Steps 1 and 2, the tree**: `mcts.py`. PUCT over bundles in 4 determinized worlds, with the opponent's reply as nodes of the tree (the opponent moves with its own
  policy), a virtual loss so that several simulations of a world run together, the visits added over the worlds at the root, a score-difference value (own score
  plus own value, minus the opponent's score plus the opponent's value: the network is asked once for each seat, no new head is needed). Used by self-play, the gate
  and the lobby bot through `make_search(brain, config)`; `iterate.py --search mcts` (and `--simulations --worlds --leaves --branch`).
- **Not built**: Step 3 (the policy trained toward the visit counts: `SearchResult.visits` has them, the examples still learn the bundle that was played), a value
  head for the score difference (the two value calls stand in for it).
- **What the measurements said** (a new medium network, one game position at a time; `services/ai/src/seti_ai/iter_benchmark.py`): the search is CPU work. The old
  search took 2.6 s on average (0.4 to 3.9 s); the tree took 5.4 s (16 simulations), 8.6 s (32) and 19.9 s (48 simulations, 4 worlds, 6 bundles a node). The time is
  not in the network (about 15%): it is the views (the encoding of each view takes 5 ms, the mark of the irreversible moves 15 ms of a view of 62 moves, 95% of the time of a
  view before the next point) and the copies of the engine state. So:
  1. the mark of the irreversible moves is **left out of the views of the Beta networks** (`NetConfig.irreversible=False`, `views.py`): a view then takes 0.5 ms instead of
     up to 23 ms. The older networks keep it, because it is one of their inputs. Decision for the owner: the mark is a hint about hidden draws; a network that has to find
     out for itself from the moves' own descriptions is the cost of 10 times faster searches.
  2. games are played in several processes (`parallel.py`, `--workers`), one core each.
