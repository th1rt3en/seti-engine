// The AI model: its versions and how each one played. The model is trained on the owner's computer (services/ai); only a version that the owner has
// approved is ever served to players. The numbers here come from offline matches of a version against the three training bots on fixed games.
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

export default async function BotsPage() {
  const versions = await botVersions(getDb());
  const live = versions.find((v) => v.live);
  return (
    <>
      <h1>AI</h1>
      <p className="muted">
        A computer player that learns to raise its own score by playing games against itself, for 2 players in the base game to begin with.
        It is trained on the owner&apos;s computer. A new version is only put on the site after the owner has approved it. This page lists
        every version and how it played against three simple training bots (random, greedy and heuristic) on the same games, with the seats
        swapped. Scores are final scores.
      </p>
      <p>
        {live ? (
          <>
            Playing on the site now: <b>{live.version}</b>.
          </>
        ) : (
          <>No version is served to players yet: the versions below only play offline matches.</>
        )}
      </p>
      {versions.length === 0 ? (
        <p>No version has been published yet.</p>
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
        The score is the sum of the board, the end-of-game cards, the gold tiles and the other end scoring. The bots are weak players made
        for training. A version that beats the heuristic bot is a long way from a strong human player.
      </p>
    </>
  );
}
