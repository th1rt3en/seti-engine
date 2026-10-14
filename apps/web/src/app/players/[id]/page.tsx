import { getDb } from "@/lib/db";
import { profile } from "@/lib/queries";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function Player({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = await profile(getDb(), id);
  if (p === null) notFound();
  const data = p as NonNullable<typeof p>;
  return (
    <>
      <h1>{data.user.name}</h1>
      <p className="muted">
        {data.user.is_guest ? "Guest" : "Registered player"}
        {data.rating ? ` · rating ${data.rating.rating} after ${data.rating.games} rated games` : " · no rated game yet"}
      </p>
      <h2>Recent games</h2>
      {data.recent.length === 0 ? <p className="muted">No games yet.</p> : null}
      <table>
        <thead>
          <tr>
            <th>Game</th>
            <th>Players</th>
            <th>Result</th>
            <th>Rated</th>
          </tr>
        </thead>
        <tbody>
          {data.recent.map((g) => {
            const players = (JSON.parse(g.options_json) as { players: number }).players;
            return (
              <tr key={g.id}>
                <td>
                  <Link href={g.status === "finished" ? `/replay/${g.id}` : `/games/${g.id}`}>{g.id.slice(0, 8)}</Link>
                </td>
                <td>{players === 1 ? "solo" : players}</td>
                <td>
                  {g.status === "finished"
                    ? `rank ${g.rank ?? "?"}, ${g.score ?? "?"} points${g.reason && g.reason !== "completed" ? ` (${g.reason})` : ""}`
                    : "in progress"}
                </td>
                <td>{g.rated_counted ? "yes" : "no"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {data.history.length > 0 ? (
        <>
          <h2>Rating history</h2>
          <table>
            <tbody>
              {data.history.map((h) => (
                <tr key={h.game_id}>
                  <td>{new Date(h.at).toLocaleDateString("en-GB")}</td>
                  <td>
                    {h.rating_before} → {h.rating_after} ({h.rating_after >= h.rating_before ? "+" : ""}
                    {h.rating_after - h.rating_before})
                  </td>
                  <td>rank {h.rank}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </>
  );
}
