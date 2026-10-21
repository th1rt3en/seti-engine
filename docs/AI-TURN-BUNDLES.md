# The turn as the unit of the AI: bundling micro actions (design, for the owner's approval)

Status: **decisions 1 to 5 are answered (section 8); the engine labels (section 4) are built and tested; the cutting of games into bundles and everything after is
not.** Training is stopped and all saved models are deleted (`docs/AI-DECISIONS.md`, 2026-10-21). Training does not resume until
this is built and the owner has approved it.

## 1. The problem

Today one *step* of the model is one decision of the engine: one `place_data`, one `discard_free`, one `move_probe` space, one `tuck`. A player makes about
80 to 120 of them in a game. The reward of a step is the points gained before the next step, so most steps get 0. The points of a plan that takes several
moves (data into the computer, then `analyze`, then a trace) have to be carried back over many steps. After 10 rounds of self-play the large network was still
at about 92 points (37% of the 250 that an advanced player scores) and lost 40% of its games against v008.

## 2. The turn, as the engine already has it

The engine already tells the parts of a turn apart (`services/engine/src/seti_engine/engine.py`):

| Part | In the engine | Examples |
|---|---|---|
| free action | `_free_moves` | `place_data`, `exchange`, `move_energy`, `discard_free` (the corner of a card), `tuck`, `buy_card`, `complete_mission`, `org_free` |
| main action | `_main_moves`, once a turn (`state.main_done`) | `launch`, `scan`, `analyze`, `research`, `orbit`, `land`, `play_card`, `pass` |
| answer | `_decision_moves`, the decisions a move asks (`state.pending`) | which tech, which trace colour, which sector, where a probe goes, which gold tile |
| end | `end_turn` (a `pass` ends the turn by itself) | |

A turn is: **free actions, the main action (with the answers it asks for), free actions, end of the turn.** Rule FREE-00 lets a free action interrupt the answers
of a main action, so the free actions of a turn are not always cleanly before or after the main action. A turn ends when the turn passes to the other seat.
The decisions of setup (organization, quick start cards), the choice of the end-of-round card, and the resolution of sectors and milestones after a main
action are answers or steps of their own and are described in section 6.

## 3. What a bundle is

> A **bundle** is everything one seat does from the moment it is to act until the turn passes to the other seat: 0 or more free actions, the main action with
> its answers, 0 or more free actions (including the ones that interrupted the answers), and the end of the turn.

A bundle is the **step of the model**: the unit that is valued, rewarded and compared. A game has about 20 to 25 of them per player (about 4 to 5 rounds of 4 to
5 turns), instead of about 100 micro steps.

## 4. The classification belongs in the engine

The AI must not hold rules (CLAUDE.md, rule 5). So the engine gets one small addition, with tests (built: `engine.legal_classified`, `View.classes`,
`tests/test_move_classes.py`): every legal move has a **class**: `free`, `main`, `answer`, `end`, or `control` (`undo` and the practice-game marker, which are no part
of a turn). The class depends on the situation, not only on the type of the move: `place_data` is a free action in a turn and an answer when a decision of the
engine asks for it. The engine already knows it (it builds the moves from separate lists); it only has to say it. It is sent next to `legal` in the view, as a list of the same
length, like `notes` is today:

```json
"legal":   [{"type": "place_data"}, {"type": "discard_free", "card": "17"}, {"type": "scan"}, {"type": "end_turn"}],
"notes":   [null, {"irreversible": true}, null, null],
"classes": ["free", "free", "main", "end"]
```

