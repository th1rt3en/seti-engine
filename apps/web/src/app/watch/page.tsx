import { getDb } from "@/lib/db";
import { playingGames } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";

/** How long ago a game started, in words. */
function since(ms: number | null): string {
  if (ms === null) return "";
  const minutes = Math.max(0, Math.round((Date.now() - ms) / 60_000));
  if (minutes < 1) return "just started";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
}

export default async function Watch() {
  const games = await playingGames(getDb());
  return (
    <>
      <header className="pagehead">
        <h1>Watch a game</h1>
        <p className="muted">
          Games that are being played now. Anybody can watch; the hands and the decks stay hidden, and spectators cannot act.
        </p>
      </header>
      <section className="open">
        <h2>
          Games in progress <span className="count">{games.length}</span>
        </h2>
        {games.length === 0 ? (
          <p className="card muted empty">
            No game is being played right now. <Link href="/lobby">Start one</Link>.
          </p>
        ) : null}
        <div className="gamelist">
          {games.map((g) => (
            <article className="card game" key={g.id}>
              <div className="gamehead">
                <strong>{g.seats.length > 0 ? g.seats.join(" vs ") : `Game ${g.id.slice(0, 8)}`}</strong>
                <span className="badges">
                  {g.solo ? <span className="pill">solo</span> : <span className="pill">{g.players} players</span>}
                  {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                  {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                  {g.organizations ? <span className="pill exp">organizations</span> : null}
                </span>
              </div>
              <p className="muted small">
                {g.clock} · started {since(g.started_at)}
              </p>
              <div className="actions">
                <Link href={`/games/${g.id}`} className="btn small">
                  Watch
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
