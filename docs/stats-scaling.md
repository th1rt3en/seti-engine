# Plan: the statistics summary when there are thousands of rows

Status: planned, not started (2026-10-22). Needs the owner's go, because it changes the database schema and how the Worker stores statistics.

## Where it stands

- `game_stats` has one row per player per finished game: the rank, score, organization, species and every counter as one JSON value (about 1 to 2 KB).
- The stats page (`apps/web/src/app/stats/page.tsx`) reads all rows and works the averages, spreads, organization/species/tech/gold tables and derived
  numbers out in memory (`lib/stats.ts` `aggregate`).
- Since 2026-10-22 `lib/statsCache.ts` keeps the rows and each filter's summary in the memory of the isolate, valid until a row of `game_stats` is written
  (checked with `SELECT MAX(rowid)`). A visit to an unchanged table costs one cheap query; a cold isolate or a new game reads every row again.

That is plenty for a few hundred games. It stops being plenty when reading and parsing every row hurts.

## When to do it

Start when any of these is true (check them every few weeks, or when the page feels slow):
- `game_stats` has more than about 3,000 rows (a cold isolate then reads 4 to 6 MB and parses that much JSON before the first page);
- the stats page takes more than about 1 second to answer on a cold isolate;
- D1 rows read per day, from this page, is a visible part of the free allowance.

How to look: `SELECT COUNT(*), SUM(LENGTH(counters_json)) FROM game_stats;` and the timing of `/stats` in the Cloudflare dashboard.

## Design

Keep the cache layer. Replace what it loads: instead of every row, a precomputed summary that is kept up to date when a game ends.

1. **A table of mergeable totals.** `stats_totals(slice, counter, n, sum, sumsq, min, max)`. A slice is one cell of the filters that matter
   (players 1 to 4, expansion yes/no, rated yes/no, who people/ai), 32 cells, and the page adds cells up for the filters it was asked for (all of
   them "any"). `n`, `sum`, `sumsq`, `min` and `max` are enough for the mean, the minimum, the maximum and the standard deviation of every counter, and they
   add up exactly, so a filter is a sum of a few cells.
2. **Tables for what is not a plain counter.** `stats_orgs(slice, org, offered, picked, won, elo_sum, elo_n)`, `stats_species(slice, species, rows, score_sum,
   score_sumsq, score_min, score_max, games)`, `stats_gold(slice, face, times, points_sum, points_sumsq, points_min, points_max)`, `stats_tech(slice, tech,
   players, rows)`, and the score histogram (`stats_scores(slice, bucket, rows)`).
3. **Derived numbers become counters.** A number the page works out from several counters of one player and shows with a spread (for example the sum of
   resources from a source) cannot be made from totals. Each such number gets a counter of its own in the engine's `stats.py` (it is pure and the old games
   can be replayed again with `tools/engine/backfill_stats.py`). The mission completion rate stays a ratio of two means, which is exact from totals.
4. **Updating.** `recordStats` in `apps/worker/src/core/d1.ts` already writes the player rows when a game ends. In the same batch it adds the game's rows
   to the totals (an upsert that adds to `n`, `sum`, `sumsq` and takes `min` and `max`). Everything is one D1 batch, so the rows and the totals cannot
   disagree.
5. **Reading.** The page reads the 32 slices it needs (or fewer) and adds them: a few hundred small rows whatever the number of games. The memory cache stays on
   top (version = `MAX(rowid)` of `stats_totals`), so a visit to an unchanged table is still one query.
6. **Raw rows stay.** `game_stats` is kept: it is the source for a rebuild, for the players' own pages and for new counters.

## Rebuild and migration

- A tool `tools/engine/rebuild_stats_totals.py` clears the totals and fills them from `game_stats` in one pass (used once at the migration, and whenever a
  counter is added or the engine's `stats.py` VERSION changes after a backfill).
- Migration `00NN_stats_totals.sql` creates the tables. The deploy action's `migrations` input applies it; then the tool runs once against D1.
- Order of the release: migration, Worker (writes totals), rebuild once, web (reads totals). Until the web release the page keeps reading raw rows, so each
  step can be undone.

## Tests

- The totals of a set of rows equal `aggregate` over the same rows for every filter: mean, min, max, standard deviation, win rate, organization table,
  species table, gold table, tech shares (a property test over generated rows; the current `aggregate` is the oracle).
- `recordStats` twice for the same game does not count it twice (INSERT OR REPLACE on the rows; the totals are rebuilt or keyed by game).
- A backfill followed by the rebuild gives the same totals as adding the games one by one.

## Open points for the owner

- A game's statistics replaced by a backfill (a new counter, a rule that changed) must replace its contribution to the totals. The simple way is to rebuild all
  totals after any backfill. Adding a "game version" to each row and subtracting the old contribution is exact but more work; I would start with the rebuild.
- Exact percentiles (a median score, say) cannot be made from totals. If they are wanted, keep a histogram per counter that matters (like the score
  histogram), not a general solution.
- Whether to keep the per-player rows readable by anybody (the players' own pages) is unchanged by this plan.