The **turn number is already in the view** (`state.round` and `state.turn`: the turn counts +1 for each turn, the rival's included, and starts again in each round), so
nothing is added for that.

`seti_ai` then cuts a game into bundles without knowing any rule: a new bundle begins when the turn (round and turn number) changes. The classes are used to
describe a bundle ("2 free, the main action `analyze`, 1 free") and to check it (at most one main action).

What the addition touches:

- the engine: one function that gives the class of a move, one new field of the view, tests (every move type of `move-types.json` has exactly one class: a type
  without one fails the test);
- the protocol: the JSON schema and the TypeScript types are generated again (one new list, optional for a reader);
- the Worker and the website: nothing changes in what they do (the Worker passes the view through, the website does not read the field); they only get the new type;
- hidden information: nothing, the class of a move depends only on its type;
- old games and replays: nothing, the classes are worked out when a view is made;
- deploy: the field is only added, so the order of deploying does not matter.

## 5. How the model learns with bundles (two stages)

**Stage A: the value, the reward and the advantage are per bundle.** The policy still chooses micro actions one after another (each sees the board as it is after
the one before), so every legal combination stays possible, but the learning signal is per bundle:

- one **value** per bundle, predicted at its start (the value head is read once at the start of the turn);
- one **reward** per bundle: the points the seat gained during it, divided by 20 (the objective stays the own final score);
- one **advantage** per bundle (GAE over the bundles of the seat, about 25 of them instead of about 100 micro steps), shared by all the micro actions of the
  bundle: a good turn raises the probability of everything that was done in it, a bad one lowers it;
- the **probability of a bundle** is the product of the probabilities of its micro actions, and the PPO ratio is taken over the whole bundle, so the update
  cannot change one micro action a lot to chase a bundle's reward.

**Stage B: bundles are searched and compared.** At the start of a turn the bot proposes K bundles by playing the turn on copies of the game with the
policy (chance events drawn again), evaluates each by `points gained + value at the next own turn start`, and plays the best. The best bundle (and how it
compared to the others) becomes a training target for the micro actions in it. This is the search that `seti_ai/netsearch.py` does for the rest of one turn today,
but with whole bundles and in training. It is built only after stage A works.

## 5b. The problem of long bundles, and what is done about it

With micro actions chosen one at a time the probability of a bundle is the product of the probabilities of its moves, so **a bundle with many micro actions is
sampled less often than a short one**: to find "place 3 data, discard 2 corners, scan, place 1 more data" by chance the policy has to make every one of those
choices in a row. Stage A alone does not fix this: it tells the model well how good a bundle was *once it has been played*; it does not make long bundles be played.
A second pull in the same direction: after the main action the policy can end the turn at any micro step, and a policy that ends early only produces short bundles.

What is done about it:

1. **The copy stage and the first rounds** start the network from games that contain long bundles (a bot that does all its free actions), so they are in its
   distribution from the start.
2. **Search finds what sampling does not** (this is stage B, and it is the real answer): the candidate bundles of a turn are not only sampled, they are *built*:
   take a sampled bundle and try its neighbours (insert one more free action the engine offers, remove one, move one to the other side of the main action),
   evaluate each neighbour (points gained plus the value at the next own turn), keep the best. A longer bundle that is better is found even if the policy
   would almost never have sampled it, and **it becomes the training target** (the policy learns to play it): this is the way AlphaZero escapes the same problem.
3. **Two numbers are logged at every evaluation** so that the problem would be seen: the distribution of the number of micro actions per bundle, and the share of
   turns in which a free action was available at the end of the turn and was not used.

## 6. Cases that need a rule written down (to approve)

1. **Setup:** the choice of the organization and of the quick start cards (and the cards tucked at the start) are **one bundle** for the seat, outside the turns
   (owner's ruling, 2026-10-21).
2. **Passing and the end-of-round card:** the steps of passing (discarding down to 4 cards, rotating the solar system, and **choosing the end-of-round card**) are all
   part of the bundle of the `pass`. (Owner's ruling, 2026-10-21: the card selection is not a bundle of its own.)
3. **Resolving sectors and milestones after the main action** (decisions of the engine's `stage`): part of the bundle of the turn that caused them.
4. **Solo rival's turn:** not trained (2 players first); it only advances the game.
5. **Every bundle has exactly one main action:** the engine offers `end_turn` only after the main action was taken (`pass` is a main action), so a bundle without
   one cannot exist. The check of a bundle (section 7) fails if it has none or two.
6. **Interruption of the answers by a free action:** the free action is in the same bundle, and its own place in the order is kept.

## 7. What is built, and how it is tested (nothing runs on the real games before approval)

- `engine`: the class of each move and the turn number in the view, with tests for every move type (each is exactly one class) and for the turn number.
- `seti_ai/bundles.py`: cuts a game (a list of decisions with the seat and the turn) into bundles; checks them (one main action at most, one seat, the points of the
  bundles add up to the final score of the seat). Tested on the archives of real games (the 289-action solo game, and the offline games of the bots).
- `train.py`: PPO over bundles (stage A); the head-to-head gate (`gate.py`) and the logging of the mean scores against 250 stay as they are.
- Stage B (`seti_ai/bundle_search.py`) after stage A.
- A short offline check before any real run: the cut into bundles of 100 games of the bots, and the sums of rewards against the final scores.

## 8. Decisions for the owner

1. Is the bundle exactly "from the turn passing to a seat until it passes on" (section 3), with the interruptions and the sector resolution inside it (section 6)?
   **Answer (2026-10-21): yes.**
2. Is the reward per bundle the **own** points gained during it (not minus what the opponent gained in the reply)? **Answer: own points only.**
3. Stage A first or stage B first? **Answer: skip A, go straight to B (searching bundles). B is the target.** (Section 5, stage A, is therefore not built on its own;
   the per-bundle value and reward that B needs are built as part of B.)
4. Is the engine addition in section 4 acceptable? **Answer: acceptable, but it has to be tested thoroughly** (done: `tests/test_move_classes.py`, 22 kinds of game, the
   partition of the moves, the rule that a decision, the main action and the end of the turn exclude one another, the interruption by free actions, one main action in
   every finished turn).
5. Anything in section 6 to change? **Answer: the choice of the end-of-round card is part of the pass bundle; the organization and the quick start cards are one
   bundle; everything else in section 6 agreed.**

## 9. The alpha model and learning from the games of people (a proposal, to approve)

The owner's plan (2026-10-21): build an **alpha** model that may be very weak and unable to form long bundles, release it, and play against it; those games are the
training data. The method has to improve a lot from that limited data.

**9.1 What the alpha is.** Not a trained network at first. A *bundle-search bot with the existing hand-made evaluator*: at the start of a turn it builds candidate
bundles (sampled, and the neighbours of the best ones: one free action more, one less, one moved to the other side of the main action) on copies of the game, scores each
with the evaluator (`bots._board_value`: points plus weights for resources and structures, the heuristic bot's), and plays the best bundle. It needs no training, it is
weak (about as good as the heuristic bot, 40 to 60 points, but it plays whole turns), and it is the same machinery as stage B, so the pipeline (candidates,
evaluation, logging of the chosen bundle) is built and tested once. The network takes the evaluator's place later.

**9.2 What is recorded for each game against it** (archive header and actions, as decided earlier): which seats are the bot's, the version of the bot, the version of
the rules, and for every bundle the bot played the candidates and their scores. Human turns are recorded as they are (every micro action, with its class).

**9.3 How the model learns from a limited number of human games** (what the network is trained with, in the order of the value of the data):

1. **Human bundles as examples.** Every turn of a person is a complete bundle, long ones included: the network learns to *produce* them (imitation of the micro actions
   of the bundle, weighted by how well that player did in the game: for example only the games of the better half of the players, or a weight that grows with the
   final score). This is what makes long bundles appear at all, and it needs no search.
2. **The value from the outcomes.** From each position at the start of a human turn the network learns the points that the seat gained from there to the end of
   the game (one label per bundle start: about 25 per player per game, from the games of people and of the bots).
3. **Search on the human positions (expert iteration).** From the start of every human turn the bundle search runs with the current value and finds bundles that are
   better than the one that was played (or confirms it); the better bundle is a new training example. One human game gives hundreds of such positions, realistic
   ones, and this is how a small number of games gives a lot of data.
4. **Games that continue from human positions.** The engine can start a game from any turn of a human game; self-play (the bot against itself, or against the bot)
   continues from there, so the network meets the kind of positions that people reach and not only those of its own play.
5. **Checks that it is working, on games that are not used for training:** how often the network's bundle is the human's (the longer bundles included), the error of the
   value, and the head-to-head gate against the current champion (`gate.py`: 100 games, 55% of the wins, the score against heuristic v3 not lower, the mean scores
   shown against the 250 of an advanced player).

**9.4 What is needed to release the alpha** (each is a piece of work to be built and tested before any release): a bot seat in the lobby (the Worker asks the AI service
when it is the bot's turn, with the clock rules of D24 to D28), the AI service (the candidates are searched on copies of the game, so it needs the engine in the same
process: a small service next to the engine on Cloud Run), the consent warning when a bot is added to a lobby (decided earlier), the bot and its version in the archive
header, `seti_ai.dataset` (copies the new games from the bucket and replays them with the engine of their rules version), the `/bots` page with the released version, and
the approval of the version by the owner.

**9.5 Questions for the owner:** (a) is the alpha as described in 9.1 (a search with the heuristic evaluator, no network) what you want to release first? (b) is the
list in 9.3 the way to learn from the games of people, and should only the better players' games count for the imitation? (c) in what order: the bundles and the search
first (so that the alpha can be played), then the bot seat and the data pipeline, and the network after the first human games?

## 10. The owner's answers to section 9 (2026-10-21) and the plan that follows

**(a) The alpha is a trained network**, very weak, not a search with a hand-made evaluator (section 9.1 is replaced by this). It is trained on the games of the bots
(cut into bundles) so that it plays and can be released; the bundle search of stage B runs on top of it when it plays.

**(b) Learning from the games of people: yes, with these rules for a game of a person against the model:**
- a game that **the model lost** counts, with **more weight**: the bundles of the person (who won) are examples to imitate, and the positions of both seats give
  the value labels;
- a game that **the model won** is **skipped**: nothing is learned from it.

A caution that I will keep in the design (not a change of the rule): if the value is learned only from lost games it becomes pessimistic about every position. The
games of the bots against each other (and the model against the bots) are mixed in with the games of people in every training batch, so that it sees wins as well. The
share of the games of people is a setting.

**(c) The order:** 1) the bundle search; 2) the network is trained (the alpha); 3) while it trains, the model in the lobby and the pipeline of data for the games of
people against the model are built.

### The pieces, in order, and what each needs from the owner

| # | Piece | Needs the owner |
|---|---|---|
| 1 | Bundle search (`seti_ai/bundle_search.py`): candidate bundles by sampling the micro policy on copies of the game (the hidden cards of the opponent drawn again, chance drawn again), their neighbours (a free action added, removed, or moved to the other side of the main action), each scored by points gained + the value of the position after the bundle; the best one is played. Tests: it finds a better bundle than the sampled ones when the value is known; it never reads the opponent's real hand. | the design above (done) |
| 2 | The network at the level of bundles (the same transformer; the class of each move is a feature; the value is read at the end of the own bundle) and the training (`seti_ai/bundle_train.py`): examples are the bundles chosen by the search, the value labels are the points gained from the end of a bundle to the end of the game, the games of people are weighted as in (b); pause and resume; the head-to-head gate; metrics against 250. Tests on the games of the bots, without training. | **a go before the first training run** (the training stays stopped until then) |
| 3 | The alpha: a short training on the games of the bots, then the gate | the go for the run; the approval of the version |
| 4 | The lobby: a bot seat (the Worker asks the AI service when it is the bot's turn), the AI service, the consent warning, the version in the archive header, the `/bots` page | the approval of the version before it is released |
| 5 | The data pipeline: `seti_ai.dataset` copies the new games from the bucket, replays them with the engine of their rules version and the right random-state encoding, cuts them into bundles, applies the rule (b), and writes the examples | |


## 11. The model in the lobby and the data pipeline (built 2026-10-21)

**Seat.** The host of a lobby adds an AI with the lobby page: they choose a released version and tick that the game is recorded and used to train it. The room
refuses it without that (`consent`), makes the game unrated, and starts the game when the last seat is filled. The seat has the id `bot:<version>:<n>`, no clock
that can run out, and no rating row. Hands and the deck never leave the room unprojected: the AI service gets the seed (it is private and its requests are signed),
and builds the seat's own view.

**Turn.** When the engine waits for an AI seat the room asks the service (`POST /move`: options, the whole log, the seat, the rest of the plan) once at a time and
plays the answer through the normal path (the same checks as for a person). The service plans a whole bundle with the bundle search and returns its first move and
the rest; the room hands the rest back with the next request while the game is where the plan left it, so there is one search per turn. If the service fails the
room asks again every 10 seconds (the alarm). The service is stateless, so any instance can answer.

**Archive.** The header names the seat (`bot: {model}`) and keeps the host's agreement (`consent`: who, when). Nothing in the public replay shows anything new.

**Data.** `seti_ai.dataset` reads the downloaded archive and applies the rule of section 10(b). A game with a model seat and no `consent`, a game not played to the
end, and a game the engine cannot replay any more are skipped and counted. `mix` brings the games of people into the games of the bots by share (repeating them up
to 20 times each), as section 10(b) asks, so the value does not become pessimistic. Training with them is `bundle_train alpha --people DIR --people-share 0.3`, and
waits for the owner's go like every training.

**Open for the owner.** What the rules version of a game is (the header has no rules version; a game the current engine cannot replay is skipped); whether the
games of the lowest-rated people should count at all (now every completed game counts); the search settings of the service (`SETI_SEARCH`).
