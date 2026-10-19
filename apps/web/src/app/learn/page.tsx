// A short guide for a first game: how a round and a turn go, in the order the game asks things. It summarises the rulebook (the rule IDs are those of
// docs/spec) and says how this site shows each step; the official rulebook is the source of the rules.
import Link from "next/link";

export const metadata = { title: "How to play" };

export default function Learn() {
  return (
    <>
      <h1>How to play</h1>
      <p className="muted">
        A short guide to a first game of SETI on this site. It is a summary: the official rulebook of the game is the source of every rule.
        The numbers in brackets are the rule numbers of the site's rules reference.
      </p>

      <section className="card">
        <h2>The goal</h2>
        <p>
          You send probes into the solar system, scan the stars, land on planets and learn about alien life. You score points on the way.
          After the fifth round the end-of-game cards and the gold scoring tiles add their points, and the player with the most points wins
          (END-01).
        </p>
      </section>

      <section className="card">
        <h2>Setting up</h2>
        <ul>
          <li>
            Each player draws 5 cards and tucks one of them under their income card: it gives its resource now and every round (SETUP-36).
          </li>
          <li>The game draws who starts. Play goes clockwise (GAME-02).</li>
        </ul>
      </section>

      <section className="card">
        <h2>A turn</h2>
        <p>
          On your turn you take exactly one <b>main action</b> (TURN-01). Free actions can be taken before, during or after it (TURN-02).
          Then you end the turn. A card is used for only one of its benefits: played for its effect, or discarded for its corner (TURN-03).
        </p>
        <h3>The main actions</h3>
        <ul>
          <li>
            <b>Launch a probe</b> for 2 credits: it appears on Earth. You can have 1 probe in space unless a tech says more (LAUNCH-01,
            LAUNCH-02).
          </li>
          <li>
            <b>Orbit</b> a planet for 1 credit and 1 energy, with a probe that stands on it. The first orbiter scores 3 more points
            (ORBIT-01, ORBIT-04).
          </li>
          <li>
            <b>Land</b> on a planet for 3 energy (2 if someone already orbits it) with a probe that stands on it (LAND-01).
          </li>
          <li>
            <b>Scan</b> for 1 credit and 2 energy: the steps go from left to right on the page, and the context bar says which step you are
            at. Every scan marks at least 2 signals (SCAN-01, SCAN-05).
          </li>
          <li>
            <b>Analyze data</b> for 1 energy when the top row of your computer is full: you mark a blue life trace (ANALYZE-01).
          </li>
          <li>
            <b>Research a tech</b> for 6 publicity: the solar system turns first (TECHACT-01).
          </li>
          <li>
            <b>Play a card</b> for its effect, paying its cost.
          </li>
          <li>
            <b>Pass</b> for the rest of the round (see below).
          </li>
        </ul>
        <h3>The free actions</h3>
        <ul>
          <li>Spend 1 energy for 1 movement, then click a highlighted space for a probe (FREE-01).</li>
          <li>Discard a card for the action in its top-left corner (FREE-02).</li>
          <li>Place data from your pool in your computer (FREE-03).</li>
          <li>Trade resources, or buy a card for 3 publicity (FREE-05, FREE-06).</li>
          <li>Complete a mission when its condition is met (FREE-07).</li>
        </ul>
        <p className="small">
          On this site you click a highlighted place on the board, a card, or a button in the bar. The bar above the board always says what
          the game is waiting for, and the <b>?</b> next to it explains it.
        </p>
      </section>

      <section className="card">
        <h2>Passing and the end of a round</h2>
        <ol>
          <li>You may take free actions on the turn you pass.</li>
          <li>Discard down to 4 cards (PASS-02).</li>
          <li>The first player to pass in a round turns the solar system (PASS-03).</li>
          <li>Take one of the end-of-round cards into your hand (PASS-04). There are none in round 5 (PASS-05).</li>
        </ol>
        <p>
          When everyone has passed, everyone gets their income, the starting player moves on and the next round begins (ROUND-01, ROUND-02).
          After round 5 the game ends and no income is paid (ROUND-03).
        </p>
      </section>

      <section className="card">
        <h2>Points, milestones and aliens</h2>
        <ul>
          <li>
            Milestones at 25, 50 and 70 points let you mark a gold scoring tile; at 20 and 30 the nonplayer groups learn about the aliens
            (MILE-02, MILE-05).
          </li>
          <li>Milestones are resolved at the end of the turn in which you reach them (MILE-01).</li>
          <li>
            Life traces fill the three discovery spaces of an alien species; when they are full the species is revealed and its board opens.
          </li>
          <li>With few players the nonplayer markers help to discover the species. In a solo game a rival plays with you.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Good to know on this site</h2>
        <ul>
          <li>
            Take a move back with <b>Undo</b> or the key <kbd>U</kbd> while it can be taken back; a move that shows something hidden asks
            first.
          </li>
          <li>The log can be filtered, searched and copied; the yellow outline on the board shows where the last move happened.</li>
          <li>
            The <Link href="/rules">rules of the site</Link> explain ratings and clocks. The Sandbox in a solo game lets you try things
            freely.
          </li>
        </ul>
      </section>
    </>
  );
}
