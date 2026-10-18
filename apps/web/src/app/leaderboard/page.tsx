import { getDb } from "@/lib/db";
import { leaderboard } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Leaderboard() {
  const rows = await leaderboard(getDb());
  return (
    <>
      <h1>Leaderboard</h1>
      <p className="muted">
        Elo rating from rated games with 2 to 4 players. Everyone starts at 0: a new player gains fast, nobody drops below 100, and a player
        below 100 loses nothing.
      </p>
      {rows.length === 0 ? (
        <p>No rated game has been played yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Rating</th>
              <th>Games</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.user_id}>
                <td>{i + 1}</td>
                <td>
                  <Link href={`/players/${r.user_id}`}>{r.name}</Link>
                </td>
                <td>{r.rating}</td>
                <td>{r.games}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
