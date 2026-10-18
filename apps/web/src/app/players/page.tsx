import { getDb } from "@/lib/db";
import { allPlayers } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata = { title: "Players" };

export default async function Players({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const rows = await allPlayers(getDb(), q.trim().slice(0, 40));
  return (
    <>
      <h1>Players</h1>
      <form action="/players" method="get" className="inline">
        <input type="search" name="q" defaultValue={q} placeholder="Find a player" aria-label="Find a player" maxLength={40} />{" "}
        <button type="submit">Search</button>
      </form>
      <p className="muted">
        {rows.length} registered player{rows.length === 1 ? "" : "s"}
        {q ? ` with “${q}” in their name` : ""}. Players who have not played a rated game have the starting rating, 0.
      </p>
      {rows.length === 0 ? (
        <p>No player found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Player</th>
              <th>Rating</th>
              <th>Rated games</th>
              <th>Games</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.user_id}>
                <td>
                  <Link href={`/players/${r.user_id}`}>{r.name}</Link>
                </td>
                <td>{r.rating}</td>
                <td>{r.rated_games}</td>
                <td>{r.games}</td>
                <td>{new Date(r.joined).toISOString().slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
