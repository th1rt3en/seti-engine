-- The invitations of a lobby: the host holds a seat for a registered player until they answer. The room (a Durable Object) is the owner of them; this table
-- is the copy that the site reads to tell an invited player, wherever they are on the site, that they have been invited (written by recordLobby).

CREATE TABLE IF NOT EXISTS lobby_invites (
  game_id TEXT NOT NULL,
  seat INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  host_name TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (game_id, seat)
);
CREATE INDEX IF NOT EXISTS lobby_invites_user ON lobby_invites(user_id, status);
