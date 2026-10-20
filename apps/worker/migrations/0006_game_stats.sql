-- Statistics of the games that were played to their end (services/engine stats.py): one row for each player of a game.
-- `counters_json` holds the flat counters of the engine ("action.launch", "incomerate.r2.credit" ...); the site averages them over the rows that
-- match a filter. Only games that ended as completed are here. The Elo change of a player is in rating_history (same game and user).
CREATE TABLE IF NOT EXISTS game_stats (
  game_id TEXT NOT NULL REFERENCES games(id),
  seat INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  players INTEGER NOT NULL,
  rated INTEGER NOT NULL,
  expansion INTEGER NOT NULL,
  rank INTEGER NOT NULL,
  won INTEGER NOT NULL,
  score INTEGER NOT NULL,
  org TEXT,
  org_offered_json TEXT NOT NULL,
  species_json TEXT NOT NULL,
  counters_json TEXT NOT NULL,
  ended_at INTEGER NOT NULL,
  PRIMARY KEY (game_id, seat)
);
CREATE INDEX IF NOT EXISTS game_stats_filter ON game_stats(players, rated, expansion);
