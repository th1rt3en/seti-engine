-- The failed attempts to open the administrator's page (a few per address and quarter of an hour are allowed), kept so that guessing the passphrase is slow.
CREATE TABLE IF NOT EXISTS admin_attempts (
  ip TEXT NOT NULL,
  at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS admin_attempts_ip ON admin_attempts(ip, at);
