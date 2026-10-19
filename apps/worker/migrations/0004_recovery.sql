-- A one-time recovery code for each account (only its scrypt hash is kept): it is shown once, at signup, and lets the player set a new password
-- if the old one is lost. Using it makes a new code. The administrator can also set a password (the /admin page).
CREATE TABLE IF NOT EXISTS recovery_codes (
  user_id TEXT PRIMARY KEY REFERENCES users(id),
  code_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
-- The failed recoveries and password changes from an address (a few per quarter of an hour are allowed), so that a code cannot be guessed.
CREATE TABLE IF NOT EXISTS auth_attempts (
  ip TEXT NOT NULL,
  at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_attempts_ip ON auth_attempts(ip, at);
