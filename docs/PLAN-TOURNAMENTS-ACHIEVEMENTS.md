# Plan: tournaments and achievements (the next platform upgrade)

Status: **a plan for the owner to approve. Nothing of it is built.** Written 2026-10-24 from the owner's brief. It extends `docs/PLAN.md` and does not contradict it: when the owner approves it, the decisions in section 9 go into the decision log (D41 and D42) and the open questions in section 8 are answered first (hard rule 3: an unclear rule means stop, not a guess).

Two features that share one piece of ground: both are built on the result of a finished game (D24, D37) and both add pages to the player's profile.

- **Tournaments**: a registered player creates a tournament; registered players join; the system makes the tables, plays the rounds and ranks the players. All games are rated and turn-based.
- **Achievements**: a curated list of badges that a player earns from their rating and from tournaments, announced by a pop-up when the game that earned one ends, and searchable in the game history of the profile.

---

## 1. What the owner asked for (the brief, kept as the source)

### Tournaments
- A registered player can create tournaments. At most **5** of their tournaments can be in registration or in progress; to make another they wait for one to conclude, or cancel one that is still in registration.
- **All tournament games are rated.**
- **All tournament games are turn based.** The creator chooses the time control. A player who times out can be kicked as usual (D24).
- A player who is **kicked from a tournament game is disqualified** for the rest of the tournament. Every game they still have scheduled counts as lost, and the remaining players of those games are the winners.
- Formats:
  1. **Single elimination**: participants are paired at random; the winner(s) go on, the losers are out.
  2. **Swiss system**: players play up to *x* matches (the creator sets *x*, from 2 to 8). A match gives points by placement: 4 players +6 / +4 / +2 / 0 for 1st / 2nd / 3rd / 4th; 3 players +4 / +2 / 0; 2 players +2 / 0. After every round the players are shuffled into the next matches by their points (players of similar strength together). A switch at creation tries not to pair the same players again.
  3. **Round robin**: details to be given.
  4. **Group stage**: details to be given.

### Achievements
- A curated list of achievements that a player earns from their performance in tournaments or from their rating.
- Each has a **badge** shown in the player's profile (placeholder pictures for now).
- They are tracked automatically and given **at once, after the game in which they were earned, by a pop-up**.
- A game that unlocked an achievement has a **special icon** (a generated placeholder) in the game history of the profile. The game history gets **filters**: opponent name, alien species, achievement unlocked, minimum score.

---

## 2. How it fits what exists

| Existing | What the new work does with it |
|---|---|
| Rated games, Elo, floor 100 (D15, D37, `apps/worker/src/core/elo.ts`, `ratings.ts`) | Tournament games are ordinary rated games: no second rating. Achievements read the rating before and after. |
| Kick, timeout, 2-player loss on timeout (D24) | Unchanged. A kick in a tournament game also disqualifies (section 3.4). |
| Turn-based clocks (D34: slow 4 d + 12 h, normal 3 d + 9 h, fast 2 d + 6 h per turn) | The creator picks one of the three; "no clock" and the real-time speeds are not offered. |
| Open-table limit (guest 1, account 10; built 2026-10-24) | Needs a rule for tournament games (open question Q3). |
| Game rooms (`GameRoom` Durable Object, lobby, host starts the game) | A tournament game is created by the system with its seats fixed and starts by itself, without a lobby. |
| Result sink in D1 (`recordEnd`, `rating_history`, `game_stats`) | The place where tournament results and achievements are computed, in the same D1 batch as the ratings. |
| Numbers in addresses (D38) | Tournaments get a number too: `/tournaments/12`. |
| Archive (D25) | Unchanged; each tournament game is archived like any other and gets its tournament number in the header. |
| Profile page, game history, filter forms (`FilterForm`) | Extended with the badges, the unlock icon and the filters. |
| Engine | **Not touched.** Tournament pairing and standings are platform logic, not game rules (rule 5 is about the rules of SETI). They still follow rule 4 in spirit: the pairing code is pure and takes its randomness from a stored seed, so a tournament can be replayed and tested. |

---

## 3. Tournaments

### 3.1 Lifecycle

```
registration --(creator starts, or the deadline passes with enough players)--> in progress --(last game done)--> concluded
registration --(creator cancels)--> cancelled
in progress  --(administrator cancels)--> cancelled        (nobody's rating changes for games not played; the games played stay rated)
```

