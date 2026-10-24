# Plan: tournaments and achievements (the next platform upgrade)

Status: **a plan for the owner to approve. Nothing of it is built.** Written 2026-10-24 from the owner's brief; the owner answered the first 19 questions the same day (section 8). It extends `docs/PLAN.md` and does not contradict it: when the owner approves it, the decisions in section 9 go into the decision log (D41 and D42). The outcomes that are still unclear are listed in section 8.2 and in the catalogue of edge cases (section 10); they are answered before the phase that needs them (hard rule 3: an unclear rule means stop, not a guess).

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
  1. **Tables of mixed sizes** (both formats). The creator gives a smallest and a largest table size. For *n* players the tables are made like this (the rule is proposed from the owner's two examples and is to be confirmed, Q22):
1. seat everybody if a split exists with all tables between the smallest and the largest size; leave out as few players as possible otherwise (the players left out get a **bye**);
2. among those splits, make as many largest tables as possible.

Examples (the owner's): sizes 2 to 4 with 10 players give 4 + 4 + 2 (rather than 4 + 3 + 3); sizes 3 to 3 with 10 players give 3 + 3 + 3 and one random player with a bye. Sizes 2 to 4 with 9 players give 4 + 3 + 2 (no one is left out: 4 + 4 + 1 is not allowed).

**Single elimination**
- Round 1: players are shuffled with the tournament seed and cut into tables as above; the players left out get **random byes**.
- The creator sets how many players advance from a table, **1 or 2**. A table of 2 players always advances 1 (the number is the smaller of the setting and the table size minus one).
- The players who advance are the best of the table by placement; ties are broken by the **play order of the first round of that game: the player who played earlier loses** (the rulebook has no tie-break, so this is the owner's rule).
- A bye is not a win and gives nothing; it only advances the player. A player gets a second bye only after everyone has had one.
- Rounds continue until the players left fit one table: that table is the final, its placements are the tournament's top places; the winner is first. The others are ranked by the round they left in, then by their placement in the table they left.
- A table starts as soon as its feeder tables are done (no waiting for the whole round), because turn-based games last days.
- What happens when too few players are left to make a table of the smallest size (for example, sizes 3 to 3 with 6 players: two tables of 3 leave 2 players) is open: Q23.

**Swiss**
- *x* rounds, 2 to 8. In every round every player plays one match; the tables are made as above; a player left out has a **bye and gets +2 points** (a bye is not a win).
- Points by placement (the owner's table): 4 players +6/+4/+2/0, 3 players +4/+2/0, 2 players +2/0. A tournament can have tables of several sizes, so each table gives the points of its own size. Placement ties are broken by the play order of the first round (the player who played earlier is placed lower), so points are never split; to be confirmed with Q24.
- Round 1: random. Later rounds: players are sorted by points; players with equal points are shuffled; consecutive players are cut into tables (sizes as above), so similar strength meets. Which player gets the bye is open (Q25).
- **Avoid rematches** (a switch at creation, default on): the pairing tries to avoid putting together players who have already met. It is best effort: it searches for a pairing with the fewest repeated meetings (a bounded search with the seeded shuffle), and it never leaves a round unplayed because of it.
- A round ends when all its games are done, then the next round's tables are made at once. (This is the cost of Swiss: one slow game holds the round. Turn-based clocks plus the kick keep it moving; section 7 lists the other safeguards.)
- Final ranking (the owner's order): points, then **the points of the opponents** (the sum for the opponents met), then the **total game score**, then the **rating at the start (the lower rating wins the tie-break)**.

**Round robin** and **group stage**: details to come from the owner. The plan makes room for them: the interface above, a `format` column, a free-form `settings` JSON, and standings that are not tied to one table size. They will be added as their own phase once described (they may need: points rules, how groups are drawn, how many advance, a play-off).

### 3.4 Disqualification

- A kick in a tournament game (D24) disqualifies the kicked player from the whole tournament (the owner's rule).
- In a 2-player game nobody is kicked: the player whose time runs out **loses the game and nothing more** (the owner, Q19), exactly as D24 says today.
- Every game of a disqualified player that has not started is affected (see below); a game that is in progress when the kick happens ends as D24 says (the other players share first place; the kicked player is placed last).
- A table that has not started and whose player is disqualified: the others play if at least the smallest table size remains and the creator's size limits allow it; otherwise, or when only one player is left, the remaining player(s) win by **walkover**. A walkover is recorded without a game and without a rating change. These details are open (Q26 and Q27).
- In Swiss, a disqualified player keeps the points they earned (so the opponents' tie-breaks stay fair) and is marked as out.
- A resignation is not a kick: the player loses that game (as today) and goes on.

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

- **A new tab "Tournaments" in the top navigation bar**, with `/tournaments`: open tournaments (registration), in progress, concluded; a filter by format and by the creator; "Create a tournament" for registered players (shows how many of the 5 are used); and "Your tournament games" (the games that wait for the player, the ones in progress).
- `/tournaments/12`: settings, the players, the standings, the bracket or the rounds with every match linking to its game (watch while it is on, replay when it is done), the creator's controls (start, cancel) and a join / leave button.
- A player with a tournament game that waits for them sees a mark on the Tournaments tab.
- Admin page: list, cancel.
- Profile: the tournaments a player took part in with their rank, and tournament badges (section 4).
- The game page of a tournament game says which tournament, round and match it is.

---

## 4. Achievements

### 4.1 What counts

**Only rated games count, and so do the games of tournaments** (which are rated anyway): a friendly game, a solo game, a practice game and a game with an AI never give an achievement and never count toward a streak (owner, 2026-10-24). Everything below is evaluated for the registered players of a rated game.

The list is the owner's, in `docs/achievements.md` (the list is **not exhaustive**: more will be added, so a new achievement is one new entry and no new machinery). The names and thresholds are the owner's; the "how it is checked" column is this plan's reading of each line, **confirmed by the owner on 2026-10-24** (8.2b).

| # | Achievement (owner's text) | How it is checked (to confirm where marked) |
|---|---|---|
| 1 | **Beginner / Intermediate / Expert / Master**: Elo 100 / 300 / 500 / 700 | The rating at the end of a rated game reaches the level (an unlock is kept if the rating falls). Four badges. The **highest title reached is shown beside the player's name** on the profile. |
| 2 | **First win**: first rated game win | The player is **alone in first place** in a rated game. A shared first place (a tie, or the others after a kick, D24) is **not a win**. |
| 3 | ***X* in a row**: 2 / 3 / 5 / 10 / 20 / 50 rated wins in a row | A streak of consecutive rated wins (a win as in 2), in the order the games ended. Any other result of a rated game (not first, a shared first place, a kick, a resignation) ends it. Six badges. A friendly game does not touch it. |
| 4 | **Master Assassin**: first rated win against a Master (700 current Elo) | The player is first (alone, as in 2) in a rated game with a player at the table whose rating **before the game** was 700 or more. |
| 5 | **First tournament win** | The player finishes a tournament in first place (the winner of the final in elimination; first of the standings in Swiss). Given at the end of the tournament; the game stored is the deciding game of the player. |
| 6 | **Tournament Creator**: first tournament started (for the creator) | The creator's first tournament goes from registration to in progress. It has no game: no icon in the history, and the pop-up comes with the answer of the "start" button. |
| 7 | **Engineer**: 10+ orbiters/landers at the end of the game | The orbiters and the landers of the player together, on planets and moons, at the end: the sum is 10 or more. |
| 8 | **Dynamo**: 10+ missions completed at the end of the game | Missions completed by the player, **every kind** (full, quick and trigger missions). |
| 9 | **Researcher**: all 12 techs researched at the end of the game | The player holds one of each of the 12 techs of the tech board (3 kinds of 4). |
| 10 | **Tourist**: an orbiter or lander on every planet at the end of the game | On each of the 7 planets of the base game. A lander on a moon counts as being on its planet. Pluto (the promo card) is ignored. |
| 11 | **Deliverer**: deliver 4+ Mascamite samples | Samples delivered by the player in the game (a counter that the statistics already keep). |
| 12 | **Anomaly Master**: benefactor of every Anomaly token trigger in the game (at least 3) | The player is the one paid by every anomaly trigger of the game, the game had at least 3 triggers, and a trigger that pays nobody breaks it. |
| 13 | **Archaeologist** (spelled "Archaelogist" in the list): gain and spend 12+ exofossils | The player gained 12 or more **and** spent 12 or more exofossils in the game. |
| 14 | **Cryptologist**: play and complete 8+ Centaurian messages | Message cards that the player played and whose green part was resolved, 8 or more. |
| 15 | **Daredevil**: 40+ danger at the end of the game | The Exertian danger of the player at the end (cards and board together, a counter that the statistics keep). |
| 16 | **Tactician**: 20+ danger and not lose points for having the highest danger | Danger of 20 or more at the end, and no loss in the end scoring (ALIEN-EXE-07). |
| 17 | **Explorer**: play all 3 security cards for 3 major explorations and trigger 15+ minor explorations in one game | All three security cards breached, three explorations that gave the major reward, and 15 or more minor rewards triggered. |
| 18 | **Hoarder**: 20+ Glyphids tokens at the end of the game | The glyph tokens the player holds at the end. |
| 19 | **Evolutionist**: trigger 20+ groups of organelle in a single game | Amoeba group triggers of the player in the game (a counter that the statistics keep). |

Any player at the table can earn a game achievement, the winner or not. The numbers come from what the engine recorded during the game and at its end (the events and the final scores), not from a second count.

An achievement is a small record: an id, a name, a text, a badge and a check. The general ones (1 to 6) are checked by the Worker from D1 (ratings, results, the tournament); the game ones (7 to 19) are checked from **the facts of the game that the engine reports at the end** (the next section).

### 4.1a Where the game achievements are computed

The facts of a game (orbiters and landers, missions, techs, planets, samples delivered, anomaly triggers and their beneficiaries, exofossils gained and spent, messages resolved, danger and the danger loss, security cards, explorations, glyph tokens, organelle groups) are state of the game, and some come from the events of the whole game. The engine already makes such numbers for the statistics (`stats.py`, one counter set per player at the end of a game). The plan adds a **pure function in the engine package, `achievements.py`**, next to `stats.py`: it takes the finished game (the same replay that makes the statistics) and returns, for each player, the list of game achievements that the game earned (ids). The Worker asks for it when a rated game ends, in the same step as the statistics, and passes the ids to the unlock step. Why in the engine: the checks read the state and the events of the game, which the Worker does not interpret (hard rule 5: rule logic stays in the engine). The counters that do not exist yet are added to `stats.py` (anomaly beneficiaries, exofossils spent, messages resolved) with tests and with the statistics backfill, so that the statistics page can use them too.

The general achievements (1 to 6) need only ratings, results and tournaments, which the Worker already holds, so they stay in the Worker.

### 4.2 When it is given

- **After a rated game that ends** (an ordinary rated game or a tournament game; nothing else counts), in the same step that settles the ratings (`finish` in the room, and the D1 batch of `recordEnd`): the facts are checked against the list for every registered player of the game. A new unlock is written once (`achievement_unlocks`: user, achievement, game, time; unique on user + achievement) and the game id stored is the game that earned it.
- **Tournament achievements** that depend on the end of the tournament (win, top ten percent) are checked when the tournament concludes; the game stored is the final game of that player's tournament, so that the history has an icon on a real game.
- **The pop-up**: the `ended` message of the game's WebSocket carries the achievements that this viewer unlocked in the game; the page shows a pop-up (name, badge, text, a link to the profile). A player who was not on the page (the game ended while they were away, which is the normal case on a turn-based clock) sees it the next time they open any page: a `seen` flag on the unlock row, a small request at page load, and a pop-up for each unseen one. Each is shown once.
- **Existing players**: only rated games that end after the release count (the owner, Q13). Nothing is computed from the past, and a win streak starts at the release. What a rating achievement needs when a player is already above a level at the release is Q28.
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
| **Alien species** | a **multiple-selection dropdown** of the species; shows the games in which **any** of the chosen species was in play | the species of each game stored per game (see below) |
| **Achievement unlocked** | only the games that unlocked an achievement; optionally one chosen achievement | `achievement_unlocks.game_id` |
| **Minimum score** | games in which this player scored at least that many points | `game_players.score` |

- The filters combine (all must hold) and the pagination keeps them.
- **The species of each game**: today the species are in the game state and in the statistics counters of the games that ended, not as a plain list. A new table `game_species (game_id, species)` is filled when a game ends (the engine's result already knows which species were discovered, or the two that were in play; to be confirmed against `stats.py`), and **backfilled** for finished games by the existing backfill tool pattern (`tools/engine/backfill_stats.py`: replay each archived game with the engine, read the species). Games that cannot be replayed any more (the skip list) have no species and simply do not match the species filter.
- Indexes: `game_players (user_id, game_id)` exists; add `game_species (species, game_id)` and `achievement_unlocks (user_id, game_id)`.

---

## 6. Work, in phases

Each phase ends with tests, a report in the form CLAUDE.md asks for, and stays behind the owner's review gate for the phase marked with a star. As for the rules of the game (hard rules 2 and 3), every tournament rule has an id (`TOUR-...`) in `docs/spec/tournaments.md`, the code that implements it cites the id, and every id has a test that names it.

| Phase | Work | Notes |
|---|---|---|
| **0** | The owner answers section 8 and approves sections 3, 4 and 5; the two decisions are logged (D41, D42) | star: the gate for everything below |
| **1a** | **The catalogue of edge cases** (section 10): every corner case of the tournament progression is written with its expected outcome; the owner answers each one marked *needs a ruling*; the answers go into `docs/spec/tournaments.md` and become test cases, **before any pairing or progression code is written** | star |
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
- **Many tables for one player**. A player in several tournaments can have many games at once. Tournament tables do not count toward the open-table limit of an account (answer 3), so a tournament cannot be made unplayable by it.
- **Gaming the rating through tournaments** (all games are rated): a creator can invite friends and feed rating. The limit of 5, registered-only play, and the existing rating rules (pairwise Elo, the floor) are the defence; a minimum number of participants and a visible creator on every tournament help moderation. The creator can set a minimum rating for a tournament (answer 14); the plan holds no rating back for small tournaments.
- **Rating cheating by kicks**: a disqualification costs the player the rest of the tournament, so there is no gain in forcing a kick on an opponent beyond the normal game loss.
- **Pop-ups that are missed**: solved by the unseen flag (4.2).
- **Placeholder art shipped by mistake**: all placeholders are in `docs/asset-gaps.md`.
- **Rule logic outside the engine** (rule 5): the tournament formats are platform logic. If the owner reads rule 5 more strictly, the alternative is a second small pure module in the engine package that the Worker calls over HTTP like the game engine; it costs a call per pairing and nothing else. This is noted for the owner's ruling (8.3).

---

## 8. The owner's answers, and what is still open

### 8.1 Answers (2026-10-24)

| # | Question | Answer |
|---|---|---|
| 1 | Who can join | Only registered players; the creator can join their own tournament |
| 2 | Size | The creator chooses, from 2 to 128 |
| 3 | The open-table limit | Tournament tables do not count toward the 10 tables of an account |
| 4 | Match size | The creator chooses the smallest and the largest number of players at a table (for example 2 and 4: 10 players make two tables of 4 and one of 2; 3 and 3: 10 players make three tables of 3 and a random player with a bye) |
| 5 | Time controls | The turn-based speeds of D34 and two new slower ones: *slower* and *slowest* (values: see 8.2) |
| 6 | A cancelled tournament table | The administrator picks its result when cancelling it |
| 7 | Elimination with 3 or 4 players per table | The creator sets how many advance from a table, 1 or 2; byes are random |
| 8 | Tie in a match | The rulebook has no tie-break: the player who played earlier in the first round of that game loses the tie |
| 9 | Swiss ranking | Points, then the opponents' points, then the total game score, then the starting rating (the lower rating wins) |
| 10 | Walkovers and ratings | A bye is not a win |
| 11 | Swiss byes | A bye gives +2 points |
| 12 | The list of achievements | To be decided |
| 13 | Existing players | Only games after the release count for achievements |
| 14 | Very small tournaments | The creator can set a minimum rating for the tournament; the default is 0 |
| 15 | Where the logic lives | Asked what it is: see 8.3 |
| 16 | Round robin and group stage | To be decided |
| 17 | The species filter | A multiple-selection dropdown; shows the games with any of the chosen species |
| 18 | Notifications | A new tab for tournaments on the top navigation bar |
| 19 | A 2-player timeout | Only a loss (no disqualification) |

### 8.2 Still open: outcomes that are not clear (the owner is asked to rule; a suggestion is given for each)

These came out of the answers and out of the edge-case catalogue (section 10). Until each is ruled, the code for it is not written.

- **Q20 Withdrawing after the start**: *(suggested: a withdrawal is treated like a disqualification: the player's later games are walkovers; the points they have stay.)*
- **Q21 A cancelled table with a result picked by the administrator**: does it change the ratings? *(suggested: no: the game was not played to its end, so only the tournament uses the result.)*
- **Q22 Splitting the players into tables**: the rule in 3.3 (seat everybody if a split exists, then as many largest tables as possible, byes only if no split exists, as few as possible) gives the owner's examples. Is it right? Two more cases it decides: sizes 2 to 4 with 9 players give 4 + 3 + 2; sizes 3 to 4 with 10 players give 4 + 3 + 3 (not 4 + 4 + 2: two is below the smallest size).
- **Q23 Too few players left for a table of the smallest size** (elimination): for example sizes 3 to 3 with 6 players: 2 tables, 1 advances from each, 2 are left. *(suggested: the last tables may be smaller than the smallest size, down to 2 players, because no other end is possible; with "advance 2" the setting is lowered to 1 when 2 per table would leave fewer players than the smallest table.)*
- **Q24 Swiss placement ties**: the tie-break by play order (earlier loses) applies to the placement in every match, so no points are split *(suggested)*; or tied players split the points?
- **Q25 Who gets a Swiss bye**: *(suggested: the lowest in the standings who has not had one; a player gets a second bye only after everybody has had one.)* Elimination byes are random (answered).
- **Q26 A disqualification before a table starts**: if the smallest table size is still met the others play with fewer players; if not, they win by walkover *(suggested)*. Is that right? What if the table would then be a table of 1 (the last player wins by walkover)?
- **Q27 Walkover points in Swiss**: the winners of a walkover get *(suggested: the points of 1st place of that table size; an opponent who is out gets 0)*.
- **Q28 Rating achievements at the release**: a player who is already above a level when the feature goes live: do they unlock that level at their next game *(suggested: yes, at the first game that ends after the release with a rating at or above the level)*, or only when they cross it again?
- **Q29 The minimum rating of a tournament**: checked when a player joins *(suggested)* and again when the tournament starts (a player who fell below is removed with a message)? Unrated new players start at 0.
- **Q30 A kick that leaves several players sharing first place in an elimination table** (D24: all the others share first): *(suggested: the play-order tie-break puts them in order, and the first "advance" of them go on.)*
- **Q31 The two new speeds**: values for *slower* and *slowest* *(suggested: slower 6 days + 18 h per turn; slowest 10 days + 1 day per turn; today's slow is 4 days + 12 h)*.
- **Q32 What "a tab for tournament games" means**: one tab, "Tournaments", with the list of tournaments and "Your tournament games" inside it *(suggested)*; or two tabs.

### 8.2b Answered (2026-10-24): the questions of the achievements

| Q | Answer |
|---|---|
| The reading of the list in 4.1 | Agreed in full |
| Q33 Titles | The highest title reached is shown next to the player's name |
| Q34 A shared first place | Not a win: it is lost (so a game that ends by a kick, where the others share first, is not a win for anybody; it ends a streak) |
| Q35 The streak | As in the table: any non-win ends it; six separate badges (agreed with the table) |
| Q36 Win against a Master | First place (alone), with a Master at the table |
| Q38 Orbiters and landers | The sum, moons included |
| Q39 Missions | Every kind counts |
| Q40 Techs | One of each of the 12 techs of the tech board |
| Q41 Planets | The 7 base planets; a lander on a moon counts for its planet; Pluto ignored |
| Q42 Anomaly Master | A trigger that pays nobody breaks it |
| Q43 Exofossils | Gain 12 or more and spend 12 or more |
| Q44 Explorer | All three security cards, three major explorations and 15 or more minor ones |
| Q45 Who can earn a game achievement | Any player at the table, winner or not |
| Q46 The pop-ups | Several at once are shown in the alphabetical order of the title |
| Q47 The numbers of the checks | Taken from the engine's own record of the game (the question was about whether to re-count; the plan does not re-count, so nothing changes) |
| Q37 Tournament Creator | Agreed: given when the creator's tournament starts, with the pop-up at once |

### 8.3 What the "format logic" is (question 15)

A tournament format is the part of the system that answers three questions: *who plays whom next* (pairing, byes, the sizes of the tables), *what a result does* (points, who advances, who is out) and *how the players are ranked at the end* (the tie-breaks). It is not part of the rules of SETI. The plan puts it in the Worker as pure TypeScript functions with a seed (no clock, no network), which the tournament Durable Object calls, with tests. The alternative is to put the same functions in the Python engine package and have the Worker call them over HTTP like the game engine; that keeps every rule in one language but costs a call per pairing and puts platform logic into the rules engine. Suggestion: the Worker, unless the owner wants rule 5 read strictly (Q15 stays open until the owner says).

---

## 9. Decisions to log when the owner approves

- **D41 Tournaments**: registered players create and join; at most 5 of a creator in registration or in progress; every game rated and turn based; a kick disqualifies; formats single elimination and Swiss first, round robin and group stage when described; `TournamentRoom` Durable Object and D1 tables; the engine untouched.
- **D42 Achievements**: a curated list from rating and tournaments; checked in the result step; given by a pop-up and kept unseen until shown; badges are placeholders; a game history icon and filters (opponent, species, achievement, minimum score); `game_species` with backfill.

(D40, the open-table limit of 1 for a guest and 10 for an account, was built on 2026-10-24 on the owner's word and is logged in `docs/PLAN.md`.)

---

## 10. The catalogue of edge cases (phase 1a)

Every case below becomes one or more tests (`TOUR-nnn` ids in `docs/spec/tournaments.md`). *Clear* means that the answers above decide it. *Needs a ruling* points to the open question in 8.2. The test of a case is written in phase 1a as a table of inputs and the expected outcome, so that the owner reads the outcomes before any code exists.

**Registration and limits**
1. The creator joins their own tournament: allowed, counts as a participant. *Clear.*
2. A guest tries to join: refused. *Clear.* A registered player below the minimum rating: refused with the minimum named. *Clear;* re-check at the start: *Q29.*
3. The same player joins twice: refused. *Clear.*
4. A sixth tournament: refused with the limit and what to do; cancelling one in registration frees a place; a concluded or cancelled one frees a place. *Clear.*
5. The start with fewer players than one table's smallest size: refused. With exactly one table's worth: starts. *Clear.*
6. 128 players: allowed; 129: refused. *Clear.*
7. The registration deadline passes with too few players: the tournament is cancelled. *Suggested; clear unless the owner objects.*
8. A player leaves during registration: removed, no trace. *Clear.*

**Splitting into tables** (the same function for every round of both formats)
9. n from 2 to 128 for every pair of smallest and largest size from 2 to 4 (all 6 pairs): every player is at exactly one table or has a bye; no table is outside the sizes; the owner's examples hold (2 to 4 with 10: 4+4+2; 3 to 3 with 10: 3+3+3 and a bye); the number of byes is the smallest possible. *Needs a ruling: Q22.*
10. n smaller than the smallest size: no table (the tournament cannot start; in later rounds see Q23).

**Single elimination**
11. 2 players: one table, the final. *Clear.*
12. n a power of the table size with advance 1 and equal sizes: a clean bracket. *Clear.*
13. n that leaves byes in round 1: byes are random, not a win, a second bye only after everybody had one. *Clear.*
14. Advance 2 from a table of 2: becomes 1. *Clear (3.3).*
15. Advance 2 from tables of 4 with 8 players: 4 players left, they play the final (one table). *Clear.*
16. Fewer players left than the smallest size (3 to 3 with 6 players). *Needs a ruling: Q23.*
17. A tie in a table for the advancing place: the earlier player of round 1 loses. *Clear (Q8).* A tie for a place that does not decide who advances: the same order is used for the ranking. *Clear.*
18. A kick in a table that leaves several players sharing first place. *Needs a ruling: Q30.*
19. A table whose feeder tables are not done: waits. A table whose feeders are done: starts at once. *Clear.*
20. The final's placements decide first to last; the players who left earlier are ranked by the round they left in, then by placement. *Clear (3.3).*

**Swiss**
21. x from 2 to 8 with n from 2 upward: every player plays every round or has a bye; no table is outside the sizes. *Clear.*
22. A bye gives +2 and is not a win. Who gets it. *Needs a ruling: Q25.*
23. Pairing by points: the order of the players by points, equal points shuffled with the seed; the same seed gives the same pairing. *Clear.*
24. Avoid rematches on: the pairing has the fewest repeated meetings possible and never fails; off: no check. *Clear.*
25. More rounds than distinct opponents (for example 4 players, 8 rounds): rematches are unavoidable, the round is still made. *Clear.*
26. Points per table size (2, 3, 4 players); placement ties. *Needs a ruling: Q24.*
27. The final ranking: points, opponents' points, total game score, lower starting rating. Every tie-break level is tested, and a full tie after all four (two players equal in everything): *needs a ruling:* *(suggested: the tournament seed order.)*
28. A round starts only when every game of the previous round is done. *Clear.*

**Disqualification, withdrawal, cancellation**
29. A kick in game A: the player is out; their games in later rounds are walkovers; their points stay. *Clear.* The kick in a game with 2 players cannot happen (D24); a 2-player timeout is a loss only. *Clear (Q19).*
30. A disqualification before a table starts: the table is played with fewer players, or the rest win by walkover. *Needs a ruling: Q26.*
31. The walkover points (Swiss) and the advancing (elimination). *Needs a ruling: Q27 (points); advancing: the winner of the walkover advances. Clear.*
32. Every other player of a tournament is disqualified or out: the last one wins. *Clear.*
33. A withdrawal. *Needs a ruling: Q20.*
34. The administrator cancels a table and picks the result; the tournament goes on. *Clear;* the ratings: *Q21.*
35. The administrator cancels the whole tournament: games played keep their ratings; unplayed ones are void. *Clear.*
36. The creator cancels after the start: refused. *Clear.*

**Results and ratings**
37. A result arrives twice or two results arrive together: one effect. *Clear.*
38. A tournament game ends by resignation: the resigning player is last, goes on in Swiss, is out in elimination (they lost). *Clear.*
39. A tournament game is archived with the tournament's number in its header; a replay works. *Clear.*
40. The rating changes of a tournament game are the ordinary ones (pairwise Elo, floor 100). *Clear (D37).*

**Achievements that depend on tournaments** (phase 5)
41. The unlock of "win a tournament" is stored on the deciding game; the pop-up is shown at its end or on the next page load. *Clear.*
42. A tournament with a walkover or a bye does not give a "won a match" for it. *Clear (Q10).*
43. Achievements are given only for games that end after the release. *Clear (Q13).* A rating level for a player already above it: *Q28.*

44. A friendly game, a solo game, a practice game and a game with an AI never give an achievement and never touch a streak. *Clear (owner).*
45. Two achievements in one game (for example a tournament win and a title): both are shown, once each. *Clear;* shown in the alphabetical order of the title (Q46).
46. A result that is sent twice, or a game archived again after a restart: the unlock is written once (unique on player and achievement). *Clear.*
47. A player who is kicked in a rated game: no game achievement from that game; a streak is reset. *Clear: a kick is a non-win and ends a streak (Q34, Q35).*
48. The same game achievement earned by two players in one game: each gets it. *Clear (Q45 suggested).*
49. The achievement checks and the statistics page agree on the numbers of the same game (a test over archived games). *Clear.*
50. The general achievements: a title is given at the first rated game that ends with the rating at or above its level; a streak counts only games after the release; a win with a Master needs the Master's rating before the game. *Clear (Q36: first place); Q28 is open.*

The answers to the questions marked *needs a ruling* are copied into `docs/spec/tournaments.md` with the rule ids, as the answers to ambiguities are copied into the spec of the game.
