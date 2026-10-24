import { Pager } from "@/components/Pager";
import { PlayerLink, PlayerNames } from "@/components/PlayerLink";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import { countEndedGames, countPlayingGames, endedGames, playingGames } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 10;
const ROUNDS = 5;

/** Where a game in progress stands (the Worker tells the round, the turn and the points that everybody can see); null when it does not answer in time. */
interface Progress {
  round: number;
  turn: number;
  scores: number[];
  rival?: number;
  actions: number;
}
async function progressOf(id: string): Promise<Progress | null> {
  try {
    const res = await fetch(`${loadConfig().workerUrl}/games/${id}`, { signal: AbortSignal.timeout(2500), cache: "no-store" });
    if (!res.ok) return null;
    return ((await res.json()) as { progress?: Progress } | null)?.progress ?? null;
  } catch {
    return null;
  }
}

/** How long ago a game started, in words. */
function since(ms: number | null): string {
  if (ms === null) return "";
  const minutes = Math.max(0, Math.round((Date.now() - ms) / 60_000));
  if (minutes < 1) return "just started";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
}

const pageOf = (value: string | undefined): number => {
  const n = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(n) && n >= 1 ? n : 1;
};

/** The link to a page of one section; the page of the other section is kept. */
const href = (playing: number, ended: number): string => {
  const q = new URLSearchParams();
  if (playing > 1) q.set("playing", String(playing));
  if (ended > 1) q.set("ended", String(ended));
  const text = q.toString();
  return text ? `/watch?${text}` : "/watch";
};

/** How a finished game ended, in words. */
function endText(reason: string, forfeit: string | null): string | null {
  if (reason === "completed") return null;
  if (reason === "resigned") return forfeit ? `${forfeit} resigned` : "resigned";
  if (reason === "timeout") return forfeit ? `${forfeit} ran out of time` : "out of time";
  if (reason === "kicked") return forfeit ? `${forfeit} was removed for being out of time` : "a player was removed";
  return reason;
}

export default async function Watch({ searchParams }: { searchParams: Promise<{ playing?: string; ended?: string }> }) {
  const q = await searchParams;
  const db = getDb();
  const [playingTotal, endedTotal] = await Promise.all([countPlayingGames(db), countEndedGames(db)]);
  const playingPages = Math.max(1, Math.ceil(playingTotal / PAGE_SIZE));
  const endedPages = Math.max(1, Math.ceil(endedTotal / PAGE_SIZE));
  const playingPage = Math.min(pageOf(q.playing), playingPages);
  const endedPage = Math.min(pageOf(q.ended), endedPages);
  const [games, over] = await Promise.all([
    playingGames(db, PAGE_SIZE, (playingPage - 1) * PAGE_SIZE),
    endedGames(db, PAGE_SIZE, (endedPage - 1) * PAGE_SIZE),
  ]);
  const standing = await Promise.all(games.map((g) => progressOf(g.id)));
  return (
    <div className="watchpage">
      <header className="pagehead">
        <h1>Watch a game</h1>
        <p className="muted">
          Games that are being played now, and the games that are over. Anybody can watch; the hands and the decks stay hidden, and
          spectators cannot act.
        </p>
      </header>
      <section className="open">
        <h2>
          Games in progress <span className="count">{playingTotal}</span>
        </h2>
        {games.length === 0 ? (
          <p className="card muted empty">
            No game is being played right now. <Link href="/lobby">Start one</Link>.
          </p>
        ) : null}
        <div className="gamelist">
          {games.map((g, k) => {
            const pr = standing[k] ?? null;
            return (
              <article className="card game" key={g.id}>
                <div className="gamehead">
                  <strong>{g.seats.length > 0 ? <PlayerNames seats={g.seats} /> : `Game ${g.num ?? g.id.slice(0, 8)}`}</strong>
                  <span className="badges">
                    {g.solo ? <span className="pill">solo</span> : <span className="pill">{g.players} players</span>}
                    {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                    {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                    {g.organizations ? <span className="pill exp">organizations</span> : null}
                  </span>
                </div>
                {pr ? (
                  <div className="gamestatus">
                    <span className="round">
                      Round {Math.min(pr.round, ROUNDS)} of {ROUNDS}
                    </span>
                    <span className="muted small">turn {pr.turn}</span>
                    <span className="scorelist">
                      {g.seats.map((x, i) => (
                        <span key={`${g.id}-${x.name}-${i}`}>
                          {x.name} (<b>{pr.scores[i] ?? 0}</b>)
                        </span>
                      ))}
                      {pr.rival !== undefined ? (
                        <span>
                          rival (<b>{pr.rival}</b>)
                        </span>
                      ) : null}
                    </span>
                  </div>
                ) : null}
                <p className="muted small">
                  {g.clock} · started {since(g.started_at)}
                  {pr ? ` · ${pr.actions} moves` : ""}
                </p>
                <div className="actions">
                  <Link href={`/games/${g.num ?? g.id}`} className="btn small">
                    Watch
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
        <Pager page={playingPage} pages={playingPages} link={(p) => href(p, endedPage)} />
      </section>
      <section className="open">
        <h2>
          Completed games <span className="count">{endedTotal}</span>
        </h2>
        {over.length === 0 ? <p className="card muted empty">No game is over yet.</p> : null}
        <div className="gamelist">
          {over.map((g) => {
            const note = endText(g.reason, g.forfeit);
            const ranked = g.seats.some((x) => x.rank !== null);
            return (
              <article className="card game" key={g.id}>
                <div className="gamehead">
                  <strong>
                    {g.seats.length > 0
                      ? g.seats.map((x, i) => (
                          <span key={`${g.id}-${x.name}-${i}`}>
                            {i > 0 ? " vs " : ""}
                            <PlayerLink num={x.num} name={x.name} />
                            {ranked && x.rank === 1 ? " 🏆" : ""}
                            {x.score !== null ? ` (${x.score})` : ""}
                          </span>
                        ))
                      : `Game ${g.num ?? g.id.slice(0, 8)}`}
                  </strong>
                  <span className="badges">
                    {g.solo ? <span className="pill">solo</span> : <span className="pill">{g.players} players</span>}
                    {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                    {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                    {g.organizations ? <span className="pill exp">organizations</span> : null}
                    {note ? <span className="pill">{note}</span> : null}
                  </span>
                </div>
                <p className="muted small">ended {since(g.ended_at).replace("just started", "just now")}</p>
                <div className="actions">
                  <Link href={`/replay/${g.num ?? g.id}`} className="btn small">
                    Replay
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
        <Pager page={endedPage} pages={endedPages} link={(p) => href(playingPage, p)} />
      </section>
    </div>
  );
}
