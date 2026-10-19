// The rules of the site in one page: how the rating works, the clocks, what happens when time runs out, kicks, and how to report a problem.
// The numbers are those of the decision log (docs/PLAN.md: D15, D24 to D28, D34, D36, D37); the code that applies them is named in the plan.
import Link from "next/link";

export const metadata = { title: "Rules of the site" };

export default function Rules() {
  return (
    <>
      <h1>Rules of the site</h1>
      <p className="muted">
        How games are rated and timed here. The rules of SETI itself are those of the official rulebook; this page covers only what the site
        decides.
      </p>

      <section className="card">
        <h2>Rated games</h2>
        <ul>
          <li>A rated game has 2 to 4 players who all have an account. Guests and solo games are never rated.</li>
          <li>Everyone starts at a rating of 0. Ratings use the Elo system.</li>
          <li>
            The change for a game depends on how many rated games you have played: a factor of 60 for your first 10 rated games, 40 for the
            next 10, and 20 after that. So a new player moves fast and an established one slowly.
          </li>
          <li>
            In a game of 3 or 4 players every pair of players is compared (the one with more points beat the other; equal points are a
            draw). Your change is the sum over the other players, so one game never moves your rating by more than the factor above.
          </li>
          <li>A rating never drops below 100, and a player below 100 loses nothing by losing. The player who beat them gains as usual.</li>
          <li>
            A rated game counts however it ends and however short it was: finished, resigned, ended by a clock, or a kick. Resigning or
            running out of time counts as a loss to every other player. A game that an administrator cancels counts for nobody.
          </li>
        </ul>
        <p>
          The ratings are on the <Link href="/leaderboard">leaderboard</Link>.
        </p>
      </section>

      <section className="card">
        <h2>Clocks</h2>
        <ul>
          <li>
            A table can have no clock, a real-time clock (minutes) or a turn-based clock (days). Each has three speeds. The clock is a bank
            of time: you start with the full amount, which is also the most you can hold, and you gain the increment each time you finish a
            turn.
          </li>
          <li>Real time: fast 5 min + 1 min 30 s, normal 7 min 30 s + 2 min 30 s, slow 10 min + 3 min 30 s.</li>
          <li>Turn-based: fast 2 days + 6 h, normal 3 days + 9 h, slow 4 days + 12 h.</li>
          <li>
            There are no emails. To know when it is your turn, keep the tab open (it rings and changes its title) or allow notifications in
            the game settings.
          </li>
        </ul>
      </section>

      <section className="card">
        <h2>When time runs out, and kicks</h2>
        <ul>
          <li>In a game of 1 or 2 players the game ends when a clock runs out, and the player whose time ran out loses.</li>
          <li>
            In a game of 3 or 4 players a clock running out does not end the game. The time of that player goes below zero and any other
            player can kick them.
          </li>
          <li>A kick ends the game at once. All the other players share first place and the kicked player is ranked behind them.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Tables</h2>
        <ul>
          <li>
            The player who creates a table is its host and joins it at once. If the host leaves, the player who joined next becomes the
            host. A table with nobody in it is deleted.
          </li>
          <li>The seats do not decide the play order: who starts and who sits where is drawn when the game begins.</li>
          <li>Every game that started is recorded and can be replayed from its page after it is over.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Accounts</h2>
        <ul>
          <li>An account is a username and a password. There is no email.</li>
          <li>
            When you make an account you get a one-time recovery code. Keep it: it is the way to set a new password if you forget yours.
            Using it gives you a new code.
          </li>
          <li>
            You can change your password and make a new recovery code on your <Link href="/account">account page</Link>.
          </li>
        </ul>
      </section>

      <section className="card">
        <h2>Reporting a problem</h2>
        <p>
          If a game behaves in a way you think is wrong, write down the address of the game (it is in the browser bar) and what you did. The
          log of the game can be copied or downloaded from the log panel. Send both to the contact below.
        </p>
        <p>
          This is an unofficial, fan-made, non-commercial project, not affiliated with Czech Games Edition. Contact:{" "}
          <a href="mailto:seti.web.tobiko11@gmail.com">seti.web.tobiko11@gmail.com</a>.
        </p>
      </section>
    </>
  );
}
