-- The integer number of a player and of a game, for the addresses of their pages (/players/12, /games/345). The long ids stay the keys everywhere else.
-- An autoincrement key never gives a number twice, even when the row it was for is deleted (a lobby that everybody left is destroyed).

CREATE TABLE IF NOT EXISTS user_nums (
  num INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS game_nums (
  num INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id TEXT NOT NULL UNIQUE
);

-- the players and the games that exist, numbered in the order they were made
INSERT OR IGNORE INTO user_nums (user_id) SELECT id FROM users ORDER BY created_at, id;
INSERT OR IGNORE INTO game_nums (game_id) SELECT id FROM games ORDER BY created_at, id;
