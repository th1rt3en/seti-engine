-- The settings of a player's game page (sound, confirmations, notifications, size of the hand), kept with the account so that they follow the player to
-- another device. A small JSON object of a few known keys; the website checks what it stores.
CREATE TABLE IF NOT EXISTS user_settings (
  user_id TEXT PRIMARY KEY REFERENCES users(id),
  settings_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