- **Who**: a registered player creates, and only registered players join (a rated game needs registered players, D15). Guests can watch.
- **Settings at creation**: name; format; players per match (2, 3 or 4); the size limits (minimum 2 matches' worth of players, maximum to be decided, Q5); the turn-based speed; whether the Space Agencies expansion and organizations are on (the same options as a table, fixed for every game of the tournament); the registration deadline (optional); format settings (rounds *x* for Swiss, the rematch switch, how many advance).
- **Limit**: at most 5 tournaments per creator in registration or in progress. At 5, creating another is refused with a message that names the limit and says what to do (wait for one to conclude, or cancel one that is in registration). A tournament that is cancelled or concluded no longer counts.
- **Registration**: join and leave freely. The creator starts it by hand once the minimum is reached; if there is a deadline, it starts then (or is cancelled if there are too few).
- **After the start**: nobody joins. A player can withdraw; a withdrawal is treated like a disqualification (3.4) because the games they have are forfeited.
- **Cancel**: the creator can cancel only in registration. An administrator can cancel at any time (the existing admin page gets a section).

### 3.2 Games of a tournament

- The system creates each table: the seats are the players of the match, the options and the clock are the tournament's, `rated` is always true, and the game starts at once (no lobby, no start button). The seats are drawn by the existing seating rule (D28).
- The table is announced to its players: a "Your tournament games" panel on the site and the existing "ting" when it is their turn (D34). No e-mail (D34 stands).
- A game result (placement of every seat, with the existing tie rules) is sent by the game room to the tournament, which updates the standings and, when a round is complete, makes the next tables. The call is idempotent and retried (the same pattern as the archive writes).
- A game that an administrator cancels is a game with no result; what the tournament does with it is Q6.

### 3.3 Formats

All formats implement one small interface so that the two to come (round robin, group stage) are added without touching the rest: `start(players, settings, seed) -> state`, `matchesToPlay(state) -> matches`, `record(state, match, placements) -> state`, `standings(state)`, `isOver(state)`. They live in `apps/worker/src/core/tournament/` as pure functions with tests.

**Single elimination**
- Round 1: players are shuffled with the tournament seed and cut into matches of the chosen size. When the number of players does not fit, **byes** go to the players drawn last (a bye advances without a game; the bye is chosen before the draw so nobody gets two).
- A match with 2 players: the winner advances. A match with 3 or 4 players: the creator sets how many advance (default 1; with 4 players, 2 is the other useful choice). The number advancing must keep the bracket sound (Q7).
- Rounds continue until one match is left; its winner wins the tournament; the others are ranked by the round they left in and then by their score in it.
- A match starts as soon as its feeder matches are done (no waiting for the whole round), because turn-based games last days.
- Ties in a match are the open question Q8.

**Swiss**
- *x* rounds, 2 to 8. In every round every player plays one match (bye if the players do not fill the tables).
- Points by placement (the owner's table): 4 players +6/+4/+2/0, 3 players +4/+2/0, 2 players +2/0. The tables of a tournament have one size, so one row of this table applies to it.
- Round 1: random. Later rounds: players are sorted by points; players with equal points are shuffled; consecutive players are cut into matches of the chosen size, so similar strength meets.
- **Avoid rematches** (a switch at creation, default on): the pairing tries to avoid putting together players who have already met. It is best effort: it searches for a pairing with the fewest repeated meetings (a bounded search with the seeded shuffle), and it never leaves a round unplayed because of it.
- A round ends when all its games are done, then the next round's tables are made at once. (This is the cost of Swiss: one slow game holds the round. Turn-based clocks plus the kick keep it moving; section 7 lists the other safeguards.)
- Final ranking: points, then the sum of the points of the opponents met (a Buchholz-like tie-break), then the total game score, then the rating at the start. The tie-breaks are open question Q9.

**Round robin** and **group stage**: details to come from the owner. The plan makes room for them: the interface above, a `format` column, a free-form `settings` JSON, and standings that are not tied to one table size. They will be added as their own phase once described (they may need: points rules, how groups are drawn, how many advance, a play-off).

### 3.4 Disqualification

- A kick in a tournament game (D24) disqualifies the kicked player from the whole tournament (the owner's rule). In a 2-player game nobody is kicked: the player whose time runs out loses the game (D24, as today); whether that also disqualifies them is Q19.
- Every game they have scheduled or not yet started is lost, and the other players of those matches are the winners (a walkover; the match is recorded without a game, no rating change, because no game was played, Q10). A game they have in progress at that moment ends as D24 says for a kick.
- In Swiss, a disqualified player keeps the points they earned (so the opponents' tie-breaks stay fair) and is marked as out; their later matches are walkovers for the others (the points of a win by walkover are Q11).
- A resignation is not a kick: the player loses that game (as today) and goes on, unless they resign the tournament, which is a withdrawal (3.1).

### 3.5 Data

New D1 tables (migration 0009 onwards; the numbers follow D38):

| Table | Holds |
|---|---|
| `tournaments` | id, number, creator, name, format, settings JSON (players per match, speed, options, rounds, switches), status, seed, created / started / ended times, winner |
| `tournament_players` | tournament, user, status (`active`, `out`, `disqualified`, `withdrawn`), points, seed position, final rank |
| `tournament_matches` | tournament, round, slot, status (`waiting`, `playing`, `done`, `walkover`), game id, the players, the placements |
| `game_tournament` (or a column on `games`) | the game's tournament and match, so the game page, the history and the archive can link back |

The state that decides what happens next (which match feeds which, the current round) is derived from these rows and the seed; there is no hidden state. Transitions are serialized in **one Durable Object per tournament** (`TournamentRoom`): joins, the start, a result arriving, the deadline alarm. It writes the D1 rows at each change (these are checkpoint-sized writes, in line with D6) and creates the game rooms through the existing creation path with the seats fixed. Why a Durable Object and not only D1: two results arriving together must not both advance the same round, and the deadline needs an alarm.

### 3.6 Pages

- `/tournaments`: open tournaments (registration), in progress, concluded; a filter by format and by the creator; "Create a tournament" for registered players (shows how many of the 5 are used).
- `/tournaments/12`: settings, the players, the standings, the bracket or the rounds with every match linking to its game (watch while it is on, replay when it is done), the creator's controls (start, cancel) and a join / leave button.
- "Your tournament games" on the home page and on the lobby page for a player who has games waiting.
- Admin page: list, cancel.
- Profile: the tournaments a player took part in with their rank, and tournament badges (section 4).
- The game page of a tournament game says which tournament, round and match it is.

---

## 4. Achievements

### 4.1 What counts

The owner said: performance in **tournaments** and the **Elo rating**. The plan fixes the two sources and a first list for the owner to curate. These are **examples, not a decision**: the final list is Q12.

| Group | Examples |
|---|---|
| Rating | Reach a rating of 100 / 250 / 500 / 750 / 1000 / 1250 / 1500 (a badge for each level; the highest level reached is the one shown large) |
| Tournament, taking part | Finish a first tournament; finish a Swiss tournament with every round played; play in a tournament of 8, 16, 32 players |
| Tournament, results | Win a match of a tournament; reach the final / the last four; win a tournament (once, three times, in every format); win a Swiss tournament with the maximum points; finish a tournament in the top 10% |
| Tournament, conduct | Play all the games of a tournament without being the one who times out (no kick, no disqualification) |

An achievement is defined in one file (`apps/worker/src/core/achievements/list.ts`) as: an id, a name, a text, a group, the badge, and a pure function that says whether it is earned, given the facts of a finished game (the rating before and after, the tournament and the match, the standings). The same list is shown on every player's profile with the locked ones greyed out.

### 4.2 When it is given

- **After a game that ends**, in the same step that settles the ratings (`finish` in the room, and the D1 batch of `recordEnd`): the facts are checked against the list for every registered player of the game. A new unlock is written once (`achievement_unlocks`: user, achievement, game, time; unique on user + achievement) and the game id stored is the game that earned it.
- **Tournament achievements** that depend on the end of the tournament (win, top ten percent) are checked when the tournament concludes; the game stored is the final game of that player's tournament, so that the history has an icon on a real game.
- **The pop-up**: the `ended` message of the game's WebSocket carries the achievements that this viewer unlocked in the game; the page shows a pop-up (name, badge, text, a link to the profile). A player who was not on the page (the game ended while they were away, which is the normal case on a turn-based clock) sees it the next time they open any page: a `seen` flag on the unlock row, a small request at page load, and a pop-up for each unseen one. Each is shown once.
- **Existing players**: the first deploy computes, from their rating history and finished tournaments, what they would already hold. These are given **without a pop-up** and dated by the game that earned them, so the history icons are right from the start (Q13).
- **Recomputation**: an administrator can recompute a player's achievements after the list changes (an unlock is never removed by recomputation, only added; a removal is an admin action with a note).

### 4.3 Badges

- A badge is a picture file named by the achievement id (`packages/assets` and the provenance manifest, hard rule 8).
- **Placeholders for now**: generated SVGs, one shape and colour per group and a level mark, plus one placeholder icon for "this game unlocked something" in the history. All are listed in `docs/asset-gaps.md` as placeholders to replace.
- The profile shows the unlocked badges first (newest first, with the date and a link to the game that earned each), then the locked ones greyed with how to earn them.

---

## 5. The game history of the profile

### 5.1 The icon

A game row whose game unlocked at least one achievement shows the badge icon next to the game number; hovering or tapping shows which ones (the names), and each links to the badge on the profile.

### 5.2 The filters

A `FilterForm` above the history (a GET form: the address holds the filters, so a filtered view can be linked, and the page does not jump):

| Filter | Meaning | Needs |
|---|---|---|
| **Opponent name** | games in which a player whose name contains the text (any case) sat at the table | already in `game_players` |
| **Alien species** | games in which that species was one of the two in play | the species of each game stored per game (see below) |
| **Achievement unlocked** | only the games that unlocked an achievement; optionally one chosen achievement | `achievement_unlocks.game_id` |
| **Minimum score** | games in which this player scored at least that many points | `game_players.score` |

- The filters combine (all must hold) and the pagination keeps them.
- **The species of each game**: today the species are in the game state and in the statistics counters of the games that ended, not as a plain list. A new table `game_species (game_id, species)` is filled when a game ends (the engine's result already knows which species were discovered, or the two that were in play; to be confirmed against `stats.py`), and **backfilled** for finished games by the existing backfill tool pattern (`tools/engine/backfill_stats.py`: replay each archived game with the engine, read the species). Games that cannot be replayed any more (the skip list) have no species and simply do not match the species filter.
- Indexes: `game_players (user_id, game_id)` exists; add `game_species (species, game_id)` and `achievement_unlocks (user_id, game_id)`.

---

## 6. Work, in phases

Each phase ends with tests, a report in the form CLAUDE.md asks for, and stays behind the owner's review gate for the phase marked with a star.

| Phase | Work | Notes |
|---|---|---|
| **0** | The owner answers section 8 and approves sections 3, 4 and 5; the two decisions are logged (D41, D42) | star: the gate for everything below |
| **1** | Foundations: `game_species` with the backfill; the filters and the history icon slot on the profile (filters work without achievements); the migration; tests | useful on its own |
| **2** | Achievements, rating group: the list file, the unlock table, the check in the result step, the pop-up (live and "unseen"), the profile badge grid, placeholder badges, the retroactive run, the admin recompute | rating achievements need no tournament |
| **3** | Tournament core: the tables, `TournamentRoom`, creation with the limit of 5, registration, start, the game creation with fixed seats, results back from the game room, disqualification, pages, admin cancel | one format at first: single elimination |
| **4** | Swiss (points table, pairing by points, the rematch switch, the tie-breaks) | |
| **5** | Tournament achievements | after 3 and 4 |
| **6** | Round robin and group stage | **blocked until the owner gives the details** |
| 7 | Review: a rules-style review of the pairing and of the disqualification against this document, a load test with many tournaments, the first public tournament as a trial | star |

Order of deploy for every phase that touches the Worker, as before: the engine (if it changed; here it does not), then the D1 migration, then the Worker and the website with the GitHub Action.

### Tests that belong to the work

- Pairing (pure): every player is in exactly one match per round; no player in two; no rematches when the pairing allows it; the same seed gives the same pairing; byes are spread; the bracket of any number of players from 2 to 128 is sound.
- Swiss: points per placement for 2, 3 and 4 players; the ranking and its tie-breaks; a simulation of whole tournaments with random results (the standings add up, every player plays every round).
- Disqualification: a kick in a game removes the player and turns their later matches into walkovers, in elimination and in Swiss.
- The tournament room: two results arriving together; a result arriving twice; the deadline alarm; a restart in the middle (state from D1 is enough).
- Limits: the sixth tournament is refused with the right message; cancelling one in registration frees a place; a concluded one frees a place.
- Achievements: each rule has a test that names the achievement; an achievement is given once; the pop-up data reaches only its owner; the retroactive run gives the same set as the live checks over the same history.
- The history filters: each alone and combined, with pagination.

---

## 7. Risks and how the plan meets them

- **A stuck round** (Swiss and elimination wait for games that last days). The turn-based clock plus the kick (3 and 4 players) and the loss on timeout (2 players) always end a game, and every disqualification turns the rest of that player's games into walkovers. An administrator can also cancel a single game and decide its result (Q6).
- **Many tables for one player**. A player in several tournaments can have many games at once. The open-table limit must not make a tournament unplayable (Q3).
- **Gaming the rating through tournaments** (all games are rated): a creator can invite friends and feed rating. The limit of 5, registered-only play, and the existing rating rules (pairwise Elo, the floor) are the defence; a minimum number of participants and a visible creator on every tournament help moderation. Whether to hold back rating for very small tournaments is Q14.
- **Rating cheating by kicks**: a disqualification costs the player the rest of the tournament, so there is no gain in forcing a kick on an opponent beyond the normal game loss.
- **Pop-ups that are missed**: solved by the unseen flag (4.2).
- **Placeholder art shipped by mistake**: all placeholders are in `docs/asset-gaps.md`.
- **Rule logic outside the engine** (rule 5): the tournament formats are platform logic. If the owner reads rule 5 more strictly, the alternative is a second small pure module in the engine package that the Worker calls over HTTP like the game engine; it costs a call per pairing and nothing else. This is noted for the owner's ruling (Q15).

---

## 8. Open questions for the owner

Each needs an answer before the phase that depends on it. Suggested answers are marked *(suggested)*.

1. **Who can join**: only registered players (the games are rated, so yes) *(suggested)*; can the creator be a participant? *(suggested: yes)*.
2. **Size**: the maximum number of players of a tournament *(suggested: 64)*; the minimum *(suggested: two matches' worth, so 4 players for 2-player matches)*.
3. **The open-table limit**: do tournament games count toward the 10 of an account? A player in three tournaments would hold three games at once. *(Suggested: they do not count toward the 10, and a player may have at most 5 tournament games in progress at a time; Swiss and elimination give one game per round, so only many tournaments at once could reach it.)*
4. **Match size**: one size for the whole tournament, chosen by the creator (2, 3 or 4) *(suggested)*. Swiss points are given for that size.
5. **Time controls**: only the three turn-based speeds of D34 *(suggested)*, or also a custom time?
6. **A cancelled game** (administrator): the administrator picks a result, or the match is played again with the same seats *(suggested: replayed, as a new table with the same seats and the same clock)*.
7. **Elimination with 3 or 4 players per match**: how many advance (1 or 2)? When the number of survivors does not make a clean bracket, who gets byes? *(Suggested: the creator sets "advance" as 1 or half the match size; byes are drawn from the lowest seeds, which are random in round 1.)*
8. **Ties in a match** (equal final scores): the game already ranks equal scores as a shared rank. For elimination something must break the tie *(suggested: the tie-break of the rulebook if it has one, then the seat order of the game, then the tournament seed)* and for Swiss tied players split the points of the placements they share (rounded down) *(suggested)*. The rulebook's own tie-break must be quoted from the rulebook, not guessed (rule 1).
9. **Swiss ranking tie-breaks**: points, then opponents' points, then total game score, then starting rating *(suggested)*.
10. **Walkovers and rating**: no game is played, so no rating change *(suggested)*; do the walkover winners get a "won a match" for the achievements? *(Suggested: yes for elimination advancement; no "won a game" count.)*
11. **Walkover points in Swiss**: the maximum for the table size, or the average placement's points? *(Suggested: the points of 1st place.)* And a **bye**: *(suggested: the points of 2nd place in a 4-player table, the points of 1st place in a 2-player table, written down so a player has at most one bye).*
12. **The list of achievements**: the first list is in 4.1; the owner curates the final list, names and thresholds.
13. **Existing players**: give them what they already earned, silently and dated by the game that earned it *(suggested)*, or only count from the deploy?
14. **Very small tournaments**: all games rated regardless *(as asked)*; any minimum field to avoid feeding rating (4 players?) *(suggested: the minimum in question 2)*.
15. **Where the format logic lives**: in the Worker as pure TypeScript with tests *(suggested)*, or in the engine package behind an HTTP call.
16. **Round robin and group stage**: the details the owner will give (points rules, how groups are drawn, how many advance, play-offs). Not needed before phase 6.
17. **The game history filter on species**: the two species of the game or every species that was ever face up? *(Suggested: the species that were in play, any of the two or three of the game.)*
18. **Notifications**: the "ting" and an on-site panel only (D34: no e-mail) *(suggested)*.
19. **A timeout in a 2-player tournament game** is a loss, not a kick (D24). Does it disqualify the player from the tournament like a kick *(suggested: yes, for the same reason: they have left their game on a turn-based clock)*, or only lose that match?

---

## 9. Decisions to log when the owner approves

- **D41 Tournaments**: registered players create and join; at most 5 of a creator in registration or in progress; every game rated and turn based; a kick disqualifies; formats single elimination and Swiss first, round robin and group stage when described; `TournamentRoom` Durable Object and D1 tables; the engine untouched.
- **D42 Achievements**: a curated list from rating and tournaments; checked in the result step; given by a pop-up and kept unseen until shown; badges are placeholders; a game history icon and filters (opponent, species, achievement, minimum score); `game_species` with backfill.

(D40, the open-table limit of 1 for a guest and 10 for an account, was built on 2026-10-24 on the owner's word and is logged in `docs/PLAN.md`.)
