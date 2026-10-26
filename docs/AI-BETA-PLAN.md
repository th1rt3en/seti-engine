# Beta lineage: the training plan (2026-10-26, for the owner's approval)

Status: a plan. **Nothing was trained.** The only runs were short measurements with a new network that was thrown away (`python -m seti_ai.iter_benchmark`), which wrote
no checkpoint, buffer or version. Training starts only with the owner's explicit go (`docs/AI-DECISIONS.md`).

The Beta line is a **new network** (the `medium` preset, 30.1M parameters: 384 wide, 6 layers, 6 heads, 1536 feed-forward, 2 move layers), trained from nothing with the
tree search of `docs/AI-MCTS.md` (Steps 0 to 2, built). Alpha (v003, the 144M `large` network, one-turn search) stays as it is.

## 1. What was built for it

| Piece | Where | What it does |
|---|---|---|
| `medium` preset | `agent.py` | 30M parameters (small 14M, base 53M). A batch of 64: update 51 ms, answer 14 ms, 1.1 GB of GPU memory (RTX 3060). |
| Tree search | `mcts.py` | PUCT over bundles in 4 determinized worlds, the opponent's reply inside the tree, a score-difference value, virtual loss, batched network calls. `iterate.py --search mcts`. |
| Batching | `bundle_search.drive`, `NetBrain.answer_many`, `LocalNet.evaluate_many` | Many requests of the search answered with one network call. Tested: the same bundles as one by one. |
| Views without the irreversible mark | `views.py`, `NetConfig.irreversible=False` for `medium` | See section 2. |
| Parallel games | `parallel.py`, `iterate.py --workers N` | Self-play and gate games in N processes. |
| Benchmark | `iter_benchmark.py` | Times games and one pass of training, and plans an iteration. |

Not built: Step 3 of the design (the policy trained toward the visit counts: `SearchResult.visits` has them, the examples still learn the bundle that was played) and a
separate score-difference value head (the tree asks the value head once for each seat instead).

## 2. What the measurements said, and the one change they forced

The search is **CPU work**, not network work: in a profile of one tree search the network is about 15% of the time. The rest is the engine and the views.

- A view of a position costs up to 23 ms, and 95% of that is the mark `irreversible` of the legal moves (found by trying every move on a copy of the game; it is
  the warning of the page about moves that cannot be taken back). Without it a view takes 0.5 ms. The tree search makes thousands of views for a turn.
- **Decision for the owner: the Beta networks are made without that mark** (`NetConfig.irreversible=False`; a flag in the network's file, so Alpha and the lobby are
  unchanged). The mark is a hint about hidden draws that a network can learn from the moves' own descriptions. The alternative is a search 10 times slower.
- The search time per turn, one process, medium network (5 positions): the old search 2.6 s (0.4 to 3.9); tree 16 simulations 5.4 s; 32 simulations 8.6 s; 48 simulations
  (the default of `MCTSConfig`) 19.9 s. The budget for training is **32 simulations, 4 worlds, 4 leaves, 5 bundles a node**, with 8 worker processes.

## 3. One iteration, measured and estimated

Measured (medium network, 8 workers, the budget above, 8 self-play games, a new network): **242 s for 8 games = 30 s of wall time a game**, 131 searches (1.85 s each
over all the workers). Those games were short (16 searches, 85 steps), because a new network passes early; a trained network plays about 25 to 33 searches a game, so the
plan uses **50 s a game**. Training: **3.85 ms an example** (one pass over 645 examples took 2.5 s).

| Part of an iteration | Estimate | Based on |
|---|---|---|
| Self-play, 24 games (a quarter against the heuristic bot) | 20 min | 50 s a game |
| Training, 2 epochs over the buffer (about 20,000 examples) | 3 min | 3.85 ms an example |
| Network alone against the heuristic bot, 6 games | 2 min | not measured |
| Gate, 20 games against the champion, both with the tree (the owner: at least 20) | 20 min | three waves of 8 workers (8, 8, 4), about 400 s a game |
| **An iteration** | **about 45 min** | about 32 a day |

Not in the estimate: the search at positions of people (`--human-positions`) runs in one process, about 8 s a position: 200 positions would add 27 minutes, so the plan
uses 0 and takes the **value of the positions of the games of people without a search** (`--people`), which costs nothing.

## 4. The numbers to choose

- **Buffer: the last 6 iterations** (144 games, about 20,000 examples, about 3 hours of play, about 0.5 GB of RAM as the pickled buffers of the last run were
  85 MB each). A larger window keeps value targets that were made by a much weaker network; a smaller one forgets too fast. The first iterations have a shorter buffer.
- **Epochs 2, batch 64, learning rate 1e-4** (as the last run).
- **Total: 40 iterations, about 30 hours**, in three stages with a stop after each (the run saves a checkpoint at every iteration and pauses at the end of one):
  1. **Iterations 1 to 12 (about 9 hours).** Question: does it learn? Look at the value error (it must fall under 8 points; the last run stood at 4 to 6 with a network almost 5 times larger and 13 iterations of data), the share of its own searched move that the policy picks, and the score against the heuristic bot.
  2. **Iteration 12: the match that decides whether the tree is worth it.** 20 games (seats swapped), the same network with the tree search and with the old search at the same
     time per move. A tree that does not win here is dropped and the run goes on with the old search (`--search bundle`) at no loss.
  3. **Iterations 13 to 40.** At the end a 40-game match against Alpha (both at the time per move that the lobby allows), the evidence for a promotion to the lobby. A promotion
     also needs a measurement of the time per move on the 1 CPU, 1 GiB service (the 8-bit copy, `slim.py`): a tree of 32 simulations will not fit there; the lobby would use a
     much smaller budget or the old search.
- **Stop earlier** if the gate promotes nothing in 10 iterations in a row and the value error does not fall. **Go on to 60** only if the curve is still rising at 40.

## 5. The command (not run)

```
cd services/ai
python -m uv run python -m seti_ai.iterate run --owner-approved --preset medium --models models_beta --start models_alpha/v002 \
  --people <the downloaded archive of games> --human-positions 0 --search mcts --simulations 32 --worlds 4 --leaves 4 --branch 5 \
  --workers 8 --selfplay-games 24 --epochs 2 --batch 64 --lr 1e-4 --buffer 6 --gate-games 20 --eval-games 6 --iterations 40 --seed 11
```

`--start` is only the first champion of the gate (the old small v002, which any early Beta network beats). Pause with `python -m seti_ai.iterate pause --models models_beta`;
go on with `--resume`. Resident cost: 8 workers each hold a copy of the network on the GPU (about 0.5 GB each of the 12 GB) and a core each of the 12; the PC is busy while it runs.

## 6. Decisions for the owner

1. **A go** for the run above (or for Stage 1 only, iterations 1 to 12).
2. **The irreversible mark left out of the Beta views** (section 2): yes or no. No means about 10 times fewer searches in the same time.
3. **The budget**: 32 simulations a turn and 8 workers (about 45 minutes an iteration with a gate of 20 games), or a smaller tree for a faster look (16 simulations, about 30 minutes).
4. **The people's games**: their value positions in the training (cost-free, included above), and whether to pay for the search at their positions later (needs a parallel version).
5. The champion of the gate: v002 (cheap, weak) or Alpha (a better yardstick but a search 20 s a turn with the mark: a gate of 20 games would take about 4 hours).
