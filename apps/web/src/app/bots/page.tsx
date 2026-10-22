// The AI model: its versions and how each one played. The model is trained on the owner's computer (services/ai); only a version that the owner has
// approved is ever served to players. The numbers here come from offline matches of a version against the three training bots on fixed games.
import { type BotRecord, loadBotRecords } from "@/lib/botRecord";
import { getDb } from "@/lib/db";
import { type BotMatch, botVersions } from "@/lib/queries";

export const dynamic = "force-dynamic";
export const metadata = { title: "AI" };

const OPPONENTS: [string, string][] = [
  ["random", "Random bot"],
  ["greedy", "Greedy bot"],
  ["heuristic", "Heuristic bot"],
];
const pct = (x: number): string => `${Math.round(x * 100)}%`;
const day = (iso: string): string => iso.slice(0, 10);

function Match({ m }: { m: BotMatch | undefined }) {
  if (!m) return <td>–</td>;
  return (
    <td>
      <b>{m.agent_score}</b> against {m.bot_score}
      <br />
      <span className="muted small">
        wins {pct(m.win_rate)} · {m.games} games
      </span>
    </td>
  );
}

function PeopleCell({ r }: { r: BotRecord | undefined }) {
  if (!r || r.games === 0) return <td className="muted small">no games yet</td>;
  return (
    <td>
      <b>wins {pct(r.winRate)}</b>
      <br />
      <span className="muted small">
        {r.games} game{r.games === 1 ? "" : "s"} · rating about {r.rating}
        {r.provisional ? " (rough)" : ""}
      </span>
    </td>
  );
}

export default async function BotsPage() {
  // only the versions that have been released (approved by the owner) are listed: the ones that are still being tested show no numbers
  const versions = (await botVersions(getDb())).filter((v) => v.live || v.approved);
  const records = await loadBotRecords(getDb());
  const live = versions.find((v) => v.live);
  return (
    <>
      <h1>AI</h1>
      <p className="muted">
        A computer player that learns to play SETI by playing a very large number of games, and tries to get the highest score it can for
        itself. This page says what it is for, how it is made and how each version played.
      </p>
      <h2>What it is</h2>
      <ul>
        <li>
          <b>Goal:</b> its own final score. It plays to score high, not only to beat the others.
        </li>
        <li>
          <b>First:</b> games of 2 players, in the base game and with the Space Agencies expansion (organizations and quick start cards).
          Games of 3 and 4 players come later, with their own versions.
        </li>
        <li>
          <b>What it knows:</b> only what a player sitting at the table knows. It never sees the cards in your hand or the order of the
          deck. For what it cannot see it knows how many there are, and it remembers the cards that were shown or taken from the display.
        </li>
      </ul>
      <h2>How it is made</h2>
      <ul>
        <li>It learns by playing against itself, against earlier versions of itself and against simple training bots.</li>
        <li>
          A new version is only put on the site after the owner has approved it by hand. The numbers of every released version are public,
          on this page.
        </li>
      </ul>
      <h2>Playing against it</h2>
      <ul>
        <li>
          When the AI can be added to a game, a warning is shown first. Adding it means that you agree that the game is kept and used to
          train future versions.
        </li>
        <li>All the games between the AI and people are kept for that purpose.</li>
      </ul>
      <h2>Versions</h2>
      <p className="muted">
        Every version is listed with how it played against three simple training bots (random, greedy and heuristic) on the same games, with
        the seats swapped. Scores are final scores.
      </p>
      <p>
        {live ? (
          <>
            Playing on the site now: <b>{live.version}</b>.
          </>
        ) : (
          <>No version is served to players yet.</>
        )}
      </p>
      {versions.length === 0 ? (
        <p>No version has been released yet.</p>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Version</th>
                <th>Date</th>
                {OPPONENTS.map(([, label]) => (
                  <th key={label}>Against the {label.toLowerCase()}</th>
                ))}
                <th>Against people</th>
                <th>Trained</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.version}>
                  <td>
                    <b>{v.version}</b>
                    {v.parent ? <span className="muted small"> from {v.parent}</span> : null}
                  </td>
                  <td>{day(v.created)}</td>
                  {OPPONENTS.map(([key]) => (
                    <Match key={key} m={v.evaluation[key]} />
                  ))}
                  <PeopleCell r={records.get(v.version)} />
                  <td className="small">
                    {v.training.iterations
                      ? `${v.training.iterations} rounds of ${v.training.games_per_iteration} games`
                      : "copy of the heuristic bot"}
                    <br />
                    <span className="muted">rules {v.rules_version}</span>
                  </td>
                  <td>
                    {v.live ? (
                      <span className="pill">playing</span>
                    ) : v.approved ? (
                      <span className="pill">approved</span>
                    ) : (
                      <span className="muted">testing</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted small">
        Against people: the share of finished games, with at least one person, in which the version came first (a shared first place counts
        half). The rating is an internal estimate worked out like the players&apos; ratings: it starts at 0, each game moves it against the
        people&apos;s ratings (0 for a person without a rating), it never drops below 100, and below 100 a loss costs nothing. It is rough
        until the version has played 10 games, and it is not on the leaderboard.
      </p>
      <p className="muted small">
        The score is the sum of the board, the end-of-game cards, the gold tiles and the other end scoring. The bots are weak players made
        for training. A version that beats the heuristic bot is a long way from a strong human player.
      </p>
    </>
  );
}
