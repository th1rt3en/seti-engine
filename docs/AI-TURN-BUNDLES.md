# The turn as the unit of the AI: bundling micro actions (design, for the owner's approval)

Status: **a proposal, nothing built.** Training is stopped and all saved models are deleted (`docs/AI-DECISIONS.md`, 2026-10-21). Training does not resume until
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

The AI must not hold rules (CLAUDE.md, rule 5). So the engine gets one small addition, with tests: every legal move has a **class**: `free`, `main`, `answer` or
`end`. The engine already knows it (it builds the moves from separate lists); it only has to say it. It is sent next to `legal` in the view, as a list of the same
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

1. **Setup** (organization, quick start cards): one bundle per decision, outside the turns (they do not change the points).
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
3. Stage A first or stage B first (see also section 5b: the neighbour search of stage B is what finds long bundles)? A changes only how the model is *trained* (it plays as now, but it is told how good each turn was, instead of each micro move). B changes
   how it *plays* (at the start of a turn it plays out several candidate turns on copies of the game and picks the best), which is slower, and which needs a good value
   per turn to choose with, and that is what A produces. Recommendation: A first. **Open.**
4. Is the engine addition in section 4 (the class of each move, in the view) acceptable? **Open.**
5. Anything in section 6 to change? **Open.**
