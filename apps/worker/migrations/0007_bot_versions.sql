-- The versions of the AI model that is trained on the owner's machine (services/ai): what each is and how it played in the offline matches.
-- Only the numbers are here; the weights stay on the machine until the owner approves a version for serving. The site shows this table to everybody.
CREATE TABLE IF NOT EXISTS bot_versions (
  version TEXT PRIMARY KEY,
  created TEXT NOT NULL,
  rules_version TEXT NOT NULL,
  parent TEXT,
  players INTEGER NOT NULL,
  training_json TEXT NOT NULL,
  evaluation_json TEXT NOT NULL,
  approved INTEGER NOT NULL DEFAULT 0,
  live INTEGER NOT NULL DEFAULT 0,
  note TEXT
);
