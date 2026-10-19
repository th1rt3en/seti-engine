import { TurnstileWidget } from "@/components/TurnstileWidget";
import { getDb } from "@/lib/db";
import { leaderboard, lobbyGames } from "@/lib/queries";
import { currentUser } from "@/lib/session";
import Link from "next/link";
import { guestAction } from "./actions";

export const dynamic = "force-dynamic";

const FEATURES = [
  {
    icon: "🛰️",
    title: "The full base game",
    text: "Probes, scans, sectors, tech, missions and all five alien species, played by the official rules.",
  },
  {
    icon: "🏆",
    title: "Rated play",
    text: "An Elo rating for games of two to four players, a leaderboard and a profile with your history.",
  },
  {
    icon: "⏱️",
    title: "Your pace",
    text: "Real-time tables with a clock or turn-based games over days. Undo any move that shows nothing hidden.",
  },
  {
    icon: "🤖",
    title: "Solo and sandbox",
    text: "Test yourself against the rival at five difficulty levels, or practise freely in the sandbox.",
  },
  {
    icon: "🌌",
    title: "Space Agencies",
    text: "Organizations with their own powers and incomes, quick start cards and signal tokens from the expansion.",
  },
  { icon: "🎞️", title: "Replays", text: "Every game is archived and can be replayed move by move, with the log beside the board." },
];

export default async function Home() {
  const user = await currentUser();
  const [open, top] = await Promise.all([lobbyGames(getDb(), 3), leaderboard(getDb(), 5)]);
  return (
    <>
      <section className="hero">
        <p className="eyebrow">Search for Extraterrestrial Intelligence</p>
        <h1>SETI online</h1>
        <p className="lead">
          A fan-made, non-commercial version of the board game SETI for one to four players. Launch probes, scan the sky, and be the first
          to find life.
        </p>
        <p className="cta">
          {user ? (
            <>
              <Link className="btn primary big" href="/lobby">
                Go to the lobby
              </Link>
              <Link className="btn big ghost" href={`/players/${user.id}`}>
                Your profile
              </Link>
            </>
          ) : (
            <>
              <Link className="btn primary big" href="/signup">
                Sign up to play rated
              </Link>
              <Link className="btn big ghost" href="/login">
                Log in
              </Link>
            </>
          )}
        </p>
        <ul className="stats">
          <li>
            <b>{open.length === 0 ? "No" : open.length}</b> open {open.length === 1 ? "game" : "games"}
          </li>
          <li>
            <b>{top.length === 0 ? "—" : (top[0] as NonNullable<(typeof top)[0]>).rating}</b> top rating
          </li>
        </ul>
      </section>

      {user ? null : (
        <section className="card guest">
          <div>
            <h2>Just want to try it?</h2>
            <p className="muted">
              Pick a name and start. Guests cannot play rated games, but you can create an account later and keep your games.
            </p>
          </div>
          <form action={guestAction} className="stack">
            <label>
              Name (optional)
              <input name="name" maxLength={32} placeholder="Guest" />
            </label>
            <TurnstileWidget />
            <button type="submit" className="primary">
              Play as a guest
            </button>
          </form>
        </section>
      )}

      <section className="features">
        {FEATURES.map((f) => (
          <article className="feature" key={f.title}>
            <span className="ficon" aria-hidden="true">
              {f.icon}
            </span>
            <h3>{f.title}</h3>
            <p className="muted">{f.text}</p>
          </article>
        ))}
      </section>

      <div className="grid two">
        <section className="card">
          <h2>Waiting for players</h2>
          {open.length === 0 ? (
            <p className="muted">
              No game is open right now. <Link href="/lobby">Start one</Link>.
            </p>
          ) : (
            <ul className="plain">
              {open.map((g) => (
                <li key={g.id}>
                  <Link href={`/games/${g.id}`}>{g.host}</Link>{" "}
                  <span className="muted">
                    {g.seats.length}/{g.players} · {g.clock}
                  </span>{" "}
                  {g.rated ? <span className="pill rated">rated</span> : null}
                  {g.expansion ? <span className="pill exp">Space Agencies</span> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card">
          <h2>Top players</h2>
          {top.length === 0 ? (
            <p className="muted">No rated game has been played yet.</p>
          ) : (
            <ol className="plain ranked">
              {top.map((r) => (
                <li key={r.user_id}>
                  <Link href={`/players/${r.user_id}`}>{r.name}</Link> <b>{r.rating}</b>
                </li>
              ))}
            </ol>
          )}
          <p className="small">
            <Link href="/leaderboard">Full leaderboard</Link>
          </p>
        </section>
      </div>
    </>
  );
}
