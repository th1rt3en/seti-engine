import { Pager } from "@/components/Pager";
import { PlayerLink } from "@/components/PlayerLink";
import { getDb } from "@/lib/db";
import { LEADERBOARD_PAGE_SIZE, pageOf, soloCount, soloScores } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata = { title: "Solo high scores" };

const date = (ms: number): string => (ms > 0 ? new Date(ms).toISOString().slice(0, 10) : "");

export default async function SoloLeaderboard({
  searchParams,
}: { searchParams: Promise<{ difficulty?: string; expansion?: string; page?: string }> }) {
  const sp = await searchParams;
  const d = Number(sp.difficulty);
  const difficulty = Number.isInteger(d) && d >= 1 && d <= 5 ? d : null;
  const expansion = sp.expansion === "yes" ? true : sp.expansion === "no" ? false : null;
  const filter = { difficulty, expansion };
  const { page, pages, offset } = pageOf(await soloCount(getDb(), filter), sp.page, LEADERBOARD_PAGE_SIZE);
  const rows = await soloScores(getDb(), filter, LEADERBOARD_PAGE_SIZE, offset);
  const link = (n: number): string => {
    const params = new URLSearchParams({
      ...(difficulty !== null ? { difficulty: String(difficulty) } : {}),
      ...(expansion !== null ? { expansion: expansion ? "yes" : "no" } : {}),
      ...(n > 1 ? { page: String(n) } : {}),
    }).toString();
    return params ? `/leaderboard/solo?${params}` : "/leaderboard/solo";
  };
  return (
    <>
      <h1>Solo high scores</h1>
      <nav className="libtabs" aria-label="Leaderboards">
        <Link href="/leaderboard">Rated ranking</Link>
        <Link href="/leaderboard/solo" aria-current="page">
          Solo high scores
        </Link>
      </nav>
      <p className="muted">The best final scores of solo games that were played to their end. Sandbox games do not count.</p>
      <form
        method="get"
        action="/leaderboard/solo"
        className="card"
        style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}
      >
        <label>
          Rival difficulty
          <select name="difficulty" defaultValue={difficulty === null ? "" : String(difficulty)}>
            <option value="">any</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} gold star{n === 1 ? "" : "s"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Space Agencies expansion
          <select name="expansion" defaultValue={expansion === null ? "" : expansion ? "yes" : "no"}>
            <option value="">with or without</option>
            <option value="yes">with</option>
            <option value="no">without</option>
          </select>
        </label>
        <button type="submit" className="primary">
          Show
        </button>
      </form>
      {rows.length === 0 ? (
        <p>No solo game matches yet.</p>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Player</th>
                <th>Score</th>
                <th>Rival</th>
                <th>Difficulty</th>
                <th>Expansion</th>
                <th>Date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.game_id}>
                  <td>{offset + i + 1}</td>
                  <td>{r.registered ? <PlayerLink num={r.user_num} name={r.name} /> : r.name}</td>
                  <td>
                    <b>{r.score}</b>
                  </td>
                  <td>
                    {r.rival === null ? "–" : r.rival} {r.rival !== null && r.score > r.rival ? <span className="pill">beaten</span> : null}
                  </td>
                  <td>{"★".repeat(r.difficulty)}</td>
                  <td>{r.expansion ? "yes" : "no"}</td>
                  <td>{date(r.ended_at)}</td>
                  <td>
                    <Link href={`/replay/${r.num ?? r.game_id}`}>replay</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager page={page} pages={pages} link={link} labels={["← Higher", "Lower →"]} />
    </>
  );
}
