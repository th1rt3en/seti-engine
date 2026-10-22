import { NewGameFields } from "@/components/NewGameFields";
import { PlayerLink, PlayerNames } from "@/components/PlayerLink";
import { SubmitOnce } from "@/components/SubmitOnce";
import { getDb } from "@/lib/db";
import { filterLobby, lobbyGames } from "@/lib/queries";
import { currentUser } from "@/lib/session";
import { CLOCK_PRESETS } from "@/lib/worker";
import Link from "next/link";
import { createGameAction, joinAction } from "../actions";

export const dynamic = "force-dynamic";

export default async function Lobby({
  searchParams,
}: { searchParams: Promise<{ error?: string; players?: string; rated?: string; expansion?: string; mode?: string }> }) {
  const user = await currentUser();
  const { error, ...filter } = await searchParams;
  const all = await lobbyGames(getDb());
  const games = filterLobby(all, filter);
  const filtered = games.length !== all.length;
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
              <SubmitOnce className="primary big" busy="Creating the game...">
                Create the game
              </SubmitOnce>
            </form>
          )}
        </section>
        <section className="open">
          <h2>
            Open games <span className="count">{games.length}</span>
          </h2>
          <form method="get" action="/lobby" className="lobbyfilter" aria-label="Filter the open games">
            <select name="players" defaultValue={filter.players ?? "any"} aria-label="Players">
              <option value="any">Any number of players</option>
              <option value="1">Solo</option>
              <option value="2">2 players</option>
              <option value="3">3 players</option>
              <option value="4">4 players</option>
            </select>
            <select name="rated" defaultValue={filter.rated ?? "any"} aria-label="Rated or casual">
              <option value="any">Rated or casual</option>
              <option value="rated">Rated</option>
              <option value="casual">Casual</option>
            </select>
            <select name="expansion" defaultValue={filter.expansion ?? "any"} aria-label="Expansion">
              <option value="any">With or without the expansion</option>
              <option value="yes">With Space Agencies</option>
              <option value="no">Base game</option>
            </select>
            <select name="mode" defaultValue={filter.mode ?? "any"} aria-label="Time">
              <option value="any">Any clock</option>
              <option value="realtime">Real time</option>
              <option value="turnbased">Turn-based</option>
              <option value="none">No clock</option>
            </select>
            <button type="submit" className="secondary small">
              Filter
            </button>
            {filtered ? (
              <Link href="/lobby" className="small">
                Show all {all.length}
              </Link>
            ) : null}
          </form>
          {games.length === 0 ? (
            <p className="card muted empty">
              {filtered ? "No open game matches this filter." : "No game is waiting for players. Create one and others can join it."}
            </p>
          ) : null}
          <div className="gamelist">
            {games.map((g) => (
              <article className="card game" key={g.id}>
                <div className="gamehead">
                  <strong>
                    <PlayerLink num={g.host.num} name={g.host.name} />
                  </strong>
                  <span className="badges">
                    {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                    {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                    {g.organizations ? <span className="pill exp">organizations</span> : null}
                    {g.promo ? <span className="pill">promo cards</span> : null}
                  </span>
                </div>
                <div className="seats" aria-label={`${g.seats.length} of ${g.players} seats taken`}>
                  {Array.from({ length: g.players }, (_, i) => `${g.id}-${i}`).map((key, i) => (
                    <span key={key} className={i < g.seats.length ? "seat taken" : "seat"} title={g.seats[i]?.name ?? "free seat"}>
                      {g.seats[i]?.name.slice(0, 1).toUpperCase() ?? "+"}
                    </span>
                  ))}
                  <span className="muted small">
                    <PlayerNames seats={g.seats} separator=", " /> · {g.players - g.seats.length} free
                  </span>
                </div>
                <p className="muted small">{g.clock}</p>
                <div className="actions">
                  {user ? (
                    <form action={joinAction}>
                      <input type="hidden" name="id" value={g.id} />
                      <button type="submit" className="primary small">
                        Join
                      </button>
                    </form>
                  ) : null}
                  <Link href={`/games/${g.num ?? g.id}`} className="small">
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
