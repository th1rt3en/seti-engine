import { getDb } from "@/lib/db";
import { lobbyGames } from "@/lib/queries";
import { currentUser } from "@/lib/session";
import { CLOCK_PRESETS } from "@/lib/worker";
import Link from "next/link";
import { createGameAction, joinAction } from "../actions";

export const dynamic = "force-dynamic";

export default async function Lobby({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await currentUser();
  const { error } = await searchParams;
  const games = await lobbyGames(getDb());
  return (
    <>
      <h1>Lobby</h1>
      {error ? <p className="error">{error}</p> : null}
      {user === null ? (
        <p>
          <Link href="/login">Log in</Link> or <Link href="/">play as a guest</Link> to create or join a game.
        </p>
      ) : (
        <section className="card">
          <h2>New game</h2>
          <form action={createGameAction} className="stack">
            <label>
              Players (1 is the solo game against the rival)
              <select name="players" defaultValue="2">
                <option value="1">1 (solo)</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
              </select>
            </label>
            <label>
              Solo difficulty (gold stars)
              <select name="difficulty" defaultValue="3">
                {[1, 2, 3, 4, 5].map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Clock
              <select name="clock" defaultValue="none">
                {Object.entries(CLOCK_PRESETS).map(([k, p]) => (
                  <option key={k} value={k}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="row">
              <input type="checkbox" name="rated" disabled={user.isGuest} /> Rated (2 to 4 players, accounts only)
            </label>
            <label className="row">
              <input type="checkbox" name="promo" /> Include the two promo cards
            </label>
            <button type="submit">Create the game</button>
          </form>
        </section>
      )}
      <h2>Open games</h2>
      {games.length === 0 ? <p className="muted">No game is waiting for players.</p> : null}
      <div className="grid">
        {games.map((g) => (
          <section className="card" key={g.id}>
            <p>
              <strong>{g.host}</strong> {g.rated ? <span className="pill">rated</span> : <span className="pill">casual</span>}
            </p>
            <p className="muted">
              {g.seats.length} of {g.players} players: {g.seats.join(", ")}
              <br />
              {g.clock}
            </p>
            {user ? (
              <form action={joinAction}>
                <input type="hidden" name="id" value={g.id} />
                <button type="submit">Join</button>
              </form>
            ) : null}
            <p className="small">
              <Link href={`/games/${g.id}`}>Watch the lobby</Link>
            </p>
          </section>
        ))}
      </div>
    </>
  );
}
