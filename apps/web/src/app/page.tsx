import { TurnstileWidget } from "@/components/TurnstileWidget";
import { currentUser } from "@/lib/session";
import Link from "next/link";
import { guestAction } from "./actions";

export default async function Home() {
  const user = await currentUser();
  return (
    <>
      <h1>SETI, online</h1>
      <p>
        A fan-made, non-commercial version of the board game SETI for one to four players. Play a rated game against other players, play for
        fun, or test yourself against the rival in solo mode. Games run in real time or by turns.
      </p>
      {user ? (
        <p>
          <Link className="btn" href="/lobby">
            Go to the lobby
          </Link>
        </p>
      ) : (
        <div className="grid">
          <section className="card">
            <h2>Play without an account</h2>
            <p className="muted">
              Pick a name and start. Guests cannot play rated games, but you can create an account later and keep your games.
            </p>
            <form action={guestAction} className="stack">
              <label>
                Name (optional)
                <input name="name" maxLength={32} placeholder="Guest" />
              </label>
              <TurnstileWidget />
              <button type="submit">Play as a guest</button>
            </form>
          </section>
          <section className="card">
            <h2>Rated games</h2>
            <p className="muted">Rated games for 2 to 4 players use an Elo rating (K = 20). You need an account.</p>
            <p>
              <Link className="btn" href="/signup">
                Sign up
              </Link>{" "}
              <Link href="/login">or log in</Link>
            </p>
          </section>
        </div>
      )}
    </>
  );
}
