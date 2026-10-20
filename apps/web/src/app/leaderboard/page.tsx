import { getDb } from "@/lib/db";
import { leaderboard } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Leaderboard({ searchParams }: { searchParams: Promise<{ q?: string; min?: string }> }) {
  const { q = "", min = "0" } = await searchParams;
  const rows = await leaderboard(getDb(), 100, q, Number(min) || 0);
  return (
    <>
      <h1>Leaderboard</h1>
      <nav className="libtabs" aria-label="Leaderboards">
        <Link href="/leaderboard" aria-current="page">
          Rated ranking
        </Link>
        <Link href="/leaderboard/solo">Solo high scores</Link>
      </nav>
      <p className="muted">
        Elo rating from rated games with 2 to 4 players. Everyone starts at 0: a new player gains fast, nobody drops below 100, and a player
        below 100 loses nothing.
      </p>
      <form method="get" action="/leaderboard" className="card" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}>
        <label>
          Find a player
          <input type="search" name="q" defaultValue={q} placeholder="Name" />
        </label>
        <label>
          At least
          <select name="min" defaultValue={min}>
            <option value="0">any number of rated games</option>
            <option value="5">5 rated games</option>
            <option value="10">10 rated games</option>
            <option value="20">20 rated games</option>
          </select>
        </label>
        <button type="submit" className="secondary">
          Show
        </button>
      </form>
      <p className="muted small">A rating does not drop below 100: after that a loss costs nothing.</p>
      {rows.length === 0 ? (
        <p>{q || Number(min) > 0 ? "No player matches." : "No rated game has been played yet."}</p>
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
