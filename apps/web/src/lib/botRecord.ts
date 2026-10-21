// How each version of the AI model did against people: the games finished with an AI seat and at least one person. The win rate and an internal rating
// (an Elo estimate, not a ranking on the leaderboard) are made from those games alone.
import type { Db } from "./db";

export interface BotRecord {
  /** Games finished against at least one person. */
  games: number;
  /** First places; a shared first place counts as half. */
  wins: number;
  winRate: number;
  /** Internal Elo estimate: starts at 0 like the players' ratings, moved by each game against the people's ratings (0 for a person without one). */
  rating: number;
  /** Fewer than 10 games: the estimate is rough. */
  provisional: boolean;
}

export interface GameRow {
  game_id: string;
  user_id: string;
  rank: number | null;
}

const START = 0;
const expected = (ra: number, rb: number): number => 1 / (1 + 10 ** ((rb - ra) / 400));
/** The same K as the players' ratings (docs/PLAN.md, D37): 60 for the first 10 games, 40 for the next 10, then 20. */
const kFor = (games: number): number => (games < 10 ? 60 : games < 20 ? 40 : 20);

export const isBot = (userId: string): boolean => userId.startsWith("bot:");
/** The version in an AI seat's id (`bot:<version>:<n>`). */
export const versionOf = (userId: string): string => userId.split(":")[1] ?? "";

/**
 * The record of each version. `rows` are the players of finished games in the order the games ended (the players of a game together); `ratings` are the
 * people's current ratings by user id.
 */
export function botRecords(rows: GameRow[], ratings: Map<string, number>): Map<string, BotRecord> {
  const byGame = new Map<string, GameRow[]>();
  for (const r of rows) byGame.set(r.game_id, [...(byGame.get(r.game_id) ?? []), r]);
  const state = new Map<string, { games: number; wins: number; rating: number }>();
  for (const players of byGame.values()) {
    const people = players.filter((p) => !isBot(p.user_id));
    if (people.length === 0 || players.some((p) => p.rank === null)) continue;
    for (const bot of players.filter((p) => isBot(p.user_id))) {
      const v = versionOf(bot.user_id);
      const s = state.get(v) ?? { games: 0, wins: 0, rating: START };
      const rank = bot.rank as number;
      const best = Math.min(...players.map((p) => p.rank as number));
      s.wins += rank === best ? (players.filter((p) => p.rank === best).length > 1 ? 0.5 : 1) : 0;
      let delta = 0;
      for (const h of people) {
        const actual = rank < (h.rank as number) ? 1 : rank === h.rank ? 0.5 : 0;
        delta += (kFor(s.games) / people.length) * (actual - expected(s.rating, ratings.get(h.user_id) ?? START));
      }
      s.rating += delta;
      s.games += 1;
      state.set(v, s);
    }
  }
  return new Map(
    [...state].map(([v, s]) => [
      v,
      {
        games: s.games,
        wins: s.wins,
        winRate: s.games > 0 ? s.wins / s.games : 0,
        rating: Math.round(s.rating),
        provisional: s.games < 10,
      },
    ]),
  );
}

export async function loadBotRecords(db: Db): Promise<Map<string, BotRecord>> {
  const rows = await db.all<GameRow>(
    `SELECT g.id AS game_id, p.user_id AS user_id, p.rank AS rank
       FROM games g JOIN game_players p ON p.game_id = g.id
      WHERE g.status = 'finished' AND g.reason = 'completed'
        AND g.id IN (SELECT game_id FROM game_players WHERE user_id LIKE 'bot:%')
      ORDER BY g.ended_at, g.id, p.seat`,
  );
  const ratings = new Map(
    (await db.all<{ user_id: string; rating: number }>("SELECT user_id, rating FROM ratings")).map((r) => [r.user_id, r.rating]),
  );
  return botRecords(rows, ratings);
}

/** The line shown beside a version: "wins 40% of 5 games against people, rating about 85". */
export function describeRecord(r: BotRecord | undefined): string {
  if (!r || r.games === 0) return "no games against people yet";
  return `wins ${Math.round(r.winRate * 100)}% of ${r.games} game${r.games === 1 ? "" : "s"} against people · rating about ${r.rating}${r.provisional ? " (rough)" : ""}`;
}
