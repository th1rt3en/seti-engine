import { Pager } from "@/components/Pager";
import { RatingChart } from "@/components/RatingChart";
import { getDb } from "@/lib/db";
import { resolveUser } from "@/lib/ids";
import { profile } from "@/lib/queries";
import { currentUser } from "@/lib/session";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { resignSoloAction } from "../../actions";

export const dynamic = "force-dynamic";

const START_RATING = 0;

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="stat">
      <span className="statvalue">{value}</span>
      <span className="statlabel">{label}</span>
      {note ? <span className="statnote">{note}</span> : null}
    </div>
  );
}

export default async function Player({
  params,
  searchParams,
}: { params: Promise<{ id: string }>; searchParams: Promise<{ page?: string }> }) {
  const { id: param } = await params;
  const { page } = await searchParams;
  // the address is the number of the player; the uuid (an address from before the numbers) goes to it
  const resolved = await resolveUser(getDb(), param);
  if (resolved === null) notFound();
  const found = resolved as NonNullable<typeof resolved>;
  if (found.redirect !== null) permanentRedirect(`/players/${found.redirect}`);
  const id = found.id;
  const p = await profile(getDb(), id, Number.parseInt(page ?? "1", 10));
  if (p === null) notFound();
  const data = p as NonNullable<typeof p>;
  const viewer = await currentUser();
  const own = viewer !== null && viewer.id === id; // the owner of the profile can resign their solo games from it
  const { stats } = data;
  const last = data.history[0];
  const change = last ? last.rating_after - last.rating_before : null;
  // history is newest first; the chart reads oldest to newest and starts at the rating before the first game
  const oldest = data.history[data.history.length - 1];
  const points = oldest ? [oldest.rating_before, ...[...data.history].reverse().map((h) => h.rating_after)] : [];
  const buckets = ["solo", "2", "3", "4"].filter((k) => stats.byPlayers[k]);
  return (
    <>
      <header className="profilehead">
        <span className="avatar" aria-hidden="true">
          {data.user.name.slice(0, 1).toUpperCase()}
        </span>
        <div>
          <h1>{data.user.name}</h1>
          <p className="muted">
            {data.user.is_guest ? "Guest" : "Registered player"} · member since {new Date(data.user.created_at).toLocaleDateString("en-GB")}
          </p>
        </div>
      </header>

      <section className="statgrid">
        <Stat
          label="Current rating"
          value={data.rating ? String(data.rating.rating) : String(START_RATING)}
          note={data.rating ? `peak ${data.peak}` : "no rated game yet"}
        />
        <Stat
          label="Last rated game"
          value={change === null ? "—" : `${change >= 0 ? "+" : ""}${change}`}
          note={last ? `rank ${last.rank}` : undefined}
        />
        <Stat
          label="Win rate"
          value={stats.winRate === null ? "—" : `${stats.winRate}%`}
          note={`${stats.wins} won of ${stats.games} played`}
        />
        <Stat
          label="Rated wins"
          value={stats.ratedGames === 0 ? "—" : `${stats.ratedWins}/${stats.ratedGames}`}
          note={stats.ratedGames === 0 ? undefined : `${Math.round((stats.ratedWins / stats.ratedGames) * 100)}% of rated games`}
        />
        <Stat
          label="Average score"
          value={stats.avgScore === null ? "—" : String(stats.avgScore)}
          note={stats.bestScore === null ? undefined : `best ${stats.bestScore}`}
        />
        {stats.expansionGames > 0 ? <Stat label="Space Agencies games" value={String(stats.expansionGames)} /> : null}
      </section>

      {points.length >= 2 ? (
        <section className="card">
          <h2>Rating over time</h2>
          <RatingChart points={points} />
        </section>
      ) : null}

      {buckets.length > 0 ? (
        <section className="card">
          <h2>By table size</h2>
          <div className="bars">
            {buckets.map((k) => {
              const b = stats.byPlayers[k] as NonNullable<(typeof stats.byPlayers)[string]>;
              const pct = Math.round((b.wins / b.games) * 100);
              return (
                <div className="barrow" key={k}>
                  <span className="barlabel">{k === "solo" ? "Solo" : `${k} players`}</span>
                  <span className="bartrack">
                    <span className="barfill" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="barvalue">
                    {b.wins}/{b.games} · {pct}%
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {stats.expansionGames > 0 ? (
        <section className="card">
          <h2>With or without the expansion</h2>
          <div className="bars">
            {(["without", "with"] as const).map((k) => {
              const b = stats.byExpansion[k];
              if (!b) return null;
              const pct = Math.round((b.wins / b.games) * 100);
              return (
                <div className="barrow" key={k}>
                  <span className="barlabel">{k === "with" ? "Space Agencies" : "Base game"}</span>
                  <span className="bartrack">
                    <span className="barfill" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="barvalue">
                    {b.wins}/{b.games} · {pct}%
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <h2>Game history</h2>
      {data.recent.length === 0 ? <p className="muted">No games yet.</p> : null}
      {data.recent.length > 0 ? (
        <table className="history">
          <thead>
            <tr>
              <th>Game</th>
              <th>Table</th>
              <th>Result</th>
              <th>Score</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            {data.recent.map((g) => {
              const o = JSON.parse(g.options_json) as { players: number; expansion?: boolean; sandbox?: boolean };
              const h = data.pageRatings.find((x) => x.game_id === g.id);
              return (
                <tr key={g.id}>
                  <td>
                    <Link href={g.status === "finished" ? `/replay/${g.num ?? g.id}` : `/games/${g.num ?? g.id}`}>
                      #{g.num ?? g.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>
                    {o.sandbox ? "sandbox" : o.players === 1 ? "solo" : `${o.players} players`}
                    {o.expansion ? <span className="pill exp">Space Agencies</span> : null}
                    {g.rated_counted ? <span className="pill rated">rated</span> : null}
                  </td>
                  <td>
                    {g.status !== "finished" ? (
                      <>
                        in progress
                        {own && o.players === 1 ? (
                          <form action={resignSoloAction} className="inline">
                            <input type="hidden" name="id" value={g.id} />
                            <button type="submit" className="secondary small" title="End this solo game now (it counts as resigned)">
                              Resign
                            </button>
                          </form>
                        ) : null}
                      </>
                    ) : (
                      <>
                        {g.rank === 1 ? <span className="pill win">won</span> : <span className="pill">rank {g.rank ?? "?"}</span>}
                        {g.reason && g.reason !== "completed" ? <span className="muted small"> ({g.reason})</span> : null}
                      </>
                    )}
                  </td>
                  <td>{g.score ?? "—"}</td>
                  <td>
                    {h ? (
                      <span className={h.rating_after >= h.rating_before ? "up" : "down"}>
                        {h.rating_after} ({h.rating_after >= h.rating_before ? "+" : ""}
                        {h.rating_after - h.rating_before})
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
      <Pager page={data.page} pages={data.pages} link={(n) => (n > 1 ? `/players/${param}?page=${n}` : `/players/${param}`)} />
    </>
  );
}
