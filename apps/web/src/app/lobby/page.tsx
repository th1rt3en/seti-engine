import { NewGameFields } from "@/components/NewGameFields";
import { SubmitOnce } from "@/components/SubmitOnce";
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
      <header className="pagehead">
        <h1>Lobby</h1>
        <p className="muted">Join a game that is waiting for players, or start your own.</p>
      </header>
      {error ? <p className="error banner">{error}</p> : null}
      <div className="lobby">
        <section className="card newgame">
          <h2>New game</h2>
          {user === null ? (
            <p>
              <Link href="/login">Log in</Link> or <Link href="/">play as a guest</Link> to create or join a game.
            </p>
          ) : (
            <form action={createGameAction} className="stack">
              <NewGameFields
                isGuest={user.isGuest}
                clocks={Object.entries(CLOCK_PRESETS).map(([key, p]) => ({ key, label: p.label, mode: p.mode }))}
              />
              <SubmitOnce className="big" busy="Creating the game...">
                Create the game
              </SubmitOnce>
            </form>
          )}
        </section>
        <section className="open">
          <h2>
            Open games <span className="count">{games.length}</span>
          </h2>
          {games.length === 0 ? (
            <p className="card muted empty">No game is waiting for players. Create one and others can join it.</p>
          ) : null}
          <div className="gamelist">
            {games.map((g) => (
              <article className="card game" key={g.id}>
                <div className="gamehead">
                  <strong>{g.host}</strong>
                  <span className="badges">
                    {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                    {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                    {g.organizations ? <span className="pill exp">organizations</span> : null}
                    {g.promo ? <span className="pill">promo cards</span> : null}
                  </span>
                </div>
                <div className="seats" aria-label={`${g.seats.length} of ${g.players} seats taken`}>
                  {Array.from({ length: g.players }, (_, i) => `${g.id}-${i}`).map((key, i) => (
                    <span key={key} className={i < g.seats.length ? "seat taken" : "seat"} title={g.seats[i] ?? "free seat"}>
                      {g.seats[i]?.slice(0, 1).toUpperCase() ?? "+"}
                    </span>
                  ))}
                  <span className="muted small">
                    {g.seats.join(", ")} · {g.players - g.seats.length} free
                  </span>
                </div>
                <p className="muted small">{g.clock}</p>
                <div className="actions">
                  {user ? (
                    <form action={joinAction}>
                      <input type="hidden" name="id" value={g.id} />
                      <button type="submit">Join</button>
                    </form>
                  ) : null}
                  <Link href={`/games/${g.id}`} className="small">
                    Open the table
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
