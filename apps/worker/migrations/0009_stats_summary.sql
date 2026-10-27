-- The statistics page used to work its summary out from every row of game_stats on each visit that the isolate had not seen (about 100 ms of CPU for 100 rows,
-- which delays the other requests of that isolate). The summary of a filter is now kept here in parts, one row each, and made again only after a row of game_stats was
-- written: `version` is the highest rowid of game_stats it was made from (apps/web/src/lib/statsCache.ts). A part is the JSON of a field of the statistics
-- (the core, the cards, the numbers of one alien species ...), so that a tab reads only what it shows. The table holds a copy that can be rebuilt: it can be emptied.
CREATE TABLE IF NOT EXISTS stats_summary (
  filter_key TEXT NOT NULL,
  part TEXT NOT NULL,
  version INTEGER NOT NULL,
  json TEXT NOT NULL,
  PRIMARY KEY (filter_key, part)
);
