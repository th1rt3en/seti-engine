-- One-off data fix (2026-10-25): a game with an AI is never rated. Games made rated (the default) and then given an AI kept `rated = 1` in the table
-- (the Worker did not write the flag again); no rating was ever changed by them (`rated_counted` is 0). Run once, by the owner:
--   cd apps/worker && node node_modules/wrangler/bin/wrangler.js d1 execute seti --remote --file ../../tools/deploy/fix-ai-games-unrated.sql
UPDATE games SET rated = 0 WHERE rated = 1 AND id IN (SELECT game_id FROM game_players WHERE user_id LIKE 'bot:%');
UPDATE game_stats SET rated = 0 WHERE rated = 1 AND game_id IN (SELECT game_id FROM game_players WHERE user_id LIKE 'bot:%');
