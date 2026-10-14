-- Initial D1 schema (docs/PLAN.md section 3). The website owns users and sessions; the Worker writes games, players, logs and ratings.

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  password_hash TEXT,
  is_guest INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS games (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,            -- lobby, playing, finished, cancelled
  options_json TEXT NOT NULL,      -- the engine options, with the seed: seed + log replay the game
  clock_json TEXT NOT NULL,
  rated INTEGER NOT NULL,          -- 1 when the game was created as rated
  rated_counted INTEGER NOT NULL DEFAULT 0, -- 1 when the result changed the ratings
  reason TEXT,                     -- completed, resigned, timeout
  result_json TEXT,
  actions INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  started_at INTEGER,
  ended_at INTEGER
);
CREATE INDEX IF NOT EXISTS games_status ON games(status);

CREATE TABLE IF NOT EXISTS game_players (
  game_id TEXT NOT NULL REFERENCES games(id),
  seat INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  registered INTEGER NOT NULL,
  rank INTEGER,
  score INTEGER,
  rating_before INTEGER,
  rating_after INTEGER,
  PRIMARY KEY (game_id, seat)
);
CREATE INDEX IF NOT EXISTS game_players_user ON game_players(user_id);

-- The action log of a finished game (seed + log replay it, decision D8).
CREATE TABLE IF NOT EXISTS game_logs (
  game_id TEXT PRIMARY KEY REFERENCES games(id),
  log_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ratings (
  user_id TEXT PRIMARY KEY,
  rating INTEGER NOT NULL,
  games INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ratings_rating ON ratings(rating DESC);

CREATE TABLE IF NOT EXISTS rating_history (
  game_id TEXT NOT NULL REFERENCES games(id),
  user_id TEXT NOT NULL,
  rating_before INTEGER NOT NULL,
  rating_after INTEGER NOT NULL,
  rank INTEGER NOT NULL,
  at INTEGER NOT NULL,
  PRIMARY KEY (game_id, user_id)
);
CREATE INDEX IF NOT EXISTS rating_history_user ON rating_history(user_id, at);
